import html
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_news import (
    FEEDS,
    MAX_ARTICLES,
    USER_AGENT,
    build_article_html,
    build_site,
    fetch_articles,
    strip_html,
    write_markdown,
)


class TestStripHtml(unittest.TestCase):
    def test_removes_tags(self):
        self.assertEqual(strip_html("<b>Hello</b>"), "Hello")

    def test_unescapes_entities(self):
        self.assertEqual(strip_html("&amp;"), "&")

    def test_entities_then_tags(self):
        # &lt;b&gt;text&lt;/b&gt; → <b>text</b> → text
        self.assertEqual(strip_html("&lt;b&gt;text&lt;/b&gt;"), "text")

    def test_none_returns_empty(self):
        self.assertEqual(strip_html(None), "")

    def test_empty_string(self):
        self.assertEqual(strip_html(""), "")

    def test_plain_text_unchanged(self):
        self.assertEqual(strip_html("Hello World"), "Hello World")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(strip_html("  hello  "), "hello")

    def test_nested_tags(self):
        self.assertEqual(strip_html("<p><strong>deep</strong></p>"), "deep")


class TestFetchArticles(unittest.TestCase):
    def _feed(self, entries, bozo=False, exc=None):
        f = MagicMock()
        f.bozo = bozo
        f.bozo_exception = exc
        f.entries = entries
        return f

    @patch("fetch_news.feedparser.parse")
    def test_returns_entries(self, mock_parse):
        entries = [MagicMock() for _ in range(3)]
        mock_parse.return_value = self._feed(entries)
        self.assertEqual(fetch_articles("http://x.com/rss", "Test"), entries)

    @patch("fetch_news.feedparser.parse")
    def test_caps_at_max_articles(self, mock_parse):
        entries = [MagicMock() for _ in range(MAX_ARTICLES + 5)]
        mock_parse.return_value = self._feed(entries)
        self.assertEqual(len(fetch_articles("http://x.com/rss", "Test")), MAX_ARTICLES)

    @patch("fetch_news.feedparser.parse")
    def test_bozo_with_no_entries_returns_empty(self, mock_parse):
        mock_parse.return_value = self._feed([], bozo=True, exc=Exception("bad xml"))
        self.assertEqual(fetch_articles("http://x.com/rss", "Test"), [])

    @patch("fetch_news.feedparser.parse")
    def test_bozo_with_entries_still_returns_them(self, mock_parse):
        # Some feeds are technically malformed but still parseable
        entries = [MagicMock()]
        mock_parse.return_value = self._feed(entries, bozo=True, exc=Exception("minor"))
        self.assertEqual(fetch_articles("http://x.com/rss", "Test"), entries)

    @patch("fetch_news.feedparser.parse")
    def test_empty_feed_returns_empty(self, mock_parse):
        mock_parse.return_value = self._feed([])
        self.assertEqual(fetch_articles("http://x.com/rss", "Test"), [])

    @patch("fetch_news.feedparser.parse")
    def test_passes_url_and_browser_agent_to_feedparser(self, mock_parse):
        mock_parse.return_value = self._feed([])
        fetch_articles("http://example.com/feed", "Test")
        mock_parse.assert_called_once_with("http://example.com/feed", agent=USER_AGENT)


