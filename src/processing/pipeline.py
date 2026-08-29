from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from src.models import Candidate
from src.utils import canonical_url, parse_datetime


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return sorted({keyword for keyword in keywords if keyword.lower() in lowered})


def enrich_keywords(candidate: Candidate, config: dict[str, Any]) -> Candidate:
    text = " ".join(
        [candidate.name, candidate.description, candidate.raw_text, " ".join(candidate.tags)]
    )
    candidate.metadata["agent_keyword_hits"] = _keyword_hits(
        text, config["keywords"]["agent"]
    )
    candidate.metadata["commercial_keyword_hits"] = _keyword_hits(
        text, config["keywords"]["commercialization"]
    )
    candidate.metadata["ecosystem_keyword_hits"] = _keyword_hits(
        text, config["keywords"]["ecosystem"]
    )
    return candidate


def is_recent(candidate: Candidate, lookback_days: int) -> bool:
    parsed = parse_datetime(candidate.published_at)
    if parsed is None:
        return True
    return parsed >= datetime.now(timezone.utc) - timedelta(days=lookback_days + 1)


def is_relevant(candidate: Candidate) -> bool:
    hits = candidate.metadata.get("agent_keyword_hits", [])
    if hits:
        return True
    fallback_terms = ("agent", "assistant", "operator", "automation", "copilot")
    lowered = f"{candidate.name} {candidate.description}".lower()
    return any(term in lowered for term in fallback_terms)


def deduplicate(candidates: list[Candidate]) -> list[Candidate]:
    accepted: list[Candidate] = []
    urls: set[str] = set()
    for candidate in candidates:
        url = canonical_url(candidate.url)
        if url and url in urls:
            continue
        normalized_name = candidate.name.lower().strip()
        duplicate = any(
            SequenceMatcher(None, normalized_name, existing.name.lower().strip()).ratio() >= 0.94
            for existing in accepted
        )
        if duplicate:
            continue
        if url:
            urls.add(url)
        accepted.append(candidate)
    return accepted


def prepare_candidates(
    candidates: list[Candidate], config: dict[str, Any]
) -> list[Candidate]:
    lookback = int(config["project"].get("lookback_days", 7))
    enriched = [enrich_keywords(candidate, config) for candidate in candidates]
    relevant = [
        candidate
        for candidate in enriched
        if is_recent(candidate, lookback) and is_relevant(candidate)
    ]
    unique = deduplicate(relevant)
    limit = int(config["project"].get("candidate_limit", 60))
    buckets: dict[str, list[Candidate]] = {
        "github": [],
        "hackernews": [],
        "producthunt": [],
        "news": [],
    }
    for candidate in unique:
        if candidate.source == "GitHub":
            buckets["github"].append(candidate)
        elif candidate.source == "Hacker News":
            buckets["hackernews"].append(candidate)
        elif candidate.source == "Product Hunt":
            buckets["producthunt"].append(candidate)
        else:
            buckets["news"].append(candidate)

    # Round-robin selection prevents a noisy source from crowding out an
    # entire opportunity archetype before scoring.
    balanced: list[Candidate] = []
    while len(balanced) < limit and any(buckets.values()):
        for bucket in buckets.values():
            if bucket and len(balanced) < limit:
                balanced.append(bucket.pop(0))
    return balanced
