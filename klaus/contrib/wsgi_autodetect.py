import contextlib
import os
import warnings

from .app_args import get_args_from_env, strtobool
from .wsgi_autodetecting import make_autodetecting_app

try:
    repos_root = os.environ["KLAUS_REPOS_ROOT"]
except KeyError:
    repos_root = os.environ["KLAUS_REPOS"]
    warnings.warn(
        "use KLAUS_REPOS_ROOT instead of KLAUS_REPOS for the autodecting apps",
        DeprecationWarning,
    )

args, kwargs = get_args_from_env()
args = (repos_root,) + args[1:]

with contextlib.suppress(KeyError):
    kwargs["detect_removals"] = bool(strtobool(os.environ["KLAUS_DETECT_REMOVALS"]))

with contextlib.suppress(KeyError):
    kwargs["export_ok_path"] = os.environ["KLAUS_EXPORT_OK_PATH"]

with contextlib.suppress(KeyError):
    # How to deal with repository directories named "foo" and/or "foo.git".
    # This is a list of potential suffixes, with your operating system's
    # directory separator as a separator. Examples:
    #
    # KLAUS_EXPORT_OK_PATH="/.git"
    #   Directories with and without .git are accepted
    #   (the first entry is the empty string). Default.
    #
    # KLAUS_EXPORT_OK_PATH=".git"
    #   Only .git directories are accepted.
    #
    # KLAUS_EXPORT_OK_PATH=""
    #   The .git suffix is not considered.

    kwargs["directory_suffixes"] = os.environ["KLAUS_DIRECTORY_SUFFIXES"].split(os.sep)

application = make_autodetecting_app(*args, **kwargs)
