import sys
import os
import re
import stat
import time
import urlparse
import mimetypes
from future_builtins import map
from functools import wraps

from dulwich.objects import Commit, Blob

from jinja2 import Environment, FileSystemLoader

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, \
                            guess_lexer, ClassNotFound
from pygments.formatters import HtmlFormatter

from nano import NanoApplication, HttpError
from repo import Repo


KLAUS_ROOT = os.path.join(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(KLAUS_ROOT, 'templates')

try:
    KLAUS_VERSION = ' ' + open(os.path.join(KLAUS_ROOT, '.git/refs/heads/master')).read()[:7]
except IOError:
    KLAUS_VERSION = ''


def query_string_to_dict(query_string):
    """ Transforms a POST/GET string into a Python dict """
    return dict((k, v[0]) for k, v in urlparse.parse_qs(query_string).iteritems())

class KlausApplication(NanoApplication):
    def __init__(self, *args, **kwargs):
        super(KlausApplication, self).__init__(*args, **kwargs)
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                                     extensions=['jinja2.ext.autoescape'],
                                     autoescape=True)
        self.jinja_env.globals['build_url'] = self.build_url
        self.jinja_env.globals['KLAUS_VERSION'] = KLAUS_VERSION

    def route(self, pattern):
        """
        Extends `NanoApplication.route` by multiple features:

        - Overrides the WSGI `HTTP_HOST` by `self.custom_host` (if set)
        - Tries to use the keyword arguments returned by the view function
          to render the template called `<class>.html` (<class> being the
          name of `self`'s class). Raising `Response` can be used to skip
          this behaviour, directly returning information to Nano.
        """
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

app = application = KlausApplication(debug=True, default_content_type='text/html')
# KLAUS_REPOS=/foo/bar/,/spam/ --> {'bar': '/foo/bar/', 'spam': '/spam/'}
app.repos = dict(
    (repo.rstrip(os.sep).split(os.sep)[-1], repo)
    for repo in (sys.argv[1:] or os.environ.get('KLAUS_REPOS', '').split())
)

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
    """ Returns the difference between `when` and `now` in human readable form. """
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
    """ Does all kind of magic to turn `s` into unicode """
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

def extract_author_name(email):
    """
    Extracts the name from an email address...
    >>> extract_author_name("John <john@example.com>")
    "John"

    ... or returns the address if none is given.
    >>> extract_author_name("noname@example.com")
    "noname@example.com"
    """
    match = re.match('^(.*?)<.*?>$', email)
    if match:
        return match.group(1).strip()
    return email

def shorten_sha1(sha1):
    if re.match('[a-z\d]{20,40}', sha1):
        sha1 = sha1[:10]
    return sha1

app.jinja_env.filters['u'] = force_unicode
app.jinja_env.filters['timesince'] = timesince
app.jinja_env.filters['shorten_sha1'] = shorten_sha1
app.jinja_env.filters['shorten_message'] = lambda msg: msg.split('\n')[0]
app.jinja_env.filters['pygmentize'] = pygmentize
app.jinja_env.filters['is_binary'] = guess_is_binary
app.jinja_env.filters['is_image'] = guess_is_image
app.jinja_env.filters['shorten_author'] = extract_author_name

def subpaths(path):
    """
    Yields a `(last part, subpath)` tuple for all possible sub-paths of `path`.

    >>> list(subpaths("foo/bar/spam"))
    [('foo', 'foo'), ('bar', 'foo/bar'), ('spam', 'foo/bar/spam')]
    """
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
        self.GET = query_string_to_dict(env.get('QUERY_STRING', ''))
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
    """ Shows a list of all repos and can be sorted by last update. """
    def view(self):
        self['repos'] = repos = []
        for name in app.repos.iterkeys():
            repo = get_repo(name)
            refs = [repo[ref_hash] for ref_hash in repo.get_refs().itervalues()]
            refs.sort(key=lambda obj:getattr(obj, 'commit_time', None),
                      reverse=True)
            last_updated_at = None
            if refs:
                last_updated_at = refs[0].commit_time
            repos.append((name, last_updated_at))
        if 'by-last-update' in self.GET:
            repos.sort(key=lambda x: x[1], reverse=True)
        else:
            repos.sort(key=lambda x: x[0])

class BaseRepoView(BaseView):
    def __init__(self, env, repo, commit_id, path=None):
        self['repo'] = repo = get_repo(repo)
        self['commit_id'] = commit_id
        self['commit'], isbranch = self.get_commit(repo, commit_id)
        self['branch'] = commit_id if isbranch else 'master'
        self['branches'] = repo.get_branch_names(exclude=[commit_id])
        self['path'] = path
        if path:
            self['subpaths'] = list(subpaths(path))
        self['build_url'] = self.build_url
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
        """ Builds url relative to the current repo + commit """
        if view is None:
            view = self.__class__.__name__
        default_kwargs = {
            'repo': self['repo'].name,
            'commit_id': self['commit_id']
        }
        if view == 'history' and kwargs.get('path') is None:
            kwargs['path'] = ''
        return app.build_url(view, **dict(default_kwargs, **kwargs))


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

@route('/:repo:/tree/:commit_id:/(?P<path>.*)', 'history')
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

@route('/:repo:/blob/:commit_id:/(?P<path>.*)', 'view_blob')
class BlobView(BaseBlobView, TreeViewMixin):
    """ Shows a single file, syntax highlighted """
    def view(self):
        BaseBlobView.view(self)
        TreeViewMixin.view(self)
        self['raw_url'] = self.build_url('raw_blob', path=self['path'])
        self['too_large'] = sum(map(len, self['blob'].chunked)) > 100*1024


@route('/:repo:/raw/:commit_id:/(?P<path>.*)', 'raw_blob')
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
                mime = 'appliication/octet-stream'
            return mime, encoding
        else:
            return 'text/plain', 'utf-8'


@route('/:repo:/commit/:commit_id:/', 'view_commit')
class CommitView(BaseRepoView):
    """ Shows a single commit diff """
    def view(self):
        pass


@route('/static/(?P<path>.+)', 'static')
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
