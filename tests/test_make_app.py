import os
import shutil
import subprocess
import sys
import tempfile
import time

import pytest
import requests
import requests.auth

import klaus
from klaus import scip_generate, scip_index, scip_pb2

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
                    checks = [check]
                elif check.endswith("auth"):
                    checks = ["can_%s" % check]
                else:
                    checks = ["can_%s_unauth" % check, "can_%s_auth" % check]
                for check in checks:
                    assert globals()[check]() == permitted, check

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


# Reach
def can_reach_unauth():
    return _check_http200(_GET_unauth, TEST_REPO_BASE_URL)


def can_reach_auth():
    return _check_http200(_GET_auth, TEST_REPO_BASE_URL)


# Clone
def can_clone_unauth():
    return _can_clone(_GET_unauth, UNAUTH_TEST_REPO_URL)


def can_clone_auth():
    return _can_clone(_GET_auth, AUTH_TEST_REPO_URL)


def _can_clone(http_get, url):
    tmp = tempfile.mkdtemp()
    try:
        return all(
            [
                "git clone" in http_get(TEST_REPO_BASE_URL).text,
                _check_http200(
                    http_get, TEST_REPO_BASE_URL + "info/refs?service=git-upload-pack"
                ),
                subprocess.call(["git", "clone", url, tmp]) == 0,
            ]
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Push
def can_push_unauth():
    return _can_push(_GET_unauth, UNAUTH_TEST_REPO_URL)


def can_push_auth():
    return _can_push(_GET_auth, AUTH_TEST_REPO_URL)


def _can_push(http_get, url):
    return all(
        [
            any(
                [
                    _check_http200(
                        http_get,
                        TEST_REPO_BASE_URL + "info/refs?service=git-receive-pack",
                    ),
                    _check_http200(http_get, TEST_REPO_BASE_URL + "git-receive-pack"),
                ]
            ),
            subprocess.call(["git", "push", url, "master"], cwd=TEST_REPO) == 0,
        ]
    )


# SCIP
def _write_test_scip_dump():
    """Build a small SCIP dump for the test repo covering test.c and test.js."""
    index = scip_pb2.Index()
    index.metadata.version = scip_pb2.UnspecifiedProtocolVersion
    index.metadata.text_document_encoding = scip_pb2.UTF8
    index.metadata.project_root = "file://" + TEST_REPO

    c_doc = index.documents.add()
    c_doc.relative_path = "test.c"
    c_doc.language = "C"
    c_int = c_doc.occurrences.add()
    c_int.range.extend([0, 0, 0, 3])
    c_int.syntax_kind = scip_pb2.IdentifierBuiltinType
    c_a = c_doc.occurrences.add()
    c_a.range.extend([0, 4, 0, 5])
    c_a.symbol = "scip-test c/a."
    c_a.symbol_roles = scip_pb2.Definition
    c_a.syntax_kind = scip_pb2.IdentifierConstant

    js_doc = index.documents.add()
    js_doc.relative_path = "test.js"
    js_doc.language = "JavaScript"
    js_kw = js_doc.occurrences.add()
    js_kw.range.extend([0, 0, 0, 8])
    js_kw.syntax_kind = scip_pb2.IdentifierKeyword
    js_def = js_doc.occurrences.add()
    js_def.range.extend([0, 9, 0, 13])
    js_def.symbol = "scip-test js/test()."
    js_def.symbol_roles = scip_pb2.Definition
    js_def.syntax_kind = scip_pb2.IdentifierFunctionDefinition

    scip_dir = os.path.join(TEST_REPO, ".scip")
    os.makedirs(scip_dir, exist_ok=True)
    with open(os.path.join(scip_dir, "HEAD.scip"), "wb") as f:
        f.write(index.SerializeToString())
    scip_index.clear_cache()


def _remove_test_scip_dump():
    scip_dir = os.path.join(TEST_REPO, ".scip")
    shutil.rmtree(scip_dir, ignore_errors=True)
    scip_index.clear_cache()


def test_scip_renders_syntax_classes():
    _write_test_scip_dump()
    try:
        with serve():
            response = requests.get(UNAUTH_TEST_REPO_URL + "blob/master/test.c")
            assert response.status_code == 200, response.text
            assert "scip-identifier-builtin-type" in response.text
            assert "scip-identifier-constant" in response.text
    finally:
        _remove_test_scip_dump()


def test_scip_falls_back_to_pygments_when_no_dump():
    scip_index.clear_cache()
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_URL + "blob/master/test.c")
        assert response.status_code == 200, response.text
        # Pygments emits a <table class="highlighttable"> with linenos but no scip- classes.
        assert "scip-" not in response.text
        assert 'class="highlighttable"' in response.text


