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
            assert tarball.extractfile('README').read() == b'Hello World\n'


def test_no_newline_at_end_of_file():
    with serve():
        response = requests.get(TEST_REPO_NO_NEWLINE_URL + "commit/HEAD/").content
        assert "No newline at end of file" in response
        assert "2<del></del>" in response
        assert "2<ins></ins>" in response
