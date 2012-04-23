# -*- encoding: utf-8 -*-

import sys
import os

from jinja2 import Environment, FileSystemLoader

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.wsgi import SharedDataMiddleware

from klaus import views
from klaus.utils import query_string_to_dict
from klaus.utils import force_unicode, timesince, shorten_sha1, pygmentize, \
                        guess_is_binary, guess_is_image, extract_author_name


KLAUS_ROOT = os.path.join(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(KLAUS_ROOT, 'templates')

try:
    KLAUS_VERSION = ' ' + open(os.path.join(KLAUS_ROOT, '.git/refs/heads/master')).read()[:7]
except IOError:
    KLAUS_VERSION = ''


urlmap = Map([
    Rule('/', endpoint='repo_list'),
    Rule('/<repo>/blob/<commit_id>/', defaults={'path': ''}, endpoint='blob'),
    Rule('/<repo>/blob/<commit_id>/<path:path>', endpoint='blob'),
    Rule('/<repo>/raw/<commit_id>/', defaults={'path': ''}, endpoint='raw'),
    Rule('/<repo>/raw/<commit_id>/<path:path>', endpoint='raw'),
    Rule('/<repo>/commit/<commit_id>/', endpoint='commit'),
    Rule('/<repo>/tree/<commit_id>/', defaults={'path': ''}, endpoint='history'),
    Rule('/<repo>/tree/<commit_id>/<path:path>', endpoint='history')
])


class SubUri(object):
    """Wrap the application in this middleware to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is different
    than what is used locally. If you don't send HTTP_X_SCRIPT_NAME,
    you can optionally use ``klaus --prefix=/myprefix/``.

    -- via http://flask.pocoo.org/snippets/35/
    """
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', self.prefix)
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


class Klaus(object):

    def __init__(self, repos):

        self.repos = repos
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                                     extensions=['jinja2.ext.autoescape'],
                                     autoescape=True)
        self.jinja_env.globals['KLAUS_VERSION'] = KLAUS_VERSION

    def render_template(self, template_name, **kwargs):
        return self.jinja_env.get_template(template_name).render(**kwargs)

    def dispatch(self, request, start_response):
        adapter = urlmap.bind_to_environ(request.environ)
        request.adapter = adapter

        try:
            endpoint, values = adapter.match()
            if hasattr(endpoint, '__call__'):
                handler = endpoint
            else:
                handler = getattr(views, endpoint)
            return handler(self, request, **values)
        except NotFound, e:
            return Response('Not Found', 404)
        except HTTPException, e:
            return e
        except InternalServerError, e:
            return Response(e, 500)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        request.GET = query_string_to_dict(environ.get('QUERY_STRING', ''))

        response = self.dispatch(request, start_response)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def make_app(repos, prefix='/'):

    repos = dict(
        (repo.rstrip(os.sep).split(os.sep)[-1].replace('.git', ''), repo)
        for repo in (repos or os.environ.get('KLAUS_REPOS', '').split())
    )

    app = Klaus(repos)

    app.jinja_env.filters['u'] = force_unicode
    app.jinja_env.filters['timesince'] = timesince
    app.jinja_env.filters['shorten_sha1'] = shorten_sha1
    app.jinja_env.filters['shorten_message'] = lambda msg: msg.split('\n')[0]
    app.jinja_env.filters['pygmentize'] = pygmentize
    app.jinja_env.filters['is_binary'] = guess_is_binary
    app.jinja_env.filters['is_image'] = guess_is_image
    app.jinja_env.filters['shorten_author'] = extract_author_name

    app.wsgi_app = SubUri(app.wsgi_app, prefix=prefix)
    app = SharedDataMiddleware(app, {
        '/static/': os.path.join(os.path.dirname(__file__), 'static/')
    })

    return app
