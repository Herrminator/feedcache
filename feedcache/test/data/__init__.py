from copy import deepcopy
from .. import TEST_TMP, IS_WINDOWS
from .  import rss

EMPTY = {}

EMPTY_FEED = {
    "feeds": [
        {
          "name": "empty.feed.atom",
          "url": (TEST_TMP / "empty.rss").as_uri(),
          "_data": {
            "file": (TEST_TMP / "empty.rss"),
            "content": rss.EMPTY_RSS,
          }
        },
    ]
}

EMPTY_FEED_WITH_INTERVAL = deepcopy(EMPTY_FEED)
EMPTY_FEED_WITH_INTERVAL["feeds"][0]["interval"] = 60

EMPTY_FEED_WITH_FORCE = deepcopy(EMPTY_FEED)
EMPTY_FEED_WITH_FORCE["feeds"][0]["force"] = True

EMPTY_FEED_WITH_FORCE_MOD = deepcopy(EMPTY_FEED_WITH_FORCE)
EMPTY_FEED_WITH_FORCE_MOD["feeds"][0]["_data"]["content"] = rss.EMPTY_RSS_MOD

EMPTY_FEED_WITH_FORCE_MOD_IGNORE = deepcopy(EMPTY_FEED_WITH_FORCE_MOD)
EMPTY_FEED_WITH_FORCE_MOD_IGNORE["feeds"][0]["ignore"] = "<pubDate>.*?</pubDate>"

EMPTY_FEED_WITH_CURL = deepcopy(EMPTY_FEED)
EMPTY_FEED_WITH_CURL["downloader"] = "curl"

EMPTY_FEED_WITH_NATIVE_DL = deepcopy(EMPTY_FEED)
EMPTY_FEED_WITH_NATIVE_DL["downloader"] = "native"

MISSING_FEED_FILE = {
    "feeds": [
        {
          "name": "missing.feed.atom",
          "url": f"file:///{'C:' if IS_WINDOWS else '' }/this-feed-does-not-exist-i-hope.rss", # ??? 'C:' makes path absolute on windows!
        },
    ]
}

INVALID_FEED = {
    "feeds": [
        {
          "name": "invalid.feed.atom",
          "url": (TEST_TMP / "invalid.rss").as_uri(),
          "_data": {
            "file": (TEST_TMP / "invalid.rss"),
            "content": rss.INVALID_RSS,
          }
        },
    ]
}


SIMPLE_TEST_1 = {

}

INVALID_SERVER = {
    "feeds": [
        {
          "name": "invalid.server.atom",
          "url": "https://254.0.0.42:6917/no-server.rss",
        },
    ]
}

