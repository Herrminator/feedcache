import sys, re, logging
from .constants import * # @UnusedWildImport
from typing import Any, Callable, List, Optional, Tuple

LOGGER = logging.getLogger("feedcache")

class Feed(object):
    def __init__(self, name, url, interval=ALWAYS,
                             outdir=None, tmpdir=None,
                             retry=False, useragent=UA, timeout=None, ignore=None, verify=False, proxies=None):
        self.name = name
        self.url  = url
        self.out  = os.path.normpath(os.path.join(outdir if outdir is not None else OUT, name))
        self.tmp  = os.path.normpath(os.path.join(tmpdir if tmpdir is not None else TMP, name))
        self.log  = self.tmp + '.log'
        self.err  = self.tmp + '.err'
        self.cookies  = self.tmp + '.cookies'
        self.interval = interval # minutes
        self.retry    = retry
        self.useragent= useragent
        self.timeout  = timeout
        self.ignore   = re.compile(ignore) if ignore else None
        self.verify   = verify
        self.proxies  = proxies

    def _json(self): return { "name": self.name, "url": self.url }

    def __str__(self):
        return "Feed<{0.url},{0.out}>".format(self)

class AttrDict(dict):
    get: Callable[..., Any]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
    def __getattr__(self, name: str) -> Any: return self.get(name)

class Config(AttrDict):
    feedlist: Optional[List[Feed]]
    disabled: bool
class State(AttrDict):
    last: str
    etag: str

DownloaderResult = Tuple[int, str, Optional[str]]
DownloaderFunc   = Callable[[Feed, Config, State, Optional[logging.Logger]], DownloaderResult]

def ensure_state(state, feed):
    fs = state.get(feed.name)
    if fs is None: fs = State(); state[feed.name] = fs
    return fs

#-----------------------------------------------------------------------------
def info(msg, *args, **kwargs):
    logger = kwargs.pop("logger", LOGGER)
    logger.info(msg.format(*args), **kwargs)

def debug(msg, *args, **kwargs):
    logger = kwargs.pop("logger", LOGGER)
    logger.debug(msg.format(*args), **kwargs)

def error(msg, *args, **kwargs):
    logger = kwargs.pop("logger", LOGGER)
    logger.error(msg.format(*args), **kwargs)

def log_error(log, feed, exc, info=None):
    # import traceback
    if info is None: info = sys.exc_info()
    log.error(str(exc), exc_info=info) # , traceback.print_exc()
