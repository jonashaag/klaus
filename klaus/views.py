import os
import stat

from flask import request, render_template, current_app
from flask.views import View

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound

from dulwich.objects import Blob

from klaus import markup
from klaus.utils import parent_directory, subpaths, get_mimetype_and_encoding, \
                        pygmentize, force_unicode, guess_is_binary, guess_is_image


def repo_list():
    """Shows a list of all repos and can be sorted by last update. """
    if 'by-last-update' in request.args:
        sort_key = lambda repo: repo.get_last_updated_at()
        reverse = True
    else:
        sort_key = lambda repo: repo.name
        reverse = False
    repos = sorted(current_app.repos, key=sort_key, reverse=reverse)
    return render_template('repo_list.html', repos=repos)


class BaseRepoView(View):
    """
    Base for all views with a repo context.

    The arguments `repo`, `commit_id`, `path` (see `dispatch_request`) define
    the repository, branch/commit and directory/file context, respectively --
    that is, they specify what (and in what state) is being displayed in all the
    derived views.

    For example: The 'history' view is the `git log` equivalent, i.e. if `path`
    is "/foo/bar", only commits related to "/foo/bar" are displayed, and if
    `commit_id` is "master", the history of the "master" branch is displayed.
    """
    def __init__(self, view_name, template_name=None):
        self.view_name = view_name
        self.template_name = template_name
        self.context = {}

    def dispatch_request(self, repo, commit_id=None, path=''):
        self.make_context(repo, commit_id, path.strip('/'))
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_context(self, repo, commit_id, path):
        try:
            repo = current_app.repo_map[repo]
            if commit_id is None:
                commit_id = repo.get_default_branch()
            commit = repo.get_ref_or_commit(commit_id)
        except KeyError:
            raise NotFound("Commit not found")

        try:
            blob_or_tree = repo.get_blob_or_tree(commit, path)
        except KeyError:
            raise NotFound("File not found")

        self.context = {
            'view': self.view_name,
            'repo': repo,
            'commit_id': commit_id,
            'commit': commit,
            'branches': repo.get_branch_names(exclude=commit_id),
            'tags': repo.get_tag_names(),
            'path': path,
            'blob_or_tree': blob_or_tree,
            'subpaths': list(subpaths(path)) if path else None,
        }


class TreeViewMixin(object):
    """
    Implements the logic required for displaying the current directory in the sidebar
    """
    def make_context(self, *args):
        super(TreeViewMixin, self).make_context(*args)
        self.context['root_tree'] = self.listdir()

    def listdir(self):
        """
        Returns a list of directories and files in the current path of the
        selected commit
        """
        root_directory = self.get_root_directory()
        root_tree = self.context['repo'].get_blob_or_tree(
            self.context['commit'],
            root_directory
        )

        dirs, files = [], []
        for entry in root_tree.iteritems():
            name, entry = entry.path, entry.in_path(root_directory)
            if entry.mode & stat.S_IFDIR:
                dirs.append((name.lower(), name, entry.path))
            else:
                files.append((name.lower(), name, entry.path))
        files.sort()
        dirs.sort()

        if root_directory:
            dirs.insert(0, (None, '..', parent_directory(root_directory)))

        return {'dirs' : dirs, 'files' : files}

    def get_root_directory(self):
        root_directory = self.context['path']
        if isinstance(self.context['blob_or_tree'], Blob):
            # 'path' is a file (not folder) name
            root_directory = parent_directory(root_directory)
        return root_directory


class HistoryView(TreeViewMixin, BaseRepoView):
    """ Show commits of a branch + path, just like `git log`. With pagination. """
    def make_context(self, *args):
        super(HistoryView, self).make_context(*args)

        try:
            page = int(request.args.get('page'))
        except (TypeError, ValueError):
            page = 0

        self.context['page'] = page

        if page:
            self.context['history_length'] = 30
            self.context['skip'] = (self.context['page']-1) * 30 + 10
            if page > 7:
                self.context['previous_pages'] = [0, 1, 2, None] + range(page)[-3:]
            else:
                self.context['previous_pages'] = xrange(page)
        else:
            self.context['history_length'] = 10
            self.context['skip'] = 0


class BlobViewMixin(object):
    def make_context(self, *args):
        super(BlobViewMixin, self).make_context(*args)
        self.context['filename'] = os.path.basename(self.context['path'])


class BlobView(BlobViewMixin, TreeViewMixin, BaseRepoView):
    """ Shows a file rendered using ``pygmentize`` """
    def make_context(self, *args):
        super(BlobView, self).make_context(*args)

        if guess_is_binary(self.context['blob_or_tree']):
            self.context.update({
                'is_markup': False,
                'is_binary': True,
                'is_image': False,
            })
            if guess_is_image(self.context['filename']):
                self.context.update({
                    'is_image': True,
                })
        else:
            render_markup = 'markup' not in request.args
            rendered_code = pygmentize(
                force_unicode(self.context['blob_or_tree'].data),
                self.context['filename'],
                render_markup
            )
            self.context.update({
                'too_large': sum(map(len, self.context['blob_or_tree'].chunked)) > 100*1024,
                'is_markup': markup.can_render(self.context['filename']),
                'render_markup': render_markup,
                'rendered_code': rendered_code,
                'is_binary': False,
            })


class RawView(BlobViewMixin, BaseRepoView):
    """
    Shows a single file in raw for (as if it were a normal filesystem file
    served through a static file server)
    """
    def get_response(self):
        chunks = self.context['blob_or_tree'].chunked

        if len(chunks) == 1 and not chunks[0]:
            # empty file
            chunks = []
            mime = 'text/plain'
            encoding = 'utf-8'
        else:
            mime, encoding = get_mimetype_and_encoding(chunks, self.context['filename'])

        headers = {'Content-Type': mime}
        if encoding:
            headers['Content-Encoding'] = encoding

        return Response(chunks, headers=headers)


#                                     TODO v
history = HistoryView.as_view('history', 'history', 'history.html')
commit = BaseRepoView.as_view('commit', 'commit', 'view_commit.html')
blob = BlobView.as_view('blob', 'blob', 'view_blob.html')
raw = RawView.as_view('raw', 'raw')
