EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Empty Test Feed</title>
        <link>https://www.example.com/news/world</link>
        <description>An empty feed.</description>
        <language>en-US</language>
        <copyright>DITJ</copyright>
        <pubDate>Wed, 20 Nov 2024 16:24:52 -0500</pubDate>
        <ttl>5</ttl>
        <image>
            <title>Just a test</title>
            <link>https://www.example.com/news/world</link>
            <url>http://l.yimg.com/rz/d/yahoo_news_en-US_s_f_p_168x21_news.png</url>
        </image>
    </channel>
</rss>
"""
EMPTY_RSS_MOD = EMPTY_RSS.replace("20 Nov", "21 Nov")

INVALID_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss></html>
"""


SIMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0">
    <channel>
        <title>Test Feed with a few items</title>
        <link>https://www.example.com/news/world</link>
        <description>A simple feed.</description>
        <language>en-US</language>
        <copyright>DITJ</copyright>
        <pubDate>Wed, 20 Nov 2024 16:24:52 -0500</pubDate>
        <ttl>5</ttl>
        <image>
            <title>Just a test</title>
            <link>https://www.example.com/news/world</link>
            <url>http://l.yimg.com/rz/d/yahoo_news_en-US_s_f_p_168x21_news.png</url>
        </image>
        <item>
            <title>Southern African leaders resolve to keep troops in conflict-torn eastern Congo for another year</title>
            <link>https://www.yahoo.com/news/southern-african-leaders-resolve-keep-205117401.html</link>
            <pubDate>2024-11-20T20:51:17Z</pubDate>
            <source url="https://apnews.com/">Associated Press</source>
            <guid isPermaLink="false">southern-african-leaders-resolve-keep-205117401.html</guid>
            <media:content height="86" url="https://media.zenfs.com/en/ap.org/189c74d3a4a786abc095ae71438551ea" width="130"/>
            <media:credit role="publishing company"/>
        </item>
        <item>
            <title>Zelensky tells Ukrainians not to panic as fears of escalation mount</title>
            <link>https://www.yahoo.com/news/zelensky-tells-ukrainians-not-panic-204309014.html</link>
            <pubDate>2024-11-20T20:43:09Z</pubDate>
            <source url="https://nordot.app/-/units/601684660556563553">dpa international</source>
            <guid isPermaLink="false">zelensky-tells-ukrainians-not-panic-204309014.html</guid>
            <media:content height="86" url="https://media.zenfs.com/en/dpa_international_526/6a5505671c5daa0838dc91c01d27bb1d" width="130"/>
            <media:credit role="publishing company"/>
        </item>
    </channel>
</rss>
"""