from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from src.models import Candidate
from src.utils import USER_AGENT, clean_text, stable_id


API_URL = "https://api.github.com/search/repositories"


def collect(config: dict[str, Any], token: str | None = None) -> list[Candidate]:
    source_config = config["sources"]["github"]
    if not source_config.get("enabled", True):
        return []

    lookback = int(config["project"].get("lookback_days", 7))
    created_after = (datetime.now(timezone.utc) - timedelta(days=lookback)).date().isoformat()
    per_query = max(5, int(source_config.get("max_results", 35)) // len(source_config["queries"]))
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    candidates: list[Candidate] = []
    seen: set[int] = set()
    for base_query in source_config["queries"]:
        params = {
            "q": f"{base_query} created:>={created_after}",
            "sort": "stars",
            "order": "desc",
            "per_page": min(per_query, 50),
        }
        response = requests.get(API_URL, params=params, headers=headers, timeout=25)
        response.raise_for_status()
        for repo in response.json().get("items", []):
            repo_id = int(repo["id"])
            if repo_id in seen:
                continue
            seen.add(repo_id)
            topics = repo.get("topics") or []
            description = clean_text(repo.get("description"))
            full_text = " ".join([repo.get("full_name", ""), description, " ".join(topics)])
            stars = int(repo.get("stargazers_count", 0))
            forks = int(repo.get("forks_count", 0))
            issues = int(repo.get("open_issues_count", 0))
            candidates.append(
                Candidate(
                    id=stable_id("github", str(repo_id)),
                    source="GitHub",
                    name=repo.get("full_name") or repo.get("name") or "Unnamed repository",
                    url=repo.get("html_url", ""),
                    description=description or "No repository description provided.",
                    published_at=repo.get("created_at", ""),
                    author=(repo.get("owner") or {}).get("login", ""),
                    metrics={
                        "stars": stars,
                        "forks": forks,
                        "open_issues": issues,
                        "watchers": int(repo.get("watchers_count", 0)),
                    },
                    tags=topics,
                    evidence=[
                        f"{stars:,} GitHub stars",
                        f"{forks:,} forks",
                        f"Created {repo.get('created_at', '')[:10]}",
                    ],
                    raw_text=full_text,
                    metadata={
                        "language": repo.get("language"),
                        "updated_at": repo.get("updated_at"),
                        "homepage": repo.get("homepage"),
                    },
                )
            )
    return candidates

