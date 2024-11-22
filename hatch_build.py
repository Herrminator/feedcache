import re
from hatchling.metadata.plugin.interface import MetadataHookInterface

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
  helpout = io.StringIO()
  with contextlib.redirect_stdout(helpout):
      try: feedcache.feedcache.main(["--help"])
      except SystemExit: pass
  return helpout.getvalue()

class CustomHook(MetadataHookInterface):

    def update(self, meta):
        help   = HELP_TEMPLATE.format(help=get_help())
        # a little side effect never hurts ;)
        with open(HELP_FILE, "w") as f: f.write(help)
        with open("README.md", "r") as fh, open("CHANGELOG.md") as cl:
            readme = fh.read()
            readme = CHANGE_PATT.sub(cl.read(), readme)
            readme = HELP_PATT.sub(help, readme)
            meta["readme"] = {
                "content-type": "text/markdown",
                "text": readme
            }

