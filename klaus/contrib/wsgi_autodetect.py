import os
import warnings
import distutils.util

from .app_args import get_args_from_env
from .wsgi_autodetecting import make_autodetecting_app


try:
    repos_root = os.environ['KLAUS_REPOS_ROOT']
except KeyError:
    repos_root = os.environ['KLAUS_REPOS']
    warnings.warn(
        "use KLAUS_REPOS_ROOT instead of KLAUS_REPOS for the autodecting apps",
        DeprecationWarning,
    )

args, kwargs = get_args_from_env()
args = (repos_root,) + args[1:]

try:
    detect_removals = os.environ['KLAUS_DETECT_REMOVALS']
except KeyError:
    pass
else:
    kwargs['detect_removals'] = distutils.util.strtobool(detect_removals)

try:
    kwargs['export_ok_path'] = os.environ['KLAUS_EXPORT_OK_PATH']
except KeyError:
    pass

application = make_autodetecting_app(*args, **kwargs)