class TestWriteMarkdown(unittest.TestCase):
    def _entry(self, title="Title", link="http://x.com", desc="", author=""):
        return {"title": title, "link": link, "description": desc, "author": author}

    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry()], "2026-01-01", d, "Feed")
            self.assertTrue(os.path.exists(os.path.join(d, "2026-01-01.md")))

    def _read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_header_contains_feed_name_and_date(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([], "2026-01-01", d, "My Feed")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("# My Feed 뉴스 - 2026-01-01", content)

    def test_article_link_in_output(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry("Art", "http://ex.com/1")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("[Art](http://ex.com/1)", content)

    def test_author_included_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry(author="Jane")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("*Jane*", content)

    def test_author_omitted_when_empty(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry(author="")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            lines = [l for l in content.splitlines() if l.startswith("*") and l.endswith("*")]
            self.assertEqual(lines, [])

    def test_description_included(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry(desc="Summary text")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("Summary text", content)

    def test_multiple_entries_numbered(self):
        with tempfile.TemporaryDirectory() as d:
            entries = [self._entry("A"), self._entry("B")]
            write_markdown(entries, "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("## 1.", content)
            self.assertIn("## 2.", content)

    def test_html_stripped_from_title(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry(title="<b>Bold</b>")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("Bold", content)
            self.assertNotIn("<b>", content)

    def test_html_stripped_from_description(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry(desc="<p>Para</p>")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("Para", content)
            self.assertNotIn("<p>", content)

    def test_separators_between_articles(self):
        with tempfile.TemporaryDirectory() as d:
            write_markdown([self._entry("A"), self._entry("B")], "2026-01-01", d, "F")
            content = self._read(os.path.join(d, "2026-01-01.md"))
            self.assertIn("---", content)


class TestBuildArticleHtml(unittest.TestCase):
    def _md(self, tmpdir, content):
        path = os.path.join(tmpdir, "2026-01-01.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_h1_rendered(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "# My Title\n"), "2026-01-01", "../index.html")
            self.assertIn("<h1>My Title</h1>", out)

    def test_h2_with_link(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(
                self._md(d, "## 1. [Article](http://example.com)\n"),
                "2026-01-01", "../index.html",
            )
            self.assertIn('href="http://example.com"', out)
            self.assertIn(">Article<", out)

    def test_h2_without_link_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(
                self._md(d, "## Plain Heading\n"), "2026-01-01", "../index.html"
            )
            self.assertIn("<h2>Plain Heading</h2>", out)

    def test_hr_rendered(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "---\n"), "2026-01-01", "../index.html")
            self.assertIn("<hr>", out)

    def test_em_rendered(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "*Author*\n"), "2026-01-01", "../index.html")
            self.assertIn("<em>Author</em>", out)

    def test_plain_paragraph(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "Some text\n"), "2026-01-01", "../index.html")
            self.assertIn("<p>Some text</p>", out)

    def test_back_link_href(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, ""), "2026-01-01", "../index.html")
            self.assertIn('href="../index.html"', out)

    def test_title_contains_date(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, ""), "2026-01-01", "../index.html")
            self.assertIn("2026-01-01", out)

    def test_paragraph_text_is_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "a < b\n"), "2026-01-01", "../index.html")
            self.assertIn("a &lt; b", out)

    def test_link_opens_in_new_tab(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(
                self._md(d, "## 1. [X](http://x.com)\n"), "2026-01-01", "../index.html"
            )
            self.assertIn('target="_blank"', out)

    def test_valid_html_structure(self):
        with tempfile.TemporaryDirectory() as d:
            out = build_article_html(self._md(d, "# T\n"), "2026-01-01", "../index.html")
            self.assertIn("<!DOCTYPE html>", out)
            self.assertIn("<html", out)
            self.assertIn("</html>", out)
            self.assertIn("<body>", out)
            self.assertIn("</body>", out)


class TestBuildSite(unittest.TestCase):
    def _write_md(self, articles_dir, key, date):
        src = os.path.join(articles_dir, key)
        os.makedirs(src, exist_ok=True)
        path = os.path.join(src, f"{date}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Feed\n\n---\n\n## 1. [Art](http://x.com)\n\nDesc\n")
        return path

    def test_creates_html_for_each_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-01")
            self._write_md(art, "mk", "2026-01-02")
            build_site(art, site)
            self.assertTrue(os.path.exists(os.path.join(site, "mk", "2026-01-01.html")))
            self.assertTrue(os.path.exists(os.path.join(site, "mk", "2026-01-02.html")))

    def test_creates_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-01")
            build_site(art, site)
            self.assertTrue(os.path.exists(os.path.join(site, "index.html")))

    def _read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_index_lists_feed_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-01")
            self._write_md(art, "bbc", "2026-01-01")
            build_site(art, site)
            content = self._read(os.path.join(site, "index.html"))
            self.assertIn("MK 매일경제", content)
            self.assertIn("BBC News", content)

    def test_skips_missing_source_dirs_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            os.makedirs(art)
            self._write_md(art, "mk", "2026-01-01")
            build_site(art, site)
            self.assertTrue(os.path.exists(os.path.join(site, "index.html")))

    def test_most_recent_month_details_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-15")
            self._write_md(art, "mk", "2025-12-31")
            build_site(art, site)
            content = self._read(os.path.join(site, "index.html"))
            self.assertIn("<details open>", content)

    def test_article_html_links_back_to_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-01")
            build_site(art, site)
            content = self._read(os.path.join(site, "mk", "2026-01-01.html"))
            self.assertIn("../index.html", content)

    def test_index_links_to_article_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "articles")
            site = os.path.join(tmp, "site")
            self._write_md(art, "mk", "2026-01-01")
            build_site(art, site)
            content = self._read(os.path.join(site, "index.html"))
            self.assertIn("mk/2026-01-01.html", content)


class TestFeedsConfig(unittest.TestCase):
    def test_all_feeds_have_required_keys(self):
        for feed in FEEDS:
            for key in ("key", "name", "url"):
                self.assertIn(key, feed, f"Feed missing '{key}': {feed}")

    def test_feed_keys_are_unique(self):
        keys = [f["key"] for f in FEEDS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_four_sources_present(self):
        keys = {f["key"] for f in FEEDS}
        for expected in ("mk", "hankyung", "nhk", "bbc"):
            self.assertIn(expected, keys)

    def test_bbc_url(self):
        bbc = next(f for f in FEEDS if f["key"] == "bbc")
        self.assertEqual(bbc["url"], "https://feeds.bbci.co.uk/news/rss.xml")
        self.assertEqual(bbc["name"], "BBC News")

    def test_urls_are_non_empty_strings(self):
        for feed in FEEDS:
            self.assertIsInstance(feed["url"], str)
            self.assertTrue(feed["url"].startswith("http"))

    def test_max_articles_is_positive(self):
        self.assertGreater(MAX_ARTICLES, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
