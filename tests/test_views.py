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
            assert tarball.extractfile('README').read() == 'Hello World\n'
