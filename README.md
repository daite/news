# news

Daily Korean news aggregator that fetches top articles from Korean and Japanese financial news sources via RSS, builds a static HTML archive, deploys to GitHub Pages, and sends Telegram notifications.

**Live site**: https://daite.github.io/news/

## Sources

| Key | Source | Language |
|-----|--------|----------|
| `mk` | [MK 매일경제](https://www.mk.co.kr) | Korean |
| `hankyung` | [한국경제](https://www.hankyung.com) | Korean |
| `nhk` | [NHK NEWS](https://www3.nhk.or.jp/news/) | Japanese |

## How it works

1. **Fetch** — `scripts/fetch_news.py` pulls the top 10 articles from each RSS feed and saves them as Markdown files under `articles/<source>/<YYYY-MM-DD>.md`.
2. **Build** — The same script renders per-day HTML pages and an index listing all archived dates, writing output to `site/`.
3. **Deploy** — GitHub Actions commits the new articles, uploads the `site/` directory as a Pages artifact, and deploys it.
4. **Notify** — A Telegram message is sent on both success and failure.

The workflow runs automatically every day at **5:00 AM KST** (20:00 UTC) and can also be triggered manually via `workflow_dispatch`.

## Repository structure

```
.
├── articles/
│   ├── mk/           # MK 매일경제 markdown files
│   ├── hankyung/     # 한국경제 markdown files
│   └── nhk/          # NHK NEWS markdown files
├── scripts/
│   └── fetch_news.py # Fetch, build, and site-generation script
├── .github/
│   └── workflows/
│       └── fetch_news.yml
└── requirements.txt
```

## Setup

### 1. Fork & enable GitHub Pages

In your fork's settings, enable GitHub Pages and set the source to **GitHub Actions**.

### 2. Add repository secrets

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Chat or channel ID to receive notifications |

### 3. Run manually (optional)

Trigger the workflow from the **Actions** tab using the `workflow_dispatch` button to fetch articles immediately.

## Local usage

```bash
pip install -r requirements.txt
python scripts/fetch_news.py
# Opens site/index.html for the generated archive
```

## Requirements

- Python 3.12+
- `feedparser`
- `requests`
