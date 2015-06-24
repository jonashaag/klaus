import os
import time
import contextlib
import subprocess
import tempfile
import shutil
import requests
import requests.auth
import klaus

import werkzeug.serving
import threading


TEST_REPO = os.path.abspath("tests/repos/test_repo")
TEST_REPO_URL = "test_repo/"
TEST_SITE_NAME = "Some site"
HTDIGEST_FILE = "tests/credentials.htdigest"

UNAUTHORIZED_TEST_SERVER = "http://invalid:password@localhost:9876/"
UNAUTHORIZED_TEST_REPO_URL = UNAUTHORIZED_TEST_SERVER + TEST_REPO_URL
AUTHORIZED_TEST_SERVER = "http://testuser:testpassword@localhost:9876/"
AUTHORIZED_TEST_REPO_URL = AUTHORIZED_TEST_SERVER + TEST_REPO_URL


def GET_unauthorized(url=""):
    return requests.get(UNAUTHORIZED_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("invalid", "password"))

def GET_authorized(url=""):
    return requests.get(AUTHORIZED_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("testuser", "testpassword"))


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
            time.sleep(0.3)


def testserver_require_auth(*args, **kwargs):
    kwargs['htdigest_file'] = open(HTDIGEST_FILE)
    kwargs['require_browser_auth'] = True
    return testserver(*args, **kwargs)


def test_no_smarthttp_no_require_browser_auth():
    with testserver():
        assert can_reach_site_unauthorized()
        assert can_reach_site_authorized()
        assert_cannot_clone()
        assert not can_push_unauthorized()
        assert not can_push_authorized()


def test_smarthttp_no_require_browser_auth():
    # Push is disabled either if no credentials are given or the 'disable_push' option is set:
    for server in [
        testserver(use_smarthttp=True),
        testserver(use_smarthttp=True, htdigest_file=open(HTDIGEST_FILE), disable_push=True)
    ]:
        with server:
            assert can_clone_unauthorized()
            assert not can_push_unauthorized()
            assert not can_push_authorized()


def test_smarthttp_push_no_require_browser_auth():
    with testserver(use_smarthttp=True, htdigest_file=open(HTDIGEST_FILE)):
        assert can_clone_unauthorized()
        assert not can_push_unauthorized()
        assert can_push_authorized()


def test_no_smarthttp_require_browser_auth():
    with testserver_require_auth():
        assert not can_reach_site_unauthorized()
        assert can_reach_site_authorized()
        assert not can_clone_unauthorized()
        assert not can_clone_authorized()
        assert not can_push_unauthorized()
        assert not can_push_authorized()


def test_smarthttp_require_browser_auth():
    with testserver_require_auth(use_smarthttp=True, disable_push=True):
        assert not can_clone_unauthorized()
        assert can_clone_authorized()
        assert not can_push_unauthorized()
        assert not can_push_authorized()


def test_smarthttp_push_require_browser_auth():
    with testserver_require_auth(use_smarthttp=True):
        assert not can_clone_unauthorized()
        assert can_clone_authorized()
        assert not can_push_unauthorized()
        assert can_push_authorized()


def assert_cannot_clone():
    assert "git clone" not in GET_unauthorized(TEST_REPO_URL).content
    assert 404 == GET_unauthorized(TEST_REPO_URL + "info/refs?service=git-upload-pack").status_code
    assert 128 == subprocess.call(["git", "clone", AUTHORIZED_TEST_REPO_URL])


def assert_cannot_push_authorized(expected_status):
    assert expected_status == GET_authorized(TEST_REPO_URL + "info/refs?service=git-receive-pack").status_code
    assert expected_status == GET_authorized(TEST_REPO_URL + "git-receive-pack").status_code
    assert 128 == subprocess.call(["git", "push", AUTHORIZED_TEST_REPO_URL, "master"], cwd=TEST_REPO)


def assert_cannot_push_unauthorized(expected_status):
    assert expected_status == GET_unauthorized(TEST_REPO_URL + "info/refs?service=git-receive-pack").status_code
    assert expected_status == GET_unauthorized(TEST_REPO_URL + "git-receive-pack").status_code
    # XXX 'git push' asks for a new username/password and blocks
    # assert 128 == subprocess.call(["git", "push", UNAUTHORIZED_TEST_REPO_URL, "master"], cwd=TEST_REPO)


# Clone
def can_clone_unauthorized():
    tmp = tempfile.mkdtemp()
    try:
        return subprocess.call(["git", "clone", UNAUTHORIZED_TEST_REPO_URL, tmp]) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def can_clone_authorized():
    tmp = tempfile.mkdtemp()
    try:
        return subprocess.call(["git", "clone", AUTHORIZED_TEST_REPO_URL, tmp]) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Push
def can_push_unauthorized():
    return subprocess.call(["git", "push", UNAUTHORIZED_TEST_REPO_URL, "master"], cwd=TEST_REPO) == 0

def can_push_authorized():
    return subprocess.call(["git", "push", AUTHORIZED_TEST_REPO_URL, "master"], cwd=TEST_REPO) == 0


# Reach
def can_reach_site_unauthorized():
    return GET_unauthorized("test_repo").status_code == 200

def can_reach_site_authorized():
    return GET_authorized(TEST_REPO_URL).status_code == 200
