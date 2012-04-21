# -*- encoding: utf-8 -*-

from werkzeug.wrappers import Response
from werkzeug.exceptions import InternalServerError

import os
import stat
import mimetypes

from dulwich.objects import Commit, Blob

from klaus.repo import get_repo
from klaus.utils import subpaths, guess_is_binary


def prepare(func):
    """This prepares repo, commit_id and path (if available) into a single
    dictionary and builds the url builder function."""

    def get_commit(repo, id):
        commit, isbranch = repo.get_branch_or_commit(id)
        if not isinstance(commit, Commit):
            raise KeyError('"%s" has no commit "%s"' % (repo.name, id))
        return commit, isbranch


    def dec(app, request, repo, commit_id, path=None):

        defaults = {'repo': repo, 'commit_id': commit_id, 'path': path}
        repo = get_repo(app, repo)

        try:
            commit, isbranch = get_commit(repo, commit_id)
        except KeyError as e:
            return Response(e, 404)

        response = {
            'environ': request.environ,
            'repo': repo,
            'commit_id': commit_id,
            'commit': commit,
            'branch': commit_id if isbranch else 'master',
            'branches': repo.get_branch_names(exclude=[commit_id]),
            'path': path }

        if path:
            defaults['path'] = ''
            response['subpaths'] = list(subpaths(path))

        response['build'] = lambda v, **kw: request.adapter.build(v, dict(defaults, **kw))

        return func(app, request, response, repo, commit_id, path)
    return dec


def repo_list(app, request):
    """Shows a list of all repos and can be sorted by last update. """

    response = {'environ': request.environ, 'build': lambda v, **kw: request.adapter.build(v, kw)}
    response['repos'] = repos = []

    for name in app.repos.iterkeys():

        try:
            repo = get_repo(app, name)
        except KeyError:
            raise InternalServerError

        refs = [repo[ref_hash] for ref_hash in repo.get_refs().itervalues()]
        refs.sort(key=lambda obj:getattr(obj, 'commit_time', None),
                  reverse=True)
        last_updated_at = None
        if refs:
            last_updated_at = refs[0].commit_time
        repos.append((name, last_updated_at))
    if 'by-last-update' in request.GET:
        repos.sort(key=lambda x: x[1], reverse=True)
    else:
        repos.sort(key=lambda x: x[0])

    return Response(app.render_template('repo_list.html', **response), 200,
                    content_type='text/html')

@prepare
def history(app, request, response, repo, commit_id, path):

    response = TreeView(request, response)
    response['view'] = 'history'

    return Response(app.render_template('history.html', **response), 200,
                    content_type='text/html')


@prepare
def commit(app, request, response, repo, commit_id, path=None):

    response = CommitView(request, response)
    response['view'] = 'commit'

    return Response(app.render_template('view_commit.html', **response), 200,
                    content_type='text/html')


@prepare
def blob(app, request, response, repo, commit_id, path):

    response = BlobView(request, response)
    response['view'] = 'blob'

    return Response(app.render_template('view_blob.html', **response), 200,
                    content_type='text/html')

@prepare
def raw(app, request, response, repo, commit_id, path):
    """ Shows a single file in raw for (as if it were a normal filesystem file
        served through a static file server)"""

    def get_mimetype_and_encoding(blob, filename):
        if guess_is_binary(blob):
            mime, encoding = mimetypes.guess_type(filename)
            if mime is None:
                mime = 'application/octet-stream'
            return mime, encoding
        else:
            return 'text/plain', 'utf-8'

    filename = os.path.basename(path)
    body = response['repo'].get_tree(response['commit'], path).chunked

    if len(body) == 1 and not body[0]:
        body = []

    mime, encoding = get_mimetype_and_encoding(body, filename)
    headers = {'Content-Type': mime}

    if encoding:
        headers['Content-Encoding'] = encoding

    return Response(body, 200, headers=headers)


class BaseView(dict):
    def __init__(self, request, response):
        dict.__init__(self)

        self.GET = request.GET
        self.update(response)
        self.view()


class TreeViewMixin(object):

    def view(self):
        self['tree'] = self.listdir()

    def listdir(self):
        """
        Returns a list of directories and files in the current path of the
        selected commit
        """
        dirs, files = [], []
        tree, root = self.get_tree()
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

    def get_tree(self):
        """ Gets the Git tree of the selected commit and path """
        root = self['path']
        tree = self['repo'].get_tree(self['commit'], root)
        if isinstance(tree, Blob):
            root = os.path.split(root)[0]
            tree = self['repo'].get_tree(self['commit'], root)
        return tree, root


class TreeView(TreeViewMixin, BaseView):
    """
    Shows a list of files/directories for the current path as well as all
    commit history for that path in a paginated form.
    """
    def view(self):
        super(TreeView, self).view()
        try:
            page = int(self.GET.get('page'))
        except (TypeError, ValueError):
            page = 0

        self['page'] = page

        if page:
            self['history_length'] = 30
            self['skip'] = (self['page']-1) * 30 + 10
            if page > 7:
                self['previous_pages'] = [0, 1, 2, None] + range(page)[-3:]
            else:
                self['previous_pages'] = xrange(page)
        else:
            self['history_length'] = 10
            self['skip'] = 0


class BaseBlobView(BaseView):
    def view(self):
        self['blob'] = self['repo'].get_tree(self['commit'], self['path'])
        self['directory'], self['filename'] = os.path.split(self['path'].strip('/'))


class BlobView(BaseBlobView, TreeViewMixin):
    """ Shows a single file, syntax highlighted """
    def view(self):
        BaseBlobView.view(self)
        TreeViewMixin.view(self)
        self['raw_url'] = self['build']('raw', path=self['path'], repo=self['repo'].name,
                                        commit_id=self['commit_id'])
        self['too_large'] = sum(map(len, self['blob'].chunked)) > 100*1024


class CommitView(BaseView):
    """ Shows a single commit diff """
    def view(self):
        pass
