"""
WSGI application entry point for Klaus with auto-reloading functionality.

This module creates a WSGI application that automatically reloads when changes
are detected in the repository files. It handles environment variable configuration,
argument processing, and htdigest file caching.
"""

import io
import os
import warnings

from .app_args import get_args_from_env
from .wsgi_autoreloading import make_autoreloading_app

# Check for deprecated environment variable and issue warning
if "KLAUS_REPOS" in os.environ:
    warnings.warn(
        "use KLAUS_REPOS_ROOT instead of KLAUS_REPOS for the autoreloader apps",
        DeprecationWarning,
    )

# Get application arguments and keyword arguments from environment variables
args, kwargs = get_args_from_env()

# Determine the repository root path from environment variables
# Prefer KLAUS_REPOS_ROOT over the deprecated KLAUS_REPOS
repos_root = os.environ.get("KLAUS_REPOS_ROOT") or os.environ["KLAUS_REPOS"]

# Replace the first argument with the repository root path
args = (repos_root,) + args[1:]

# Handle htdigest file caching if specified
if kwargs["htdigest_file"]:
    # Cache the contents of the htdigest file, the application will not read
    # the file like object until later when called.
    with open(kwargs["htdigest_file"], encoding="utf-8") as htdigest_file:
        kwargs["htdigest_file"] = io.StringIO(htdigest_file.read())

# Create the auto-reloading WSGI application with processed arguments
application = make_autoreloading_app(*args, **kwargs)
