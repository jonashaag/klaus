import os

from flask import request, render_template, current_app, url_for
from flask.views import View

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound

import dulwich.objects
import dulwich.archive

try:
    import ctags
except ImportError:
    ctags = None
else:
    from klaus import ctagscache
    CTAGS_CACHE = ctagscache.CTagsCache()

from klaus import markup
from klaus.highlighting import pygmentize
from klaus.utils import parent_directory, subpaths, force_unicode, guess_is_binary, \
                        guess_is_image, replace_dupes


def repo_list():
    """Show a list of all repos and can be sorted by last update."""
    if 'by-last-update' in request.args:
        sort_key = lambda repo: repo.get_last_updated_at()
        reverse = True
    else:
        sort_key = lambda repo: repo.name
        reverse = False
    repos = sorted(current_app.repos.values(), key=sort_key, reverse=reverse)
    return render_template('repo_list.html', repos=repos)


def robots_txt():
    """Serve the robots.txt file to manage the indexing of the site by search engines."""
    return current_app.send_static_file('robots.txt')


def _get_repo_and_rev(repo, rev=None):
    try:
        repo = current_app.repos[repo]
    except KeyError:
        raise NotFound("No such repository %r" % repo)

    if rev is None:
        rev = repo.get_default_branch()
        if rev is None:
            raise NotFound("Empty repository")
    try:
        commit = repo.get_commit(rev)
    except KeyError:
        raise NotFound("No such commit %r" % rev)

    return repo, rev, commit


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

    def dispatch_request(self, repo, rev=None, path=''):
        self.make_template_context(repo, rev, path.strip('/'))
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_template_context(self, repo, rev, path):
        repo, rev, commit = _get_repo_and_rev(repo, rev)
        try:
            blob_or_tree = repo.get_blob_or_tree(commit, path)
        except KeyError:
            raise NotFound("File not found")

        self.context = {
            'view': self.view_name,
            'repo': repo,
            'rev': rev,
            'commit': commit,
            'branches': repo.get_branch_names(exclude=rev),
            'tags': repo.get_tag_names(),
            'path': path,
            'blob_or_tree': blob_or_tree,
            'subpaths': list(subpaths(path)) if path else None,
        }


class CommitView(BaseRepoView):
    template_name = 'view_commit.html'


class PatchView(BaseRepoView):
    def get_response(self):
        return Response(
            self.context['repo'].raw_commit_diff(self.context['commit']),
            mimetype='text/plain',
        )


class TreeViewMixin(object):
    """The logic required for displaying the current directory in the sidebar."""
    def make_template_context(self, *args):
        super(TreeViewMixin, self).make_template_context(*args)
        self.context['root_tree'] = self.listdir()

    def listdir(self):
        """Return a list of directories and files in the current path of the selected commit."""
        root_directory = self.get_root_directory()
        return self.context['repo'].listdir(
            self.context['commit'],
            root_directory
        )

    def get_root_directory(self):
        root_directory = self.context['path']
        if isinstance(self.context['blob_or_tree'], dulwich.objects.Blob):
            # 'path' is a file (not folder) name
            root_directory = parent_directory(root_directory)
        return root_directory


class HistoryView(TreeViewMixin, BaseRepoView):
    """Show commits of a branch + path, just like `git log`. With pagination."""
    template_name = 'history.html'

    def make_template_context(self, *args):
        super(HistoryView, self).make_template_context(*args)

        try:
            page = int(request.args.get('page'))
        except (TypeError, ValueError):
            page = 0

        self.context['page'] = page

        if page:
            history_length = 30
            skip = (self.context['page']-1) * 30 + 10
            if page > 7:
                self.context['previous_pages'] = [0, 1, 2, None] + list(range(page))[-3:]
            else:
                self.context['previous_pages'] = range(page)
        else:
            history_length = 10
            skip = 0

        history = self.context['repo'].history(
            self.context['commit'],
            self.context['path'],
            history_length + 1,
            skip
        )
        if len(history) == history_length + 1:
            # At least one more commit for next page left
            more_commits = True
            # We don't want show the additional commit on this page
            history.pop()
        else:
            more_commits = False

        self.context.update({
            'history': history,
            'more_commits': more_commits,
        })


