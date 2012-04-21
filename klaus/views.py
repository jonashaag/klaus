# -*- encoding: utf-8 -*-

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError

import os
import stat
from dulwich.objects import Commit, Blob

from klaus.repo import get_repo
from klaus.utils import subpaths, query_string_to_dict


def repo_list(klaus, request, response):
    """ Shows a list of all repos and can be sorted by last update. """

    response['repos'] = repos = []

    for name in klaus.repos.iterkeys():

        try:
            repo = get_repo(klaus, name)
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

    return Response(klaus.render_template('repo_list.html', **response), 200,
                    content_type='text/html')


def history(klaus, request, response, repo, commit_id, path):

    response.update(TreeView(klaus, request, response, repo, commit_id, path))
    defaults = {'repo': repo, 'commit_id': commit_id, 'path': path}

    build = response['adapter'].build
    response['build'] = lambda v, **kw: build(v, dict(defaults, **kw))
    response['view'] = 'history'

    return Response(klaus.render_template('history.html', **response), 200,
                    content_type='text/html')


def commit(klaus, request, response, repo, commit_id):
    # XXX not really DRY
    response.update(CommitView(klaus, request, response, repo, commit_id, ''))
    defaults = {'repo': repo, 'commit_id': commit_id, 'path': ''}

    build = response['adapter'].build
    response['build'] = lambda v, **kw: build(v, dict(defaults, **kw))
    response['view'] = 'commit'

    return Response(klaus.render_template('view_commit.html', **response), 200,
                    content_type='text/html')


def blob(klaus, request, response, repo, commit_id, path):

    response.update(BlobView(klaus, request, response, repo, commit_id, path))
    defaults = {'repo': repo, 'commit_id': commit_id, 'path': path}

    build = response['adapter'].build
    response['build'] = lambda v, **kw: build(v, dict(defaults, **kw))
    response['view'] = 'blob'

    return Response(klaus.render_template('view_blob.html', **response), 200,
                    content_type='text/html')


class BaseView(dict):
    def __init__(self, request, response):
        dict.__init__(self)

        self.GET = request.GET
        self.view()

    def direct_response(self, *args):
        # XXX
        raise Response(*args)


class BaseRepoView(BaseView):
    def __init__(self, klaus, request, response, repo, commit_id, path):

        self.update(response)
        self['repo'] = repo = get_repo(klaus, repo)
        self['commit_id'] = commit_id
        self['commit'], isbranch = self.get_commit(repo, commit_id)
        self['branch'] = commit_id if isbranch else 'master'
        self['branches'] = repo.get_branch_names(exclude=[commit_id])
        self['path'] = path

        if path:
            self['subpaths'] = list(subpaths(path))

        super(BaseRepoView, self).__init__(request, response)

    def get_commit(self, repo, id):
        try:
            commit, isbranch = repo.get_branch_or_commit(id)
            if not isinstance(commit, Commit):
                raise KeyError
        except KeyError:
            # XXX remove HttpError
            raise HttpError(404, '"%s" has no commit "%s"' % (repo.name, id))
        return commit, isbranch


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

# @route('/:repo:/tree/:commit_id:/(?P<path>.*)', 'history')
class TreeView(TreeViewMixin, BaseRepoView):
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

class BaseBlobView(BaseRepoView):
    def view(self):
        self['blob'] = self['repo'].get_tree(self['commit'], self['path'])
        self['directory'], self['filename'] = os.path.split(self['path'].strip('/'))

# @route('/:repo:/blob/:commit_id:/(?P<path>.*)', 'view_blob')
class BlobView(BaseBlobView, TreeViewMixin):
    """ Shows a single file, syntax highlighted """
    def view(self):
        BaseBlobView.view(self)
        TreeViewMixin.view(self)
        self['raw_url'] = self['build']('raw', path=self['path'], repo=self['repo'],
                                        commit_id=self['commit_id'])
        self['too_large'] = sum(map(len, self['blob'].chunked)) > 100*1024


# @route('/:repo:/raw/:commit_id:/(?P<path>.*)', 'raw_blob')
class RawBlob(BaseBlobView):
    """
    Shows a single file in raw form
    (as if it were a normal filesystem file served through a static file server)
    """
    def view(self):
        super(RawBlob, self).view()
        mime, encoding = self.get_mimetype_and_encoding()
        headers = {'Content-Type': mime}
        if encoding:
            headers['Content-Encoding'] = encoding
        body = self['blob'].chunked
        if len(body) == 1 and not body[0]:
            body = []
        self.direct_response('200 yo', headers, body)


    def get_mimetype_and_encoding(self):
        if guess_is_binary(self['blob'].chunked):
            mime, encoding = mimetypes.guess_type(self['filename'])
            if mime is None:
                mime = 'application/octet-stream'
            return mime, encoding
        else:
            return 'text/plain', 'utf-8'


# @route('/:repo:/commit/:commit_id:/', 'view_commit')
class CommitView(BaseRepoView):
    """ Shows a single commit diff """
    def view(self):
        pass


# @route('/static/(?P<path>.+)', 'static')
class StaticFilesView(BaseView):
    """
    Serves assets (everything under /static/).

    Don't use this in production! Use a static file server instead.
    """
    def __init__(self, env, path):
        self['path'] = path
        super(StaticFilesView, self).__init__(env)

    def view(self):
        path = './static/' + self['path']
        relpath = os.path.join(KLAUS_ROOT, path)
        if os.path.isfile(relpath):
            self.direct_response(open(relpath))
        else:
            raise HttpError(404, 'Not Found')
