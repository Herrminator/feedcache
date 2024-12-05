import os, io, time, copy
from contextlib import redirect_stdout
from datetime   import datetime, timedelta
from typing import Callable
from .  import (
    TestBase, TEST_ARGS, TEST_ARGS_QUIET, TEST_FEEDS, TEST_STATE, TEST_TMP, TEST_CURL,
    unittest, patch, MagicMock,
    data, json, setUpModule, tearDownModule, redirected,
    CURL_INSTALLED, IS_WINDOWS
)
from freezegun     import freeze_time, config as freezegun_config
from freezegun.api import FrozenDateTimeFactory

from .. import feedcache, common

# I hope, this won't hurt ;) But most of our code runs in threads
# TODO: REMOVEME: Maybe, once we refactored the code to asyncio?
fg_ignore = [ i for i in freezegun_config.DEFAULT_IGNORE_LIST if i != "threading" ]
freezegun_config.configure(default_ignore_list=fg_ignore)

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
    @freeze_time(timedelta(minutes=-15), as_kwarg="frozen") # otherwise, it's UTC
    def test_unchanged(self, stdout: io.StringIO, stderr: io.StringIO, frozen: FrozenDateTimeFactory):
        """ Unchanged feeds are not updated """
        self.set_config(data.EMPTY_FEED_WITH_FORCE)

        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sunchanged:\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)
        # avoid not "downloading" local file
        frozen.tick(timedelta(minutes=15)); now = time.time()
        for f in self.data.feeds: os.utime(f._data.file, (now, now))

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
    def test_not_downloaded(self, stdout: io.StringIO, stderr: io.StringIO):
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
    def test_etag_disappeared(self, stdout: io.StringIO, stderr: io.StringIO):
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
    @freeze_time(as_kwarg="frozen")
    def test_interval(self, stdout: io.StringIO, stderr: io.StringIO, frozen: FrozenDateTimeFactory):
        """ Feeds are skipped within their interval """
        self.set_config(data.EMPTY_FEED_WITH_INTERVAL)
        interval = self.data.feeds[0].interval * 60.0

        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc,
                assert_overall=[
                    lambda: self.assertRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                    lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                ])
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        frozen.tick(interval - 2 * common.EPS)

        with self.subTest("within interval"):
            # is skipped during interval...
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc,
                    assert_overall=[
                        lambda: self.assertNotRegex(stderr.getvalue(), r"\sdownloaded:\s"),
                        lambda: self.assertRegex(stderr.getvalue(), r"\sSkipping\s"),
                    ],
                    assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        with self.subTest("with force"):
            # ...unless the `--force` is used. But then the mighty ETag prevents download
            rc = feedcache.main(TEST_ARGS + ["--force"])
            self.assertSimpleResult(rc,
                    assert_overall=[
                        lambda: self.assertRegex(stderr.getvalue(), r"\snot downloaded:\s"),
                        lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                    ],
                    assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))

        frozen.tick(interval - common.EPS + 1)

        with self.subTest("interval expired"):
            # ...or the interval. But still, the mighty ETag prevents download
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc,
                    assert_overall=[
                        lambda: self.assertRegex(stderr.getvalue(), r"\snot downloaded:\s"),
                        lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"),
                    ],
                    assert_feed=lambda name, _state: self.assertFalse((TEST_TMP / f"{name}.previous").exists()))


    @redirected(stderr=True)
    @freeze_time(as_kwarg="frozen")
    @patch("requests.Session", name="mock_session")
    def test_skip_and_retry_failed(self, mock_session, stdout: io.StringIO, stderr: io.StringIO, frozen: FrozenDateTimeFactory):
        """ Failed feeds are skipped within their interval """
        mock_session.side_effect = InterruptedError(42)
        self.set_config(data.EMPTY_FEED_WITH_INTERVAL)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sInterruptedError:\s"),
                assert_feed=lambda _name, state: self.assertEqual(common.ERR_UNKNOWN_EXCEPTION, state["rc"]))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        with self.subTest("skipping failed"):
            # is skipped during interval...
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                    assert_overall=lambda: self.assertRegex(stderr.getvalue(), r"\sSkipping\s"))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        with self.subTest("retry flag set"):
            # ...unless retry is set
            cfg = copy.deepcopy(data.EMPTY_FEED_WITH_INTERVAL)
            for f in cfg["feeds"]: f["retry"] = True

            self.set_config(cfg)
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                    assert_overall=lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

        with self.subTest("interval expired"):
            # ...or the interval expired
            frozen.tick(self.data.feeds[0].interval * 60.0)

            self.set_config(data.EMPTY_FEED_WITH_INTERVAL)
            rc = feedcache.main(TEST_ARGS)
            self.assertSimpleResult(rc, files_expected=0, feed_rc_expected=common.ERR_UNKNOWN_EXCEPTION,
                    assert_overall=lambda: self.assertNotRegex(stderr.getvalue(), r"\sSkipping\s"))
        stderr.truncate(0); stderr.seek(0, io.SEEK_SET)

    @redirected(stderr=True)
    def test_modified(self, stdout: io.StringIO, stderr: io.StringIO):
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
    def test_modified_with_ignore(self, stdout: io.StringIO, stderr: io.StringIO):
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
    def test_dry_run(self, stdout: io.StringIO, stderr: io.StringIO):
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
    def test_excplicit(self, stdout: io.StringIO, stderr: io.StringIO):
        """ curl downloader is configured in config file """
        self.set_config(data.EMPTY_FEED_WITH_CURL)
        rc = feedcache.main(TEST_ARGS)
        self.assertSimpleResult(rc)

@patch.object(feedcache, "download", name="mock_download")
class TestParallel(TestBase):
    NUM_FEEDS       = 10
    NUM_WORKERS     = 5
    DELAY           = 0.1
    SAMPLE          = data.MISSING_FEED_FILE["feeds"][0]
    EXPECTED_FACTOR = float(NUM_WORKERS) / float(NUM_FEEDS) * 1.333 # probably even less

    feedcache_download: Callable[..., None] = feedcache.download

    def setUp(self):
        super().setUp()

        config = { "feeds": [] }
        for i in range(self.NUM_FEEDS):
            feed = copy.deepcopy(self.SAMPLE)
            feed["name"] = f"parallel.{i:02d}.atom"
            config["feeds"] += [ feed ]
        self.set_config(config)

    def init_mock(self, mock_download: MagicMock):
        mock_download.side_effect = self._download

    def _download(self, *args, **kwargs):
        time.sleep(self.DELAY)
        return TestParallel.feedcache_download(*args, **kwargs)

    def run_threads(self, threads, min_time, max_time, mock_download):
        start = time.monotonic()
        self.init_mock(mock_download)
        rc = feedcache.main(TEST_ARGS + [f"--parallel={threads}"])
        self.assertSimpleResult(rc, 404, files_expected=0) # we don't care about the result here...
        stop = time.monotonic()
        self.assertGreaterEqual(stop - start, min_time)
        self.assertLessEqual(stop - start, max_time)

    def test_single_thread(self, mock_download: MagicMock):
        """ single thread: time > sum(times) """
        self.run_threads(1, self.NUM_FEEDS * self.DELAY, self.NUM_FEEDS * self.DELAY * 2.0, mock_download)

    def test_multi_thread(self, mock_download: MagicMock):
        """ multiple threads: time <= sum(times) * 0.666 """
        self.run_threads(self.NUM_WORKERS, 0.0, self.NUM_FEEDS * self.DELAY * self.EXPECTED_FACTOR, mock_download)
