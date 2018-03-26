import os
import warnings
import io

from .app_args import get_args_from_env
from .wsgi_autoreloading import make_autoreloading_app


if 'KLAUS_REPOS' in os.environ:
    warnings.warn("use KLAUS_REPOS_ROOT instead of KLAUS_REPOS for the autoreloader apps", DeprecationWarning)

args, kwargs = get_args_from_env()
repos_root = os.environ.get('KLAUS_REPOS_ROOT') or os.environ['KLAUS_REPOS']
args = (repos_root,) + args[1:]

if kwargs['htdigest_file']:
    # Cache the contents of the htdigest file, the application will not read
    # the file like object until later when called.
    with io.open(kwargs['htdigest_file'], encoding='utf-8') as htdigest_file:
        kwargs['htdigest_file'] = io.StringIO(htdigest_file.read())

application = make_autoreloading_app(*args, **kwargs)
