import contextlib
import os
import threading
import time

import werkzeug.serving

import klaus

TEST_SITE_NAME = "Some site"
HTDIGEST_FILE = "tests/credentials.htdigest"

UNAUTH_TEST_SERVER = "http://invalid:password@localhost:9876/"
AUTH_TEST_SERVER = "http://testuser:testpassword@localhost:9876/"

NAMESPACE = "namespace1"

TEST_REPO = os.path.abspath("tests/repos/build/test_repo")
TEST_REPO_ROOT = os.path.abspath("tests/repos/build")
TEST_REPO_BASE_URL = f"~{NAMESPACE}/test_repo/"
UNAUTH_TEST_REPO_URL = UNAUTH_TEST_SERVER + TEST_REPO_BASE_URL
AUTH_TEST_REPO_URL = AUTH_TEST_SERVER + TEST_REPO_BASE_URL

TEST_REPO_NO_NAMESPACE = TEST_REPO
TEST_REPO_NO_NAMESPACE_ROOT = TEST_REPO_ROOT
TEST_REPO_NO_NAMESPACE_BASE_URL = "test_repo/"
AUTH_TEST_REPO_NO_NAMESPACE_URL = AUTH_TEST_SERVER + TEST_REPO_NO_NAMESPACE_BASE_URL

TEST_REPO_NO_NEWLINE = os.path.abspath("tests/repos/build/no-newline-at-end-of-file")
TEST_REPO_NO_NEWLINE_BASE_URL = "no-newline-at-end-of-file/"
UNAUTH_TEST_REPO_NO_NEWLINE_URL = UNAUTH_TEST_SERVER + TEST_REPO_NO_NEWLINE_BASE_URL

TEST_REPO_DONT_RENDER = os.path.abspath("tests/repos/build/dont-render")
TEST_REPO_DONT_RENDER_BASE_URL = "dont-render/"
UNAUTH_TEST_REPO_DONT_RENDER_URL = UNAUTH_TEST_SERVER + TEST_REPO_DONT_RENDER_BASE_URL

TEST_INVALID_REPO = os.path.abspath("tests/repos/build/invalid_repo")
TEST_INVALID_REPO_NAME = "invalid_repo"

REPOS = [TEST_REPO_NO_NEWLINE, TEST_REPO_DONT_RENDER, TEST_INVALID_REPO]
ALL_TEST_REPOS = {NAMESPACE: [TEST_REPO], None: REPOS}


@contextlib.contextmanager
def serve(*args, **kwargs):
    app = klaus.make_app(ALL_TEST_REPOS, TEST_SITE_NAME, *args, **kwargs)
    with serve_app(app):
        yield


@contextlib.contextmanager
def serve_app(app):
    server = werkzeug.serving.make_server("localhost", 9876, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield
    finally:
        server.server_close()
        if os.getenv("CI"):
            # This fixes some "Address already in use" cases on CI.
            time.sleep(1)
