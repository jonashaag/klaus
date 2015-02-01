import os
import dulwich
import logging

from klaus.repo import FancyRepo
from klaus import Klaus, make_app

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        DirCreatedEvent,
        DirDeletedEvent,
    )
except ImportError:
    import sys
    print("To automatically detect and reload repositories as they change, watchdog must be installed")
    print("see https://pypi.python.org/pypi/watchdog/")
    sys.exit()


logger = logging.getLogger(__file__)

def is_subdirectory(haystack, needle):
    """
    checks whether `needle` exists as a subdirectory of `haystack`
    """
    def func(arg, dirname, fnames):
        if dirname == needle or needle in fnames:
            logger.debug('%s is within %s', needle, haystack)
            raise StopIteration()
    try:
        os.path.walk(haystack, func, None)
    except StopIteration:
        return True
    return False


class KlausEventHandler(FileSystemEventHandler):
    """
    Basic file-system event handler for a klaus app.
    When git repositories are created, moved or deleted, watchdog will notify us here.
    We try and update the klaus wsgi app with the modifications as they happen.
    """
    def __init__(self, klausapp, *args, **kwargs):
        self.app = klausapp
        return super(KlausEventHandler, self).__init__(*args, **kwargs)

    def _add_dir(self, directory):
        """
        Attempts to register `directory` with the klaus app as a git repository.
        If `directory` is not a git repo, this method does nothing.
        """
        try:
            repo = FancyRepo(directory)
        except dulwich.errors.NotGitRepository:
            logger.debug("Dulwich says '%s' is not a git repository", directory)
            return

        matching = filter(lambda existing_repo: existing_repo.name == repo.name, self.app.repos)
        if matching:
             logger.warning("skipping repo with duplicate name:%s", repo)
             return
        logger.info("Adding repository, '%s' at '%s'", repo.name, directory)
        self.app.repos.append(repo)

    def on_created(self, event):
        # We're only interested in directories; A git repo is always a directory
        if type(event) != DirCreatedEvent:
            return
        logger.debug("Received directory creation event for '%s'", event.src_path)
        self._add_dir(event.src_path)
        self.app.update_repos_list()

    def on_deleted(self, event):
        if type(event) != DirDeletedEvent:
            return
        matching = filter(lambda existing_repo : existing_repo.path == event.src_path, self.app.repos)

        map(lambda x: self.app.repos.remove(x), matching)
        logger.info("%s was deleted; removing from klaus", event.src_path)
        self.app.update_repos_list()

    def on_moved(self, event):
        """
        Moved is not the same as deleted, unless the moved dir is no longer a subset of
        any of the watched trees. In that case we need to consider it a deletion,
        and remove it from the list of watched repos; otherwise we need to update its path.
        This is a potentially expensive operation, because the only reliable way
        to detect whether it is a subset (including symlinks etc) is to walk the path.
        In practice, this shouldn't affect performance in the general case,
        as moving a repository is a rare event.
        """

        matching = filter(lambda existing_repo : existing_repo.path == event.src_path, self.app.repos)
        if not matching:
            logger.debug("ignored non-repo move, %s -> %s", event.src_path, event.dest_path)
            return

        #first unregister old repositories
        map(lambda x: self.app.repos.remove(x), matching)
        # then see if the new destination is part of the klaus watchlist
        for directory in self.app.basedirs:
            if is_subdirectory(directory, event.dest_path):
                logger.info("'%s' -> '%s'; updating references", event.src_path, event.dest_path)
                self._add_dir(event.dest_path)

        self.app.update_repos_list()
        logger.info(
            "%s was moved out of KLAUS_REPOS to %s, and is no longer a watched repository",
            event.src_path,
            event.dest_path
        )


class KlausAutoDiscover(Klaus):
    """
    Instead of the normal Klaus behaviour of receiving a list of git repositories
    as `os.environ['KLAUS_REPOS']`, this app searches `os.environ['KLAUS_REPOS']`
    for valid git repositories and updates the application automatically when any
    changes are made.
    This simplifies administration significantly, but may cause problems with
    large repositories.
    """
    def __init__(self, basedirs, site_name, use_smarthttp, **kwargs):
        self.basedirs = basedirs
        repo_paths = []
        # first find all the existing repos in the given base directory
        for directory in basedirs:
            for fspath in os.listdir(directory):
                try:
                    path = os.path.join(directory, fspath)
                    FancyRepo(path)  # The result is discarded. This is just a test.
                    repo_paths.append(path)
                except dulwich.errors.NotGitRepository:
                    continue
        self.observer = Observer()
        fs_event_handler = KlausEventHandler(self)
        # Then setup up a handler to notify us when the content of any of those directories change.
        map(lambda directory: self.observer.schedule(fs_event_handler, directory, recursive=True), basedirs)
        self.observer.start()
        return super(KlausAutoDiscover, self).__init__(repo_paths, site_name, use_smarthttp, **kwargs)

    def __del__(self):
        self.observer.stop()


if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as file:
        application = make_app(
            os.environ['KLAUS_REPOS'].split(),
            os.environ['KLAUS_SITE_NAME'],
            os.environ.get('KLAUS_USE_SMARTHTTP'),
            file,
            KlausAutoDiscover
        )
else:
    application = make_app(
        os.environ['KLAUS_REPOS'].split(),
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
        None,
        KlausAutoDiscover
    )

