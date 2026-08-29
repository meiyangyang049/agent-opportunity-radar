from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse


USER_AGENT = "AgentOpportunityRadar/0.1 (+https://github.com/meiyangyang049/agent-opportunity-radar)"


def stable_id(source: str, value: str) -> str:
    digest = hashlib.sha1(f"{source}:{value}".encode("utf-8")).hexdigest()[:12]
    return f"{source}-{digest}"


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    decoded = html.unescape(html.unescape(value))
    without_html = re.sub(r"<[^>]+>", " ", decoded)
    return re.sub(r"\s+", " ", without_html).strip()


def truncate_text(value: str, limit: int = 360) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def canonical_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean).rstrip("/")


def parse_datetime(value: str | int | float | None) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
