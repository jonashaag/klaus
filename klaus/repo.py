import os
import cStringIO

import dulwich, dulwich.patch

from klaus.utils import check_output
from klaus.diff import prepare_udiff


class FancyRepo(dulwich.repo.Repo):
    # TODO: factor out stuff into dulwich
    @property
    def name(self):
        return self.path.rstrip(os.sep).split(os.sep)[-1].replace('.git', '')

    def get_last_updated_at(self):
        refs = [self[ref_hash] for ref_hash in self.get_refs().itervalues()]
        refs.sort(key=lambda obj:getattr(obj, 'commit_time', None),
                  reverse=True)
        if refs:
            return refs[0].commit_time
        return None

    def get_branch_or_commit(self, id):
        """
        Returns a `(commit_object, is_branch)` tuple for the commit or branch
        identified by `id`.
        """
        try:
            return self[id], False
        except KeyError:
            return self.get_branch(id), True

    def get_branch(self, name):
        """ Returns the commit object pointed to by the branch `name`. """
        return self['refs/heads/'+name]

    def get_default_branch(self):
        """
        Tries to guess the default repo branch name.
        """
        for candidate in ['master', 'trunk', 'default', 'gh-pages']:
            try:
                self.get_branch(candidate)
                return candidate
            except KeyError:
                pass
        return self.get_branch_names()[0]

    def get_branch_names(self, exclude=()):
        """ Returns a sorted list of branch names. """
        branches = []
        for ref in self.get_refs():
            if ref.startswith('refs/heads/'):
                name = ref[len('refs/heads/'):]
                if name not in exclude:
                    branches.append(name)
        branches.sort()
        return branches

    def get_tag_names(self):
        """ Returns a sorted list of tag names. """
        tags = []
        for ref in self.get_refs():
            if ref.startswith('refs/tags/'):
                tags.append(ref[len('refs/tags/'):])
        tags.sort()
        return tags

    def history(self, commit, path=None, max_commits=None, skip=0):
        """
        Returns a list of all commits that infected `path`, starting at branch
        or commit `commit`. `skip` can be used for pagination, `max_commits`
        to limit the number of commits returned.

        Similar to `git log [branch/commit] [--skip skip] [-n max_commits]`.
        """
        # XXX The pure-Python/dulwich code is very slow compared to `git log`
        #     at the time of this writing (mid-2012).
        #     For instance, `git log .tx` in the Django root directory takes
        #     about 0.15s on my machine whereas the history() method needs 5s.
        #     Therefore we use `git log` here until dulwich gets faster.
        #     For the pure-Python implementation, see the 'purepy-hist' branch.

        cmd = ['git', 'log', '--format=%H']
        if skip:
            cmd.append('--skip=%d' % skip)
        if max_commits:
            cmd.append('--max-count=%d' % max_commits)
        cmd.append(commit)
        if path:
            cmd.extend(['--', path])

        sha1_sums = check_output(cmd, cwd=os.path.abspath(self.path))
        return [self[sha1] for sha1 in sha1_sums.strip().split('\n')]

    def get_tree(self, commit, path):
        """ Returns the Git tree object for `path` at `commit`. """
        tree = self[commit.tree]
        if path:
            for directory in path.strip('/').split('/'):
                if directory:
                    tree = self[tree[directory][1]]
        return tree

    def commit_diff(self, commit):
        from klaus.utils import guess_is_binary, force_unicode

        if commit.parents:
            parent_tree = self[commit.parents[0]].tree
        else:
            parent_tree = None

        changes = self.object_store.tree_changes(parent_tree, commit.tree)
        for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in changes:
            try:
                if newsha and guess_is_binary(self[newsha]) or \
                   oldsha and guess_is_binary(self[oldsha]):
                    yield {
                        'is_binary': True,
                        'old_filename': oldpath or '/dev/null',
                        'new_filename': newpath or '/dev/null',
                        'chunks': None
                    }
                    continue
            except KeyError:
                # newsha/oldsha are probably related to submodules.
                # Dulwich will handle that.
                pass

            stringio = cStringIO.StringIO()
            dulwich.patch.write_object_diff(stringio, self.object_store,
                                            (oldpath, oldmode, oldsha),
                                            (newpath, newmode, newsha))
            files = prepare_udiff(force_unicode(stringio.getvalue()),
                                  want_header=False)
            if not files:
                # the diff module doesn't handle deletions/additions
                # of empty files correctly.
                yield {
                    'old_filename': oldpath or '/dev/null',
                    'new_filename': newpath or '/dev/null',
                    'chunks': []
                }
            else:
                yield files[0]
