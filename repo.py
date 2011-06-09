import os
from itertools import islice
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import dulwich, dulwich.patch
from diff import prepare_udiff

def pairwise(iterable):
    prev = None
    for item in iterable:
        if prev is not None:
            yield prev, item
        prev = item

class RepoWrapper(dulwich.repo.Repo):
    def get_branch_or_commit(self, id):
        try:
            return self[id], False
        except KeyError:
            return self.get_branch(id), True

    def get_branch(self, name):
        return self['refs/heads/'+name]

    def get_default_branch(self):
        return self.get_branch('master')

    def get_branch_names(self):
        branches = []
        for ref in self.get_refs():
            if ref.startswith('refs/heads/'):
                branches.append(ref[len('refs/heads/'):])
        branches.sort()
        return branches

    def get_tag_names(self):
        tags = []
        for ref in self.get_refs():
            if ref.startswith('refs/tags/'):
                tags.append(ref[len('refs/tags/'):])
        tags.sort()
        return tags

    def history(self, commit=None, path=None, max_commits=None, skip=0):
        if not isinstance(commit, dulwich.objects.Commit):
            commit, _ = self.get_branch_or_commit(commit)
        commits = self._history(commit)
        path = path.strip('/')
        if path:
            commits = (c1 for c1, c2 in pairwise(commits)
                       if self._path_changed_between(path, c1, c2))
        return list(islice(commits, skip, skip+max_commits))

    def _history(self, commit):
        if commit is None:
            commit = self.get_default_branch()
        while commit.parents:
            yield commit
            commit = self[commit.parents[0]]
        yield commit

    def _path_changed_between(self, path, commit1, commit2):
        path, filename = os.path.split(path)
        try:
            blob1 = self.get_tree(commit1, path)
            if not isinstance(blob1, dulwich.objects.Tree):
                return True
            blob1 = blob1[filename]
        except KeyError:
            blob1 = None
        try:
            blob2 = self.get_tree(commit2, path)
            if not isinstance(blob2, dulwich.objects.Tree):
                return True
            blob2 = blob2[filename]
        except KeyError:
            blob2 = None
        if blob1 is None and blob2 is None:
            # file present in neither tree
            return False
        return blob1 != blob2

    def get_tree(self, commit, path):
        tree = self[commit.tree]
        if path:
            for directory in path.strip('/').split('/'):
                if directory:
                    tree = self[tree[directory][1]]
        return tree

    def listdir(self, commit, root=None):
        tree = self.get_tree(commit, root)
        return ((entry.path, entry.in_path(root)) for entry in tree.iteritems())

    def commit_diff(self, commit):
        from klaus import guess_is_binary, force_unicode

        if commit.parents:
            parent_tree = self[commit.parents[0]].tree
        else:
            parent_tree = None

        changes = self.object_store.tree_changes(parent_tree, commit.tree)
        for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in changes:
            try:
                if newsha and guess_is_binary(self[newsha].chunked) or \
                   oldsha and guess_is_binary(self[oldsha].chunked):
                    yield {
                        'is_binary': True,
                        'old_filename': oldpath or 'dev/null',
                        'new_filename': newpath or 'dev/null',
                        'chunks': [[{'line' : 'Binary diff not shown'}]]
                    }
                    continue
            except KeyError:
                # newsha/oldsha are probably related to submodules.
                # Dulwich will handle that.
                pass

            stringio = StringIO()
            dulwich.patch.write_object_diff(stringio, self.object_store,
                                            (oldpath, oldmode, oldsha),
                                            (newpath, newmode, newsha))
            files = prepare_udiff(force_unicode(stringio.getvalue()),
                                  want_header=False)
            if not files:
                # the diff module doesn't handle deletions/additions
                # of empty files correctly.
                yield {
                    'old_filename': oldpath or 'dev/null',
                    'new_filename': newpath or 'dev/null',
                    'chunks': []
                }
            else:
                yield files[0]


def Repo(name, path, _cache={}):
    repo = _cache.get(path)
    if repo is None:
        repo = _cache[path] = RepoWrapper(path)
        repo.name = name
    return repo
