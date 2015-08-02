# encoding: utf-8
import os
import re
import time
import datetime
import mimetypes
import locale
import six
try:
    import chardet
except ImportError:
    chardet = None

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, guess_lexer, ClassNotFound, TextLexer
from pygments.formatters import HtmlFormatter

from humanize import naturaltime

from klaus import markup


class SubUri(object):
    """
    WSGI middleware that tweaks the WSGI environ so that it's possible to serve
    the wrapped app (klaus) under a sub-URL and/or to use a different HTTP
    scheme (http:// vs. https://) for proxy communication.

    This is done by making your proxy pass appropriate HTTP_X_SCRIPT_NAME and
    HTTP_X_SCHEME headers.

    For instance if you have klaus mounted under /git/ and your site uses SSL
    (but your proxy doesn't), make it pass ::

        X-Script-Name = '/git'
        X-Scheme = 'https'

    Snippet stolen from http://flask.pocoo.org/snippets/35/
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name.rstrip('/')

        if script_name and environ['PATH_INFO'].startswith(script_name):
            # strip `script_name` from PATH_INFO
            environ['PATH_INFO'] = environ['PATH_INFO'][len(script_name):]

        if 'HTTP_X_SCHEME' in environ:
            environ['wsgi.url_scheme'] = environ['HTTP_X_SCHEME']

        return self.app(environ, start_response)


class KlausFormatter(HtmlFormatter):
    def __init__(self):
        HtmlFormatter.__init__(self, linenos='table', lineanchors='L',
                               linespans='L', anchorlinenos=True)

    def _format_lines(self, tokensource):
        for tag, line in HtmlFormatter._format_lines(self, tokensource):
            if tag == 1:
                # sourcecode line
                line = '<span class=line>%s</span>' % line
            yield tag, line


def pygmentize(code, filename=None, render_markup=True):
    """
    Renders code using Pygments, markup (markdown, rst, ...) using the
    corresponding renderer, if available.
    """
    if render_markup and markup.can_render(filename):
        return markup.render(filename, code)

    try:
        lexer = get_lexer_for_filename(filename, code)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = TextLexer()
    return highlight(code, lexer, KlausFormatter())


def timesince(when, now=time.time):
    """ Returns the difference between `when` and `now` in human readable form. """
    return naturaltime(now() - when)


def formattimestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%b %d, %Y %H:%M:%S')


def guess_is_binary(dulwich_blob):
    return any(b'\0' in chunk for chunk in dulwich_blob.chunked)


def guess_is_image(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime is None:
        return False
    return mime.startswith('image/')


def encode_for_git(s):
    # XXX This assumes everything to be UTF-8 encoded
    return s.encode('utf8')


def decode_from_git(b):
    # XXX This assumes everything to be UTF-8 encoded
    return b.decode('utf8')


def force_unicode(s):
    """ Does all kind of magic to turn `s` into unicode """
    # It's already unicode, don't do anything:
    if isinstance(s, six.text_type):
        return s

    # Try some default encodings:
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError as exc:
        pass
    try:
        return s.decode(locale.getpreferredencoding())
    except UnicodeDecodeError:
        pass

    if chardet is not None:
        # Try chardet, if available
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)

    raise exc  # Give up.


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
        sha1 = sha1[:7]
    return sha1


def parent_directory(path):
    return os.path.split(path)[0]


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


def shorten_message(msg):
    return msg.split('\n')[0]


def replace_dupes(ls, replacement):
    """
    Replaces items in `ls` that are equal to their predecessors with `replacement`.

    >>> ls = [1, 2, 2, 3, 2, 2, 2]
    >>> replace_dupes(x, 'x')
    >>> ls
    [1, 2, 'x', 3, 2, 'x', 'x']
    """
    last = object()
    for i, elem in enumerate(ls):
        if last == elem:
            ls[i] = replacement
        else:
            last = elem


try:
    from subprocess import check_output
except ImportError:
    # Python < 2.7 fallback, stolen from the 2.7 stdlib
    def check_output(*popenargs, **kwargs):
        from subprocess import Popen, PIPE, CalledProcessError
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = Popen(stdout=PIPE, *popenargs, **kwargs)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd, output=output)
        return output


def guess_git_revision():
    """
    Try to guess whether this instance of klaus is run directly from a klaus
    git checkout.  If it is, guess and return the currently checked-out commit
    SHA.  If it's not (installed using pip, setup.py or the like), return None.

    This is used to display the "powered by klaus $VERSION" footer on each page,
    $VERSION being either the SHA guessed by this function or the latest release number.
    """
    git_dir = os.path.join(os.path.dirname(__file__), '..', '.git')
    try:
        return check_output(
            ['git', 'log', '--format=%h', '-n', '1'],
            cwd=git_dir
        ).strip()
    except OSError:
        # Either the git executable couldn't be found in the OS's PATH
        # or no ".git" directory exists, i.e. this is no "bleeding-edge" installation.
        return None
