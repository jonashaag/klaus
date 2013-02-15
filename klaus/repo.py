import os
import cStringIO

import dulwich, dulwich.patch
from dulwich.object_store import tree_lookup_path

from klaus.utils import check_output, force_unicode
from klaus.diff import prepare_udiff
from klaus.markup import can_render, render


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

    def get_description(self):
        description_file = self.get_named_file('description')
        if description_file:
            description = force_unicode(description_file.read())
            if not description.startswith("Unnamed repository;"):
                return description

    def get_readme(self):
        readme_formats = {'.md':   None,
                          '.mkdn': None,
                          '.rst':  None,
                          '.rest': None}
        tree = self["HEAD"].tree

        for format in readme_formats.keys():
            file = "README" + format
            try:
                readme_formats[format] = tree_lookup_path(self.get_object, tree, file)
            except KeyError:
                pass

        for format, asset in readme_formats.items():
            if asset:
                file = "README" + format
                content = self[asset[1]].data
                if can_render(file):
                    return {'rendered': True, 'content': render(file, content)}
                else:
                    return {'rendered': False, 'content': force_unicode(content)}

        return None

    def get_commit(self, rev):
        for prefix in ['refs/heads/', 'refs/tags/', '']:
            key = prefix + rev
            try:
                # XXX: Workaround https://github.com/jelmer/dulwich/issues/82
                if not key.isalnum():
                    key = self.refs[key]
                obj = self.object_store[key]
                if isinstance(obj, dulwich.objects.Tag):
                    obj = self[obj.object[1]]
                return obj
            except KeyError:
                pass
        raise KeyError(rev)

    def get_default_branch(self):
        """
        Tries to guess the default repo branch name.
        """
        for candidate in ['master', 'trunk', 'default', 'gh-pages']:
            try:
                self.get_commit(candidate)
                return candidate
            except KeyError:
                pass
        return self.get_branch_names()[0]

    def get_sorted_ref_names(self, prefix, exclude=None):
        refs = self.refs.as_dict(prefix)
        if exclude:
            refs.pop(prefix + exclude, None)

        def get_commit_time(refname):
            obj = self[refs[refname]]
            if isinstance(obj, dulwich.objects.Tag):
                return obj.tag_time
            return obj.commit_time

        return sorted(refs.iterkeys(), key=get_commit_time, reverse=True)

    def get_branch_names(self, exclude=None):
        """ Returns a sorted list of branch names. """
        return self.get_sorted_ref_names('refs/heads', exclude)

    def get_tag_names(self):
        """ Returns a sorted list of tag names. """
        return self.get_sorted_ref_names('refs/tags')

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

    def get_blob_or_tree(self, commit, path):
        """ Returns the Git tree or blob object for `path` at `commit`. """
        tree_or_blob = self[commit.tree]  # Still a tree here but may turn into
                                          # a blob somewhere in the loop.
        for part in path.strip('/').split('/'):
            if part:
                if isinstance(tree_or_blob, dulwich.objects.Blob):
                    # Blobs don't have sub-files/folders.
                    raise KeyError
                tree_or_blob = self[tree_or_blob[part][1]]
        return tree_or_blob

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
