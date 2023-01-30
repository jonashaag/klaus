from __future__ import print_function
import os
import os.path
import time
import threading
import warnings

from klaus import make_app

# Shared state between poller and application wrapper
class _:
    #: the real WSGI app
    inner_app = None
    should_reload = True


def find_git_repos_recursive(dir):
    if dir.endswith('.git'):
        yield dir
        return

    subdirectories = []
    for entry in os.scandir(dir):
        if entry.name == '.git':
            yield dir
            return

        if entry.is_dir():
            subdirectories.append(entry.path)

    for path in subdirectories:
        yield from find_git_repos_recursive(path)


def namespaceify(root, repos):
    map = {}
    raw = []
    map[None] = raw
    for path in repos:
        repo = os.path.relpath(path, root)
        try:
            [namespace, name] = repo.rsplit('/', 1)
            map[namespace] = map.get(namespace, [])
            map[namespace].append(path)
        except ValueError:
            raw.append(path)
    return map


def poll_for_changes(interval, dir):
    """
    Polls `dir` for changes every `interval` seconds and sets `should_reload`
    accordingly.
    """
    old_contents = list(find_git_repos_recursive(dir))
    while 1:
        time.sleep(interval)
        if _.should_reload:
            # klaus application has not seen our change yet
            continue
        new_contents = find_git_repos_recursive(dir)
        if new_contents != old_contents:
            # Directory contents changed => should_reload
            old_contents = new_contents
            _.should_reload = True


def make_autoreloading_app(repos_root, *args, **kwargs):
    def app(environ, start_response):
        if _.should_reload:
            # Refresh inner application with new repo list
            print("Reloading repository list...")
            _.inner_app = make_app(
                namespaceify(repos_root, find_git_repos_recursive(repos_root)),
                *args, **kwargs
            )
            _.should_reload = False
        return _.inner_app(environ, start_response)

    # Background thread that polls the directory for changes
    poller_thread = threading.Thread(target=(lambda: poll_for_changes(10, repos_root)))
    poller_thread.daemon = True
    poller_thread.start()

    return app


if 'KLAUS_REPOS' in os.environ:
    warnings.warn("use KLAUS_REPOS_ROOT instead of KLAUS_REPOS for the autoreloader apps", DeprecationWarning)

if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as file:
        application = make_autoreloading_app(
            os.environ.get('KLAUS_REPOS_ROOT') or os.environ['KLAUS_REPOS'],
            os.environ['KLAUS_SITE_NAME'],
            os.environ.get('KLAUS_USE_SMARTHTTP'),
            file,
        )
else:
    application = make_autoreloading_app(
        os.environ.get('KLAUS_REPOS_ROOT') or os.environ['KLAUS_REPOS'],
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
    )
