# -*- encoding: utf-8 -*-

import re
from crypt import crypt

from werkzeug.wrappers import Request, Response

from dulwich.repo import Repo
from dulwich.server import DictBackend
from dulwich.web import handle_service_request
from dulwich.web import HTTPGitRequest, HTTPGitApplication
from dulwich.web import LimitedInputFilter, GunzipFilter


def authenticated(func, auth={}):
    """This wraps a function around HTTP Basic Authentication using
    a dictionary of {username: lambda passwd: True or False} to verify
    the password using the common htpasswd file.

    Unfortunately we can not use werkzeug's Response object since it
    would result in a major rewrite of the dulwich/web.py module."""

    def dec(req, backend, mat, *args, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Basic Auth failed."""

        service = mat.group().lstrip('/')
        if not req.authorization:
            req.respond(
                status='401 Unauthorized',
                content_type='application/x-%s-result' % service,
                headers=[('WWW-Authenticate', 'Basic realm="Git Smart HTTP"')]
            )
            return ''
        else:
            user, passwd = req.authorization.username, req.authorization.password
            if not auth.get(user, lambda x: False)(passwd):
                req.respond(
                    status='403 Forbidden',
                    content_type='application/x-%s-result' % service
                )
                return ''
        return func(req, backend, mat, *args, **kwargs)
    return dec


class SmartGitRequest(HTTPGitRequest, Request):
    """We use werkzeug's Request object to parse the authorization headers. Due
    the design of Dulwich's we can not use a native Request object."""

    def __init__(self, environ, start_response, dumb=False, handlers=None):
        Request.__init__(self, environ)
        HTTPGitRequest.__init__(self, environ, start_response, dumb, handlers)


class AuthenticatedGitApplication(HTTPGitApplication):
    """Add basic HTTP authentication to ``git push``; pathced to pass
    unknown urls to Klaus.

    Instead of the common URL scheme http://foo.bar/repo.git we can
    safely run klaus and git-http-backend in parallel. Thus to clone
    or push a repository, just use http://foo.bar/repo/ as URL.
    """
    def __init__(self, app, backend, htpasswd):
        super(AuthenticatedGitApplication, self).__init__(backend)

        self.app = app
        self.auth = {}

        if htpasswd:
            for line in open(htpasswd, 'r').readlines():
                username, pwhash = line.rstrip().split(':')
                self.auth[username] = lambda passwd: crypt(passwd, pwhash) == pwhash

        key = ('POST', re.compile('/git-receive-pack$'))
        self.services[key] = authenticated(handle_service_request, self.auth)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        method = environ['REQUEST_METHOD']
        req = SmartGitRequest(environ, start_response, dumb=self.dumb,
                              handlers=self.handlers)
        # environ['QUERY_STRING'] has qs args
        for smethod, spath in self.services.iterkeys():
            if smethod != method:
                continue
            mat = spath.search(path)
            if mat:
                handler = self.services[smethod, spath]
                break
        else:
            return self.app(environ, start_response)
        return handler(req, self.backend, mat)


def make_app(app, repos, htpasswd):

    # DictBackend uses keys with a leading slash
    backend = DictBackend(dict(('/'+k, Repo(v)) for k, v in repos.iteritems()))
    wsgi_app = app.wsgi_app

    app = AuthenticatedGitApplication(app, backend, htpasswd)
    app.wsgi_app = wsgi_app
    app = GunzipFilter(LimitedInputFilter(app))
    app.wsgi_app = wsgi_app

    return app
