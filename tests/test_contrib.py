import os
try:
    from importlib import reload  # Python 3.4+
except ImportError:
    pass

import pytest

from klaus.contrib import app_args
from .utils import *
from .test_make_app import can_reach_unauth, can_push_auth


def check_env(env, expected_args, expected_kwargs):
    os.environ.update(env)
    args, kwargs = app_args.get_args_from_env()
    assert args == expected_args
    assert kwargs == expected_kwargs


def test_minimum_env(monkeypatch):
    """Test to provide only required env var"""
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    check_env(
        {'KLAUS_SITE_NAME': TEST_SITE_NAME},
        ([], TEST_SITE_NAME),
        dict(
            htdigest_file=None,
            use_smarthttp=False,
            require_browser_auth=False,
            disable_push=False,
            unauthenticated_push=False,
            ctags_policy='none')
    )


def test_complete_env(monkeypatch):
    """Test to provide all supported env var"""
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    check_env(
        {
            'KLAUS_REPOS': TEST_REPO,
            'KLAUS_SITE_NAME': TEST_SITE_NAME,
            'KLAUS_HTDIGEST_FILE': HTDIGEST_FILE,
            'KLAUS_USE_SMARTHTTP': 'yes',
            'KLAUS_REQUIRE_BROWSER_AUTH': '1',
            'KLAUS_DISABLE_PUSH': 'false',
            'KLAUS_UNAUTHENTICATED_PUSH': '0',
            'KLAUS_CTAGS_POLICY': 'ALL'
        },
        ([TEST_REPO], TEST_SITE_NAME),
        dict(
            htdigest_file=HTDIGEST_FILE,
            use_smarthttp=True,
            require_browser_auth=True,
            disable_push=False,
            unauthenticated_push=False,
            ctags_policy='ALL')
    )


def test_unsupported_boolean_env(monkeypatch):
    """Test that unsupported boolean env var raises ValueError"""
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    with pytest.raises(ValueError):
        check_env(
            {
                'KLAUS_REPOS': TEST_REPO,
                'KLAUS_SITE_NAME': TEST_SITE_NAME,
                'KLAUS_HTDIGEST_FILE': HTDIGEST_FILE,
                'KLAUS_USE_SMARTHTTP': 'unsupported',
            }, (), {}
        )


def test_wsgi(monkeypatch):
    """Test start of wsgi app"""
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    os.environ['KLAUS_REPOS'] = TEST_REPO
    os.environ['KLAUS_SITE_NAME'] = TEST_SITE_NAME
    from klaus.contrib import wsgi
    with serve_app(wsgi.application):
        assert can_reach_unauth()
        assert not can_push_auth()

    os.environ['KLAUS_HTDIGEST_FILE'] = HTDIGEST_FILE
    os.environ['KLAUS_USE_SMARTHTTP'] = 'yes'
    reload(wsgi)
    with serve_app(wsgi.application):
        assert can_reach_unauth()
        assert can_push_auth()


def test_wsgi_autoreload(monkeypatch):
    """Test start of wsgi autoreload app"""
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    os.environ['KLAUS_REPOS_ROOT'] = TEST_REPO_ROOT
    os.environ['KLAUS_SITE_NAME'] = TEST_SITE_NAME
    from klaus.contrib import wsgi_autoreload, wsgi_autoreloading
    with serve_app(wsgi_autoreload.application):
        assert can_reach_unauth()
        assert not can_push_auth()

    os.environ['KLAUS_HTDIGEST_FILE'] = HTDIGEST_FILE
    os.environ['KLAUS_USE_SMARTHTTP'] = 'yes'
    reload(wsgi_autoreload)
    reload(wsgi_autoreloading)
    with serve_app(wsgi_autoreload.application):
        assert can_push_auth()
