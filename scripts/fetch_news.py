import html
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser

RSS_URL = "https://www.mk.co.kr/rss/30000001"
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
"""


def strip_html(text):
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_articles():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo and not feed.entries:
        print(f"Error parsing RSS: {feed.bozo_exception}", file=sys.stderr)
        sys.exit(1)
    entries = feed.entries[:MAX_ARTICLES]
    if not entries:
        print("No articles found in feed", file=sys.stderr)
        sys.exit(1)
    return entries


def write_markdown(entries, date_str, articles_dir):
    lines = [f"# MK 매일경제 뉴스 - {date_str}\n"]
    for i, entry in enumerate(entries, 1):
        title = strip_html(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        desc = strip_html(entry.get("description", ""))
        lines.append(f"---\n")
        lines.append(f"## {i}. [{title}]({link})\n")
        if desc:
            lines.append(f"{desc}\n")
    path = os.path.join(articles_dir, f"{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


def build_article_html(md_path, date_str):
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
        elif line:
            body_parts.append(f"<p>{html.escape(line)}</p>")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MK News - {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<p class="back"><a href="../index.html">&larr; Back to archive</a></p>
{"".join(body_parts)}
</body>
</html>"""


def build_site(articles_dir, site_dir):
    os.makedirs(os.path.join(site_dir, "articles"), exist_ok=True)

    md_files = sorted(
        [f for f in os.listdir(articles_dir) if f.endswith(".md")],
        reverse=True,
    )

    for md_file in md_files:
        date_str = md_file.replace(".md", "")
        md_path = os.path.join(articles_dir, md_file)
        html_content = build_article_html(md_path, date_str)
        html_path = os.path.join(site_dir, "articles", f"{date_str}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    links = "\n".join(
        f'<li><a href="articles/{f.replace(".md", ".html")}">{f.replace(".md", "")}</a></li>'
        for f in md_files
    )

    index_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MK 매일경제 Daily News</title>
<style>{CSS}</style>
</head>
<body>
<h1>MK 매일경제 Daily News Archive</h1>
<ul>
{links}
</ul>
</body>
</html>"""

    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"Built site with {len(md_files)} article(s)")


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    articles_dir = os.path.join(base_dir, "articles")
    site_dir = os.path.join(base_dir, "site")
    os.makedirs(articles_dir, exist_ok=True)

    date_str = datetime.now(KST).strftime("%Y-%m-%d")

    entries = fetch_articles()
    write_markdown(entries, date_str, articles_dir)
    build_site(articles_dir, site_dir)


if __name__ == "__main__":
    main()
