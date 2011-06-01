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

    def listdir(self, branch=None, root=None):
        branch = self.get_branch(branch)
        tree = self[branch.tree]
        if root is not None:
            for directory in root.split('/'):
                tree = self[tree[directory].sha]
        return tree.iteritems()

    def commit_diff(self, commit):
        parent = self[commit.parents[0]]
        stringio = StringIO()
        dulwich.patch.write_tree_diff(stringio, self.object_store,
                                      parent.tree, commit.tree)
        return stringio.getvalue()

class ChangeWrapper(dulwich.diff_tree.TreeChange):
    def as_udiff(self):
        with open(self.old.path) as f1, open(self.new.path) as f2:
            return ''.join(difflib.unified_diff(f1, f2))

def Repo(name, path, _cache={}):
    repo = _cache.get(path)
    if repo is None:
        repo = _cache[path] = RepoWrapper(path)
        repo.name = name
    return repo
