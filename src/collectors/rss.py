from __future__ import annotations

from typing import Any

import feedparser
import requests

from src.models import Candidate
from src.utils import USER_AGENT, clean_text, stable_id, truncate_text


def _read_feed(url: str) -> feedparser.FeedParserDict:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
    response.raise_for_status()
    return feedparser.parse(response.content)


def _candidate_from_entry(
    entry: Any, source: str, feed_url: str, content_kind: str
) -> Candidate:
    link = entry.get("link", "")
    title = clean_text(entry.get("title"))
    full_description = clean_text(entry.get("summary") or entry.get("description"))
    description = truncate_text(full_description or title)
    published = entry.get("published") or entry.get("updated") or ""
    tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
    identity = entry.get("id") or link or title
    return Candidate(
        id=stable_id(source.lower().replace(" ", "-"), identity),
        source=source,
        name=title or "Untitled feed item",
        url=link,
        description=description or title,
        published_at=published,
        author=clean_text(entry.get("author")),
        tags=tags,
        evidence=[f"Published via {source}", published] if published else [f"Published via {source}"],
        raw_text=truncate_text(" ".join([title, full_description, " ".join(tags)]), 1800),
        metadata={
            "feed_url": feed_url,
            "content_kind": content_kind,
            "original_title": title,
        },
    )


def collect_producthunt(config: dict[str, Any]) -> list[Candidate]:
    source_config = config["sources"]["producthunt"]
    if not source_config.get("enabled", True):
        return []
    candidates: list[Candidate] = []
    for feed_url in source_config.get("feeds", []):
        parsed = _read_feed(feed_url)
        candidates.extend(
            _candidate_from_entry(entry, "Product Hunt", feed_url, "product_launch")
            for entry in parsed.entries[:40]
        )
    return candidates


def collect_news(config: dict[str, Any]) -> list[Candidate]:
    source_config = config["sources"]["news"]
    if not source_config.get("enabled", True):
        return []
    candidates: list[Candidate] = []
    for feed_url in source_config.get("feeds", []):
        parsed = _read_feed(feed_url)
        feed_title = clean_text(parsed.feed.get("title")) or "AI News"
        candidates.extend(
            _candidate_from_entry(entry, feed_title, feed_url, "news")
            for entry in parsed.entries[:50]
        )
    return candidates
