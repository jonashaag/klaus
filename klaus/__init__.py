import os
from functools import partial, wraps

import dulwich.web
from jinja2 import StrictUndefined
from flask import Flask
import httpauth

from klaus import views, utils
from klaus.repo import FancyRepo


KLAUS_ROOT = os.path.dirname(__file__)

try:
    KLAUS_VERSION = utils.check_output(['git', 'log', '--format=%h', '-n', '1'])
except utils.CalledProcessError:
    KLAUS_VERSION = '0.2'


class Klaus(Flask):
    jinja_options = {
        'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_'],
        'undefined': StrictUndefined
    }

    def __init__(self, repos, site_title, use_smarthttp):
        self.repos = map(FancyRepo, repos)
        self.repo_map = dict((repo.name, repo) for repo in self.repos)
        self.site_title = site_title
        self.use_smarthttp = use_smarthttp

        Flask.__init__(self, __name__)

        self.setup_routes()

    def create_jinja_environment(self):
        """ Called by Flask.__init__ """
        env = super(Klaus, self).create_jinja_environment()
        for func in [
            'force_unicode',
            'timesince',
            'shorten_sha1',
            'shorten_message',
            'pygmentize',
            'guess_is_binary',
            'guess_is_image',
            'extract_author_name',
        ]:
            env.filters[func] = getattr(utils, func)

        env.globals['KLAUS_VERSION'] = KLAUS_VERSION
        env.globals['USE_SMARTHTTP'] = self.use_smarthttp
        env.globals['SITE_TITLE'] = self.site_title

        return env

    def setup_routes(self):
        for endpoint, rule in [
            ('repo_list',   '/'),
            ('blob',        '/<repo>/blob/<commit_id>/'),
            ('blob',        '/<repo>/blob/<commit_id>/<path:path>'),
            ('raw',         '/<repo>/raw/<commit_id>/'),
            ('raw',         '/<repo>/raw/<commit_id>/<path:path>'),
            ('commit',      '/<repo>/commit/<commit_id>/'),
            ('history',     '/<repo>/tree/<commit_id>/'),
            ('history',     '/<repo>/tree/<commit_id>/<path:path>'),
        ]:
            view_func = getattr(views, endpoint)
            bound_view_func = wraps(view_func)(partial(view_func, self))
            self.add_url_rule(rule, view_func=bound_view_func)



def make_app(repos, site_title, use_smarthttp=False, htdigest_file=None):
    app = Klaus(
        repos,
        site_title,
        use_smarthttp,
    )

    if use_smarthttp:
        dulwich_backend = dulwich.server.DictBackend(
            dict(('/'+repo.name, repo) for repo in app.repos)
        )
        app.wsgi_app = dulwich.web.make_wsgi_chain(
            backend=dulwich_backend,
            fallback_app=app.wsgi_app,
        )

        PATTERN = '^/[^/]+/(info/refs|git-.+-pack)$'
        if htdigest_file:
            app.wsgi_app = httpauth.DigestFileHttpAuthMiddleware(
                htdigest_file,
                wsgi_app=app.wsgi_app,
                routes=[PATTERN],
            )
        else:
            app.wsgi_app = utils.AccessDeniedMiddleware(PATTERN, app.wsgi_app)

    return app
