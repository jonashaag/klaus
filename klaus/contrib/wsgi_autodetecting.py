"""
Alternative take on the "automatically discovered repositories" concept
that requires no threads, polling or inotify. Instead the filesystem is
consulted whenever a repository name is looked up.

Since os.path.exists() and os.listdir() are fairly quick filesystem
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

import pathlib
import os
import os.path
import functools
import collections.abc

import klaus
import klaus.repo


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
    """

    def __init__(
        self,
        root,
        namespace=None,
        detect_removals=None,
        export_ok_path=None,
    ):
        self._root = pathlib.Path(root)
        self._base = {}
        self._namespace = namespace
        self._detect_removals = coalesce(detect_removals, True)
        self._export_ok_path = coalesce(export_ok_path, 'git-daemon-export-ok')

    def __getitem__(self, name):
        if not name or name[0] == '.' or name in {os.curdir, os.pardir} or any(
            badness in name for badness in ['\0', os.sep, os.altsep]
                if badness is not None
        ):
            raise KeyError(name)

        if not self._detect_removals:
            # Try returning a cached version first, to avoid filesystem access
            try:
                return self._base[name]
            except KeyError:
                pass

        path = self._root / name
        if not os.path.exists(path / self._export_ok_path):
            self._base.pop(name, None)
            raise KeyError(name)

        if self._detect_removals:
            try:
                return self._base[name]
            except KeyError:
                pass

        repo = klaus.repo.FancyRepo(str(path), self._namespace)
        self._base[name] = repo
        return repo

    def __iter__(self):
        def is_valid_repo(name):
            if not self._detect_removals and name in self._base:
                return True
            return os.path.exists(self._root / name / self._export_ok_path)

        return (name for name in os.listdir(self._root) if is_valid_repo(name))

    def __len__(self):
        return sum(1 for _ in self)


class AutodetectingRepoContainer(klaus.repo.BaseRepoContainer):
    """
    RepoContainer based on AutodetectingRepoDict.
    See AutodetectingRepoDict for parameter descriptions.
    """

    def __init__(self, repo_paths, *args, **kwargs):
        super().__init__(repo_paths)
        self.valid = AutodetectingRepoDict(repo_paths, *args, **kwargs)


def make_autodetecting_app(
    repos_root,
    *args,
    detect_removals=None,
    export_ok_path=None,
    **kwargs,
):
    return klaus.make_app(
        repos_root,
        *args,
        repo_container_factory=functools.partial(
            AutodetectingRepoContainer,
            detect_removals=detect_removals,
            export_ok_path=export_ok_path,
        ),
        **kwargs,
    )
