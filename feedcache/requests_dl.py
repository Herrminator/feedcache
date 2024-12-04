import requests, re, time

from .common   import *
from .constants import *

FILE_ETAG_PATTERN = re.compile(r'W/"([\d.]+)"')

def log_response(log, feed, rsp):
    req = rsp.request
    log.info("> GET {0}".format(feed.url))
    if req: # pragma: nobranch
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

    rc, errtext, data = 0, "unknown error", None

    try:
        sess = requests.Session()
        sess.cookies = cookies

        if feed.url.startswith("file://"): # pragma: offline-nobranch # GitHub CI doesn't have online access
            sess.mount("file://", LocalFileAdapter())

        rsp = sess.get(feed.url, headers=headers, timeout=timeout, proxies=feed.proxies)

        if rsp.ok and rsp.text:
            data = rsp.text
            with open(feed.tmp, "w", encoding="utf-8", newline="\n") as tmp: tmp.write(rsp.text)

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

    except requests.ConnectionError as exc: # pragma: offline-nocover
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

from pathlib import Path
import io

# https://stackoverflow.com/a/22989322/10545609
class LocalFileAdapter(requests.adapters.HTTPAdapter):
    def build_response_from_file(self, request: requests.Request):
            file_path : Path = Path.from_uri(request.url)
            if file_path.exists():
                etag = request.headers.get("If-None-Match")
                if etag is not None:
                    m = FILE_ETAG_PATTERN.match(etag)
                    if m: etag = float(m.group(1))
                if etag is None or file_path.stat().st_mtime > etag:
                    with open(file_path, 'rb') as file:
                            buff = bytearray(os.path.getsize(file_path))
                            file.readinto(buff)
                else:
                    buff = bytearray(b"")
                resp = LocalFileAdapter.Resp(buff, headers={ "ETag": f'W/"{file_path.stat().st_mtime}"'})
                r = self.build_response(request, resp)
            else:
                r = self.build_response(request, LocalFileAdapter.Resp(b"Not found!", 404))
            return r

    def send(self, request, stream=False, timeout=None,
                     verify=True, cert=None, proxies=None):

            return self.build_response_from_file(request)

    # https://github.com/ambv/requests-testadapter/blob/master/src/requests_testadapter.py
    class Resp(io.BytesIO):
        def __init__(self, stream, status=200, headers=None):
                self.status = status
                self.headers = headers or {}
                self.reason = requests.status_codes._codes.get(
                        status, ['']
                )[0].upper().replace('_', ' ')
                io.BytesIO.__init__(self, stream)

        @property
        def _original_response(self): return self
        @property
        def msg(self): return self
        def read(self, chunk_size, **kwargs): return io.BytesIO.read(self, chunk_size)
        def info(self): return self # pragma: nobranch
        def get_all(self, name, default):
                result = self.headers.get(name)
                if not result: return default
                return [result] # pragma: nocover
        def getheaders(self, name): return self.get_all(name, []) # pragma: nobranch
        def release_conn(self): self.close() # pragma: nobranch

    try: # REMOVEME # Only in Python 3.13+ 
        from_uri = Path.from_uri
    except AttributeError: # pragma: py-gte-313-nocover
        # https://github.com/python/cpython/pull/107640/files
        @classmethod
        def from_uri(cls, uri):
                """Return a new path from the given 'file' URI."""
                if not uri.startswith('file:'): raise ValueError(f"URI does not start with 'file:': {uri!r}")
                path = uri[5:]
                if path[:3] == '///': path = path[2:]
                elif path[:12] == '//localhost/': path = path[11:]
                if path[:3] == '///' or (path[:1] == '/' and path[2:3] in ':|'): path = path[1:]
                if path[1:2] == '|': path = path[:1] + ':' + path[2:]
                from urllib.parse import unquote_to_bytes
                path = cls(os.fsdecode(unquote_to_bytes(path)))
                if not path.is_absolute(): raise ValueError(f"URI is not absolute: {uri!r}")
                return path
        Path.from_uri = from_uri
