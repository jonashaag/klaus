import sys
import re
import subprocess
import shutil
import klaus_cli

try:
    from unittest import mock
except ImportError:
    import mock
from klaus.utils import force_unicode


def test_covers_all_cli_options():
    if not shutil.which("man"):
        return

    manpage = force_unicode(subprocess.check_output(["man", "./klaus.1"]))

    def assert_in_manpage(s):
        clean = lambda x: re.sub("(.\\x08)|\\s", "", x)
        assert clean(s) in clean(manpage), "%r not found in manpage" % s

    mock_parser = mock.Mock()
    with mock.patch("argparse.ArgumentParser") as mock_cls:
        mock_cls.return_value = mock_parser
        klaus_cli.make_parser()

    for args, kwargs in mock_parser.add_argument.call_args_list:
        if kwargs.get("metavar") == "DIR":
            continue
        for string in args:
            assert_in_manpage(string)
        if "help" in kwargs:
            assert_in_manpage(kwargs["help"])
        if "choices" in kwargs:
            for choice in kwargs["choices"]:
                assert_in_manpage(choice)
