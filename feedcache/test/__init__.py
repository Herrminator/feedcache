import sys, io, os, unittest, builtins, json, shutil, copy, functools, logging, platform
from pathlib import Path
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout, redirect_stderr
from typing import Iterable
from .. import feedcache, common

TEST_OUTPUT     = Path(__file__).parent.resolve() / 'data' / 'output'
TEST_CONFIG     = TEST_OUTPUT / 'feedcache.json'
TEST_FEEDS      = TEST_OUTPUT / 'feeds'
TEST_TMP        = TEST_OUTPUT / 'tmp'
TEST_STATE      = TEST_TMP / 'feedcache.state.json'
TEST_CURL       = os.getenv("FEEDCACHE_TEST_CURL", "curl")
TEST_ARGS_QUIET = [ f"--config={str(TEST_CONFIG)}", f"--outdir={TEST_FEEDS}", f"--tmpdir={TEST_TMP}",
                     "--parallel=1", f"--curl={TEST_CURL}" ]
TEST_ARGS       = TEST_ARGS_QUIET + [ "-vvv" ]

CURL_INSTALLED = (shutil.which(TEST_CURL) is not None or Path(TEST_CURL).is_file())
IS_WINDOWS     = (platform.system() == "Windows")
IS_OFFLINE     = (os.environ.get("FEEDCACHE_TEST_OFFLINE") == "true")

_real_import = builtins.__import__

def mock_import_error(failing=[]):
    # https://stackoverflow.com/a/2481588/10545609
    def __mock_import__(name, globals, locals, from_list, level, *args, **kwargs):
        # TODO: FIXME: Handle the path properly
        if name in failing or (from_list is not None and (set(from_list) & set(failing))):
            raise ImportError
        return _real_import(name, globals, locals, from_list, level, *args, **kwargs)
    return __mock_import__

class TestBase(unittest.TestCase):
    def setUp(self):
        self.data = common.Config()
        self.assertFalse(TEST_OUTPUT.exists(), f"Please make sure '{TEST_OUTPUT}' doesn't exist")
        TEST_TMP.mkdir(parents=True)
        TEST_FEEDS.mkdir(parents=True)
        self.addCleanup(self.clean_up)
        self.save_logging()

    def set_config(self, data: dict):
        data = copy.deepcopy(data)
        self.data = json.loads(json.dumps(data, default=str), object_pairs_hook=common.Config)
        for feed in data.get("feeds", []):
            rss = feed.pop("_data", {})
            if rss.get("file"):
                with open(rss["file"], "w") as f: f.write(rss.get("content", ""))
        with open(TEST_CONFIG, "w") as f:
            json.dump(data, f)

    def assertSimpleResult(self, rc,
                           feed_rc_expected=0, files_expected=None, states_expected=None, rc_expected=0,
                           assert_overall : list[callable]=[], assert_feed=[], state_file_expected=True):
        if files_expected is None: files_expected = len(self.data.get("feeds", []))
        if states_expected is None: states_expected = len(self.data.get("feeds", []))
        if assert_overall and not isinstance(assert_overall, Iterable): assert_overall = [ assert_overall ]
        if assert_feed    and not isinstance(assert_feed,    Iterable): assert_feed    = [ assert_feed ]
        self.assertEqual(rc_expected, rc)
        self.assertEqual(files_expected, len(list(TEST_FEEDS.glob("*"))))
        self.assertTrue(TEST_STATE.is_file() or not state_file_expected)
        self.assertTrue(not TEST_STATE.is_file() or state_file_expected)
        for assrt in assert_overall:
            assrt()
        if not state_file_expected:
            return
        with TEST_STATE.open() as f:
            state : dict = json.load(f)
            self.assertEqual(states_expected, len(state))
            for name, feed in state.items():
                self.assertEqual(feed_rc_expected, feed["rc"])
                for assrt in assert_feed:
                    assrt(name, feed)

    def save_logging(self):
        # see self.reset_logging()
        self.logging = {}
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        loggers.append(logging.getLogger())
        logger: logging.Logger
        for logger in loggers:
            self.logging[logger.name] = {
                "level": logger.level,
                "handlers": logger.handlers[:],
                "propagate": logger.propagate,
            }

    def reset_logging(self):
        # https://til.tafkas.net/posts/-resetting-python-logging-before-running-tests/
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        loggers.append(logging.getLogger())
        logger: logging.Logger
        for logger in loggers:
            restore = self.logging.get(logger.name, {})
            handlers = logger.handlers[:]
            for handler in handlers:
                logger.removeHandler(handler)
                handler.close()
            for handler in restore.get("handlers", []):
                logger.addHandler(handler)
            logger.setLevel(restore.get("level", logging.NOTSET))

    def clean_up(self):
        shutil.rmtree(TEST_OUTPUT)
        self.reset_logging()

def redirected(test_func=None, *, stdout=None, stderr=None):
    # https://stackoverflow.com/a/24617244/10545609 et. al.
    def decorator(f, stdout=stdout, stderr=stderr, *args, **kwargs):
        @functools.wraps(f)
        def decorated(self, stdout=stdout, stderr=stderr, *args, **kwargs):
            rstdout, rstderr = stdout, stderr
            if rstdout is True: rstdout=io.StringIO()
            if rstderr is True: rstderr=io.StringIO()
            if rstdout is None: rstdout=sys.stdout
            if rstderr is None: rstderr=sys.stderr

            with redirect_stdout(rstdout), redirect_stderr(rstderr):
                rc = f(self, stdout=rstdout if stdout else None, stderr=rstderr if stderr else None, *args, *kwargs)
            return rc
        return decorated
    if test_func: # pragma: nocover
        return decorator(test_func)
    return decorator

def setUpModule():
    pass

def tearDownModule():
    pass
