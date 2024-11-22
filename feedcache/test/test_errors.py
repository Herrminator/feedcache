import sys, io, re, copy, builtins, json
from contextlib import redirect_stderr
from .  import (
    TestBase, TEST_ARGS, TEST_FEEDS, TEST_STATE, TEST_CURL, CURL_INSTALLED, IS_WINDOWS, IS_OFFLINE,
    data, patch, mock_import_error, redirected,
    unittest, patch, MagicMock
)
from .. import feedcache, constants

class TestErrors(TestBase):
    def test_missing_config(self):
        """ Non-existing config file specified """
        with self.assertRaises(FileNotFoundError):
            feedcache.main(["--config", "./i-hope-it-s-not-here.json"])

    def test_requested_feeds_not_configured(self):
        """ Requested feeds not found """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS + ["not.a.feed", "neither.is.this"])
        self.assertSimpleResult(rc, files_expected=0, states_expected=0)

    def test_feed_disabled(self):
        """ Requested feeds not found """
        cfg = copy.deepcopy(data.EMPTY_FEED)
        for f in cfg["feeds"]: f["disabled"] = True
        self.set_config(cfg)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, files_expected=0, states_expected=0)

    def test_requests_library_missing(self):
        """ Missing requests library doesn't cause error """
        import importlib
        requests_dl = feedcache.requests_dl
        self.assertIsNot(None, requests_dl)
        try:
            with patch.object(builtins, "__import__", new=mock_import_error(["requests_dl"])):
                importlib.reload(feedcache)
                from .. import feedcache as fc
                self.assertIs(None, fc.requests_dl)
        finally:
            feedcache.requests_dl = requests_dl

    @redirected(stderr=True)
    def test_feedparser_missing(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ feed verification failure """
        with patch.object(builtins, "__import__", new=mock_import_error(["feedparser"])):
            self.set_config(data.INVALID_FEED)
            rc = feedcache.main(TEST_ARGS + ["--verify"])
            self.assertSimpleResult(rc, 0,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), "Feed verification skipped"))

    def test_missing_feed_file(self):
        """ requests adapter works with missing local files """
        self.set_config(data.MISSING_FEED_FILE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, 404, files_expected=0)

    def test_verify_invalid_feed(self):
        """ feed verification failure """
        self.set_config(data.INVALID_FEED)
        rc = feedcache.main(TEST_ARGS + ["--verify"])
        self.assertSimpleResult(rc, constants.ERR_FEED_VERIFICATION, files_expected=0)

    @redirected(stderr=True)
    @patch("feedparser.parse", name="mock_parser")
    def test_verify_exception(self, mock_parser: MagicMock, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ feed verification exception """
        mock_parser.side_effect = InterruptedError(42)
        self.set_config(data.INVALID_FEED)
        rc = feedcache.main(TEST_ARGS + ["--verify"])
        self.assertSimpleResult(rc, constants.ERR_FEED_VERIFICATION, files_expected=0)

    @redirected(stderr=True)
    def test_invalid_downloader(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ invalid downloader module """
        self.set_config(data.EMPTY_FEED_WITH_NATIVE_DL)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, constants.ERR_UNKNOWN_EXCEPTION, files_expected=0, states_expected=0,
            assert_overall=lambda: self.assertRegex(stderr.getvalue(), "(?s)Continuing after exception.*NotImplementedError"))

    @unittest.skipIf(IS_OFFLINE, "FEEDCACHE_TEST_OFFLINE=true")
    def test_invalid_server(self): # pragma: offline-nocover
        """ invalid server address """
        self.set_config(data.INVALID_SERVER)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, constants.ERR_CONNECTION_FAILED, files_expected=0)

    @redirected(stderr=True)
    @patch("requests.Session", name="mock_session")
    def test_unexpected_request_error(self, mock_session: MagicMock, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ unknown error from requests """
        mock_session.side_effect = InterruptedError(42)
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, constants.ERR_UNKNOWN_EXCEPTION, files_expected=0,
            assert_overall=lambda: self.assertRegex(stderr.getvalue(), "InterruptedError"))


@unittest.skipIf(not CURL_INSTALLED, f"'{TEST_CURL}' was not found in {'$PATH' if not IS_WINDOWS else '%PATH%'}")
@patch.object(feedcache, "requests_dl", new=None)
class TestCurlErrors(TestBase):
    @redirected(stderr=True)
    def test_missing_feed_file(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ curl works with missing local files """
        self.set_config(data.MISSING_FEED_FILE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, 37, files_expected=0, # see curl manual, EXIT CODES.
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), "(FILE could\s?n.t read|unknown error 37)"))

    @unittest.skipIf(IS_OFFLINE, "FEEDCACHE_TEST_OFFLINE=true")
    @redirected(stderr=True)
    def test_invalid_server(self, stdout: io.StringIO=None, stderr: io.StringIO=None): # pragma: offline-nocover
        """ invalid server address """
        self.set_config(data.INVALID_SERVER)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, 7, files_expected=0, # see curl manual, EXIT CODES.
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), "(Failed to connect to host|unknown error 7)"))

    @redirected(stderr=True)
    def test_no_downloader(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ no downloader module """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS + ["--curl="])
        self.assertSimpleResult(rc, constants.ERR_UNKNOWN_EXCEPTION, files_expected=0, states_expected=0,
            assert_overall=lambda: self.assertRegex(stderr.getvalue(), "(?s)Continuing after exception.*NotImplementedError"))


class TestCoverage(TestBase):
    """ Not really errors ;) """
    def test_unused(self):
        """ functions that should be used
        """
        self.set_config(data.EMPTY_FEED)
        self.data.feedlist, self.data.disabled = None, False

        with self.subTest("lets get 100%"):
            feeds : list[common.Feed] = feedcache.load_feeds(self.data)
            self.assertRegex(str(feeds[0]), f"^Feed<.*{re.escape(feeds[0].name)}.*>$")
            self.assertEqual(feeds[0].url, feeds[0]._json()["url"])
            with self.assertRaises(KeyError): # seems a little incomplete
                self.assertEqual(feeds[0].interval, feeds[0]._json()["interval"])

