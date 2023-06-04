import os
from typing import List, Tuple, Callable, Optional

LANGUAGES: List[Tuple[List[str], Callable[[str], str]]] = []


def get_renderer(filename: str) -> Optional[Callable[[str], str]]:
    _, ext = os.path.splitext(filename)
    for extensions, renderer in LANGUAGES:
        if ext in extensions:
            return renderer
    return None


def can_render(filename):
    return get_renderer(filename) is not None


def render(filename, content=None) -> str:
    if content is None:
        with open(filename) as f:
            content = f.read()

    renderer = get_renderer(filename)
    assert renderer is not None, "No renderer for {}".format(filename)
    return renderer(content)


def _load_markdown() -> None:
    try:
        import markdown
    except ImportError:
        return

    def render_markdown(content):
        return markdown.markdown(content, extensions=["toc", "extra"])

    LANGUAGES.append(([".md", ".mkdn", ".mdwn", ".markdown"], render_markdown))


def _load_restructured_text() -> None:
    try:
        from docutils.core import publish_parts
        from docutils.writers.html4css1 import Writer
    except ImportError:
        return

    def render_rest(content):
        # start by h2 and ignore invalid directives and so on
        # (most likely from Sphinx)
        settings = {"initial_header_level": 2, "report_level": 0}
        return publish_parts(content, writer=Writer(), settings_overrides=settings).get(
            "html_body"
        )

    LANGUAGES.append(([".rst", ".rest"], render_rest))


for loader in [_load_markdown, _load_restructured_text]:
    loader()
