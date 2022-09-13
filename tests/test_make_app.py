import os
import re
import sys
import klaus

import pytest
import requests
import requests.auth

from .utils import *


def test_make_app_using_list():
    app = klaus.make_app(REPOS, TEST_SITE_NAME)
    with serve_app(app):
        response = requests.get(UNAUTH_TEST_SERVER).text
        assert TEST_REPO_NO_NEWLINE_BASE_URL in response


def test_htdigest_file_without_smarthttp_or_require_browser_auth():
    with pytest.raises(ValueError):
        klaus.make_app([], None, htdigest_file=object())


def test_unauthenticated_push_and_require_browser_auth():
    with pytest.raises(ValueError):
        klaus.make_app(
            [],
            None,
            use_smarthttp=True,
            unauthenticated_push=True,
            require_browser_auth=True,
        )


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
                    assert 0, check
                    checks = [globals()[check]]
                    assert globals()[check] == permitted, check
                else:
                    if check.endswith("auth"):
                        check, auth = check.rsplit("_")
                        auth = auth == "auth"
                        checks = [(check, auth)]
                    else:
                        checks = [(check, True), (check, False)]
                    for check, auth in checks:
                        res = globals()["_can_%s" % check](auth)
                        assert all(res) if permitted else not any(res), (check, auth, permitted, res)

    return test


test_nosmart_noauth = options_test({}, {"reach": True, "clone": False, "push": False})
test_smart_noauth = options_test(
    {"use_smarthttp": True}, {"reach": True, "clone": True, "push": False}
)
test_smart_push = options_test(
    {"use_smarthttp": True, "htdigest_file": open(HTDIGEST_FILE)},
    {"reach": True, "clone": True, "push_auth": True, "push_unauth": False},
)
test_unauthenticated_push = options_test(
    {"use_smarthttp": True, "unauthenticated_push": True},
    {"reach": True, "clone": True, "push": True},
)
test_nosmart_auth = options_test(
    {"require_browser_auth": True, "htdigest_file": open(HTDIGEST_FILE)},
    {"reach_auth": True, "reach_unauth": False, "clone": False, "push": False},
)
test_smart_auth = options_test(
    {
        "require_browser_auth": True,
        "use_smarthttp": True,
        "htdigest_file": open(HTDIGEST_FILE),
    },
    {
        "reach_auth": True,
        "reach_unauth": False,
        "clone_auth": True,
        "clone_unauth": False,
        "push_unauth": False,
        "push_auth": True,
    },
)
test_smart_auth_disable_push = options_test(
    {
        "require_browser_auth": True,
        "use_smarthttp": True,
        "disable_push": True,
        "htdigest_file": open(HTDIGEST_FILE),
    },
    {
        "reach_auth": True,
        "reach_unauth": False,
        "clone_auth": True,
        "clone_unauth": False,
        "push": False,
    },
)

test_ctags_disabled = options_test(
    {}, {"ctags_tags_and_branches": False, "ctags_all": False}
)
test_ctags_tags_and_branches = options_test(
    {"ctags_policy": "tags-and-branches"},
    {"ctags_tags_and_branches": True, "ctags_all": False},
)
test_ctags_all = options_test(
    {"ctags_policy": "ALL"}, {"ctags_tags_and_branches": True, "ctags_all": True}
)


def _can_reach(auth):
    return [
        _check_http200(TEST_REPO_BASE_URL, auth)
    ]


def _can_clone(auth, url=TEST_REPO_SMART_BASE_URL):
    return [
        "git clone" in _requests_get(url, auth).text,
        _check_http200(url + "/info/refs?service=git-upload-pack", auth),
        git_cmd("clone", (AUTH_TEST_SERVER if auth else UNAUTH_TEST_SERVER) + url, tmpcwd=True)[0] == 0,
    ]


def _can_push(auth, url=TEST_REPO_SMART_BASE_URL):
    return [
        _check_http200(url + "/info/refs?service=git-receive-pack", auth),
        _check_http200(url + "/git-receive-pack", auth),
        git_cmd("push", (AUTH_TEST_SERVER if auth else UNAUTH_TEST_SERVER) + url, "master", cwd=TEST_REPO)[0] == 0,
    ]


# Ctags
def ctags_tags_and_branches():
    return all(
        _ctags_enabled(ref, f)
        for ref in ["master", "tag1"]
        for f in ["test.c", "test.js"]
    )


def ctags_all():
    all_refs = re.findall(
        'href=".+/commit/([a-z0-9]{40})/">', requests.get(UNAUTH_TEST_REPO_URL).text
    )
    assert len(all_refs) == 3
    return all(
        _ctags_enabled(ref, f) for ref in all_refs for f in ["test.c", "test.js"]
    )


def _ctags_enabled(ref, filename):
    response = requests.get(UNAUTH_TEST_REPO_URL + "blob/%s/%s" % (ref, filename))
    assert response.status_code == 200, response.text
    href = '<a href="/%sblob/%s/%s#L-1">' % (TEST_REPO_BASE_URL, ref, filename)
    return href in response.text


def _check_http200(url, auth):
    return _requests_get(url, auth).status_code == 200


def _requests_get(url, auth):
    if auth:
        return requests.get(
            AUTH_TEST_SERVER + url,
            auth=requests.auth.HTTPDigestAuth("testuser", "testpassword"),
        )
    else:
        return requests.get(
            UNAUTH_TEST_SERVER + url,
            auth=requests.auth.HTTPDigestAuth("invalid", "password"),
        )
