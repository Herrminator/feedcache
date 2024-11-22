#!/usr/bin/python3 -u
import sys, os, re, shutil, argparse, threading, queue, json, time, logging, contextlib
try:  from . import requests_dl
except ImportError: requests_dl = None
from . import (curl_dl, filediff)

from .common    import * # @UnusedWildImport
from .constants import * # @UnusedWildImport
from .constants import __version__

VERSION_REQUESTS = f", using requests {requests_dl.requests.__version__}" if requests_dl else ""
VERSION_STRING   = f"{__version__}{VERSION_REQUESTS}, Python {sys.version}"

#-----------------------------------------------------------------------------
def get_feed_logger(feed, cfg):
  lvl    = logging.DEBUG if cfg.verbose else logging.INFO
  logger = logging.getLogger(feed.name)
  hdlr   = logging.FileHandler(feed.log, mode="w")
  hdlr.setLevel(lvl)
  formatter = logging.Formatter(LOGFEED, style="{")
  formatter.default_time_format = LOGDATE # s. Python manual 16.6.4 (Formatter Objects)
  hdlr.setFormatter(formatter)
  logger.addHandler(hdlr)
  logger.setLevel(lvl)
  logger.propagate = False
  return logger, hdlr

def shutil_move(src, dst):
  if os.name == "nt" and os.path.isfile(dst): os.remove(dst)
  shutil.move(src, dst)

#-----------------------------------------------------------------------------
# Move / rename completed downloads
#-----------------------------------------------------------------------------
def finish_feed_files(rc, feed, cfg, err_text, dldata=None):

  status = None

  if rc == 0 and os.path.isfile(feed.tmp): # feed.tmp won't exist if feed is not newer
    dff = filediff.diff(feed.tmp, feed.out, ignore=feed.ignore, ldata=dldata)
    if dff <= 0:
      status = "{1}: {0.url}".format(feed, "unchanged" if dff == 0 else "ignored changes")
      if cfg.verbose:
        unch = feed.tmp + ".unchanged"
        shutil_move(feed.tmp, unch)
      else:
        os.remove(feed.tmp)
      return status

    if not cfg.dry_run:
      if os.path.isfile(feed.out): # keep previous items
        prev = feed.tmp + ".previous"
        shutil_move(feed.out, prev)

      # Only after we *really* succeeded!
      shutil_move(feed.tmp, feed.out)
    else:
      status = "dry-run: {0.url}".format(feed)
      os.remove(feed.tmp)

  elif rc == 0:
    status = "not downloaded: {0.url}".format(feed)

  else:
    err_text = err_text.replace("{", "{{").replace("}", "}}") # escape format characters
    status = "rc={1}: {0.url}\n              {2}".format(feed, rc, err_text)
    if os.path.isfile(feed.log): shutil_move(feed.log, feed.err)

  return status


#-----------------------------------------------------------------------------
# Nevermind
#-----------------------------------------------------------------------------
def tmp_download_native(feed, cfg, state, logger=LOGGER):
  raise NotImplementedError("No downloader available. Please install Python requests or curl.")

#-----------------------------------------------------------------------------
# feed state handling
#-----------------------------------------------------------------------------
def last(feed, state, ts=None):
  fs = state.get(feed.name)
  if fs is None and ts is None: return 0.0 # pragma: nobranch
  if ts is not None:
    if not isinstance(ts, str): ts = time.strftime(TS_FMT, time.localtime(ts))
    if fs is None: fs = State(); state[feed.name] = fs
    fs.last = ts
    if "_last" in fs: del fs["_last"] # TODO: REMOVEME: legacy
  t = fs.get("last", 0.0)
  if isinstance(t, str): t = time.mktime(time.strptime(t, TS_FMT))
  return t

def age(feed, state):
  return time.time() - last(feed, state)

def current(feed, cfg, state):
  if cfg.force: return False
  if state.get(feed.name) is None: return False
  if state[feed.name].rc != 0 and feed.retry: return False
  return age(feed, state) < (feed.interval * 60.0 - EPS)

#-----------------------------------------------------------------------------
# we always prefer the requests module, but commandline curl is OK
#-----------------------------------------------------------------------------
def select_tmp_downloader(cfg):
  # select default downloader
  if requests_dl: tmp_downloader = requests_dl.tmp_downloader
  elif cfg.curl:  tmp_downloader = curl_dl.tmp_downloader
  else:           tmp_downloader = tmp_download_native

  if cfg.downloader:
    tmp_downloader = { "requests": getattr(requests_dl, "tmp_downloader", None),
                       "curl":     curl_dl.tmp_downloader
                     }.get(cfg.downloader, tmp_download_native)
  return tmp_downloader

