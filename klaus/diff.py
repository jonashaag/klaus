# -*- coding: utf-8 -*-
"""
    lodgeit.lib.diff
    ~~~~~~~~~~~~~~~~

    Render a nice diff between two things.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD
"""

from difflib import SequenceMatcher

def highlight_line(old_line, new_line):
    """Highlight inline changes in both lines."""
    old_line = old_line.rstrip(b'\n')
    new_line = new_line.rstrip(b'\n')
    start = 0
    limit = min(len(old_line), len(new_line))
    while start < limit and old_line[start] == new_line[start]:
        start += 1
    end = -1
    limit -= start
    while -end <= limit and old_line[end] == new_line[end]:
        end -= 1
    end += 1
    if start or end:
        def do(l, tag):
            last = end + len(l)
            return b''.join(
                [l[:start], b'<', tag, b'>', l[start:last], b'</', tag, b'>',
                 l[last:]])
        old_line = do(old_line, b'del')
        new_line = do(new_line, b'ins')
    return old_line, new_line


def render_diff(a, b, n=3):
    """Parse the diff an return data for the template."""
    actions = []
    chunks = []
    for group in SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        old_line, old_end, new_line, new_end = group[0][1], group[-1][2], group[0][3], group[-1][4]
        lines = []
        def add_line(old_lineno, new_lineno, action, line):
            actions.append(action)
            lines.append({
                'old_lineno': old_lineno,
                'new_lineno': new_lineno,
                'action': action,
                'line': line,
                'no_newline': not line.endswith(b'\n')
            })
        chunks.append(lines)
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for c, line in enumerate(a[i1:i2]):
                   add_line(i1+c, j1+c, 'unmod', line)
            elif tag == 'insert':
                for c, line in enumerate(b[j1:j2]):
                   add_line(None, j1+c, 'add', line)
            elif tag == 'delete':
                for c, line in enumerate(a[i1:i2]):
                   add_line(i1+c, None, 'del', line)
            elif tag == 'replace':
                # TODO: not sure if this is the best way to deal with replace
                # blocks, but it's consistent with the previous version.
                for c, line in enumerate(a[i1:i2-1]):
                   add_line(i1+c, None, 'del', line)
                old_line, new_line = highlight_line(a[i2-1], b[j1])
                add_line(i2-1, None, 'del', old_line)
                add_line(None, j1, 'add', new_line)
                for c, line in enumerate(b[j1+1:j2]):
                   add_line(None, j1+c+1, 'add', line)
            else:
                raise AssertionError('unknown tag %s' % tag)

    return actions.count('add'), actions.count('del'), chunks
