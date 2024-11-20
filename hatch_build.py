from hatchling.metadata.plugin.interface import MetadataHookInterface

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
        with open("README.md", "r") as fh, open("CHANGELOG.md") as cl:
            meta["readme"] = {
                "content-type": "text/markdown",
                "text": ( fh.read()
                            .replace("<usage>", get_help())
                            .replace("<changelog>", cl.read()))
            }
