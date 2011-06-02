try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import difflib
import dulwich, dulwich.patch

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

    def history(self, commit=None, max_commits=None):
        if commit is None:
            commit = self.get_default_branch()
        if max_commits is None:
            max_commits = float('inf')
        while max_commits and commit.parents:
            yield commit
            commit = self[commit.parents[0]]
            max_commits -= 1

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