#-----------------------------------------------------------------------------
# Download wrapper
#-----------------------------------------------------------------------------
def download(feed, cfg, state):

  if current(feed, cfg, state):
    info('Skipping    {0.url}, next {1}'.format(feed, time.strftime("%H:%M:%S", time.localtime(last(feed, state)+feed.interval*60-EPS))))
    return

  info('Downloading {0.url} as {0.name}'.format(feed))

  timing = time.time()

  logger, loghandler = get_feed_logger(feed, cfg)

  with contextlib.closing(loghandler):
    downloader = select_tmp_downloader(cfg)

    rc, err, data = downloader(feed, cfg, state, logger)

    timing = time.time() - timing

    if feed.verify:
      from . import verify
      try:
        verify.verify_feed(feed, data, cfg, logger)
      except verify.VerifyException as exc:
        rc, err = exc.code, exc.msg + (" {0!r}".format(exc.parsed) if exc.parsed else "")

    last(feed, state, time.time())
    state[feed.name].rc = rc

  status = finish_feed_files(rc, feed, cfg, err, dldata=data)

  if status is not None: # None: everything went as expected
    (info if rc == 0 else error)("{0} ({1:.1f}s)".format(status, timing))
  elif cfg.verbose:
    debug("downloaded: {0.url} ({1:.1f}s)".format(feed, timing))

#-----------------------------------------------------------------------------
# Threads
#-----------------------------------------------------------------------------
def worker_thread(queue, cfg, state):
  while True:
    feed = queue.get()
    if feed is None: break

    try:
      download(feed, cfg, state)
    except:
      LOGGER.error("Continuing after exception", exc_info=sys.exc_info())
    finally:
      queue.task_done()

def start_threads(queue, cfg, state):
  threads = []
  for _ in range(cfg.parallel):
    threads += [ threading.Thread(target=worker_thread, args=(queue, cfg, state)) ]
    threads[-1].start()
  return threads

def stop_threads(queue, threads):
  for _ in range(len(threads)): queue.put(None)
  for t in threads:            t.join()

#-----------------------------------------------------------------------------
# config / state
#-----------------------------------------------------------------------------
def load_feeds(cfg):
  feeds = []
  
  for f in cfg.get("feeds", []):
    if cfg.feedlist and f.name not in cfg.feedlist: continue
    if f.disabled: continue

    feeds += [ Feed(f.name, f.url,
                    outdir=cfg.outdir, tmpdir=cfg.tmpdir,
                    interval=f.get("interval", ALWAYS),
                    retry=f.get("retry", False),
                    useragent=f.get("useragent", cfg.useragent),
                    timeout=f.get("timeout", cfg.timeout),
                    ignore=f.get("ignore"),
                    verify=f.get("verify", cfg.verify),
                    proxies=f.get("proxies", cfg.proxies)) ]
  return feeds

def load_state(cfg):
  statefile = os.path.join(cfg.tmpdir, "feedcache.state.json")
  if os.path.isfile(statefile):
    with open(statefile) as sf: state = json.load(sf, object_pairs_hook=State)
  else: state = State()
  return state

def save_state(cfg, state):
  if not cfg.dry_run:
    statefile = os.path.join(cfg.tmpdir, "feedcache.state.json")
    with open(statefile, "w") as sf:
      json.dump(state, sf, indent=2)


def update_config(cfg, args):
  for name, val in vars(args).items():
    cfg[name] = val if val is not None else cfg.get(name, CFG_DEFAULTS.get(name))

#-----------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------
def main(argv=sys.argv[1:]):
  ap = argparse.ArgumentParser(prog="feedcache")
  ap.add_argument(      "feedlist",    nargs="*")
  ap.add_argument("-c", "--config",    default=os.path.join(HOME, "web", "feedcache.json"))
  ap.add_argument("-o", "--outdir",    default=None)
  ap.add_argument("-t", "--tmpdir",    default=None)
  ap.add_argument("-u", "--useragent", default=None)
  ap.add_argument("-p", "--parallel",  default=None,  type=int, help=f"Default: {NUM_THREADS}")
  ap.add_argument("-T", "--timeout",   default=None,  type=int, help="Default: none")
  ap.add_argument("-V", "--verify",    default=False, action="store_true", help="Verify feed data using feedparser")
  ap.add_argument("-f", "--force",     default=False, action="store_true", help="Force download of up-to-date feeds")
  ap.add_argument("-v", "--verbose",   default=False, action="store_true")
  ap.add_argument("-d", "--dry-run",   default=False, action="store_true", help="Don't create output / state files")
  ap.add_argument(      "--version",   default=False, action="version", version="%(prog)s " + VERSION_STRING)
  ap.add_argument(      "--curl",      default="curl")

  args = ap.parse_args(argv)

  logging.basicConfig(format=LOGFMT, style="{")
  logging.getLogger().handlers[0].formatter.default_time_format = LOGDATE # s. Python manual 16.6.4 (Formatter Objects)
  LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)

  with open(args.config) as config:
    cfg = json.load(config, object_pairs_hook=Config)

  update_config(cfg, args)

  feeds = load_feeds(cfg)
  state = load_state(cfg)

  debug("Starting feedcache v{0}", __version__)
  info("Caching {} feeds", len(feeds))

  dlqueue = queue.Queue()
  threads = start_threads(dlqueue, cfg, state)
    
  for feed in feeds:
    dlqueue.put(feed)

  dlqueue.join()

  stop_threads(dlqueue, threads)

  save_state(cfg, state)

  info("Done.")

  return 0

if __name__ == "__main__": # pragma: nocover
  sys.exit(main())
