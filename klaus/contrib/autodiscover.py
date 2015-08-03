import os
import logging
import threading
import sys

import dulwich

from klaus.repo import FancyRepo
from klaus import Klaus, make_app

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    sys.stderr.write("To automatically detect and reload repositories as they "
                     "change, watchdog must be installed.\n")
    sys.stderr.write("See https://pypi.python.org/pypi/watchdog/\n")
    sys.exit(1)

logger = logging.getLogger(__name__)


def is_subdirectory(haystack, needle):
    """
    checks whether `needle` exists as a subdirectory of `haystack`
    """
    haystack = os.path.realpath(haystack)
    needle = os.path.realpath(needle)
    if not os.path.isdir(needle):
        return False
    return needle.startswith(haystack)


class KlausFSEventHandler(FileSystemEventHandler):
    """
    Basic file-system event handler for a klaus app.
    When directories are created, moved or deleted, we will be notified here.
    We try and update the klaus wsgi app with modifications to git repos as
    they happen.
    """
    def __init__(self, klausapp, *args, **kwargs):
        self._klausapp = klausapp
        return super(KlausFSEventHandler, self).__init__(*args, **kwargs)

    def on_modified(self, event):
        if not event.is_directory:
            return
        self._klausapp.remove_repo(event.src_path)
        self._klausapp.add_repo(event.src_path)

    def on_created(self, event):
        # We're only interested in directories; A git repo is always a directory
        if not event.is_directory:
            return
        logger.debug("Received directory creation event for '%s'", event.src_path)
        self._klausapp.add_repo(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            return
        logger.debug("Received directory deletion event for '%s'", event.src_path)
        self._klausapp.remove_repo(event.src_path)

    def on_moved(self, event):
        """
        Moved is not the same as deleted, unless the moved dir is no longer a
        subset of any of the watched trees. In that case we need to consider it
        a deletion, and remove it from the list of watched repos; otherwise we
        need to update its path. This is a potentially expensive operation,
        but shouldn't affect performance in the general case, as moving a
        repository is a rare event.
        """
        logger.debug(
            "Received repository move event:'%s'->'%s'",
            event.src_path,
            event.dest_path
        )
        # first unregister old repository
        if not self._klausapp.remove_repo(event.src_path):
            logger.debug(
                "ignored non-repo move, %s -> %s",
                event.src_path, event.dest_path
            )
            return

        # then see if the new destination is part of the klaus watchlist
        for directory in self._klausapp.basedirs:
            if is_subdirectory(directory, event.dest_path):
                logger.info(
                    "'%s' -> '%s'; updating references",
                    event.src_path,
                    event.dest_path
                )
                self._klausapp.add_repo(event.dest_path)
                break
        else:
            logger.info(
                "%s was moved out of KLAUS_REPOS to %s, and is now ignored",
                event.src_path,
                event.dest_path
            )


class KlausAutoDiscover(Klaus):
    """
    Instead of the normal Klaus behaviour of receiving a list of git
    repositories as `os.environ['KLAUS_REPOS']`, this searches
    `os.environ['KLAUS_REPOS']` for valid git repositories and updates klaus
    automatically when any changes are made. if `recursive=True`, klaus will
    watch every subdirectory in the given directories, and discover all git
    repositories therein. This simplifies administration significantly, but may
    cause problems with large repositories, as the underlying file watch
    mechanisms don't expose a recursion depth parameter on any of the common
    platforms (Linux, win32, OS X).
    """
    def __init__(self, basedirs, site_name, use_smarthttp, **kwargs):
        recursive = kwargs.pop('discover_recursive', False)
        super(KlausAutoDiscover, self).__init__([], site_name, use_smarthttp, **kwargs)
        self._lock = threading.RLock()
        self._basedirs = basedirs
        self._observer = Observer()

        # First find and add all the existing repos in the given base directory.
        for directory in basedirs:
            for fspath in os.listdir(directory):
                path = os.path.join(directory, fspath)
                self.add_repo(path)

        # Then create a handler to notify us of any changes within those dirs.
        fs_event_handler = KlausFSEventHandler(self)
        for directory in basedirs:
            self._observer.schedule(fs_event_handler, directory, recursive=recursive)

        self._observer.start()

    def add_repo(self, directory):
        """
        Attempts to register `directory` with the klaus app as a git repository.
        If `directory` is not a git repo, this method does nothing.
        """
        with self._lock:
            try:
                repo = FancyRepo(directory)
            except dulwich.errors.NotGitRepository:
                logger.debug("Dulwich says '%s' is not a git repository", directory)
                return

            if self.repo_map.get(repo.name):
                logger.debug("skipping repo with duplicate name:%s", repo)
                return
            logger.info("Adding repository, '%s' at '%s'", repo.name, directory)
            self.repo_map[repo.name] = repo

    def remove_repo(self, directory):
        """
        given a filesystem path, `directory` attempts to remove the
        corresponding repository from the list of watched repositories.
        """
        with self._lock:
            key_map = dict(zip(
                (repo.path for repo in self.repo_map.values()),
                self.repo_map)
            )
            try:
                name = key_map[directory]
                del self.repo_map[name]
                return True
            except KeyError:
                logger.debug(
                    "couldn't delete '%s'; not an existing repository",
                    directory
                )
                pass

    def __del__(self):
        self._observer.stop()
        self._observer.join()


def _app(htdigest_file=None):
    return make_app(
        os.environ['KLAUS_REPOS'].split(),
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
        htdigest_file,
        klaus_class=KlausAutoDiscover,
        discover_recursive=os.environ.get('KLAUS_DISCOVER_RECURSIVE')
    )

if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as htdigest_file:
        application = _app(htdigest_file)
else:
    application = _app()
