from io import BytesIO
import os
import sys

from flask import request, render_template, current_app, url_for
from flask.views import View

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound

import dulwich.objects
import dulwich.archive
import dulwich.config
from dulwich.object_store import tree_lookup_path

try:
    import ctags
except ImportError:
    ctags = None
else:
    from klaus import ctagscache

    CTAGS_CACHE = ctagscache.CTagsCache()

from klaus import markup
from klaus.highlighting import highlight_or_render
from klaus.utils import (
    parent_directory,
    subpaths,
    force_unicode,
    guess_is_binary,
    guess_is_image,
    replace_dupes,
    sanitize_branch_name,
    encode_for_git,
)


README_FILENAMES = [
    b"README",
    b"README.md",
    b"README.mkdn",
    b"README.mdwn",
    b"README.markdown",
    b"README.rst",
]


def repo_list():
    """Show a list of all repos. Can be sorted by last update and repo names can be searched."""
    repos = [repo.freeze() for repo in current_app.valid_repos.values()]
    invalid_repos = current_app.invalid_repos.values()

    order_by = request.args.get("order_by") or "last_updated"
    search_query = request.args.get("q") or ""

    if search_query:
        repos = [r for r in repos if search_query.lower() in r.namespaced_name.lower()]
        invalid_repos = [
            r
            for r in invalid_repos
            if search_query.lower() in r.namespaced_name.lower()
        ]

    if order_by == "name":
        sort_key = lambda repo: repo.namespaced_name
    else:
        sort_key = lambda repo: (
            -(repo.fast_get_last_updated_at() or -1),
            repo.namespaced_name,
        )

    repos = sorted(repos, key=sort_key)
    invalid_repos = sorted(invalid_repos, key=lambda repo: repo.namespaced_name)

    return render_template(
        "repo_list.html",
        repos=repos,
        invalid_repos=invalid_repos,
        order_by=order_by,
        search_query=search_query,
        base_href=None,
    )


def robots_txt():
    """Serve the robots.txt file to manage the indexing of the site by search engines."""
    return current_app.send_static_file("robots.txt")


def _get_repo_and_rev(repo, namespace=None, rev=None, path=None):
    if path and rev:
        rev += "/" + path.rstrip("/")

    if namespace:
        repo_key = "~{}/{}".format(namespace, repo)
    else:
        repo_key = repo
    try:
        repo = current_app.valid_repos[repo_key]
    except KeyError:
        raise NotFound("No such repository %r" % repo)

    if rev is None:
        rev = repo.get_default_branch()
        if rev is None:
            raise NotFound("Empty repository")

    i = len(rev)
    while i > 0:
        try:
            commit = repo.get_commit(rev[:i])
            path = rev[i:].strip("/")
            rev = rev[:i]
        except (KeyError, IOError):
            i = rev.rfind("/", 0, i)
        else:
            break
    else:
        raise NotFound("No such commit %r" % rev)

    return repo, rev, path, commit


def _get_submodule(repo, commit, path):
    """Retrieve submodule URL and path."""
    submodule_blob = repo.get_blob_or_tree(commit, ".gitmodules")
    config = dulwich.config.ConfigFile.from_file(
        BytesIO(submodule_blob.as_raw_string())
    )
    key = (b"submodule", path)
    submodule_url = config.get(key, b"url")
    submodule_path = config.get(key, b"path")
    return (submodule_url, submodule_path)


class BaseRepoView(View):
    """Base for all views with a repo context.

    The arguments `repo`, `rev`, `path` (see `dispatch_request`) define the
    repository, branch/commit and directory/file context, respectively --
    that is, they specify what (and in what state) is being displayed in all the
    derived views.

    For example: The 'history' view is the `git log` equivalent, i.e. if `path`
    is "/foo/bar", only commits related to "/foo/bar" are displayed, and if
    `rev` is "master", the history of the "master" branch is displayed.
    """

    def __init__(self, view_name):
        self.view_name = view_name
        self.context = {}

    def dispatch_request(self, repo, namespace=None, rev=None, path=""):
        """Dispatch repository, revision (if any) and path (if any). To retain
        compatibility with :func:`url_for`, view routing uses two arguments:
        rev and path, although a single path is sufficient (from Git's point of
        view, '/foo/bar/baz' may be a branch '/foo/bar' containing baz, or a
        branch '/foo' containing 'bar/baz', but never both [1].

        Hence, rebuild rev and path to a single path argument, which is then
        later split into rev and path again, but revision now may contain
        slashes.

        [1] https://github.com/jonashaag/klaus/issues/36#issuecomment-23990266
        """
        self.make_template_context(repo, namespace, rev, path.strip("/"))
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_template_context(self, repo, namespace, rev, path):
        repo, rev, path, commit = _get_repo_and_rev(repo, namespace, rev, path)

        try:
            blob_or_tree = repo.get_blob_or_tree(commit, path)
        except KeyError:
            raise NotFound("File not found")

        self.context = {
            "view": self.view_name,
            "repo": repo,
            "namespace": namespace,
            "rev": rev,
            "commit": commit,
            "branches": repo.get_branch_names(exclude=rev),
            "tags": repo.get_tag_names(),
            "path": path,
            "blob_or_tree": blob_or_tree,
            "subpaths": list(subpaths(path)) if path else None,
            "base_href": None,
        }


