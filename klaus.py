import os
import stat
import time
import mimetypes
from future_builtins import map
from functools import wraps

from dulwich.objects import Commit

from jinja2 import Environment, FileSystemLoader

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, \
                            guess_lexer, ClassNotFound
from pygments.formatters import HtmlFormatter

from nano import NanoApplication, HttpError
from repo import Repo

class KlausApplication(NanoApplication):
    def __init__(self, *args, **kwargs):
        super(KlausApplication, self).__init__(*args, **kwargs)
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self.jinja_env.globals['build_url'] = self.build_url

    def route(self, pattern):
        super_decorator = super(KlausApplication, self).route(pattern)
        def decorator(callback):
            @wraps(callback)
            def wrapper(env, **kwargs):
                if hasattr(self, 'custom_host'):
                    env['HTTP_HOST'] = self.custom_host
                try:
                    return self.render_template(callback.__name__ + '.html',
                                                **callback(env, **kwargs))
                except Response as e:
                    if len(e.args) == 1:
                        return e.args[0]
                    return e.args
            return super_decorator(wrapper)
        return decorator

    def render_template(self, template_name, **kwargs):
        return self.jinja_env.get_template(template_name).render(**kwargs)

app = KlausApplication(debug=True, default_content_type='text/html')

def pygmentize(code, filename=None, language=None):
    if language:
        lexer = get_lexer_by_name(language)
    else:
        try:
            lexer = get_lexer_for_filename(filename)
        except ClassNotFound:
            lexer = guess_lexer(code)
    return highlight(code, lexer, pygments_formatter)
pygments_formatter = HtmlFormatter(linenos=True)

def timesince(when, now=time.time):
    delta = now() - when
    result = []
    break_next = False
    for unit, seconds, break_immediately in [
        ('year', 365*24*60*60, False),
        ('month', 30*24*60*60, False),
        ('week', 7*24*60*60, False),
        ('day', 24*60*60, True),
        ('hour', 60*60, False),
        ('minute', 60, True),
        ('second', 1, False),
    ]:
        if delta > seconds:
            n = int(delta/seconds)
            delta -= n*seconds
            result.append((n, unit))
            if break_immediately:
                break
            if not break_next:
                break_next = True
                continue
        if break_next:
            break

    if len(result) > 1:
        n, unit = result[0]
        if unit == 'month':
            if n == 1:
                # 1 month, 3 weeks --> 7 weeks
                result = [(result[1][0] + 4, 'week')]
            else:
                # 2 months, 1 week -> 2 months
                result = result[:1]
        elif unit == 'hour' and n > 5:
            result = result[:1]

    return ', '.join('%d %s%s' % (n, unit, 's' if n != 1 else '')
                     for n, unit in result[:2])

def guess_is_binary(data):
    if isinstance(data, basestring):
        return '\0' in data
    else:
        return any(map(guess_is_binary, data))

def guess_is_image(filename):
    mime, encoding = mimetypes.guess_type(filename)
    if mime is None:
        return False
    return mime.startswith('image/')

def force_unicode(s):
    if isinstance(s, unicode):
        return s
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError as exc:
        pass
    try:
        return s.decode('iso-8859-1')
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)
    except (ImportError, UnicodeDecodeError):
        raise exc

app.jinja_env.filters['u'] = force_unicode
app.jinja_env.filters['timesince'] = timesince
app.jinja_env.filters['shorten_id'] = lambda id: id[:7] if len(id) in {20, 40} else id
app.jinja_env.filters['shorten_message'] = lambda msg: msg.split('\n')[0]
app.jinja_env.filters['pygmentize'] = pygmentize
app.jinja_env.filters['is_binary'] = guess_is_binary
app.jinja_env.filters['is_image'] = guess_is_image

def subpaths(path):
    seen = []
    for part in path.split('/'):
        seen.append(part)
        yield part, '/'.join(seen)

def get_repo(name):
    try:
        return Repo(name, app.repos[name])
    except KeyError:
        raise HttpError(404, 'No repository named "%s"' % name)

class Response(Exception):
    pass

class BaseView(dict):
    def __init__(self, env):
        dict.__init__(self)
        self['environ'] = env
        self.view()

    def direct_response(self, *args):
        raise Response(*args)

def route(pattern, name=None):
    def decorator(cls):
        cls.__name__ = name or cls.__name__.lower()
        app.route(pattern)(cls)
        return cls
    return decorator

