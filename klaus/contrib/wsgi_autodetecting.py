"""
Alternative take on the "automatically discovered repositories" concept
that requires no threads, polling or inotify. Instead the filesystem is
consulted whenever a repository name is looked up.

Since Path.exists() and Path.iterdir() are fairly quick filesystem
operations, performance should be good for small to medium sites.
FancyRepo() objects are cached.

Repositories are identified by the existence of a

    <reponame>/git-daemon-export-ok

file (for compatibility with gitweb). You can customize this path using
the export_ok_path parameter. Setting it to '.' will cause every
subdirectory to be considered a git repository.

For large sites this approach may be hard on the filesystem when listing
repositories, because the process of enumerating the git repositories
causes the git-daemon-export-ok file to be checked in every repository.
This can be mitigated by setting detect_removals to False.
"""

import collections.abc
import functools
import os
import pathlib

import klaus
import klaus.repo

_bad_names = frozenset([os.curdir, os.pardir])
_bad_chars = frozenset(["\0", os.sep, os.altsep])
_default_directory_suffixes = ["", ".git"]


def coalesce(*args):
    """Return the first argument that is not None"""

    return next(arg for arg in args if arg is not None)


class AutodetectingRepoDict(collections.abc.Mapping):
    """
    Maintain a virtual read-only dictionary whose contents represent
    the presence of git repositories in the given root directory.

    :param root: The path to a directory containing repositories, each
        a direct subdirectory of the root.
    :param namespace: A namespace that will be applied to all detected
        repositories.
    :param detect_removals: Detect if repositories have been removed.
        Defaults to True. Setting it to False can improve performance
        for repository listings in very large sites.
    :param export_ok_path: The filesystem path to check (relative to
        the candidate repository root) to see if it is a valid servable
        git repository. Defaults to 'git-daemon-export-ok'. Set to '.'
        if every directory is known to be a valid repository root.
    :param directory_suffixes: A list of suffixes that your git directories
        may have. The default is ['', '.git'].
    """

    def __init__(
        self,
        root,
        namespace=None,
        detect_removals=None,
        export_ok_path=None,
        directory_suffixes=None,
    ):
        self._root = pathlib.Path(root)
        self._cache = {}
        self._namespace = namespace
        self._detect_removals = coalesce(detect_removals, True)
        self._export_ok_path = coalesce(export_ok_path, "git-daemon-export-ok")
        # Use the keys of a dict in reverse order so that we can create a sort
        # of "poor man's splay tree": the suffixes are always tried in reverse
        # order. If a suffix was matched succesfully it is moved to the end by
        # removing and readding it so that it is tried as the first option for
        # the next repository.
        self._suffixes = dict.fromkeys(
            reversed(list(coalesce(directory_suffixes, _default_directory_suffixes)))
        )

    def __getitem__(self, name):
        if (
            not name
            or name.startswith(".")
            or name in _bad_names
            or not _bad_chars.isdisjoint(name)
        ):
            raise KeyError(name)

        if not self._detect_removals:
            # Try returning a cached version first, to avoid filesystem access
            try:
                return self._cache[name]
            except KeyError:
                pass

        for suffix in reversed(self._suffixes):
            # Bare git repositories may have a .git suffix on the directory name:
            path = self._root / (name + suffix)
            if (path / self._export_ok_path).exists():
                # Reorder suffix test order on the assumption that most repos will
                # have the same suffix:
                del self._suffixes[suffix]
                self._suffixes[suffix] = None
                break
        else:
            self._cache.pop(name, None)
            raise KeyError(name)

        if self._detect_removals:
            try:
                return self._cache[name]
            except KeyError:
                pass

        repo = klaus.repo.FancyRepo(str(path), self._namespace)
        self._cache[name] = repo
        return repo

    def __iter__(self):
        def is_valid_repo(path):
            if not self._detect_removals and path.name in self._cache:
                return True
            return (path / self._export_ok_path).exists()

        suffixes = sorted(self._suffixes, key=len, reverse=True)

        def removesuffixes(string):
            for suffix in suffixes:
                attempt = string.removesuffix(suffix)
                if attempt != string:
                    return attempt
            return string

        return (
            removesuffixes(path.name)
            for path in self._root.iterdir()
            if is_valid_repo(path)
        )

    def __len__(self):
        return sum(1 for _ in self)


class AutodetectingRepoContainer(klaus.repo.BaseRepoContainer):
    """
    RepoContainer based on AutodetectingRepoDict.
    See AutodetectingRepoDict for parameter descriptions.
    """

    def __init__(self, repos_root, *args, **kwargs):
        super().__init__(repos_root)
        self.valid = AutodetectingRepoDict(repos_root, *args, **kwargs)


def make_autodetecting_app(
    repos_root,
    *args,
    detect_removals=None,
    export_ok_path=None,
    directory_suffixes=None,
    **kwargs,
):
    return klaus.make_app(
        repos_root,
        *args,
        repo_container_factory=functools.partial(
            AutodetectingRepoContainer,
            detect_removals=detect_removals,
            export_ok_path=export_ok_path,
            directory_suffixes=directory_suffixes,
        ),
        **kwargs,
    )
