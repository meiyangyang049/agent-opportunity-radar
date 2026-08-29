from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from src.models import Candidate
from src.utils import parse_datetime


DIMENSIONS = (
    "growth_speed",
    "agent_innovation",
    "community_signal",
    "api_consumption_potential",
    "commercialization",
    "kimi_strategic_fit",
)


def _bounded(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _age_days(candidate: Candidate) -> float:
    created = parse_datetime(candidate.published_at)
    if not created:
        return 7.0
    return max(1.0, (datetime.now(timezone.utc) - created).total_seconds() / 86400)


def _classify_type(candidate: Candidate) -> str:
    text = f"{candidate.name} {candidate.description} {candidate.raw_text}".lower()
    ecosystem_hits = candidate.metadata.get("ecosystem_keyword_hits", [])
    if candidate.source == "GitHub" or "open source" in text or "self-hosted" in text:
        return "OpenClaw型"
    if any(term in text for term in ("launch", "waitlist", "subscription", "pricing")):
        return "Manus型"
    if ecosystem_hits and any(term in text for term in ("skill", "plugin", "framework")):
        return "OpenClaw型"
    return "其他Agent"


def dimension_scores(candidate: Candidate) -> dict[str, float]:
    agent_hits = len(candidate.metadata.get("agent_keyword_hits", []))
    commercial_hits = len(candidate.metadata.get("commercial_keyword_hits", []))
    ecosystem_hits = len(candidate.metadata.get("ecosystem_keyword_hits", []))
    stars = float(candidate.metrics.get("stars", 0))
    forks = float(candidate.metrics.get("forks", 0))
    points = float(candidate.metrics.get("points", 0))
    comments = float(candidate.metrics.get("comments", 0))
    age = _age_days(candidate)
    stars_per_day = stars / age
    observed_velocity = float(candidate.metadata.get("metric_velocity_per_day", 0))

    growth = 22 + math.log1p(stars_per_day) * 15 + math.log1p(points) * 8
    if observed_velocity > 0:
        growth = max(growth, 30 + math.log1p(observed_velocity) * 18)
    innovation = 24 + agent_hits * 11 + (10 if "tool calling" in candidate.raw_text.lower() else 0)
    community = 18 + math.log1p(stars + points * 3) * 11 + math.log1p(forks + comments) * 8
    api_potential = 25 + agent_hits * 7 + commercial_hits * 5
    if any(term in candidate.raw_text.lower() for term in ("multi-agent", "computer use", "browser agent")):
        api_potential += 18
    commercialization = 18 + commercial_hits * 14
    kimi_fit = 25 + agent_hits * 6 + ecosystem_hits * 8
    if candidate.source in ("GitHub", "Hacker News"):
        kimi_fit += 8

    return {
        "growth_speed": _bounded(growth),
        "agent_innovation": _bounded(innovation),
        "community_signal": _bounded(community),
        "api_consumption_potential": _bounded(api_potential),
        "commercialization": _bounded(commercialization),
        "kimi_strategic_fit": _bounded(kimi_fit),
    }


def apply_rule_score(candidate: Candidate, config: dict[str, Any]) -> Candidate:
    scores = dimension_scores(candidate)
    weights = config["scoring"]["weights"]
    total = sum(scores[dimension] * float(weights[dimension]) for dimension in DIMENSIONS)
    thresholds = config["scoring"]["action_thresholds"]
    if total >= float(thresholds["contact_now"]):
        action = "立即联系"
    elif total >= float(thresholds["watch"]):
        action = "持续观察"
    else:
        action = "暂不跟进"

    candidate.dimension_scores = scores
    candidate.score = round(total, 1)
    candidate.opportunity_type = _classify_type(candidate)
    candidate.recommended_action = action
    candidate.reason_to_contact_now = _rule_reason(candidate)
    candidate.commercial_summary = _rule_summary(candidate)
    candidate.scoring_mode = "规则预评分"
    return candidate


def _rule_reason(candidate: Candidate) -> str:
    evidence = [item for item in candidate.evidence if item]
    hits = candidate.metadata.get("agent_keyword_hits", [])[:3]
    if hits:
        evidence.append("Agent signals: " + ", ".join(hits))
    return "；".join(evidence[:3]) or "出现与Agent产品相关的早期公开信号"


def _rule_summary(candidate: Candidate) -> str:
    commercial_hits = candidate.metadata.get("commercial_keyword_hits", [])
    if candidate.opportunity_type == "OpenClaw型":
        return "开发者生态型机会，优先判断模型接入、默认Provider和联合社区合作空间。"
    if candidate.opportunity_type == "Manus型":
        return "产品型机会，优先判断API调用规模、付费增长和战略客户合作空间。"
    if commercial_hits:
        return "已出现商业化信号，建议补充产品、团队和模型依赖信息后继续评估。"
    return "当前信号较早，建议观察用户增速、模型依赖和商业化动作。"


def score_all(candidates: list[Candidate], config: dict[str, Any]) -> list[Candidate]:
    scored = [apply_rule_score(candidate, config) for candidate in candidates]
    return sorted(scored, key=lambda candidate: candidate.score, reverse=True)
