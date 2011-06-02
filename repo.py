try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import difflib
import dulwich, dulwich.patch

class RepoWrapper(dulwich.repo.Repo):
    def get_branch(self, name=None):
        if name is None:
            name = 'master'
        return self['refs/heads/'+name]

    def history(self, branch=None, max_commits=None):
        if max_commits is None:
            max_commits = float('inf')
        head = self.get_branch(branch)
        while max_commits and head.parents:
            yield head
            head = self[head.parents[0]]
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
