import logging
from datetime import datetime, timezone, timedelta
from time import mktime

import feedparser

from hunter.x_theme_generator.config import RSS_FEEDS, ARTICLES_MAX_AGE_HOURS
from hunter.x_theme_generator.models import Article

logger = logging.getLogger(__name__)


def _parse_date(entry: dict) -> datetime:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


def collect_articles(
    feeds: dict[str, str] | None = None,
    max_per_feed: int = 10,
    max_age_hours: int | None = None,
) -> list[Article]:
    feeds = feeds or RSS_FEEDS
    max_age = max_age_hours or ARTICLES_MAX_AGE_HOURS
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age)
    articles: list[Article] = []

    for source_name, feed_url in feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                logger.warning("フィード取得失敗: %s (%s)", source_name, feed_url)
                continue

            for entry in feed.entries[:max_per_feed]:
                pub_date = _parse_date(entry)
                if pub_date < cutoff:
                    continue

                summary = entry.get("summary", "")
                if len(summary) > 500:
                    summary = summary[:500] + "..."

                articles.append(Article(
                    title=entry.get("title", ""),
                    summary=summary,
                    link=entry.get("link", ""),
                    published=pub_date,
                    source=source_name,
                ))
        except Exception:
            logger.warning("フィード処理エラー: %s", source_name, exc_info=True)
            continue

    articles.sort(key=lambda a: a.published, reverse=True)
    return articles
