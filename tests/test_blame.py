import requests
from .utils import *


def test_dont_show_blame_link():
    with serve():
        for file in ["binary", "image.jpg", "toolarge"]:
            response = requests.get(TEST_REPO_DONT_RENDER_URL + "blob/HEAD/" + file).content
            assert "blame" not in response


def test_dont_render_blame():
    """Don't render blame even if someone navigated to the blame site by accident."""
    with serve():
        for file in ["binary", "image.jpg", "toolarge"]:
            response = requests.get(TEST_REPO_DONT_RENDER_URL + "blame/HEAD/" + file).content
            assert "Can't show blame" in response
