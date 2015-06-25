import os
import time
import contextlib
import werkzeug.serving
import threading

import klaus


TEST_REPO = os.path.abspath("tests/repos/test_repo")
TEST_REPO_URL = "test_repo/"
TEST_SITE_NAME = "Some site"
HTDIGEST_FILE = "tests/credentials.htdigest"
UNAUTH_TEST_SERVER = "http://invalid:password@localhost:9876/"
UNAUTH_TEST_REPO_URL = UNAUTH_TEST_SERVER + TEST_REPO_URL
AUTH_TEST_SERVER = "http://testuser:testpassword@localhost:9876/"
AUTH_TEST_REPO_URL = AUTH_TEST_SERVER + TEST_REPO_URL


@contextlib.contextmanager
def serve(*args, **kwargs):
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


def serve_require_auth(*args, **kwargs):
    kwargs['htdigest_file'] = open(HTDIGEST_FILE)
    kwargs['require_browser_auth'] = True
    return testserver(*args, **kwargs)
