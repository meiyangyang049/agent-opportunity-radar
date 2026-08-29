from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Candidate:
    id: str
    source: str
    name: str
    url: str
    description: str
    published_at: str = ""
    discovered_at: str = field(default_factory=utc_now_iso)
    author: str = ""
    metrics: dict[str, float | int] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    raw_text: str = ""
    opportunity_type: str = "其他Agent"
    score: float = 0.0
    dimension_scores: dict[str, float] = field(default_factory=dict)
    recommended_action: str = "暂不跟进"
    reason_to_contact_now: str = ""
    commercial_summary: str = ""
    confidence: str = "medium"
    scoring_mode: str = "rules"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Candidate":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in payload.items() if key in allowed})

