import html
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser

FEEDS = [
    {"key": "mk", "name": "MK 매일경제", "url": "https://www.mk.co.kr/rss/30000001"},
    {"key": "hankyung", "name": "한국경제", "url": "https://www.hankyung.com/feed/all-news"},
]
MAX_ARTICLES = 10
KST = timezone(timedelta(hours=9))

CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Noto Sans KR", sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
    line-height: 1.6;
}
h1 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
h2 { margin-top: 1.5em; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid #eee; margin: 1.5em 0; }
ul { padding-left: 1.5em; }
li { margin: 0.5em 0; }
.back { margin-bottom: 1em; }
.source-section { margin-bottom: 2em; }
"""


def strip_html(text):
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_articles(feed_url, feed_name):
    feed = feedparser.parse(feed_url)
    if feed.bozo and not feed.entries:
        print(f"Error parsing {feed_name} RSS: {feed.bozo_exception}", file=sys.stderr)
        return []
    entries = feed.entries[:MAX_ARTICLES]
    if not entries:
        print(f"No articles found in {feed_name} feed", file=sys.stderr)
    return entries


def write_markdown(entries, date_str, articles_dir, feed_name):
    lines = [f"# {feed_name} 뉴스 - {date_str}\n"]
    for i, entry in enumerate(entries, 1):
        title = strip_html(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        desc = strip_html(entry.get("description", ""))
        author = strip_html(entry.get("author", ""))
        lines.append("---\n")
        lines.append(f"## {i}. [{title}]({link})\n")
        if author:
            lines.append(f"*{author}*\n")
        if desc:
            lines.append(f"{desc}\n")
    path = os.path.join(articles_dir, f"{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


def build_article_html(md_path, date_str, back_href):
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    body_parts = []
    for line in content.split("\n"):
        line = line.rstrip()
        if line.startswith("# "):
            body_parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            match = re.match(r"## (\d+)\. \[(.+?)\]\((.+?)\)", line)
            if match:
                num, title, link = match.groups()
                body_parts.append(
                    f'<h2>{num}. <a href="{html.escape(link)}" target="_blank">'
                    f"{html.escape(title)}</a></h2>"
                )
            else:
                body_parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line == "---":
            body_parts.append("<hr>")
        elif line.startswith("*") and line.endswith("*"):
            body_parts.append(f"<p><em>{html.escape(line[1:-1])}</em></p>")
        elif line:
            body_parts.append(f"<p>{html.escape(line)}</p>")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>News - {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<p class="back"><a href="{back_href}">&larr; Back to archive</a></p>
{"".join(body_parts)}
</body>
</html>"""


def build_site(base_articles_dir, site_dir):
    # Build per-source pages
    for feed in FEEDS:
        key = feed["key"]
        name = feed["name"]
        src_dir = os.path.join(base_articles_dir, key)
        dst_dir = os.path.join(site_dir, key)
        os.makedirs(dst_dir, exist_ok=True)

        if not os.path.isdir(src_dir):
            continue

        md_files = sorted(
            [f for f in os.listdir(src_dir) if f.endswith(".md")],
            reverse=True,
        )

        for md_file in md_files:
            date_str = md_file.replace(".md", "")
            md_path = os.path.join(src_dir, md_file)
            html_content = build_article_html(md_path, date_str, "../index.html")
            html_path = os.path.join(dst_dir, f"{date_str}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

    # Build index page
    sections = []
    for feed in FEEDS:
        key = feed["key"]
        name = feed["name"]
        src_dir = os.path.join(base_articles_dir, key)
        if not os.path.isdir(src_dir):
            continue

        md_files = sorted(
            [f for f in os.listdir(src_dir) if f.endswith(".md")],
            reverse=True,
        )
        links = "\n".join(
            f'<li><a href="{key}/{f.replace(".md", ".html")}">'
            f'{f.replace(".md", "")}</a></li>'
            for f in md_files
        )
        sections.append(f'<div class="source-section">\n<h2>{html.escape(name)}</h2>\n<ul>\n{links}\n</ul>\n</div>')

    index_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Korean News Archive</title>
<style>{CSS}</style>
</head>
<body>
<h1>Daily Korean News Archive</h1>
{"".join(sections)}
</body>
</html>"""

    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"Built site for {len(FEEDS)} source(s)")


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    articles_dir = os.path.join(base_dir, "articles")
    site_dir = os.path.join(base_dir, "site")

    date_str = datetime.now(KST).strftime("%Y-%m-%d")

    total = 0
    for feed in FEEDS:
        feed_articles_dir = os.path.join(articles_dir, feed["key"])
        os.makedirs(feed_articles_dir, exist_ok=True)

        entries = fetch_articles(feed["url"], feed["name"])
        if entries:
            write_markdown(entries, date_str, feed_articles_dir, feed["name"])
            total += len(entries)

    if total == 0:
        print("No articles fetched from any feed", file=sys.stderr)
        sys.exit(1)

    build_site(articles_dir, site_dir)


if __name__ == "__main__":
    main()
