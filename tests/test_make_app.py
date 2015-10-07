import os
import re
import subprocess
import tempfile
import shutil
import klaus

import pytest
import requests
import requests.auth

from .utils import *


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
        with serve(**make_app_args):
            for check, permitted in expected_permissions.items():
                if check in globals():
                    checks = [check]
                elif check.endswith('auth'):
                    checks = ['can_%s' % check]
                else:
                    checks = ['can_%s_unauth' % check, 'can_%s_auth' % check]
                for check in checks:
                    assert globals()[check]() == permitted
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

test_ctags_disabled = options_test(
    {},
    {'ctags_tags_and_branches': False, 'ctags_all': False}
)
test_ctags_tags_and_branches = options_test(
    {'ctags_policy': 'tags-and-branches'},
    {'ctags_tags_and_branches': True, 'ctags_all': False}
)
test_ctags_all = options_test(
    {'ctags_policy': 'ALL'},
    {'ctags_tags_and_branches': True, 'ctags_all': True}
)


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
            b"git clone" in http_get(TEST_REPO_URL).content,
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


# Ctags
def ctags_tags_and_branches():
    return all(
        _ctags_enabled(ref, f)
        for ref in ["master", "tag1"] for f in ["test.c", "test.js"]
    )


def ctags_all():
    all_refs = re.findall('href=".+/commit/([a-z0-9]{40})/">',
                          requests.get(UNAUTH_TEST_REPO_URL).content)
    assert len(all_refs) == 3
    return all(
        _ctags_enabled(ref, f)
        for ref in all_refs for f in ["test.c", "test.js"]
    )

def _ctags_enabled(ref, filename):
    response = requests.get(UNAUTH_TEST_REPO_URL + "blob/%s/%s" % (ref, filename))
    href = '<a href="/%sblob/%s/%s#L-1">' % (TEST_REPO_URL, ref, filename)
    return href in response.content


def _GET_unauth(url=""):
    return requests.get(UNAUTH_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("invalid", "password"))

def _GET_auth(url=""):
    return requests.get(AUTH_TEST_SERVER + url, auth=requests.auth.HTTPDigestAuth("testuser", "testpassword"))

def _check_http200(http_get, url):
    try:
        return http_get(url).status_code == 200
    except:
        return False