class BaseBlobView(BaseRepoView):
    def make_template_context(self, *args):
        super(BaseBlobView, self).make_template_context(*args)
        if not isinstance(self.context['blob_or_tree'], dulwich.objects.Blob):
            raise NotFound("Not a blob")
        self.context['filename'] = os.path.basename(self.context['path'])


class BaseFileView(TreeViewMixin, BaseBlobView):
    """Base for FileView and BlameView."""
    def render_code(self, render_markup):
        should_use_ctags = current_app.should_use_ctags(self.context['repo'],
                                                        self.context['commit'])
        if should_use_ctags:
            if ctags is None:
                raise ImportError("Ctags enabled but python-ctags not installed")
            ctags_base_url = url_for(
                self.view_name,
                repo=self.context['repo'].name,
                rev=self.context['rev'],
                path=''
            )
            ctags_tagsfile = CTAGS_CACHE.get_tagsfile(
                self.context['repo'].path,
                self.context['commit'].id
            )
            ctags_args = {
                'ctags': ctags.CTags(ctags_tagsfile.encode("utf-8")),
                'ctags_baseurl': ctags_base_url,
            }
        else:
            ctags_args = {}

        return pygmentize(
            force_unicode(self.context['blob_or_tree'].data),
            self.context['filename'],
            render_markup,
            **ctags_args
        )

    def make_template_context(self, *args):
        super(BaseFileView, self).make_template_context(*args)
        self.context.update({
            'can_render': True,
            'is_binary': False,
            'too_large': False,
            'is_markup': False,
        })

        binary = guess_is_binary(self.context['blob_or_tree'])
        too_large = sum(map(len, self.context['blob_or_tree'].chunked)) > 100*1024
        if binary:
            self.context.update({
                'can_render': False,
                'is_binary': True,
                'is_image': guess_is_image(self.context['filename']),
            })
        elif too_large:
            self.context.update({
                'can_render': False,
                'too_large': True,
            })


class FileView(BaseFileView):
    """Shows a file rendered using ``pygmentize``."""
    template_name = 'view_blob.html'

    def make_template_context(self, *args):
        super(FileView, self).make_template_context(*args)
        if self.context['can_render']:
            render_markup = 'markup' not in request.args
            self.context.update({
                'is_markup': markup.can_render(self.context['filename']),
                'render_markup': render_markup,
                'rendered_code': self.render_code(render_markup),
            })


class BlameView(BaseFileView):
    template_name = 'blame_blob.html'

    def make_template_context(self, *args):
        super(BlameView, self).make_template_context(*args)
        if self.context['can_render']:
            line_commits = self.context['repo'].blame(self.context['commit'], self.context['path'])
            replace_dupes(line_commits, None)
            self.context.update({
                'rendered_code': self.render_code(render_markup=False),
                'line_commits': line_commits,
            })


class RawView(BaseBlobView):
    """Show a single file in raw for (as if it were a normal filesystem file
    served through a static file server).
    """
    def get_response(self):
        # Explicitly set an empty mimetype. This should work well for most
        # browsers as they do file type recognition anyway.
        # The correct way would be to implement proper file type recognition here.
        return Response(self.context['blob_or_tree'].chunked, mimetype='')


class DownloadView(BaseRepoView):
    """Download a repo as a tar.gz file."""
    def get_response(self):
        tarname = "%s@%s.tar.gz" % (self.context['repo'].name, self.context['rev'])
        headers = {
            'Content-Disposition': "attachment; filename=%s" % tarname,
            'Cache-Control': "no-store",  # Disables browser caching
        }

        tar_stream = dulwich.archive.tar_stream(
            self.context['repo'],
            self.context['blob_or_tree'],
            self.context['commit'].commit_time,
            format="gz"
        )
        return Response(
            tar_stream,
            mimetype="application/x-tgz",
            headers=headers
        )


history = HistoryView.as_view('history', 'history')
commit = CommitView.as_view('commit', 'commit')
patch = PatchView.as_view('patch', 'patch')
blame = BlameView.as_view('blame', 'blame')
blob = FileView.as_view('blob', 'blob')
raw = RawView.as_view('raw', 'raw')
download = DownloadView.as_view('download', 'download')
