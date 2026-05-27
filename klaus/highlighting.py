"""Source-code rendering for klaus.

When a SCIP document is available for the file being rendered, syntax classes
and cross-reference links come from SCIP.  Otherwise we fall back to Pygments
(without ctags, since cross-references in the Pygments path are gone).
"""

import hashlib
import json
from collections.abc import Iterator
from html import escape
from typing import Any

from pygments import highlight, lex
from pygments.formatters import HtmlFormatter
from pygments.formatters.html import _get_ttype_class
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

    def _format_lines(self, tokensource: Any) -> Iterator[tuple[int, str]]:
        for tag, line in super()._format_lines(tokensource):  # type: ignore[misc]
            if tag == 1:
                line = f"<span class=line>{line}</span>"
            yield tag, line


def _tokenize_per_line(source: str, lexer: Any) -> list[list[tuple[int, int, str]]]:
    """Tokenize ``source`` with Pygments and produce, for each line, a list of
    ``(start_col, end_col, css_class)`` segments covering the full line.

    Segments are non-overlapping and end-exclusive; they together cover the
    whole line including whitespace (whitespace segments may have an empty
    css_class).
    """
    lines: list[list[tuple[int, int, str]]] = [[]]
    col = 0
    for ttype, text in lex(source, lexer):
        if not text:
            continue
        css_class = _get_ttype_class(ttype) or ""
        # A token's text may contain newlines; split so each segment stays on
        # one line.
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if part:
                lines[-1].append((col, col + len(part), css_class))
                col += len(part)
            if i < len(parts) - 1:
                lines.append([])
                col = 0
    # If the source ended with a newline, splitlines drops the trailing empty
    # line; mirror that for consistency with the caller's view.
    if lines and not lines[-1] and source and not source.endswith("\n"):
        lines.pop()
    elif source.endswith("\n") and lines and not lines[-1]:
        lines.pop()
    return lines


def _splice_occurrences(
    segments: list[tuple[int, int, str]],
    occurrences: list[Occurrence],
) -> list[tuple[int, int, str, Occurrence | None]]:
    """Layer SCIP occurrences over Pygments-derived segments.

    The result is a list of ``(start, end, css_class, occurrence)`` tuples
    where ``occurrence`` is set when the segment lies inside a SCIP
    occurrence's range.  Pygments segments are split at occurrence boundaries
    as needed so each output segment is fully inside or outside an occurrence.
    """
    if not occurrences:
        return [(s, e, c, None) for s, e, c in segments]

    # Sort occurrences by start position; assume they don't overlap (SCIP
    # normally doesn't emit overlapping ranges on a line).
    occurrences = sorted(occurrences, key=lambda o: o.range.start_char)
    out: list[tuple[int, int, str, Occurrence | None]] = []
    occ_idx = 0
    for seg_start, seg_end, css in segments:
        cursor = seg_start
        while cursor < seg_end:
            # Skip occurrences entirely before the cursor.
            while (
                occ_idx < len(occurrences)
                and occurrences[occ_idx].range.end_char <= cursor
            ):
                occ_idx += 1
            if occ_idx >= len(occurrences):
                out.append((cursor, seg_end, css, None))
                cursor = seg_end
                break
            occ = occurrences[occ_idx]
            occ_start = occ.range.start_char
            occ_end = occ.range.end_char
            if occ_start >= seg_end:
                out.append((cursor, seg_end, css, None))
                cursor = seg_end
                break
            if cursor < occ_start:
                out.append((cursor, occ_start, css, None))
                cursor = occ_start
            slice_end = min(seg_end, occ_end)
            out.append((cursor, slice_end, css, occ))
            cursor = slice_end
    return out


def _symbol_id(symbol: str) -> str:
    """Stable short hash usable as an HTML ``id`` for a SCIP symbol."""
    return "sym-" + hashlib.sha1(symbol.encode("utf-8")).hexdigest()[:12]


