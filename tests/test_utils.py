import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from klaus import utils


class ForceUnicodeTests(unittest.TestCase):

    def test_ascii(self):
        self.assertEqual(u'foo', utils.force_unicode(b'foo'))

    def test_utf8(self):
        self.assertEqual(u'f\xce', utils.force_unicode(b'f\xc3\x8e'))

    def test_invalid(self):
        with mock.patch.object(utils, 'chardet', None):
            self.assertRaises(
                UnicodeDecodeError, utils.force_unicode, b'f\xce')
