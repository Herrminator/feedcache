from .common import *
from typing import Optional, Tuple

#-----------------------------------------------------------------------------
# Download using 'curl' executable
#-----------------------------------------------------------------------------
CURL_MAN = None

def curl_error(rc, cfg):
    global CURL_MAN
    if CURL_MAN is None: # pragma: nobranch
        import subprocess
        result = subprocess.run([cfg.curl, "--manual"], stdout=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:  CURL_MAN = result.stdout
    import re
    if CURL_MAN is not None:
        m = re.search(r'EXIT CODES.*?^\s+{}\s+(.*?\n$)'.format(rc), CURL_MAN, re.M|re.S)
    else: # pragma: nocover # (always at least "")
        m = None
    if m: # pragma: nocover # either curl understands `--manual`...
        return m.group(1)
    else: # pragma: nocover # ... or not.
        return "unknown error {0}".format(rc)

def tmp_downloader(feed: Feed, cfg: Config, state: State, logger: Optional[logging.Logger]=LOGGER)  -> DownloaderResult:
    import subprocess
    newer   = [ "--time-cond", feed.out ]         if os.path.isfile(feed.out) else []
    agent   = [ "--user-agent", feed.useragent ]  if feed.useragent else []
    timeout = [ "--max-time", str(feed.timeout) ] if feed.timeout   else []

    cmd = [ cfg.curl, feed.url, "-o", feed.tmp ] + newer + [ "--fail",
                    "-c", feed.cookies] + agent + timeout + [ "--stderr", feed.log,
                    "--silent", "--verbose" ]
    rc = subprocess.run(cmd).returncode

    return rc, curl_error(rc, cfg) if rc != 0 else "no error", None

