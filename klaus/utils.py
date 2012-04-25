# -*- encoding: utf-8 -*-

import re
import time
import mimetypes
import urlparse

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, \
                            guess_lexer, ClassNotFound
from pygments.formatters import HtmlFormatter

try:
    from markdown import markdown
except ImportError:
    markdown = None

# try:
#     from docutils.core import publish_parts as rst
# except ImportError:
#     rst = None


def query_string_to_dict(query_string):
    """ Transforms a POST/GET string into a Python dict """
    return dict((k, v[0]) for k, v in urlparse.parse_qs(query_string).iteritems())


class KlausFormatter(HtmlFormatter):
    def __init__(self):
        HtmlFormatter.__init__(self, linenos='table', lineanchors='L',
                               anchorlinenos=True)

    def _format_lines(self, tokensource):
        for tag, line in HtmlFormatter._format_lines(self, tokensource):
            if tag == 1:
                # sourcecode line
                line = '<span class=line>%s</span>' % line
            yield tag, line


def pygmentize(code, filename=None, language=None):

    if markdown and any(filter(lambda ext: filename.endswith(ext), ['.md', '.mkdown'])):
        return markdown(code)

    # if rst and any(filter(lambda ext: filename.endswith(ext), ['.rst', '.rest'])):
    #     settings = {'initial_header_level': 1, 'doctitle_xform': 0 }
    #     parts = rst(code, writer_name='html', settings_overrides=settings)
    #     return parts['body']

    if language:
        lexer = get_lexer_by_name(language)
    else:
        try:
            lexer = get_lexer_for_filename(filename)
        except ClassNotFound:
            lexer = guess_lexer(code)

    return highlight(code, lexer, KlausFormatter())


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
