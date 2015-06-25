import os
import stat
import tarfile
from io import BytesIO
from contextlib import closing


class ListBytesIO(object):
    """
    Turns a list of bytestrings into a file-like object.

    This is similar to creating a `BytesIO` from a concatenation of the
    bytestring list, but saves memory by NOT creating one giant bytestring first::

        BytesIO(b''.join(list_of_bytestrings)) =~= ListBytesIO(list_of_bytestrings)
    """
    def __init__(self, contents):
        self.contents = contents
        self.pos = (0, 0)

    def read(self, maxbytes=None):
        if maxbytes < 0:
            maxbytes = float('inf')

        buf = []
        chunk, cursor = self.pos

        while chunk < len(self.contents):
            if maxbytes < len(self.contents[chunk]) - cursor:
                buf.append(self.contents[chunk][cursor:cursor+maxbytes])
                cursor += maxbytes
                self.pos = (chunk, cursor)
                break
            else:
                buf.append(self.contents[chunk][cursor:])
                maxbytes -= len(self.contents[chunk]) - cursor
                chunk += 1
                cursor = 0
                self.pos = (chunk, cursor)
        return b''.join(buf)


def tar_stream(repo, tree, mtime, format=''):
    """
    Returns a generator that lazily assembles a .tar.gz archive, yielding it in
    pieces (bytestrings). To obtain the complete .tar.gz binary file, simply
    concatenate these chunks.

    'repo' and 'tree' are the dulwich Repo and Tree objects the archive shall be
    created from. 'mtime' is a UNIX timestamp that is assigned as the modification
    time of all files in the resulting .tar.gz archive.
    """
    buf = BytesIO()
    with closing(tarfile.open(None, "w:%s" % format, buf)) as tar:
        for entry_abspath, entry in walk_tree(repo, tree):
            try:
                blob = repo[entry.sha]
            except KeyError:
                # Entry probably refers to a submodule, which we don't yet support.
                continue
            data = ListBytesIO(blob.chunked)

            info = tarfile.TarInfo()
            info.name = entry_abspath
            info.size = blob.raw_length()
            info.mode = entry.mode
            info.mtime = mtime

            tar.addfile(info, data)
            yield buf.getvalue()
            buf.truncate(0)
            buf.seek(0)
    yield buf.getvalue()


def walk_tree(repo, tree, root=''):
    """
    Recursively walk a dulwich Tree, yielding tuples of (absolute path,
    TreeEntry) along the way.
    """
    for entry in tree.iteritems():
        entry_abspath = os.path.join(root, entry.path)
        if stat.S_ISDIR(entry.mode):
            for _ in walk_tree(repo, repo[entry.sha], entry_abspath):
                yield _
        else:
            yield (entry_abspath, entry)
