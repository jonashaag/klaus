import os
import stat
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

def pygmentize(code, language=None, formatter=HtmlFormatter(linenos=True)):
    if language is None:
        lexer = guess_lexer(code)
    else:
        lexer = get_lexer_by_name(language, stripall=True, tabsize=4)
    return highlight(code, lexer, formatter)

def timesince(when, now=time.time):
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

    if len(result) > 1 and result[0][1] == 'month':
        if n == 1:
            # 1 month, 3 weeks --> 7 weeks
            result = [(result[1][0] + 4, 'week')]
        else:
            # 2 months, 1 week -> 2 months
            result = result[:1]

    return ', '.join('%d %s%s' % (n, unit, 's' if n != 1 else '')
                     for n, unit in result[:2])

app.jinja_env.filters['timesince'] = timesince
app.jinja_env.filters['shorten_id'] = lambda id: id[:7]
app.jinja_env.filters['shorten_message'] = lambda msg: msg.split('\n')[0]
app.jinja_env.filters['pygmentize'] = pygmentize

def get_repo(name):
    try:
        return Repo(name, app.repos[name])
    except KeyError:
        raise HttpError(404, 'No repository named "%s"' % name)

def get_repo_and_commit(repo_name, commit_id):
    repo = get_repo(repo_name)
    try:
        commit = repo.get_branch_or_commit(commit_id)
        if not isinstance(commit, Commit):
            raise KeyError
    except KeyError:
        raise HttpError(404, '"%s" has no commit "%s"' % (repo.name, commit_id))
    return repo, commit

def get_tree_or_blob_url(repo, commit_id, tree_entry):
    if tree_entry.mode & stat.S_IFDIR:
        view = 'view_tree'
    else:
        view = 'view_blob'
    return app.build_url(view,
        repo=repo.name, commit_id=commit_id, path=tree_entry.path)

def make_title(repo, branch, path):
    if path:
        return '%s in %s/%s' % (path, repo.name, branch)
    else:
        return '%s/%s' % (repo.name, branch)

def guess_is_binary(data):
    return '\0' in data

@app.route('/')
def repo_list(env):
    return {'repos': app.repos.items()}

@app.route('/:repo:/')
def view_repo(env, repo):
    redirect_to = app.build_url('view_tree', repo=repo, commit_id='master', path='')
    return '302 Move On', {'Location': redirect_to}, ''

@app.route('/:repo:/tree/:commit_id:/(?P<path>.*)')
def view_tree(env, repo, commit_id, path):
    repo, commit = get_repo_and_commit(repo, commit_id)
    files = ((name, get_tree_or_blob_url(repo, commit_id, entry))
             for name, entry in repo.listdir(commit, path))
    return {'repo': repo, 'files': files, 'path': path, 'commit_id': commit_id,
            'title': make_title(repo, commit_id, path)}

@app.route('/:repo:/history/:commit_id:/(?P<path>.*)')
def history(env, repo, commit_id, path):
    repo, commit = get_repo_and_commit(repo, commit_id)
    try:
        page = int(env['QUERY_STRING'].replace('page=', ''))
    except (KeyError, ValueError):
        page = 0
    this_url = app.build_url('history', repo=repo.name, commit_id=commit_id, path=path)
    urls = {'next': this_url + '?page=%d' % (page+1),
            'prev': this_url + '?page=%d' % (page-1)}
    return {'repo': repo, 'path': path, 'page': page, 'urls': urls,
            'title': make_title(repo, commit_id, path)}

@app.route('/:repo:/blob/:commit_id:/(?P<path>.*)')
def view_blob(env, repo, commit_id, path):
    repo, commit = get_repo_and_commit(repo, commit_id)
    directory, filename = os.path.split(path.strip('/'))
    blob = repo[repo.get_tree(commit, directory)[filename][1]]
    if '/raw/' in env['PATH_INFO']:
        raw_data = blob.data
        mime = 'application/octet-stream' if guess_is_binary(filename) else 'text/plain'
        return '200 yo', {'Content-Type': mime}, raw_data
    else:
        return {'blob': blob, 'title': make_title(repo, commit_id, path),
                'raw_url': app.build_url('raw_file', repo=repo.name,
                                          commit_id=commit_id, path=path)}

@app.route('/:repo:/raw/:commit_id:/(?P<path>.*)')
def raw_file(*args, **kwargs):
    return view_blob(*args, **kwargs)

@app.route('/:repo:/commit/:id:/')
def view_commit(env, repo, id):
    repo, commit = get_repo_and_commit(repo, id)
    return {'commit': commit, 'repo': repo}


if app.debug:
    @app.route('/static/(?P<path>.+)')
    def view(env, path):
        path = './static/' + path
        relpath = os.path.join(os.getcwd(), path)
        if os.path.isfile(relpath):
            return open(relpath)
        else:
            raise HttpError(404, 'Not Found')
