import contextlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import werkzeug.serving

import klaus

TEST_SITE_NAME = "Some site"
HTDIGEST_FILE = "tests/credentials.htdigest"

HOST = "localhost:9876"
UNAUTH_TEST_SERVER = "http://invalid:password@" + HOST + "/"
AUTH_TEST_SERVER = "http://testuser:testpassword@" + HOST + "/"

NAMESPACE = "name/space1"
SIMPLE_NAMESPACE = "namespace2"

TEST_REPO = os.path.abspath("tests/repos/build/test_repo")
TEST_REPO_ROOT = os.path.abspath("tests/repos/build")
TEST_REPO_BASE_URL = "{}/test_repo/-/".format(NAMESPACE)
TEST_REPO_SMART_BASE_URL = TEST_REPO_BASE_URL.replace("/-/", ".git")
SIMPLENAMESPACED_TEST_REPO_BASE_URL = "{}/test_repo/-/".format(SIMPLE_NAMESPACE)
UNNAMESPACED_TEST_REPO_BASE_URL = "test_repo/-/"
UNAUTH_TEST_REPO_URL = UNAUTH_TEST_SERVER + TEST_REPO_BASE_URL
UNAUTH_SIMPLESPACED_TEST_REPO_URL = UNAUTH_TEST_SERVER + SIMPLENAMESPACED_TEST_REPO_BASE_URL
UNAUTH_UNNAMESPACED_TEST_REPO_URL = UNAUTH_TEST_SERVER + TEST_REPO_BASE_URL
AUTH_TEST_REPO_URL = AUTH_TEST_SERVER + TEST_REPO_BASE_URL

TEST_REPO_NO_NAMESPACE = TEST_REPO
TEST_REPO_NO_NAMESPACE_ROOT = TEST_REPO_ROOT
TEST_REPO_NO_NAMESPACE_BASE_URL = "test_repo/-/"

TEST_REPO_NO_NEWLINE = os.path.abspath("tests/repos/build/no-newline-at-end-of-file")
TEST_REPO_NO_NEWLINE_BASE_URL = "no-newline-at-end-of-file/-/"
UNAUTH_TEST_REPO_NO_NEWLINE_URL = UNAUTH_TEST_SERVER + TEST_REPO_NO_NEWLINE_BASE_URL

TEST_REPO_DONT_RENDER = os.path.abspath("tests/repos/build/dont-render")
TEST_REPO_DONT_RENDER_BASE_URL = "dont-render/-/"
UNAUTH_TEST_REPO_DONT_RENDER_URL = UNAUTH_TEST_SERVER + TEST_REPO_DONT_RENDER_BASE_URL

TEST_INVALID_REPO = os.path.abspath("tests/repos/build/invalid_repo")
TEST_INVALID_REPO_NAME = "invalid_repo"

REPOS = [TEST_REPO, TEST_REPO_NO_NEWLINE, TEST_REPO_DONT_RENDER, TEST_INVALID_REPO]
ALL_TEST_REPOS = {NAMESPACE: [TEST_REPO], SIMPLE_NAMESPACE: [TEST_REPO], None: REPOS}


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


def serve_require_auth(*args, **kwargs):
    kwargs["htdigest_file"] = open(HTDIGEST_FILE)
    kwargs["require_browser_auth"] = True
    return testserver(*args, **kwargs)


def git_cmd(*cmd, tmpcwd=False, cwd=None, **kwargs):
    if tmpcwd:
        assert cwd is None
        cwd = tempfile.mkdtemp()
    try:
        with subprocess.Popen(
            ["git", *cmd],
            env={"GIT_TRACE": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            **kwargs,
        ) as proc:
            stdout, stderr = proc.communicate()
            return proc.returncode, stdout, stderr
    finally:
        if tmpcwd:
            shutil.rmtree(cwd, ignore_errors=True)
