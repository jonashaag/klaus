import os
try:
    from importlib import reload  # Python 3.4+
except ImportError:
    pass

from .utils import *
from .test_make_app import can_reach_unauth, can_push_auth


def test_wsgi():
    os.environ['KLAUS_REPOS'] = TEST_REPO
    os.environ['KLAUS_SITE_NAME'] = TEST_SITE_NAME
    os.environ.pop('KLAUS_HTDIGEST_FILE', None)
    os.environ.pop('KLAUS_USE_SMARTHTTP', None)
    from klaus.contrib import wsgi
    with serve_app(wsgi.application):
        assert can_reach_unauth()

    os.environ['KLAUS_HTDIGEST_FILE'] = HTDIGEST_FILE
    os.environ['KLAUS_USE_SMARTHTTP'] = 'yes'
    reload(wsgi)
    with serve_app(wsgi.application):
        assert can_push_auth()


def test_wsgi_autoreload():
    os.environ['KLAUS_REPOS_ROOT'] = TEST_REPO_ROOT
    os.environ['KLAUS_SITE_NAME'] = TEST_SITE_NAME
    os.environ.pop('KLAUS_HTDIGEST_FILE', None)
    os.environ.pop('KLAUS_USE_SMARTHTTP', None)
    from klaus.contrib import wsgi_autoreload
    with serve_app(wsgi_autoreload.application):
        assert can_reach_unauth()

    os.environ['KLAUS_HTDIGEST_FILE'] = HTDIGEST_FILE
    os.environ['KLAUS_USE_SMARTHTTP'] = 'yes'
    reload(wsgi_autoreload)
    with serve_app(wsgi_autoreload.application):
        assert can_push_auth()
