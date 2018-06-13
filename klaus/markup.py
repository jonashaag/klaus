import os

LANGUAGES = []


def get_renderer(filename):
    _, ext = os.path.splitext(filename)
    for extensions, renderer in LANGUAGES:
        if ext in extensions:
            return renderer


def can_render(filename):
    return get_renderer(filename) is not None


def render(filename, content=None):
    if content is None:
        content = open(filename).read()

    return get_renderer(filename)(content)


def _load_markdown():
    try:
        import markdown
    except ImportError:
        return

    def render_markdown(content):
        return markdown.markdown(content, extensions=['toc', 'extra'])

    LANGUAGES.append((['.md', '.mkdn', '.mdwn', '.markdown'], render_markdown))


def _load_restructured_text():
    try:
        from docutils.core import publish_parts
        from docutils.writers.html4css1 import Writer
    except ImportError:
        return

    def render_rest(content):
        # start by h2 and ignore invalid directives and so on
        # (most likely from Sphinx)
        settings = {'initial_header_level': 2, 'report_level': 'quiet'}
        return publish_parts(content,
                             writer=Writer(),
                             settings_overrides=settings).get('html_body')

    LANGUAGES.append((['.rst', '.rest'], render_rest))


def _load_notebook():
    try:
        import nbformat
        import nbconvert
    except ImportError:
        return

    def render_notebook(content):
        nb = nbformat.reads(content, nbformat.NO_CONVERT)
        (output, resources) = nbconvert.HTMLExporter(template_file='full').from_notebook_node(nb)
        return output

    LANGUAGES.append((['.ipynb'], render_notebook))


for loader in [_load_markdown, _load_restructured_text, _load_notebook]:
    loader()