class CommitView(BaseRepoView):
    template_name = "view_commit.html"


class PatchView(BaseRepoView):
    def get_response(self):
        return Response(
            self.context["repo"].raw_commit_diff(self.context["commit"]),
            mimetype="text/plain",
        )


class TreeViewMixin(object):
    """The logic required for displaying the current directory in the sidebar."""

    def make_template_context(self, *args):
        super(TreeViewMixin, self).make_template_context(*args)
        self.context["root_tree"] = self.listdir()

    def listdir(self):
        """Return a list of directories and files in the current path of the selected commit."""
        root_directory = self.get_root_directory()
        return self.context["repo"].listdir(self.context["commit"], root_directory)

    def get_root_directory(self):
        root_directory = self.context["path"]
        if isinstance(self.context["blob_or_tree"], dulwich.objects.Blob):
            # 'path' is a file (not folder) name
            root_directory = parent_directory(root_directory)
        return root_directory

class ReadmeMixin(object):
    """The logic required for finding and displaying README files."""

    def _get_readme(self):
        commit, path = self.context["commit"], self.context["path"]
        tree = self.context["repo"].get_blob_or_tree(commit, path)

        for name in README_FILENAMES:
            if name.lower() in [t.lower() for t in tree]:
                obj = self.context["repo"][tree[name][1]]
                if obj.type_name == b'blob':
                    readme_data = obj.data
                    readme_filename = name
                    return (readme_filename, readme_data)
        else:
            raise KeyError

    def get_readme_context(self):
        try:
            (readme_filename, readme_data) = self._get_readme()
        except KeyError:
            return {
                "is_markup": None,
                "rendered_code": None,
            }
        else:
            readme_filename = force_unicode(readme_filename)
            readme_data = force_unicode(readme_data)
            return {
                "is_markup": markup.can_render(readme_filename),
                "rendered_code": highlight_or_render(readme_data, readme_filename),
            }


class HistoryView(TreeViewMixin, ReadmeMixin, BaseRepoView):
    """Show commits of a branch + path, just like `git log`. With pagination.

    Also, README, if available."""

    template_name = "history.html"

    def make_template_context(self, *args):
        super(HistoryView, self).make_template_context(*args)

        try:
            page = int(request.args.get("page"))
        except (TypeError, ValueError):
            page = 0

        self.context["page"] = page

        history_length = 30
        if page:
            skip = (self.context["page"] - 1) * history_length + 10
            if page > 7:
                self.context["previous_pages"] = [0, 1, 2, None] + list(range(page))[
                    -3:
                ]
            else:
                self.context["previous_pages"] = range(page)
        else:
            skip = 0

        history = self.context["repo"].history(
            self.context["commit"], self.context["path"], history_length + 1, skip
        )
        if len(history) == history_length + 1:
            # At least one more commit for next page left
            more_commits = True
            # We don't want show the additional commit on this page
            history.pop()
        else:
            more_commits = False

        self.context.update(
            {
                "history": history,
                "more_commits": more_commits,
            }
        )

        self.context.update(self.get_readme_context())


class IndexView(TreeViewMixin, ReadmeMixin, BaseRepoView):
    """Show commits of a branch, just like `git log`.

    Also, README, if available."""

    template_name = "index.html"

    def make_template_context(self, *args):
        super(IndexView, self).make_template_context(*args)

        self.context["base_href"] = url_for(
            "blob",
            repo=self.context["repo"].namespaced_name,
            rev=self.context["rev"],
            path="",
        )

        self.context["page"] = 0
        history_length = 10
        history = self.context["repo"].history(
            self.context["commit"],
            self.context["path"],
            history_length + 1,
            skip=0,
        )
        if len(history) == history_length + 1:
            # At least one more commit for next page left
            more_commits = True
            # We don't want show the additional commit on this page
            history.pop()
        else:
            more_commits = False

        self.context.update(
            {
                "history": history,
                "more_commits": more_commits,
            }
        )

        self.context.update(self.get_readme_context())


class BaseBlobView(BaseRepoView):
    def make_template_context(self, *args):
        super(BaseBlobView, self).make_template_context(*args)
        if not isinstance(self.context["blob_or_tree"], dulwich.objects.Blob):
            raise NotFound("Not a blob")
        self.context["filename"] = os.path.basename(self.context["path"])


