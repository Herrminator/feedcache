from .common import *

class VerifyException(Exception):
  def __init__(self, msg, cause=None, parsed=None, code=ERR_FEED_VERIFICATION, *args, **kwargs):
    super(VerifyException, self).__init__(code, msg, cause, parsed, *args, *kwargs)
  @property
  def code(self): return self.args[0]
  @property
  def msg(self): return self.args[1]
  @property
  def cause(self): return self.args[2] # pragma: nocover # unused for now
  @property
  def parsed(self): return self.args[3]

def verify_feed(feed, data, cfg, logger=LOGGER):
  try: import feedparser
  except ImportError:
    LOGGER.warning("feedparser module is not installed")
    LOGGER.warning("Feed verification skipped for '{0}'.".format(feed.url))
    return

  error, info = None, None
  try:
    f = feedparser.parse(data)
    if f.bozo != 0:
      exc = f.get("bozo_exception", RuntimeError("unknown feedparser error"))
      del f["entries"]
      error = VerifyException("feed verification: '{0}'".format(exc),
                              cause=exc, parsed=f)
      raise error
  except VerifyException:
    info = sys.exc_info()
  except Exception as exc:
    info  = sys.exc_info()
    error = VerifyException("feed verification: '{0}'".format(exc), cause=exc)

  if error is not None:
    log_error(logger, feed, error, info)
    raise error

