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


def _prompt(candidate: Candidate) -> str:
    return json.dumps(
        {
            "project": candidate.to_dict(),
            "required_output": {
                "opportunity_type": "OpenClaw型|Manus型|其他Agent",
                "score_adjustment": "-12到12之间的数字",
                "recommended_action": "立即联系|持续观察|暂不跟进",
                "reason_to_contact_now": "一句话，必须引用输入中的证据",
                "commercial_summary": "一句话，说明对Kimi的客户/生态/竞品价值",
                "confidence": "high|medium|low",
            },
        },
        ensure_ascii=False,
    )


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
    errors: list[str] = []

    for candidate in candidates[:max_candidates]:
        try:
            kwargs: dict[str, Any] = {
                "response_format": {"type": "json_object"},
                "max_completion_tokens": int(
                    kimi_config.get("max_completion_tokens", 512)
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
                    {"role": "user", "content": _prompt(candidate)},
                ],
                **kwargs,
            )
            result = _extract_json(response.choices[0].message.content or "{}")
            adjustment = max(-12.0, min(12.0, float(result.get("score_adjustment", 0))))
            candidate.score = round(max(0.0, min(100.0, candidate.score + adjustment)), 1)
            candidate.opportunity_type = result.get("opportunity_type", candidate.opportunity_type)
            candidate.recommended_action = result.get(
                "recommended_action", candidate.recommended_action
            )
            candidate.reason_to_contact_now = result.get(
                "reason_to_contact_now", candidate.reason_to_contact_now
            )
            candidate.commercial_summary = result.get(
                "commercial_summary", candidate.commercial_summary
            )
            candidate.confidence = result.get("confidence", "medium")
            candidate.scoring_mode = f"规则预评分 + {model}判断"
        except Exception as exc:
            errors.append(f"{candidate.name}: {type(exc).__name__}")

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
