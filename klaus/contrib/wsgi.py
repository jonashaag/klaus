"""
WSGI application factory module for Klaus.

This module creates a WSGI application instance by reading configuration
from environment variables and setting up optional HTTP digest authentication.
"""

from klaus import make_app

from .app_args import get_args_from_env

# Get application arguments and keyword arguments from environment variables
args, kwargs = get_args_from_env()

# Handle optional HTTP digest authentication file
if kwargs["htdigest_file"]:
    with open(kwargs["htdigest_file"]) as file:
        kwargs["htdigest_file"] = file
        application = make_app(*args, **kwargs)
else:
    application = make_app(*args, **kwargs)
