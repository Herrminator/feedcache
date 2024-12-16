### Command Line Help

<!-- Generated content. Do NOT modify! -->
```
usage: feedcache [-h] [-c CONFIG] [-o OUTDIR] [-t TMPDIR] [-u USERAGENT] [-p PARALLEL] [-T TIMEOUT] [-V] [-f] [-v]
                 [-d] [--version] [--curl CURL]
                 [feedlist ...]

positional arguments:
  feedlist

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Default: ${HOME}\web\feedcache.json
  -o OUTDIR, --outdir OUTDIR
                        Default: feedcache
  -t TMPDIR, --tmpdir TMPDIR
                        Default: tmp
  -u USERAGENT, --useragent USERAGENT
                        Default: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/133.0
  -p PARALLEL, --parallel PARALLEL
                        Default: 8
  -T TIMEOUT, --timeout TIMEOUT
                        Default: None
  -V, --verify          Verify feed data using feedparser
  -f, --force           Force download of up-to-date feeds
  -v, --verbose
  -d, --dry-run         Don't create output / state files
  --version             show program's version number and exit
  --curl CURL

```
