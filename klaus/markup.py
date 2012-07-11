import os

LANGUAGES = []

try:
    import markdown
    LANGUAGES.append((['.md', '.mkdn'], markdown.markdown))
except ImportError:
    pass

try:
    from docutils.core import publish_parts
    from docutils.writers.html4css1 import Writer

    def render_rest(content):

        # start by h2 and ignore invalid directives and so on (most likely from Sphinx)
        settings = {'initial_header_level': '2', 'report_level':'quiet'}
        return publish_parts(content,
                             writer=Writer(),
                             settings_overrides=settings).get('html_body')

    LANGUAGES.append((['.rst', '.rest'], render_rest))
except ImportError:
    pass


def get_renderer(filename):

    global LANGUAGES
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