class SubmoduleView(BaseRepoView):
    """Show an information page about a submodule."""

    template_name = "submodule.html"

    def make_template_context(self, repo, namespace, rev, path):
        repo, rev, path, commit = _get_repo_and_rev(repo, namespace, rev, path)

        try:
            submodule_rev = tree_lookup_path(
                repo.__getitem__, commit.tree, encode_for_git(path)
            )[1]
        except KeyError:
            raise NotFound("Parent path for submodule missing")

        try:
            (submodule_url, submodule_path) = _get_submodule(
                repo, commit, encode_for_git(path)
            )
        except KeyError:
            submodule_url = None
            submodule_path = None

        # TODO(jelmer): Rather than printing an information page,
        # redirect to the page in klaus for the repository at
        # submodule_path, revision submodule_rev.

        self.context = {
            "view": self.view_name,
            "repo": repo,
            "rev": rev,
            "commit": commit,
            "branches": repo.get_branch_names(exclude=rev),
            "tags": repo.get_tag_names(),
            "path": path,
            "subpaths": list(subpaths(path)) if path else None,
            "submodule_url": force_unicode(submodule_url),
            "submodule_path": force_unicode(submodule_path),
            "submodule_rev": force_unicode(submodule_rev),
            "base_href": None,
        }


class BaseFileView(TreeViewMixin, BaseBlobView):
    """Base for FileView and BlameView."""

    def render_code(self, render_markup):
        should_use_ctags = current_app.should_use_ctags(
            self.context["repo"], self.context["commit"]
        )
        if should_use_ctags:
            if ctags is None:
                raise ImportError("Ctags enabled but python-ctags not installed")
            ctags_base_url = url_for(
                self.view_name,
                repo=self.context["repo"].namespaced_name,
                rev=self.context["rev"],
                path="",
            )
            ctags_tagsfile = CTAGS_CACHE.get_tagsfile(
                self.context["repo"].path, self.context["commit"].id
            )
            ctags_args = {
                "ctags": ctags.CTags(
                    ctags_tagsfile.encode(sys.getfilesystemencoding())
                ),
                "ctags_baseurl": ctags_base_url,
            }
        else:
            ctags_args = {}

        return highlight_or_render(
            force_unicode(self.context["blob_or_tree"].data),
            self.context["filename"],
            render_markup,
            **ctags_args
        )

    def make_template_context(self, *args):
        super(BaseFileView, self).make_template_context(*args)
        self.context.update(
            {
                "can_render": True,
                "is_binary": False,
                "too_large": False,
                "is_markup": False,
            }
        )

        binary = guess_is_binary(self.context["blob_or_tree"])
        too_large = sum(map(len, self.context["blob_or_tree"].chunked)) > 100 * 1024
        if binary:
            self.context.update(
                {
                    "can_render": False,
                    "is_binary": True,
                    "is_image": guess_is_image(self.context["filename"]),
                }
            )
        elif too_large:
            self.context.update(
                {
                    "can_render": False,
                    "too_large": True,
                }
            )


class FileView(BaseFileView):
    """Shows a file rendered using ``pygmentize``."""

    template_name = "view_blob.html"

    def make_template_context(self, *args):
        super(FileView, self).make_template_context(*args)
        if self.context["can_render"]:
            render_markup = "markup" not in request.args
            self.context.update(
                {
                    "is_markup": markup.can_render(self.context["filename"]),
                    "render_markup": render_markup,
                    "rendered_code": self.render_code(render_markup),
                }
            )


class BlameView(BaseFileView):
    template_name = "blame_blob.html"

    def make_template_context(self, *args):
        super(BlameView, self).make_template_context(*args)
        if self.context["can_render"]:
            line_commits = self.context["repo"].blame(
                self.context["commit"], self.context["path"]
            )
            replace_dupes(line_commits, None)
            self.context.update(
                {
                    "rendered_code": self.render_code(render_markup=False),
                    "line_commits": line_commits,
                }
            )


class RawView(BaseBlobView):
    """Show a single file in raw for (as if it were a normal filesystem file
    served through a static file server).
    """

    def get_response(self):
        # Explicitly set an empty mimetype. This should work well for most
        # browsers as they do file type recognition anyway.
        # The correct way would be to implement proper file type recognition here.
        return Response(self.context["blob_or_tree"].chunked, mimetype="")


class DownloadView(BaseRepoView):
    """Download a repo as a tar.gz file."""

    def get_response(self):
        basename = "%s@%s" % (
            self.context["repo"].name,
            sanitize_branch_name(self.context["rev"]),
        )
        tarname = basename + ".tar.gz"
        headers = {
            "Content-Disposition": "attachment; filename=%s" % tarname,
            "Cache-Control": "no-store",  # Disables browser caching
        }

        tar_stream = dulwich.archive.tar_stream(
            self.context["repo"],
            self.context["blob_or_tree"],
            self.context["commit"].commit_time,
            format="gz",
            prefix=encode_for_git(basename),
        )
        return Response(tar_stream, mimetype="application/x-tgz", headers=headers)


history = HistoryView.as_view("history", "history")
index = IndexView.as_view("index", "index")
commit = CommitView.as_view("commit", "commit")
patch = PatchView.as_view("patch", "patch")
blame = BlameView.as_view("blame", "blame")
blob = FileView.as_view("blob", "blob")
raw = RawView.as_view("raw", "raw")
download = DownloadView.as_view("download", "download")
submodule = SubmoduleView.as_view("submodule", "submodule")
