import sys
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from klaus import utils


class ForceUnicodeTests(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(u"foo", utils.force_unicode(b"foo"))

    def test_utf8(self):
        self.assertEqual(u"f\xce", utils.force_unicode(b"f\xc3\x8e"))

    def test_invalid(self):
        if sys.platform.startswith("win"):
            return
        with mock.patch.object(utils, "chardet", None):
            self.assertEqual('fÎ', utils.force_unicode(b"f\xce"))


class TarballBasenameTests(unittest.TestCase):
    def test_examples(self):
        examples = [
            ("v0.1", "klaus-0.1"),
            ("klaus-0.1", "klaus-0.1"),
            ("0.1", "klaus-0.1"),
            (
                "b3e70e08344ca3f83cc7033ecdbefa90443d7d2e",
                "klaus@b3e70e08344ca3f83cc7033ecdbefa90443d7d2e",
            ),
            ("vanilla", "klaus-vanilla"),
        ]
        for (rev, basename) in examples:
            self.assertEqual(utils.tarball_basename("klaus", rev), basename)
