import os, io, time, copy
from contextlib import redirect_stdout
from .  import (
    TestBase, TEST_ARGS, TEST_ARGS_QUIET, TEST_FEEDS, TEST_STATE, TEST_TMP, TEST_CURL,
    unittest, patch,
    data, json, setUpModule, tearDownModule, redirected,
    CURL_INSTALLED, IS_WINDOWS
)
from .. import feedcache, common

req_dl_send = feedcache.requests_dl.LocalFileAdapter.send
def send_without_etag(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
    rsp = req_dl_send(self, request, stream, timeout, verify, cert, proxies)
    rsp.headers.pop("ETag", None)
    return rsp

class TestFeedcache(TestBase):
    def test_empty_config(self):
        """ Empty config is ignored """
        self.set_config(data.EMPTY)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, files_expected=0)

    def test_empty_feed(self):
        """ Empty feeds are ok """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS_QUIET + ["--verify"])
        self.assertSimpleResult(rc)

    @redirected(stderr=True)
    def test_unchanged(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Unchanged feeds are not updated """
        self.set_config(data.EMPTY_FEED_WITH_FORCE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sunchanged:\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        time.sleep(0.1)
        for f in self.data.feeds:
            os.utime(f._data.file)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertRegex(stderr.getvalue(), r"\sunchanged:\s"),
                ],
                assert_feed=[
                    lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()),
                    lambda name, _state: self.assertTrue((TEST_TMP / f"{name}.unchanged").exists())
                ])

    @patch.object(feedcache.requests_dl.LocalFileAdapter, "send", new=send_without_etag)
    def test_unchanged_quiet(self):
        """ Unchanged feeds are not updated and not kept """
        self.set_config(data.EMPTY_FEED_WITH_FORCE)
        rc = feedcache.main(TEST_ARGS_QUIET)
        self.assertSimpleResult(rc)
        rc = feedcache.main(TEST_ARGS_QUIET)
        self.assertSimpleResult(rc,
                assert_feed=[
                    lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()),
                    lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.unchanged").exists()) # only in verbose mode
                ])

    @redirected(stderr=True)
    def test_not_downloaded(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Matching ETags are not downloaded """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\snot downloaded:\s"),
                assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))

    @redirected(stderr=True)
    def test_etag_disappeared(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ ETag ist removed from state file """

        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                assert_feed=lambda _name, state: self.assertIsNot(None, state.get("etag")))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        with patch.object(feedcache.requests_dl.LocalFileAdapter, "send", new=send_without_etag):
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc,
                    assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\snot downloaded:\s"),
                    assert_feed=[
                        lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()),
                        lambda _name, state: self.assertIs(None, state.get("etag"))
                    ])

    @redirected(stderr=True)
    def test_skip_current(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Feeds are skipped within their interval """
        self.set_config(data.EMPTY_FEED_WITH_INTERVAL)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        # is skipped during interval...
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertRegex(stderr.getvalue(), r"\sSkipping\s"),
                ],
                assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        # ...unless the `--force` is used. But then the mighty ETag prevents download
        rc = feedcache.main(TEST_ARGS + ["--force"])
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\snot downloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                ],
                assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))

    @redirected(stderr=True)
    def test_skip_and_retry_failed(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Failed feeds are skipped within their interval """
        with patch("requests.Session") as mock_session:
            mock_session.side_effect = InterruptedError(42)
            self.set_config(data.EMPTY_FEED_WITH_INTERVAL)
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                    assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sInterruptedError:\s"),
                    assert_feed=lambda _name, state: self.assertEqual(common.ERR_UNKNOWN_EXCEPTION, state["rc"]))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        # is skipped during interval...
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                assert_overall=[
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertRegex(stderr.getvalue(), r"\sSkipping\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        # ...unless retry is set
        cfg = copy.deepcopy(data.EMPTY_FEED_WITH_INTERVAL)
        for f in cfg["feeds"]: f["retry"] = True
        self.set_config(cfg)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r":\s+downloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                ],
                assert_feed=lambda _name, state: self.assertEqual(0, state["rc"]))

    @redirected(stderr=True)
    def test_modified(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Modified feeds are updated """
        self.set_config(data.EMPTY_FEED_WITH_FORCE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sunchanged:\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        time.sleep(0.1)
        self.set_config(data.EMPTY_FEED_WITH_FORCE_MOD)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sunchanged:\s"),
                ],
                assert_feed=lambda name, _state: self.assertTrue((TEST_TMP / f"{name}.previous").exists()))

    @redirected(stderr=True)
    def test_modified_with_ignore(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Modified feeds with ignored changes are not updated """
        self.set_config(data.EMPTY_FEED_WITH_FORCE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        time.sleep(0.1)
        self.set_config(data.EMPTY_FEED_WITH_FORCE_MOD_IGNORE)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\signored changes:\s"),
                assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))

    @redirected(stderr=True)
    def test_dry_run(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ Unchanged feeds are not updated """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS + ["--dry-run"])
        self.assertSimpleResult(rc, files_expected=0, states_expected=0, state_file_expected=False,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sDownloading\s"),
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdry-run:\s"),
                ])

@unittest.skipIf(not CURL_INSTALLED, f"'{TEST_CURL}' was not found in {'$PATH' if not IS_WINDOWS else '%PATH%'}")
class TestCurl(TestBase):
    @patch.object(feedcache, "requests_dl", new=None)
    def test_automatic(self):
        """ curl downloader is selected if requests not installed """
        self.set_config(data.EMPTY_FEED)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc)

    @redirected(stdout=True, stderr=True)
    def test_excplicit(self, stdout: io.StringIO=None, stderr: io.StringIO=None):
        """ curl downloader is configured in config file """
        self.set_config(data.EMPTY_FEED_WITH_CURL)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc)
