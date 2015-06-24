import os
import time
import contextlib
import subprocess
import tempfile
import shutil
import klaus

import pytest
import requests
import requests.auth
import werkzeug.serving
import threading


TEST_REPO = os.path.abspath("tests/repos/test_repo")
TEST_REPO_URL = "test_repo/"
TEST_SITE_NAME = "Some site"
HTDIGEST_FILE = "tests/credentials.htdigest"
UNAUTH_TEST_SERVER = "http://invalid:password@localhost:9876/"
UNAUTH_TEST_REPO_URL = UNAUTH_TEST_SERVER + TEST_REPO_URL
AUTH_TEST_SERVER = "http://testuser:testpassword@localhost:9876/"
AUTH_TEST_REPO_URL = AUTH_TEST_SERVER + TEST_REPO_URL


def testserver_require_auth(*args, **kwargs):
    kwargs['htdigest_file'] = open(HTDIGEST_FILE)
    kwargs['require_browser_auth'] = True
    return testserver(*args, **kwargs)


def test_htdigest_file_without_smarthttp_or_require_browser_auth():
    with pytest.raises(ValueError):
        klaus.make_app([], None, htdigest_file=object())


def test_unauthenticated_push_and_require_browser_auth():
    with pytest.raises(ValueError):
        klaus.make_app([], None, use_smarthttp=True, unauthenticated_push=True, require_browser_auth=True)


def test_unauthenticated_push_without_use_smarthttp():
    with pytest.raises(ValueError):
        klaus.make_app([], None, unauthenticated_push=True)


def test_unauthenticated_push_with_disable_push():
    with pytest.raises(ValueError):
        klaus.make_app([], None, unauthenticated_push=True, disable_push=True)


def options_test(make_app_args, expected_permissions):
    def test():
        with testserver(**make_app_args):
            for action, permitted in expected_permissions.items():
                if action.endswith('auth'):
                    actions = [action]
                else:
                    actions = [action + '_unauth', action + '_auth']
                for action in actions:
                    funcname = 'can_%s' % action
                    assert globals()[funcname]() == permitted
    return test


test_nosmart_noauth = options_test(
    {},
    {'reach': True, 'clone': False, 'push': False}
)
test_smart_noauth = options_test(
    {'use_smarthttp': True},
    {'reach': True, 'clone': True, 'push': False}
)
test_smart_push = options_test(
    {'use_smarthttp': True, 'htdigest_file': open(HTDIGEST_FILE)},
    {'reach': True, 'clone': True, 'push_auth': True, 'push_unauth': False}
)
test_unauthenticated_push = options_test(
    {'use_smarthttp': True, 'unauthenticated_push': True},
    {'reach': True, 'clone': True, 'push': True}
)
test_nosmart_auth = options_test(
    {'require_browser_auth': True, 'htdigest_file': open(HTDIGEST_FILE)},
    {'reach_auth': True, 'reach_unauth': False, 'clone': False, 'push': False}
)
test_smart_auth = options_test(
    {'require_browser_auth': True, 'use_smarthttp': True, 'htdigest_file': open(HTDIGEST_FILE)},
    {'reach_auth': True, 'reach_unauth': False, 'clone_auth': True, 'clone_unauth': False, 'push_unauth': False, 'push_auth': True}
)
test_smart_auth_disable_push = options_test(
    {'require_browser_auth': True, 'use_smarthttp': True, 'disable_push': True, 'htdigest_file': open(HTDIGEST_FILE)},
    {'reach_auth': True, 'reach_unauth': False, 'clone_auth': True, 'clone_unauth': False, 'push': False}
)


@contextlib.contextmanager
def testserver(*args, **kwargs):
    app = klaus.make_app([TEST_REPO], TEST_SITE_NAME, *args, **kwargs)
    server = werkzeug.serving.make_server("localhost", 9876, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield
    finally:
        server.server_close()
        if 'TRAVIS' in os.environ:
            # This fixes some "Address already in use" cases on Travis.
            time.sleep(1)


# Reach
def can_reach_unauth():
    return _check_http200(_GET_unauth, "test_repo")

def can_reach_auth():
    return _check_http200(_GET_auth, "test_repo")


# Clone
def can_clone_unauth():
  return _can_clone(_GET_unauth, UNAUTH_TEST_REPO_URL)

def can_clone_auth():
  return _can_clone(_GET_auth, AUTH_TEST_REPO_URL)

def _can_clone(http_get, url):
    tmp = tempfile.mkdtemp()
    try:
        return any([
            "git clone" in http_get(TEST_REPO_URL).content,
            _check_http200(http_get, TEST_REPO_URL + "info/refs?service=git-upload-pack"),
            subprocess.call(["git", "clone", url, tmp]) == 0,
        ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Push
def can_push_unauth():
    return _can_push(_GET_unauth, UNAUTH_TEST_REPO_URL)

def can_push_auth():
    return _can_push(_GET_auth, AUTH_TEST_REPO_URL)

def _can_push(http_get, url):
    return any([
      _check_http200(http_get, TEST_REPO_URL + "info/refs?service=git-receive-pack"),
      _check_http200(http_get, TEST_REPO_URL + "git-receive-pack"),
      subprocess.call(["git", "push", url, "master"], cwd=TEST_REPO) == 0,
    ])


def _GET_unauth(url=""):
    return requests.get(UNAUTH_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("invalid", "password"))

def _GET_auth(url=""):
    return requests.get(AUTH_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("testuser", "testpassword"))

def _check_http200(http_get, url):
    try:
        return http_get(url).status_code == 200
    except:
        return False
