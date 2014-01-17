import os
import time
import threading
from klaus import make_app


# Shared state between poller and application wrapper
class _:
    #: the real WSGI app
    inner_app = None
    should_reload = True


def poll_for_changes(interval, dir):
    """
    Polls `dir` for changes every `interval` seconds and sets `should_reload`
    accordingly.
    """
    old_contents = os.listdir(dir)
    while 1:
        time.sleep(interval)
        if _.should_reload:
            # klaus application has not seen our change yet
            continue
        new_contents = os.listdir(dir)
        if new_contents != old_contents:
            # Directory contents changed => should_reload
            new_contents = old_contents
            _.should_reload = True


def make_autoreloading_app(repos_root, *args, **kwargs):
    def app(environ, start_response):
        if _.should_reload:
            # Refresh inner application with new repo list
            print "Reloading repository list..."
            _.inner_app = make_app(
                [os.path.join(repos_root, x) for x in os.listdir(repos_root)],
                *args, **kwargs
            )
            _.should_reload = False
        return _.inner_app(environ, start_response)

    # Background thread that polls the directory for changes
    poller_thread = threading.Thread(target=(lambda: poll_for_changes(10, repos_root)))
    poller_thread.daemon = True
    poller_thread.start()

    return app


application = make_autoreloading_app(
    os.environ['KLAUS_REPOS'],
    os.environ['KLAUS_SITE_NAME'],
    os.environ.get('KLAUS_USE_SMARTHTTP'),
    os.environ.get('KLAUS_HTDIGEST_FILE'),
)
