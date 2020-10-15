import requests
from .utils import *


def test_blame():
    with serve():
        response = requests.get(UNAUTH_TEST_REPO_URL + "blob/HEAD/test.c")
        assert response.status_code == 200


def test_dont_show_blame_link():
    with serve():
        for file in ["binary", "image.jpg", "toolarge"]:
            response = requests.get(
                TEST_REPO_DONT_RENDER_URL + "blob/HEAD/" + file
            ).text
            assert "blame" not in response


def test_dont_render_blame():
    """Don't render blame even if someone navigated to the blame site by accident."""
    with serve():
        for file in ["binary", "image.jpg", "toolarge"]:
            response = requests.get(
                TEST_REPO_DONT_RENDER_URL + "blame/HEAD/" + file
            ).text
            assert "Can't show blame" in response
