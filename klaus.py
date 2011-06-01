import os
import time
from functools import wraps

from dulwich.objects import Commit

from jinja2 import Environment, FileSystemLoader

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from nano import NanoApplication, HttpError
from repo import Repo

class KlausApplication(NanoApplication):
    def __init__(self, *args, **kwargs):
        super(KlausApplication, self).__init__(*args, **kwargs)
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self.jinja_env.globals['build_url'] = self.build_url

    def route(self, pattern):
        super_decorator = super(KlausApplication, self).route(pattern)
        def decorator(callback):
            @wraps(callback)
            def wrapper(*args, **kwargs):
                res = callback(*args, **kwargs)
                if isinstance(res, dict):
                    res = self.render_template(callback.__name__ + '.html', **res)
                return res
            return super_decorator(wrapper)
        return decorator

    def render_template(self, template_name, **kwargs):
        return self.jinja_env.get_template(template_name).render(**kwargs)

app = KlausApplication(debug=True, default_content_type='text/html')

#pygments_formatter = HtmlFormatter(linenos=True, cssclass='code')

def pygmentize(code, language=None, formatter=HtmlFormatter(linenos=True)):
    if language is None:
        lexer = guess_lexer(code)
    else:
        lexer = get_lexer_by_name(language, stripall=True, tabsize=4)
    return highlight(code, lexer, formatter)

def timesince(when, now=time.time):
    delta = time.time() - when
    result = []
    for unit, seconds in [
        ('year', 365*24*60*60),
        ('month', 30*24*60*60),
        ('week', 7*24*60*60),
        ('day', 24*60*60),
        ('hour', 60*60),
        ('minute', 60),
        ('second', 1),
    ]:
        if delta > seconds:
            n = int(delta/seconds)
            delta -= n*seconds
            result.append((n, unit))

    if result[0][1] != 'year':
        result = result[1:]
    return ', '.join('%d %s%s' % (n, unit, 's' if n != 1 else '')
                     for n, unit in result[:2])

app.jinja_env.filters['timesince'] = timesince
app.jinja_env.filters['shorten_id'] = lambda id: id[:7]
app.jinja_env.filters['pygmentize'] = pygmentize

def get_repo(name):
    try:
        return Repo(name, app.repos[name])
    except KeyError:
        raise HttpError(404, 'No repository named "%s"' % name)

@app.route('/')
def repo_list(env):
    return {'repos' : app.repos.items()}

@app.route('/:repo:/')
def view_repo(env, repo):
    return {'repo' : get_repo(repo)}

@app.route('/:repo:/commit/:id:/')
def view_commit(env, repo, id):
    repo = get_repo(repo)
    try:
        commit = repo[id]
        if not isinstance(commit, Commit):
            raise KeyError
    except KeyError:
        raise HttpError(404, '"%s" has no commit "%s"' % (repo.name, id))
    return {'commit' : commit, 'repo' : repo}


if app.debug:
    @app.route('/static/(?P<path>.+)')
    def view(env, path):
        path = './static/' + path
        relpath = os.path.join(os.getcwd(), path)
        if os.path.isdir(relpath):
            return index(relpath, path)
        elif os.path.isfile(relpath):
            return open(relpath)
        else:
            raise HttpError(404, 'Not Found')
