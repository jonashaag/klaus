from io import BytesIO
import requests
import tarfile
import contextlib
from .utils import *


def test_download():
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_URL + "tarball/master", stream=True)
        response_body = BytesIO(response.raw.read())
        tarball = tarfile.TarFile.gzopen("test.tar.gz", fileobj=response_body)
        with contextlib.closing(tarball):
            assert tarball.extractfile('test.c').read() == b'int a;\n'


def test_no_newline_at_end_of_file():
    with serve():
        response = requests.get(TEST_REPO_NO_NEWLINE_URL + "commit/HEAD/").content
        assert "No newline at end of file" in response
        assert "2<del></del>" in response
        assert "2<ins></ins>" in response


def test_dont_render_binary():
  with serve():
    response = requests.get(TEST_REPO_DONT_RENDER_URL + "blob/HEAD/binary").content
    assert "Binary data not shown" in response


def test_render_image():
  with serve():
    response = requests.get(TEST_REPO_DONT_RENDER_URL + "blob/HEAD/image.jpg").content
    assert '<img src="/dont-render/raw/HEAD/image.jpg"' in response


def test_dont_render_large_file():
  with serve():
    response = requests.get(TEST_REPO_DONT_RENDER_URL + "blob/HEAD/toolarge").content
    assert "Large file not shown" in response
