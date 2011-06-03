import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import difflib
import dulwich, dulwich.patch

def pairwise(iterable):
    prev = None
    for item in iterable:
        if prev is not None:
            yield prev, item
        prev = item

class RepoWrapper(dulwich.repo.Repo):
    def get_branch_or_commit(self, id):
        try:
            return self[id]
        except KeyError:
            return self.get_branch(id)

    def get_branch(self, name):
        return self['refs/heads/'+name]

    def get_default_branch(self):
        return self.get_branch('master')

    def history(self, commit=None, path=None, max_commits=None):
        commits = self._history(commit)
        if path:
            commits = (c1 for c1, c2 in pairwise(commits)
                       if self._path_changed_between(path, c1, c2))
        for commit in commits:
            if not max_commits:
                break
            max_commits -= 1
            yield commit

    def _history(self, commit):
        if commit is None:
            commit = self.get_default_branch()
        while commit.parents:
            yield commit
            commit = self[commit.parents[0]]

    def _path_changed_between(self, path, commit1, commit2):
        path, filename = os.path.split(path)
        blob1 = self.get_tree(commit1, path)[filename]
        blob2 = self.get_tree(commit2, path)[filename]
        return blob1[1] != blob2[1]

    def get_tree(self, commit, path):
        tree = self[commit.tree]
        if path:
            for directory in path.split('/'):
                tree = self[tree[directory][1]]
        return tree

    def listdir(self, commit, root=None):
        tree = self.get_tree(commit, root)
        return ((entry.path, entry.in_path(root)) for entry in tree.iteritems())

    def commit_diff(self, commit):
        parent = self[commit.parents[0]]
        stringio = StringIO()
        dulwich.patch.write_tree_diff(stringio, self.object_store,
                                      parent.tree, commit.tree)
        return stringio.getvalue()

def Repo(name, path, _cache={}):
    repo = _cache.get(path)
    if repo is None:
        repo = _cache[path] = RepoWrapper(path)
        repo.name = name
    return repo
