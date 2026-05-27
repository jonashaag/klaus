"""Source-code rendering for klaus.

When a SCIP document is available for the file being rendered, syntax classes
and cross-reference links come from SCIP.  Otherwise we fall back to Pygments
(without ctags, since cross-references in the Pygments path are gone).
"""

from html import escape
from typing import Any, Iterator, Optional, Tuple

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import (
    ClassNotFound,
    TextLexer,
    get_lexer_for_filename,
    guess_lexer,
)

from klaus import markup
from klaus.scip_index import Document, Index, Occurrence

# Map SCIP SyntaxKind enum value -> CSS class suffix.  Numbers match
# klaus.scip_pb2.SyntaxKind; using ints avoids importing the proto module
# at top level just for the names.
_SCIP_SYNTAX_CLASSES = {
    1: "comment",
    2: "punctuation-delimiter",
    3: "punctuation-bracket",
    4: "keyword",  # also IdentifierKeyword
    5: "identifier-operator",
    6: "identifier",
    7: "identifier-builtin",
    8: "identifier-null",
    9: "identifier-constant",
    10: "identifier-mutable-global",
    11: "identifier-parameter",
    12: "identifier-local",
    13: "identifier-shadowed",
    14: "identifier-namespace",  # also IdentifierModule
    15: "identifier-function",
    16: "identifier-function-definition",
    17: "identifier-macro",
    18: "identifier-macro-definition",
    19: "identifier-type",
    20: "identifier-builtin-type",
    21: "identifier-attribute",
    22: "regex-escape",
    23: "regex-repeated",
    24: "regex-wildcard",
    25: "regex-delimiter",
    26: "regex-join",
    27: "string-literal",
    28: "string-literal-escape",
    29: "string-literal-special",
    30: "string-literal-key",
    31: "character-literal",
    32: "numeric-literal",
    33: "boolean-literal",
    34: "tag",
    35: "tag-attribute",
    36: "tag-delimiter",
}


class KlausHtmlFormatter(HtmlFormatter):
    """Pygments HTML formatter wired up to klaus's CSS and link conventions."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            linenos="table",
            lineanchors="L",
            linespans="L",
            anchorlinenos=True,
            **kwargs,
        )

    def _format_lines(self, tokensource: Any) -> Iterator[Tuple[int, str]]:
        for tag, line in super()._format_lines(tokensource):  # type: ignore[misc]
            if tag == 1:
                line = f"<span class=line>{line}</span>"
            yield tag, line


def _render_scip_lines(
    source: str, document: Document, index: Index, scip_baseurl: str
) -> str:
    """Render ``source`` as HTML using occurrences from ``document``.

    Produces the same outer structure as Pygments' ``linenos='table'`` mode so
    klaus's CSS and JS keep working: ``<div class=highlight><table
    class=highlighttable>...`` with linenos column and code column.
    """
    lines = source.splitlines(keepends=False)
    linenos_parts = []
    code_parts = []
    for i, line_text in enumerate(lines, start=1):
        anchor = f"L-{i}"
        linenos_parts.append(f'<span class="normal"><a href="#{anchor}">{i}</a></span>')
        rendered_line = _render_scip_line(
            line_text, i - 1, document, index, scip_baseurl
        )
        code_parts.append(
            f'<span id="{anchor}">'
            f'<a id="{anchor}" name="{anchor}"></a>'
            f"<span class=line>{rendered_line}\n</span>"
            f"</span>"
        )

    return (
        '<div class="highlight"><table class="highlighttable"><tr>'
        '<td class="linenos"><div class="linenodiv"><pre>'
        + "\n".join(linenos_parts)
        + "</pre></div></td>"
        '<td class="code"><div><pre><span></span>'
        + "".join(code_parts)
        + "</pre></div></td></tr></table></div>"
    )


def _render_scip_line(
    line_text: str,
    line_index: int,
    document: Document,
    index: Index,
    scip_baseurl: str,
) -> str:
    """Render a single source line, splicing in spans for each occurrence."""
    occurrences = [
        o
        for o in document.occurrences_on_line(line_index)
        if o.range.end_line == line_index  # skip occurrences spanning lines
    ]
    if not occurrences:
        return escape(line_text)

    out = []
    cursor = 0
    for occ in occurrences:
        start = occ.range.start_char
        end = occ.range.end_char
        if start < cursor or end > len(line_text) or start >= end:
            continue
        if start > cursor:
            out.append(escape(line_text[cursor:start]))
        out.append(_render_occurrence(line_text[start:end], occ, index, scip_baseurl))
        cursor = end
    if cursor < len(line_text):
        out.append(escape(line_text[cursor:]))
    return "".join(out)


def _render_occurrence(
    text: str, occ: Occurrence, index: Index, scip_baseurl: str
) -> str:
    classes = []
    css_class = _SCIP_SYNTAX_CLASSES.get(occ.syntax_kind)
    if css_class:
        classes.append(f"scip-{css_class}")
    if occ.is_definition:
        classes.append("scip-definition")

    body = escape(text)
    if occ.symbol and not occ.is_definition:
        defn = index.get_definition(occ.symbol)
        if defn is not None:
            href = f"{scip_baseurl}{defn.relative_path}#L-{defn.line + 1}"
            body = f'<a href="{escape(href)}">{body}</a>'
    if classes:
        body = f'<span class="{" ".join(classes)}">{body}</span>'
    return body


def highlight_or_render(
    code: str,
    filename: str,
    render_markup: bool = True,
    scip_document: Optional[Document] = None,
    scip_index: Optional[Index] = None,
    scip_baseurl: Optional[str] = None,
) -> str:
    """Render code as HTML.

    :param code: source text
    :param filename: name of the source file (used to pick a Pygments lexer
        and decide whether the file is markup)
    :param render_markup: whether to render markup (Markdown, reST, ...) when
        the filename matches a known markup format
    :param scip_document: SCIP ``Document`` for this file, if available.  When
        provided, syntax highlighting and cross-reference links come from
        SCIP.  Without it we fall back to Pygments.
    :param scip_index: the SCIP ``Index`` that ``scip_document`` came from.
        Required when ``scip_document`` is provided.
    :param scip_baseurl: base URL used to build cross-reference hyperlinks.
        Required when ``scip_document`` is provided.
    """
    if render_markup and markup.can_render(filename):
        return markup.render(filename, code)

    if scip_document is not None:
        assert scip_index is not None and scip_baseurl is not None, (
            "scip_index and scip_baseurl are required with scip_document"
        )
        return _render_scip_lines(code, scip_document, scip_index, scip_baseurl)

    try:
        lexer = get_lexer_for_filename(filename, code)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = TextLexer()

    return highlight(code, lexer, KlausHtmlFormatter())
