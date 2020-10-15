from io import BytesIO
import requests
import tarfile
import contextlib
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
        response = requests.get(UNAUTH_TEST_REPO_URL + "tarball/master", stream=True)
        response_body = BytesIO(response.raw.read())
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
        assert '<img src="/dont-render/raw/HEAD/image.jpg"' in response


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
