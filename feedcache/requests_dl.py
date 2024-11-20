import requests, time

from .common   import *
from .constants import *

def log_response(log, feed, rsp):
  req = rsp.request
  log.info("> GET {0}".format(feed.url))
  if req:
    for h in req.headers: log.info("> {0}: {1}".format(h, req.headers[h]))

  log.info("\n< {0} {1}".format(rsp.status_code, rsp.reason))
  for h in rsp.headers: log.info("< {0}: {1}".format(h, rsp.headers[h]))
  log.info("<\n< {0}\n< ...".format(rsp.text[:LOG_HTTP_LEN].replace("\n","\n< ")))

#-----------------------------------------------------------------------------
# Download temporary feed file using Python requests
#-----------------------------------------------------------------------------
def tmp_downloader(feed, cfg, state, log=LOGGER):
  import http.cookiejar

  def mod_time(fname):
    return time.strftime("%a, %d %B %Y %H:%M:%S GMT",
             time.gmtime(os.stat(fname).st_mtime))

  fstate = ensure_state(state, feed)

  headers = {}
  if feed.useragent:           headers["User-Agent"] = feed.useragent
  if os.path.isfile(feed.out): headers["If-Modified-Since"] = mod_time(feed.out)
  if fstate.etag:              headers["If-None-Match"] = fstate.etag

  timeout = feed.timeout if feed.timeout else None
  cookies = http.cookiejar.MozillaCookieJar() if feed.cookies else None

  if cookies is not None and os.path.isfile(feed.cookies): cookies.load(feed.cookies)

  rc, errtext, data = 0, "unkown error", None

  try:
    sess = requests.Session()
    sess.cookies = cookies

    rsp = sess.get(feed.url, headers=headers, timeout=timeout, proxies=feed.proxies)

    if rsp.ok and rsp.text:
      data = rsp.text
      with open(feed.tmp, "w", encoding="utf-8") as tmp: tmp.write(rsp.text)

    rsp.raise_for_status()
    log_response(log, feed, rsp)

    if sess.cookies is not None: sess.cookies.save(feed.cookies)

    if   rsp.headers.get("ETag"): fstate.etag = rsp.headers["ETag"]
    elif fstate.etag: del fstate.etag

  except requests.HTTPError as exc:
    rc = exc.response.status_code
    errtext = "{0}".format(str(exc))
    log_response(log, feed, exc.response)
    log_error(log, feed, exc)

  except requests.ConnectionError as exc: # TODO: get OS error code
    rc = getattr(exc, "errno", getattr(exc, "code", ERR_CONNECTION_FAILED))
    rc = rc if rc is not None else ERR_CONNECTION_FAILED
    errtext = "{0}: {1}".format(str(exc.__class__.__name__), str(exc))
    log_error(log, feed, exc)

  except Exception as exc:
    rc = getattr(exc, "errno", getattr(exc, "code", ERR_UNKNOWN_EXCEPTION))
    rc = rc if rc is not None else ERR_UNKNOWN_EXCEPTION
    errtext = "{0}: {1}".format(str(exc.__class__.__name__), str(exc))
    log_error(log, feed, exc)

  return rc, "{0}: {1}".format(errtext, rc), data

