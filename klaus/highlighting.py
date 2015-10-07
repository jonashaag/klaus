from pygments import highlight
from pygments.lexers import get_lexer_for_filename, \
                            guess_lexer, ClassNotFound, TextLexer
from pygments.formatters import HtmlFormatter

from klaus import markup


class KlausDefaultFormatter(HtmlFormatter):
    def __init__(self, **kwargs):
        HtmlFormatter.__init__(self, linenos='table', lineanchors='L',
                               linespans='L', anchorlinenos=True, **kwargs)

    def _format_lines(self, tokensource):
        for tag, line in HtmlFormatter._format_lines(self, tokensource):
            if tag == 1:
                # sourcecode line
                line = '<span class=line>%s</span>' % line
            yield tag, line


def pygmentize(code, filename, render_markup):
    """Render code using Pygments, markup (markdown, rst, ...) using the
    corresponding renderer, if available.

    :param code: the program code to highlight, str
    :param filename: name of the source file the code is taken from, str
    :param render_markup: whether to render markup if possible, bool
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