@route('/', 'repo_list')
class RepoList(BaseView):
    def view(self):
        self['repos'] = repos = []
        for name in app.repos.iterkeys():
            repo = get_repo(name)
            refs = [repo[ref] for ref in repo.get_refs()]
            refs.sort(key=lambda obj:getattr(obj, 'commit_time', None),
                      reverse=True)
            repos.append((name, refs[0].commit_time))
        if 'by-last-update' in self['environ'].get('QUERY_STRING', ''):
            repos.sort(key=lambda x: x[1], reverse=True)
        else:
            repos.sort(key=lambda x: x[0])

class BaseRepoView(BaseView):
    def __init__(self, env, repo, commit_id, path=None):
        self['repo'] = repo = get_repo(repo)
        self['commit_id'] = commit_id
        self['commit'], isbranch = self.get_commit(repo, commit_id)
        self['branch'] = commit_id if isbranch else 'master'
        self['path'] = path
        if path:
            self['subpaths'] = list(subpaths(path))

        super(BaseRepoView, self).__init__(env)

    def get_commit(self, repo, id):
        try:
            commit, isbranch = repo.get_branch_or_commit(id)
            if not isinstance(commit, Commit):
                raise KeyError
        except KeyError:
            raise HttpError(404, '"%s" has no commit "%s"' % (repo.name, id))
        return commit, isbranch

    def build_url(self, view=None, **kwargs):
        if view is None:
            view = self.__class__.__name__
        default_kwargs = {
            'repo' : self['repo'].name,
            'commit_id' : self['commit_id'],
            'path' : self['path']
        }
        return app.build_url(view, **dict(default_kwargs, **kwargs))


@route('/:repo:/tree/:commit_id:/(?P<path>.*)', 'view_tree')
class TreeView(BaseRepoView):
    def view(self):
        self['tree'] = self.listdir(self['path'])
        try:
            self['page'] = int(self['environ']['QUERY_STRING'].replace('page=', ''))
        except (KeyError, ValueError):
            self['page'] = 0

        if self['page']:
            self['history_length'] = 30
            self['skip'] = (self['page']-1) * 30 + 10
        else:
            self['history_length'] = 10
            self['skip'] = 0

    def listdir(self, path):
        dirs, files = [], []
        for name, entry in self['repo'].listdir(self['commit'], path):
            if entry.mode & stat.S_IFDIR:
                dirs.append((name.lower(), name, entry.path))
            else:
                files.append((name.lower(), name, entry.path))
        files.sort()
        dirs.sort()
        if 'subpaths' in self:
            parent = self.get_parent_directory()
            if '/' in parent:
                parent = parent.rsplit('/', 1)[0]
            else:
                parent = ''
            dirs.insert(0, (None, '..', parent))
        return {'dirs' : dirs, 'files' : files}

    def get_parent_directory(self):
        return self['path']

class BaseBlobView(BaseRepoView):
    def view(self):
        directory, filename = os.path.split(self['path'].strip('/'))
        tree_id = self['repo'].get_tree(self['commit'], directory)[filename][1]
        self['blob'] = self['repo'][tree_id]
        self['directory'] = directory
        self['filename'] = filename

@route('/:repo:/blob/:commit_id:/(?P<path>.*)', 'view_blob')
class BlobView(BaseBlobView, TreeView):
    def view(self):
        super(BlobView, self).view()
        self['tree'] = self.listdir(self['directory'])
        self['raw_url'] = self.build_url('raw_blob')
        self['too_large'] = sum(map(len, self['blob'].chunked)) > 100*1024

    def get_parent_directory(self):
        return self['directory']


@route('/:repo:/raw/:commit_id:/(?P<path>.*)', 'raw_blob')
class RawBlob(BaseBlobView):
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
                mime = 'appliication/octet-stream'
            return mime, encoding
        else:
            return 'text/plain', 'utf-8'


@route('/:repo:/commit/:commit_id:/', 'view_commit')
class CommitView(BaseRepoView):
    def view(self):
        pass


@route('/static/(?P<path>.+)', 'static')
class StaticFilesView(BaseView):
    def __init__(self, env, path):
        self['path'] = path
        super(StaticFilesView, self).__init__(env)

    def view(self):
        path = './static/' + self['path']
        relpath = os.path.join(os.getcwd(), path)
        if os.path.isfile(relpath):
            self.direct_response(open(relpath))
        else:
            raise HttpError(404, 'Not Found')
