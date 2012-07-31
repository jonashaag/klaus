import os
import subprocess
import jinja2
import flask
import httpauth
import dulwich.web
from klaus import views, utils
from klaus.repo import FancyRepo


KLAUS_ROOT = os.path.dirname(__file__)

try:
    KLAUS_VERSION = utils.check_output(['git', 'log', '--format=%h', '-n', '1'])
except subprocess.CalledProcessError:
    KLAUS_VERSION = '0.2'


class Klaus(flask.Flask):
    jinja_options = {
        'extensions': ['jinja2.ext.autoescape'],
        'undefined': jinja2.StrictUndefined
    }

    def __init__(self, repo_paths, sitename, use_smarthttp):
        self.repos = map(FancyRepo, repo_paths)
        self.repo_map = dict((repo.name, repo) for repo in self.repos)
        self.sitename = sitename
        self.use_smarthttp = use_smarthttp

        flask.Flask.__init__(self, __name__)

        self.setup_routes()

    def create_jinja_environment(self):
        """ Called by Flask.__init__ """
        env = super(Klaus, self).create_jinja_environment()
        for func in [
            'force_unicode',
            'timesince',
            'shorten_sha1',
            'shorten_message',
            'extract_author_name',
        ]:
            env.filters[func] = getattr(utils, func)

        env.globals['KLAUS_VERSION'] = KLAUS_VERSION
        env.globals['USE_SMARTHTTP'] = self.use_smarthttp
        env.globals['SITENAME'] = self.sitename

        return env

    def setup_routes(self):
        for endpoint, rule in [
            ('repo_list',   '/'),
            ('blob',        '/<repo>/blob/<commit_id>/'),
            ('blob',        '/<repo>/blob/<commit_id>/<path:path>'),
            ('raw',         '/<repo>/raw/<commit_id>/'),
            ('raw',         '/<repo>/raw/<commit_id>/<path:path>'),
            ('commit',      '/<repo>/commit/<commit_id>/'),
            ('history',     '/<repo>/'),
            ('history',     '/<repo>/tree/<commit_id>/'),
            ('history',     '/<repo>/tree/<commit_id>/<path:path>'),
        ]:
            self.add_url_rule(rule, view_func=getattr(views, endpoint))


def make_app(repos, sitename, use_smarthttp=False, htdigest_file=None):
    """
    Returns a WSGI with all the features (smarthttp, authentication) already
    patched in.
    """
    app = Klaus(
        repos,
        sitename,
        use_smarthttp,
    )
    app.wsgi_app = utils.SubUri(app.wsgi_app)

    if use_smarthttp:
        # `path -> Repo` mapping for Dulwich's web support
        dulwich_backend = dulwich.server.DictBackend(
            dict(('/'+repo.name, repo) for repo in app.repos)
        )
        # Dulwich takes care of all Git related requests/URLs
        # and passes through everything else to klaus
        dulwich_wrapped_app = dulwich.web.make_wsgi_chain(
            backend=dulwich_backend,
            fallback_app=app.wsgi_app,
        )

        # `receive-pack` is requested by the "client" on a push
        # (the "server" is asked to *receive* packs), i.e. we need to secure
        # it using authentication or deny access completely to make the repo
        # read-only.
        #
        # Git first sends requests to /<repo-name>/info/refs?service=git-receive-pack.
        # If this request is responded to using HTTP 401 Unauthorized, the user
        # is prompted for username and password. If we keep responding 401, Git
        # interprets this as an authentication failure.  (We can't respond 403
        # because this results in horrible, unhelpful Git error messages.)
        #
        # Git will never call /<repo-name>/git-receive-pack if authentication
        # failed for /info/refs, but since it's used to upload stuff to the server
        # we must secure it anyway for security reasons.
        PATTERN = r'^/[^/]+/(info/refs\?service=git-receive-pack|git-receive-pack)$'
        if htdigest_file:
            # .htdigest file given. Use it to read the push-er credentials from.
            app.wsgi_app = httpauth.DigestFileHttpAuthMiddleware(
                htdigest_file,
                wsgi_app=utils.SubUri(dulwich_wrapped_app),
                routes=[PATTERN],
            )
        else:
            # no .htdigest file given. Disable push-ing.  Semantically we should
            # use HTTP 403 here but since that results in freaky error messages
            # (see above) we keep asking for authentication (401) instead.
            # Git will print a nice error message after a few tries.
            app.wsgi_app = httpauth.AlwaysFailingAuthMiddleware(
                wsgi_app=utils.SubUri(dulwich_wrapped_app),
                routes=[PATTERN],
            )

    return app
