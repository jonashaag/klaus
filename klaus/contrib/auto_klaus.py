"""
Alternative take on the "automatically discovered repositories" concept
that requires no threads, polling or inotify. Instead the filesystem is
consulted whenever a repository name is looked up.

Since os.path.exists() and os.listdir() are fairly quick filesystem
operations, performance should be good for small to medium sites.
FancyRepo() objects are cached.

Repositories are identified by the existence of a

    <reponame>/git-daemon-export-ok

file (for compatibility with gitweb).

Example usage:

    from klaus.contrib.auto_klaus import Klaus, SlashDynamicRepos

    application = Klaus('/srv/git', "My git repositories", False)

    application.wsgi_app = httpauth.AlwaysFailingAuthMiddleware(
        wsgi_app=dulwich.web.make_wsgi_chain(
            backend=dulwich.server.DictBackend(SlashDynamicRepos(application.valid_repos)),
            fallback_app=application.wsgi_app,
        ),
    )
"""

import collections.abc
import pathlib
import os
import os.path

import klaus
import klaus.repo

class FilesystemRepoDict(collections.abc.Mapping):
    """
    Maintain a virtual read-only dictionary whose contents represent
    the presence of git repositories in the given root directory.
    """

    def __init__(self, root):
        self._root = pathlib.Path(root)
        self._repos = {}

    def __getitem__(self, name):
        if not name or name[0] == '.' or '/' in name or '\0' in name:
            raise KeyError(name)

        repos = self._repos
        path = self._root / name
        if not os.path.exists(path / 'git-daemon-export-ok'):
            repos.pop(name, None)
            raise KeyError(name)

        try:
            return repos[name]
        except KeyError:
            pass

        repo = klaus.repo.FancyRepo(str(path))
        repos[name] = repo
        return repo

    def __iter__(self):
        root = self._root
        return (
            repo for repo in os.listdir(root)
                if os.path.exists(root / repo / 'git-daemon-export-ok')
        )

    def __len__(self):
        return sum(1 for _ in self)

class SlashFilesystemRepoDict(collections.abc.Mapping):
    """
    Proxy for FilesystemRepoDict that makes it so that keys start with a '/'
    character. Needed for dulwich.server.DictBackend.
    """

    def __init__(self, base):
        self._base = base

    def __getitem__(self, path):
        if not path or path[0] != '/':
            raise KeyError(path)
        return self._base[path[1:]]

    def __iter__(self):
        return ('/' + name for name in self._base)

    def __len__(self):
        return len(self._base)

class Klaus(klaus.Klaus):
    def __init__(self, root, *args):
        super().__init__([], *args)
        self.valid_repos = FilesystemRepoDict(root)

    def load_repos(self, repo_paths):
        return [], []
