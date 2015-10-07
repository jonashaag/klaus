# -*- coding: utf-8 -*-
"""
    lodgeit.lib.diff
    ~~~~~~~~~~~~~~~~

    Render a nice diff between two things.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD
"""
import re
from cgi import escape


def prepare_udiff(udiff, **kwargs):
    """Prepare an udiff for a template."""
    return DiffRenderer(udiff).prepare(**kwargs)


class DiffRenderer(object):
    """Give it a unified diff and it renders you a beautiful
    html diff :-)
    """
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
        """:param udiff:   a text in udiff format"""
        self.lines = [escape(line) for line in udiff.splitlines()]

    def _extract_filename(self, line):
        """
        Extract file name from unified diff line:
            --- a/foo/bar   ==>   foo/bar
            +++ b/foo/bar   ==>   foo/bar
        """
        if line.startswith(("--- /dev/null", "+++ /dev/null")):
            return line[len("--- "):]
        else:
            return line[len("--- a/"):]

    def _highlight_line(self, line, next):
        """Highlight inline changes in both lines."""
        start = 0
        limit = min(len(line['line']), len(next['line']))
        while start < limit and line['line'][start] == next['line'][start]:
            start += 1
        end = -1
        limit -= start
        while -end <= limit and line['line'][end] == next['line'][end]:
            end -= 1
        end += 1
        if start or end:
            def do(l):
                last = end + len(l['line'])
                if l['action'] == 'add':
                    tag = 'ins'
                else:
                    tag = 'del'
                l['line'] = u'%s<%s>%s</%s>%s' % (
                    l['line'][:start],
                    tag,
                    l['line'][start:last],
                    tag,
                    l['line'][last:]
                )
            do(line)
            do(next)

    def prepare(self, want_header=True):
        """Parse the diff an return data for the template."""
        in_header = True
        header = []
        lineiter = iter(self.lines)
        files = []
        try:
            line = next(lineiter)
            while 1:
                # continue until we found the old file
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = next(lineiter)
                    continue

                if header and all(x.strip() for x in header):
                    if want_header:
                        files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = False
                chunks = []
                files.append({
                    'is_header':        False,
                    'old_filename':     self._extract_filename(line),
                    'new_filename':     self._extract_filename(next(lineiter)),
                    'additions':        0,
                    'deletions':        0,
                    'chunks':           chunks
                })

                line = next(lineiter)
                while line:
                    match = self._chunk_re.match(line)
                    if not match:
                        in_header = True
                        break

                    lines = []
                    chunks.append(lines)

                    old_line, old_end, new_line, new_end = \
                        [int(x or 1) for x in match.groups()]
                    old_line -= 1
                    new_line -= 1
                    old_end += old_line
                    new_end += new_line
                    line = next(lineiter)

                    while old_line < old_end or new_line < new_end:
                        if line:
                            command, line = line[0], line[1:]
                        else:
                            command = ' '
                        affects_old = affects_new = False

                        if command == '+':
                            affects_new = True
                            action = 'add'
                            files[-1]['additions'] += 1
                        elif command == '-':
                            affects_old = True
                            action = 'del'
                            files[-1]['deletions'] += 1
                        else:
                            affects_old = affects_new = True
                            action = 'unmod'

                        old_line += affects_old
                        new_line += affects_new
                        lines.append({
                            'old_lineno':   affects_old and old_line or u'',
                            'new_lineno':   affects_new and new_line or u'',
                            'action':       action,
                            'line':         line,
                            'no_newline':   False,
                        })

                        # Skip "no newline at end of file" markers
                        line = next(lineiter)
                        if line == r"\ No newline at end of file":
                            lines[-1]['no_newline'] = True
                            line = next(lineiter)

        except StopIteration:
            pass

        # highlight inline changes
        for file in files:
            if file['is_header']:
                continue
            for chunk in file['chunks']:
                lineiter = iter(chunk)
                try:
                    while True:
                        line = next(lineiter)
                        if line['action'] != 'unmod':
                            nextline = next(lineiter)
                            if nextline['action'] == 'unmod' or \
                               nextline['action'] == line['action']:
                                continue
                            self._highlight_line(line, nextline)
                except StopIteration:
                    pass

        return files
