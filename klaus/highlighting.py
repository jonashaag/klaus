from six.moves import filter

from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename, \
                            guess_lexer, ClassNotFound, TextLexer
from pygments.formatters import HtmlFormatter

from klaus import markup


CTAGS_SUPPORTED_LANGUAGES = (
    "Asm Awk Basic C C# C++ Cobol DosBatch Eiffel Erlang Fortran HTML Java "
    "JavaScript Lisp Lua Make Makefile MatLab OCaml PHP Pascal Perl Python "
    "REXX Ruby SML SQL Scheme Sh Tcl Tex VHDL Verilog Vim"
    # Not supported by Pygments: Asp Ant BETA Flex SLang Vera YACC
).split()
PYGMENTS_CTAGS_LANGUAGE_MAP = dict((get_lexer_by_name(l).name, l) for l in CTAGS_SUPPORTED_LANGUAGES)


class KlausDefaultFormatter(HtmlFormatter):
    def __init__(self, language, ctags, **kwargs):
        HtmlFormatter.__init__(self, linenos='table', lineanchors='L',
                               linespans='L', anchorlinenos=True, **kwargs)
        self.language = language
        if ctags:
            # Use Pygments' ctags system but provide our own CTags instance
            self.tagsfile = True  # some trueish object
            self._ctags = ctags

    def _format_lines(self, tokensource):
        for tag, line in HtmlFormatter._format_lines(self, tokensource):
            if tag == 1:
                # sourcecode line
                line = '<span class=line>%s</span>' % line
            yield tag, line

    def _lookup_ctag(self, token):
        matches = list(self._get_all_ctags_matches(token))
        best_matches = list(self.get_best_ctags_matches(matches))
        if not best_matches:
            return None, None
        else:
            return (best_matches[0]['file'].decode("utf-8"),
                    best_matches[0]['lineNumber'])

    def _get_all_ctags_matches(self, token):
        FIELDS = ('file', 'lineNumber', 'kind', b'language')
        from ctags import TagEntry
        entry = TagEntry()  # target "buffer" for ctags
        if self._ctags.find(entry, token.encode("utf-8"), 0):
            yield dict((k, entry[k]) for k in FIELDS)
            while self._ctags.findNext(entry):
                yield dict((k, entry[k]) for k in FIELDS)

    def get_best_ctags_matches(self, matches):
        if self.language is None:
            return matches
        else:
            return filter(lambda match: match[b'language'] == self.language.encode("utf-8"), matches)


class KlausPythonFormatter(KlausDefaultFormatter):
    def get_best_ctags_matches(self, matches):
        # The first ctags match may be an import, which ctags sees as a
        # definition of the tag -- even though it might very well have found
        # the "real" definition of the tag.  Import matches aren't very helpful:
        # In the best case, we are brought to the line where the tag is imported
        # in the same file. But it may also bring us to some completely unrelated
        # import of the tag in some other file.  We change the tag lookup mechanics
        # so that non-import matches are always preferred over import matches.
        return filter(
            lambda match: match['kind'] != b'i',
            super(KlausPythonFormatter, self).get_best_ctags_matches(matches)
        )


def highlight_or_render(code, filename, render_markup=True, ctags=None, ctags_baseurl=None):
    """Render code using Pygments, markup (markdown, rst, ...) using the
    corresponding renderer, if available.

    :param code: the program code to highlight, str
    :param filename: name of the source file the code is taken from, str
    :param render_markup: whether to render markup if possible, bool
    :param ctags: tagsfile obj used for source code hyperlinks, ``ctags.CTags``
    :param ctags_baseurl: base url used for source code hyperlinks, str
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

    formatter_cls = {
        'Python': KlausPythonFormatter,
    }.get(lexer.name, KlausDefaultFormatter)
    if ctags:
        ctags_urlscheme = ctags_baseurl + "%(path)s%(fname)s%(fext)s"
    else:
        ctags_urlscheme = None
    formatter = formatter_cls(
        language=PYGMENTS_CTAGS_LANGUAGE_MAP.get(lexer.name),
        ctags=ctags,
        tagurlformat=ctags_urlscheme,
    )

    return highlight(code, lexer, formatter)
