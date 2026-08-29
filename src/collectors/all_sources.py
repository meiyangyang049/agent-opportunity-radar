from __future__ import annotations

import os
from typing import Any, Callable

from src.collectors import github, hackernews, rss
from src.models import Candidate


def collect_all(config: dict[str, Any]) -> tuple[list[Candidate], list[str]]:
    collectors: list[tuple[str, Callable[[], list[Candidate]]]] = [
        ("GitHub", lambda: github.collect(config, os.getenv("GITHUB_TOKEN"))),
        ("Hacker News", lambda: hackernews.collect(config)),
        ("Product Hunt", lambda: rss.collect_producthunt(config)),
        ("AI news RSS", lambda: rss.collect_news(config)),
    ]
    candidates: list[Candidate] = []
    warnings: list[str] = []
    for name, collector in collectors:
        try:
            candidates.extend(collector())
        except Exception as exc:  # A single public source must not stop the radar.
            warnings.append(f"{name}: {type(exc).__name__}: {exc}")
    return candidates, warnings

