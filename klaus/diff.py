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

    def _extract_rev(self, line1, line2):
        def _extract(line):
            parts = line.split(None, 1)
            if parts[0].startswith(('a/', 'b/')):
                parts[0] = parts[0][2:]
            return parts[0], (len(parts) == 2 and parts[1] or None)
        try:
            if line1.startswith('--- ') and line2.startswith('+++ '):
                return _extract(line1[4:]), _extract(line2[4:])
        except (ValueError, IndexError):
            pass
        return (None, None), (None, None)

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
            line = lineiter.next()
            while 1:
                # continue until we found the old file
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = lineiter.next()
                    continue

                if header and all(x.strip() for x in header):
                    if want_header:
                        files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = False
                chunks = []
                old, new = self._extract_rev(line, lineiter.next())
                adds, dels = 0, 0
                files.append({
                    'is_header':        False,
                    'old_filename':     old[0],
                    'old_revision':     old[1],
                    'new_filename':     new[0],
                    'new_revision':     new[1],
                    'additions':        adds,
                    'deletions':        dels,
                    'chunks':           chunks
                })

                line = lineiter.next()
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
                    line = lineiter.next()

                    while old_line < old_end or new_line < new_end:
                        if line:
                            command, line = line[0], line[1:]
                        else:
                            command = ' '
                        affects_old = affects_new = False

                        if command == '+':
                            affects_new = True
                            action = 'add'
                            adds += 1
                        elif command == '-':
                            affects_old = True
                            action = 'del'
                            dels += 1
                        else:
                            affects_old = affects_new = True
                            action = 'unmod'

                        old_line += affects_old
                        new_line += affects_new
                        lines.append({
                            'old_lineno':   affects_old and old_line or u'',
                            'new_lineno':   affects_new and new_line or u'',
                            'action':       action,
                            'line':         line
                        })
                        # Make sure to store the stats before a
                        # StopIteration is raised
                        files[-1]['additions'] = adds
                        files[-1]['deletions'] = dels
                        line = lineiter.next()

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
                        line = lineiter.next()
                        if line['action'] != 'unmod':
                            nextline = lineiter.next()
                            if nextline['action'] == 'unmod' or \
                               nextline['action'] == line['action']:
                                continue
                            self._highlight_line(line, nextline)
                except StopIteration:
                    pass

        return files
