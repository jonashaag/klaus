import contextlib
import io
import requests
import tarfile

import pytest

from .utils import *

def test_repo_list():
    with serve():
        response = requests.get(UNAUTH_TEST_SERVER).text
        assert TEST_REPO_BASE_URL in response
        assert TEST_REPO_DONT_RENDER_BASE_URL in response
        assert TEST_REPO_NO_NEWLINE_BASE_URL in response
        assert TEST_INVALID_REPO_NAME in response


def test_repo_list_search_repo():
    with serve():
        response = requests.get(
            UNAUTH_TEST_SERVER + "?q=" + TEST_INVALID_REPO_NAME
        ).text
        assert not TEST_REPO_BASE_URL in response
        assert not TEST_REPO_DONT_RENDER_BASE_URL in response
        assert not TEST_REPO_NO_NEWLINE_BASE_URL in response
        assert TEST_INVALID_REPO_NAME in response


def test_repo_list_search_namespace():
    with serve():
        response = requests.get(UNAUTH_TEST_SERVER + "?q=" + NAMESPACE).text
        assert TEST_REPO_BASE_URL in response
        assert not TEST_REPO_DONT_RENDER_BASE_URL in response
        assert not TEST_REPO_NO_NEWLINE_BASE_URL in response
        assert not TEST_INVALID_REPO_NAME in response


def test_download():
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_URL + "tarball/master/", stream=True)
        response_body = io.BytesIO(response.raw.read())
        tarball = tarfile.TarFile.gzopen("test.tar.gz", fileobj=response_body)
        with contextlib.closing(tarball):
            assert tarball.extractfile("test_repo@master/test.c").read() == b"int a;\n"


def test_no_newline_at_end_of_file():
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_NO_NEWLINE_URL + "commit/HEAD/").text
        assert response.count("No newline at end of file") == 1


def test_dont_render_binary():
    with serve():
        response = requests.get(
            UNAUTH_TEST_REPO_DONT_RENDER_URL + "blob/HEAD/binary"
        ).text
        assert "Binary data not shown" in response


def test_render_image():
    with serve():
        response = requests.get(
            UNAUTH_TEST_REPO_DONT_RENDER_URL + "blob/HEAD/image.jpg"
        ).text
        assert '<img src="/dont-render/-/raw/HEAD/image.jpg"' in response


def test_dont_render_large_file():
    with serve():
        response = requests.get(
            UNAUTH_TEST_REPO_DONT_RENDER_URL + "blob/HEAD/toolarge"
        ).text
        assert "Large file not shown" in response


def test_regression_gh233_treeview_paths():
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_URL + "tree/HEAD/folder").text
        assert "blob/HEAD/test.txt" not in response
        assert "blob/HEAD/folder/test.txt" in response


def test_display_invalid_repos():
    with serve():
        response = requests.get(UNAUTH_TEST_SERVER).text
        assert '<ul class="repolist invalid">' in response
        assert "<div class=name>invalid_repo</div>" in response


def test_smart_http():
    with serve(use_smarthttp=True):
        returncode, stdout, stderr = git_cmd("clone", UNAUTH_TEST_SERVER + TEST_REPO_SMART_BASE_URL, tmpcwd=True)
        assert returncode == 0, (stdout, stderr)


@pytest.mark.parametrize("old_url, new_url", [
    (
        UNAUTH_UNNAMESPACED_TEST_REPO_URL.replace("-/", ""),
        UNAUTH_UNNAMESPACED_TEST_REPO_URL,
    ),
    (
        UNAUTH_SIMPLESPACED_TEST_REPO_URL.replace("-/", "").replace(SIMPLE_NAMESPACE, "~" + SIMPLE_NAMESPACE),
        UNAUTH_SIMPLESPACED_TEST_REPO_URL,
    ),

])
@pytest.mark.parametrize("path", ["", "tarball/master/", "tree/HEAD/folder"])
def test_old_url_redirects(old_url, new_url, path):
    with serve():
        old_url += path
        new_url += path

        # Old URL should redirect
        redirect_response = requests.get(old_url, allow_redirects=False)
        assert redirect_response.status_code == 301
        assert new_url.endswith(HOST + redirect_response.headers["Location"])

        # Redirect should be to the same page (identical contents)
        redirected_response = requests.get(old_url)
        assert redirected_response.status_code == 200
        new_response = requests.get(new_url)
        assert new_response.status_code == 200
        assert redirected_response.content == new_response.content


@pytest.mark.parametrize("clone_url", [
    UNAUTH_TEST_SERVER + TEST_REPO_SMART_BASE_URL.replace(".git", ""),
    UNAUTH_SIMPLESPACED_TEST_REPO_URL.replace("-/", "").replace(SIMPLE_NAMESPACE, "~" + SIMPLE_NAMESPACE),
])
def test_old_smarthttp_url_redirects(clone_url):

    with serve(use_smarthttp=True):
        returncode, stdout, stderr = git_cmd("clone", clone_url, tmpcwd=True)
        assert returncode == 0, (stdout, stderr)
        assert "warning: redirecting to" in stderr
