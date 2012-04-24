# -*- encoding: utf-8 -*-

from dulwich.repo import Repo
from dulwich.server import DictBackend
from dulwich.web import HTTPGitRequest
from dulwich.web import HTTPGitApplication, GunzipFilter


class AuthenticatedGitApplication(HTTPGitApplication):
    """Add basic HTTP authentication to ``git push``."""

    def __init__(self, app, backend, dumb=False, handlers=None):
        super(AuthenticatedGitApplication, self).__init__(backend, dumb, handlers)
        self.app = app

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        method = environ['REQUEST_METHOD']
        req = HTTPGitRequest(environ, start_response, dumb=self.dumb,
                             handlers=self.handlers)
        # environ['QUERY_STRING'] has qs args
        handler = None
        for smethod, spath in self.services.iterkeys():
            if smethod != method:
                continue
            mat = spath.search(path)
            if mat:
                handler = self.services[smethod, spath]
                break
        if handler is None:
            return self.app(environ, start_response)
        return handler(req, self.backend, mat)


def make_app(app, repos):

    # DictBackend uses keys with a leading slash
    backend = DictBackend(dict(('/'+k, Repo(v)) for k, v in repos.iteritems()))
    wsgi_app = app.wsgi_app

    app = AuthenticatedGitApplication(app, backend, dumb=False, handlers=None)
    app = GunzipFilter(app)
    app.wsgi_app = wsgi_app

    return app
