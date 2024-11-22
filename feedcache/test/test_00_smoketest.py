import sys, io, re
from contextlib import redirect_stdout
from .  import TestBase
from .. import feedcache
from ..constants import __version__

class SmokeTest(TestBase):
    def test_00_smoketest(self):
        """ Check if all modules can be imported properly """
        mock_stdout = io.StringIO()
        with self.assertRaises(SystemExit) as thrown, redirect_stdout(mock_stdout):
            feedcache.main(["--help"])
        self.assertEqual(thrown.exception.code, 0)
        self.assertRegex(mock_stdout.getvalue(), r".*\sfeedlist\s.*")

    def test_01_version(self):
        """ Check if the version is plausible """
        mock_stdout = io.StringIO()
        with self.assertRaises(SystemExit) as thrown, redirect_stdout(mock_stdout):
            feedcache.main(["--version"])
        self.assertEqual(thrown.exception.code, 0)
        self.assertRegex(mock_stdout.getvalue(), rf".*feedcache {re.escape(__version__)}.*requests\s.*")
