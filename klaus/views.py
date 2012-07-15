import os
import stat

from flask import request, render_template, current_app
from flask.views import View

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound

from klaus import markup
from klaus.utils import subpaths, get_mimetype_and_encoding, pygmentize, \
                        force_unicode, guess_is_binary, guess_is_image


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
    def __init__(self, view_name, template_name=None):
        self.view_name = view_name
        self.template_name = template_name
        self.context = {}

    def dispatch_request(self, repo, commit_id, path=''):
        self.make_context(repo, commit_id, path)
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_context(self, repo, commit_id, path):
        try:
            repo = app.repo_map[repo]
            commit, isbranch = repo.get_branch_or_commit(commit_id)
        except KeyError:
            raise NotFound

        self.context = {
            'view': self.view_name,
            'repo': repo,
            'commit_id': commit_id,
            'commit': commit,
            'branch': commit_id if isbranch else 'master',
            'branches': repo.get_branch_names(exclude=[commit_id]),
            'path': path,
            'subpaths': subpaths(path) if path else None,
        }


class TreeView(BaseRepoView):
    """
    Shows a list of files/directories for the current path as well as all
    commit history for that path in a paginated form.
    """
    def make_context(self, *args):
        super(TreeView, self).make_context(*args)

        self.context['tree'] = self.listdir()

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

    def listdir(self):
        """
        Returns a list of directories and files in the current path of the
        selected commit
        """
        dirs, files = [], []
        root = self.get_directory()
        try:
            tree = self.context['repo'].get_tree(self.context['commit'], root)
        except KeyError:
            raise NotFound

        for entry in tree.iteritems():
            name, entry = entry.path, entry.in_path(root)
            if entry.mode & stat.S_IFDIR:
                dirs.append((name.lower(), name, entry.path))
            else:
                files.append((name.lower(), name, entry.path))

        files.sort()
        dirs.sort()

        if root:
            dirs.insert(0, (None, '..', os.path.split(root)[0]))

        return {'dirs' : dirs, 'files' : files}

    def get_directory(self):
        return self.context['path']


class BlobView(TreeView):
    def make_context(self, *args):
        super(BlobView, self).make_context(*args)
        blob = self.context['repo'].get_tree(self.context['commit'],
                                             self.context['path'])
        filename = os.path.basename(self.context['path'])
        render_markup = 'markup' not in request.args
        rendered_code = pygmentize(force_unicode(blob.data), filename, render_markup)

        self.context.update({
            'blob': blob,
            'filename': filename,
            'too_large': sum(map(len, blob.chunked)) > 100*1024,
            'is_markup': markup.can_render(filename),
            'render_markup': render_markup,
            'rendered_code': rendered_code,
            'is_binary': guess_is_binary(blob),
            'is_image': guess_is_image(filename),
        })

    def get_directory(self):
        return os.path.split(self.context['path'])[0]


class RawView(BlobView):
    """
    Shows a single file in raw for (as if it were a normal filesystem file
    served through a static file server)
    """
    def get_response(self):
        chunks = self.context['blob'].chunked

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
history = TreeView.as_view('history', 'history', 'history.html')
commit = BaseRepoView.as_view('commit', 'commit', 'view_commit.html')
blob = BlobView.as_view('blob', 'blob', 'view_blob.html')
raw = RawView.as_view('raw', 'raw')
