import os

__version__ = "0.1.6"

NUM_THREADS = 8

OUT    = "feedcache"
TMP    = "tmp"
UA     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0"
HOME   = os.path.expanduser("~")
ALWAYS = 0.0
EPS    = 60.0 # seconds

CFG_DEFAULTS = { "outdir": OUT,   "tmpdir": TMP,   "useragent": UA,
                 "timeout": None, "verify": False, "parallel": NUM_THREADS}

TS_FMT       = "%Y-%m-%d %H:%M:%S"

ERR_CONNECTION_FAILED = 8
ERR_UNKNOWN_EXCEPTION = 9
ERR_FEED_VERIFICATION = 10

LOGDATE = "%H:%M:%S"
LOGFMT  = "{asctime} : {levelname:5s} : {message}"
LOGFEED = "{message}"

LOG_HTTP_LEN = 2048