def test_scip_policy_gating():
    app = klaus.Klaus({None: [TEST_REPO]}, TEST_SITE_NAME, False, scip_policy="none")
    repo = next(iter(app.valid_repos.values()))
    commit = repo.get_commit("master")
    assert app.should_generate_scip(repo, commit) is False

    app = klaus.Klaus({None: [TEST_REPO]}, TEST_SITE_NAME, False, scip_policy="ALL")
    assert app.should_generate_scip(repo, commit) is True

    app = klaus.Klaus(
        {None: [TEST_REPO]}, TEST_SITE_NAME, False, scip_policy="tags-and-branches"
    )
    # master is a branch HEAD; tag1 is a tag.  Both should be eligible.
    assert app.should_generate_scip(repo, commit) is True
    tag_commit = repo.get_commit("tag1")
    assert app.should_generate_scip(repo, tag_commit) is True
    # A commit that isn't the HEAD of any ref shouldn't be eligible.  The
    # root commit (master~~) has no tag or branch pointing at it.
    root = repo.get_commit(repo.get_commit("tag1").parents[0].decode("ascii"))
    assert app.should_generate_scip(repo, root) is False


def test_scip_generate_via_worktree(monkeypatch):
    """Background generation should produce <repo>/.scip/<sha>.scip via a
    fake indexer running in a `git worktree add` tempdir."""

    scip_index.clear_cache()
    _remove_test_scip_dump()

    fake_index = scip_pb2.Index()
    fake_doc = fake_index.documents.add()
    fake_doc.relative_path = "test.c"
    fake_occ = fake_doc.occurrences.add()
    fake_occ.range.extend([0, 0, 0, 3])
    fake_occ.syntax_kind = scip_pb2.IdentifierBuiltinType
    payload = fake_index.SerializeToString().hex()
    fake_indexer = scip_generate.Indexer(
        name="fake",
        applies=lambda _: True,
        command=[
            sys.executable,
            "-c",
            f"open('index.scip','wb').write(bytes.fromhex('{payload}'))",
        ],
    )
    monkeypatch.setattr(scip_generate, "INDEXERS", [fake_indexer])

    import dulwich.repo

    sha = dulwich.repo.Repo(TEST_REPO).head().decode("ascii")
    dump_path = os.path.join(TEST_REPO, ".scip", f"{sha}.scip")

    try:
        scip_generate.request_index(TEST_REPO, sha)
        # Wait for the background thread to finish.
        for _ in range(200):
            with scip_generate._LOCK:
                thread = scip_generate._INFLIGHT.get((TEST_REPO, sha))
            if thread is None or not thread.is_alive():
                break
            time.sleep(0.05)
        else:
            raise AssertionError("indexer thread didn't finish")

        assert os.path.isfile(dump_path), "expected dump at %s" % dump_path
        index = scip_index.load_index(TEST_REPO, sha)
        assert index is not None
        assert index.get_document("test.c") is not None
    finally:
        _remove_test_scip_dump()


def _GET_unauth(url=""):
    return requests.get(
        UNAUTH_TEST_SERVER + url,
        auth=requests.auth.HTTPDigestAuth("invalid", "password"),
    )


def _GET_auth(url=""):
    return requests.get(
        AUTH_TEST_SERVER + url,
        auth=requests.auth.HTTPDigestAuth("testuser", "testpassword"),
    )


def _check_http200(http_get, url):
    return http_get(url).status_code == 200
