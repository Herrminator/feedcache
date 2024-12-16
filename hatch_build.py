import re, sys
from hatchling.metadata.plugin.interface import MetadataHookInterface # type: ignore # only available during build

CHANGE_PATT = re.compile(r'^## Changes.*CHANGELOG\.md\)', re.M | re.S)
HELP_FILE = "feedcache-help.md"
HELP_PATT = re.compile(r'Please see.*feedcache-help\.md\)\.', re.M | re.S)
HELP_TEMPLATE = """### Command Line Help

<!-- Generated content. Do NOT modify! -->
```
{help}
```
"""


def get_help():
  import sys; sys.path = [ "." ] + sys.path
  import io, feedcache.feedcache, contextlib
  from feedcache.constants import HOME
  helpout = io.StringIO()
  with contextlib.redirect_stdout(helpout):
      try: feedcache.feedcache.main(["--help"])
      except SystemExit: pass
  hlp = helpout.getvalue().replace(HOME, "${HOME}")
  return hlp

class CustomHook(MetadataHookInterface):

    def update(self, meta):
        help   = HELP_TEMPLATE.format(help=get_help())
        # a little side effect never hurts ;)
        with open(HELP_FILE, "w") as f: f.write(help)
        with open("README.md", "r") as fh, open("CHANGELOG.md") as cl:
            readme = fh.read()
            readme = CHANGE_PATT.sub(cl.read(), readme)
            readme = HELP_PATT.sub(re.escape(help), readme)
            meta["readme"] = {
                "content-type": "text/markdown",
                "text": readme
            }

