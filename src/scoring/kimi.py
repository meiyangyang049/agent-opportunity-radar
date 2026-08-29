from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any

from openai import OpenAI

from src.models import Candidate


SYSTEM_PROMPT = """你是月之暗面Kimi API商业化团队的销售情报分析师。
你的任务不是评价一个项目是否热门，而是判断它是否可能成为高价值模型API客户、生态伙伴或需要关注的竞品。
只能依据输入证据判断；信息不足时降低confidence，不得虚构融资、收入、用户数或合作关系。
OpenClaw型指开源Agent框架、开发者工具、可自托管平台或技能/插件生态；Manus型指面向终端用户或企业交付任务结果的商业Agent产品、Web/App服务或SaaS。
新闻文章只是发现信号的载体，candidate_name必须提取文章真正讨论的新产品或Agent项目，不能直接使用媒体标题或竞品价格标题。
请用简洁中文输出严格JSON，不要输出Markdown。"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _prompt(candidates: list[Candidate]) -> str:
    return json.dumps(
        {
            "projects": [candidate.to_dict() for candidate in candidates],
            "required_output": {
                "results": [
                    {
                        "id": "必须原样返回对应project.id",
                        "candidate_name": "真正的Agent产品或项目名；新闻中提取被报道对象",
                        "opportunity_type": "OpenClaw型|Manus型|其他Agent",
                        "score_adjustment": "-12到12之间的数字",
                        "recommended_action": "立即联系|持续观察|暂不跟进",
                        "reason_to_contact_now": "一句话，必须引用输入中的证据",
                        "commercial_summary": "一句话，说明对Kimi的客户/生态/竞品价值",
                        "confidence": "high|medium|low",
                    }
                ]
            },
        },
        ensure_ascii=False,
    )


def _apply_result(candidate: Candidate, result: dict[str, Any], model: str) -> None:
    adjustment = max(-12.0, min(12.0, float(result.get("score_adjustment", 0))))
    candidate.score = round(max(0.0, min(100.0, candidate.score + adjustment)), 1)
    candidate_name = str(result.get("candidate_name") or "").strip()
    if candidate.metadata.get("content_kind") == "news" and 1 < len(candidate_name) <= 100:
        candidate.name = candidate_name
    opportunity_type = result.get("opportunity_type")
    if opportunity_type in {"OpenClaw型", "Manus型", "其他Agent"}:
        candidate.opportunity_type = opportunity_type
    recommended_action = result.get("recommended_action")
    if recommended_action in {"立即联系", "持续观察", "暂不跟进"}:
        candidate.recommended_action = recommended_action
    candidate.reason_to_contact_now = result.get(
        "reason_to_contact_now", candidate.reason_to_contact_now
    )
    candidate.commercial_summary = result.get(
        "commercial_summary", candidate.commercial_summary
    )
    confidence = result.get("confidence", "medium")
    candidate.confidence = confidence if confidence in {"high", "medium", "low"} else "medium"
    candidate.scoring_mode = f"规则预评分 + {model}判断"


def apply_kimi_scores(
    candidates: list[Candidate], config: dict[str, Any]
) -> tuple[list[Candidate], str | None]:
    api_key = os.getenv("MOONSHOT_API_KEY")
    kimi_config = config["scoring"]["kimi"]
    if not kimi_config.get("enabled", True) or not api_key:
        return candidates, "未配置MOONSHOT_API_KEY，本次使用规则预评分。"

    client = OpenAI(api_key=api_key, base_url=kimi_config["base_url"])
    model = kimi_config["model"]
    max_candidates = min(len(candidates), int(kimi_config.get("max_candidates", 20)))
    batch_size = max(1, int(kimi_config.get("batch_size", 10)))
    errors: list[str] = []

    buckets = {
        "OpenClaw型": [item for item in candidates if item.opportunity_type == "OpenClaw型"],
        "Manus型": [item for item in candidates if item.opportunity_type == "Manus型"],
        "其他Agent": [item for item in candidates if item.opportunity_type == "其他Agent"],
    }
    selected: list[Candidate] = []
    while len(selected) < max_candidates and any(buckets.values()):
        for bucket in buckets.values():
            if bucket and len(selected) < max_candidates:
                selected.append(bucket.pop(0))
    for start in range(0, len(selected), batch_size):
        batch = selected[start : start + batch_size]
        try:
            kwargs: dict[str, Any] = {
                "response_format": {"type": "json_object"},
                "max_completion_tokens": int(
                    kimi_config.get("max_completion_tokens", 4096)
                ),
            }
            if model.startswith(("kimi-k2.5", "kimi-k2.6")):
                kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            else:
                kwargs["temperature"] = 0.2
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _prompt(batch)},
                ],
                **kwargs,
            )
            result = _extract_json(response.choices[0].message.content or "{}")
            raw_results = result.get("results")
            if not isinstance(raw_results, list):
                raise ValueError("Kimi batch response is missing results")
            results_by_id = {
                item.get("id"): item
                for item in raw_results
                if isinstance(item, dict) and item.get("id")
            }
            for candidate in batch:
                candidate_result = results_by_id.get(candidate.id)
                if not candidate_result:
                    errors.append(f"{candidate.name}: MissingResultError")
                    continue
                try:
                    _apply_result(candidate, candidate_result, model)
                except (TypeError, ValueError):
                    errors.append(f"{candidate.name}: InvalidResultError")
        except Exception as exc:
            errors.extend(f"{candidate.name}: {type(exc).__name__}" for candidate in batch)

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    if errors:
        error_types = Counter(error.rsplit(": ", 1)[-1] for error in errors)
        error_summary = "、".join(
            f"{error_type}×{count}" for error_type, count in error_types.most_common()
        )
        return candidates, (
            f"Kimi评分部分失败（{len(errors)}项：{error_summary}），已保留规则分数。"
        )
    return candidates, None