def _render_segment(
    text: str,
    pygments_class: str,
    occ: Occurrence | None,
    index: Index,
    scip_baseurl: str,
    anchored_definitions: set[str],
) -> str:
    """Render one slice of a line as HTML.

    ``anchored_definitions`` tracks symbol IDs that already received an
    ``id=...`` attribute in this document, so duplicate definitions (e.g.
    forward declarations) don't produce duplicate HTML IDs.  The set is
    updated in place.
    """
    classes: list[str] = []
    if pygments_class:
        classes.append(pygments_class)
    has_symbol = occ is not None and bool(occ.symbol)
    if has_symbol:
        classes.append("scip-occurrence")
    if occ is not None:
        scip_class = _SCIP_SYNTAX_CLASSES.get(occ.syntax_kind)
        if scip_class:
            classes.append(f"scip-{scip_class}")
        if occ.is_definition:
            classes.append("scip-definition")
        elif has_symbol:
            classes.append("scip-reference")

    body = escape(text)
    attrs: list[str] = []
    href: str | None = None
    if has_symbol:
        assert occ is not None
        sym_id = _symbol_id(occ.symbol)
        attrs.append(f'data-sym="{sym_id}"')
        display = index.get_display_name(occ.symbol)
        if display:
            attrs.append(f'data-display="{escape(display, quote=True)}"')
        defn = index.get_definition(occ.symbol)
        if defn is not None:
            def_href = f"{scip_baseurl}{defn.relative_path}#{sym_id}"
            attrs.append(f'data-defhref="{escape(def_href, quote=True)}"')
            attrs.append(
                f'data-defloc="{escape(defn.relative_path, quote=True)}:{defn.line + 1}"'
            )
            if not occ.is_definition:
                href = def_href
        refs = index.get_references(occ.symbol)
        if refs:
            refs_json = json.dumps(
                [
                    [
                        r.relative_path,
                        r.line + 1,
                        f"{scip_baseurl}{r.relative_path}#L-{r.line + 1}",
                    ]
                    for r in refs
                ],
                separators=(",", ":"),
            )
            attrs.append(f"data-refs='{escape(refs_json, quote=True)}'")
        if occ.is_definition and sym_id not in anchored_definitions:
            anchored_definitions.add(sym_id)
            attrs.append(f'id="{sym_id}"')

    if href:
        attrs_str = (" " + " ".join(attrs)) if attrs else ""
        cls = " ".join(classes)
        return f'<a class="{cls}" href="{escape(href)}"{attrs_str}>{body}</a>'
    if classes or attrs:
        attrs_str = (" " + " ".join(attrs)) if attrs else ""
        cls = " ".join(classes)
        return f'<span class="{cls}"{attrs_str}>{body}</span>'
    return body


def _render_scip_lines(
    source: str,
    document: Document,
    index: Index,
    scip_baseurl: str,
    lexer: Any,
) -> str:
    """Render ``source`` as HTML using Pygments tokens overlaid with SCIP
    occurrences.

    Produces the same outer structure as Pygments' ``linenos='table'`` mode so
    klaus's CSS and JS keep working.
    """
    raw_lines = source.splitlines(keepends=False)
    pygments_segments = _tokenize_per_line(source, lexer)
    # Make sure we have one segment list per source line.
    while len(pygments_segments) < len(raw_lines):
        pygments_segments.append([])

    anchored_definitions: set[str] = set()

    linenos_parts: list[str] = []
    code_parts: list[str] = []
    for i, line_text in enumerate(raw_lines, start=1):
        anchor = f"L-{i}"
        linenos_parts.append(f'<span class="normal"><a href="#{anchor}">{i}</a></span>')
        segments = pygments_segments[i - 1]
        if not segments and line_text:
            # Fallback: lexer produced nothing for this line; treat the whole
            # line as plain text.
            segments = [(0, len(line_text), "")]
        occurrences = [
            o
            for o in document.occurrences_on_line(i - 1)
            if o.range.end_line == i - 1  # skip multi-line ranges
        ]
        spliced = _splice_occurrences(segments, occurrences)
        rendered = "".join(
            _render_segment(
                line_text[s:e], css, occ, index, scip_baseurl, anchored_definitions
            )
            for s, e, css, occ in spliced
        )
        code_parts.append(
            f'<span id="{anchor}">'
            f'<a id="{anchor}" name="{anchor}"></a>'
            f"<span class=line>{rendered}\n</span>"
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


def highlight_or_render(
    code: str,
    filename: str,
    render_markup: bool = True,
    scip_document: Document | None = None,
    scip_index: Index | None = None,
    scip_baseurl: str | None = None,
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

    try:
        lexer = get_lexer_for_filename(filename, code)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = TextLexer()

    if scip_document is not None:
        assert (
            scip_index is not None and scip_baseurl is not None
        ), "scip_index and scip_baseurl are required with scip_document"
        return _render_scip_lines(code, scip_document, scip_index, scip_baseurl, lexer)

    return highlight(code, lexer, KlausHtmlFormatter())
