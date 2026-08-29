from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from src.models import Candidate
from src.utils import USER_AGENT, clean_text, stable_id


BASE_URL = "https://hacker-news.firebaseio.com/v0"


def collect(config: dict[str, Any]) -> list[Candidate]:
    source_config = config["sources"]["hackernews"]
    if not source_config.get("enabled", True):
        return []

    limit = int(source_config.get("story_limit", 250))
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(f"{BASE_URL}/newstories.json", headers=headers, timeout=20)
    response.raise_for_status()
    story_ids = response.json()[:limit]

    def fetch(story_id: int) -> dict[str, Any]:
        item_response = requests.get(
            f"{BASE_URL}/item/{story_id}.json", headers=headers, timeout=12
        )
        if not item_response.ok:
            return {}
        return item_response.json() or {}

    candidates: list[Candidate] = []
    items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch, story_id): story_id for story_id in story_ids}
        for future in as_completed(futures):
            try:
                item = future.result()
                if item:
                    items.append(item)
            except requests.RequestException:
                continue

    for item in items:
        story_id = int(item.get("id", 0))
        if item.get("type") != "story" or item.get("deleted") or item.get("dead"):
            continue
        title = clean_text(item.get("title"))
        body = clean_text(item.get("text"))
        url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        candidates.append(
            Candidate(
                id=stable_id("hackernews", str(story_id)),
                source="Hacker News",
                name=title or f"HN story {story_id}",
                url=url,
                description=body or title,
                published_at=str(item.get("time", "")),
                author=item.get("by", ""),
                metrics={
                    "points": int(item.get("score", 0)),
                    "comments": int(item.get("descendants", 0)),
                },
                evidence=[
                    f"{int(item.get('score', 0))} HN points",
                    f"{int(item.get('descendants', 0))} comments",
                ],
                raw_text=f"{title} {body}",
                metadata={
                    "discussion_url": f"https://news.ycombinator.com/item?id={story_id}"
                },
            )
        )
    return candidates
