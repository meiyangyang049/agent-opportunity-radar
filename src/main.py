from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from src.collectors.all_sources import collect_all
from src.models import Candidate
from src.processing.pipeline import enrich_keywords, prepare_candidates, select_shortlist
from src.reporting.html import generate_html
from src.scoring.kimi import apply_kimi_scores
from src.scoring.rules import score_all


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_demo(path: str | Path, config: dict[str, Any]) -> list[Candidate]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return [enrich_keywords(Candidate.from_dict(item), config) for item in payload]


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _primary_metric(candidate: Candidate) -> tuple[str, float]:
    for name in ("stars", "points", "comments", "forks"):
        if name in candidate.metrics:
            return name, float(candidate.metrics[name])
    return "none", 0.0


def load_previous_history(path: str | Path) -> dict[str, dict[str, str]]:
    target = Path(path)
    if not target.exists():
        return {}
    latest: dict[str, dict[str, str]] = {}
    with target.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            latest[row["id"]] = row
    return latest


def apply_history_signals(
    candidates: list[Candidate], previous: dict[str, dict[str, str]], run_at: datetime
) -> None:
    for candidate in candidates:
        prior = previous.get(candidate.id)
        if not prior or not prior.get("metric_value"):
            continue
        metric_name, metric_value = _primary_metric(candidate)
        if metric_name == "none" or prior.get("metric_name") != metric_name:
            continue
        try:
            prior_value = float(prior["metric_value"])
            prior_time = datetime.fromisoformat(prior["run_at"])
            elapsed_days = max((run_at - prior_time).total_seconds() / 86400, 1 / 24)
        except (ValueError, TypeError):
            continue
        delta = metric_value - prior_value
        candidate.metadata["metric_delta"] = delta
        candidate.metadata["metric_velocity_per_day"] = max(0.0, delta / elapsed_days)
        if delta > 0:
            candidate.evidence.insert(0, f"+{delta:,.0f} {metric_name} since last run")


def append_history(path: str | Path, candidates: list[Candidate], run_at: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    exists = target.exists()
    fields = [
        "run_at",
        "id",
        "name",
        "source",
        "score",
        "opportunity_type",
        "recommended_action",
        "metric_name",
        "metric_value",
    ]
    with target.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        for candidate in candidates:
            metric_name, metric_value = _primary_metric(candidate)
            writer.writerow(
                {
                    "run_at": run_at,
                    "id": candidate.id,
                    "name": candidate.name,
                    "source": candidate.source,
                    "score": candidate.score,
                    "opportunity_type": candidate.opportunity_type,
                    "recommended_action": candidate.recommended_action,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                }
            )


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = ROOT / args.config
    config = load_config(config_path)
    warnings: list[str] = []

    if args.demo:
        candidates = load_demo(ROOT / "fixtures/demo_candidates.json", config)
        mode = "演示/历史校准数据"
        notices = ["当前页面含明确标注的演示数据，用于验证流程与页面；真实运行后会被公开信号替换。"]
    else:
        raw_candidates, source_warnings = collect_all(config)
        warnings.extend(source_warnings)
        raw_path = ROOT / "data/raw/latest.json"
        write_json(raw_path, {"candidates": [item.to_dict() for item in raw_candidates]})
        candidates = prepare_candidates(raw_candidates, config)
        mode = "公开信号实时运行"
        notices = []

    history_path = ROOT / config["output"]["history_csv"]
    run_datetime = datetime.now(timezone.utc).replace(microsecond=0)
    apply_history_signals(candidates, load_previous_history(history_path), run_datetime)
    candidates = score_all(candidates, config)
    if not args.no_kimi:
        candidates, kimi_notice = apply_kimi_scores(candidates, config)
        if kimi_notice:
            notices.append(kimi_notice)
    else:
        notices.append("已通过--no-kimi关闭Kimi判断，本次仅使用规则预评分。")

    top_n = int(config["project"].get("top_n", 10))
    min_per_archetype = int(config["project"].get("min_per_archetype", 4))
    top_candidates = select_shortlist(candidates, top_n, min_per_archetype)
    pool_by_source: dict[str, int] = {}
    pool_by_type: dict[str, int] = {}
    for candidate in candidates:
        pool_by_source[candidate.source] = pool_by_source.get(candidate.source, 0) + 1
        pool_by_type[candidate.opportunity_type] = (
            pool_by_type.get(candidate.opportunity_type, 0) + 1
        )
    if not pool_by_type.get("Manus型"):
        notices.append("本期候选池未发现达到相关性门槛的Manus型项目，请检查产品源覆盖。")
    generated_at = run_datetime.isoformat()
    display_timezone = ZoneInfo(config["project"].get("timezone", "Asia/Shanghai"))
    payload = {
        "meta": {
            "project": config["project"]["name"],
            "generated_at": generated_at,
            "generated_at_display": run_datetime.astimezone(display_timezone).strftime(
                "%Y-%m-%d %H:%M %Z"
            ),
            "mode": mode,
            "sources": ["GitHub", "Hacker News", "Product Hunt", "AI news RSS"],
            "warnings": warnings,
            "notices": notices,
            "candidate_pool_size": len(candidates),
            "pool_by_source": pool_by_source,
            "pool_by_type": pool_by_type,
            "shortlist_policy": f"Top {top_n}；OpenClaw型/Manus型各至少{min_per_archetype}个（候选充足时）",
            "kimi_model": config["scoring"]["kimi"]["model"],
        },
        "candidates": [candidate.to_dict() for candidate in top_candidates],
    }

    json_path = ROOT / config["output"]["data_json"]
    html_path = ROOT / config["output"]["html"]
    write_json(json_path, payload)
    append_history(history_path, top_candidates, generated_at)
    generate_html(payload, html_path)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect emerging AI agent opportunities.")
    parser.add_argument("--config", default="config.yaml", help="Config path relative to repository root")
    parser.add_argument("--demo", action="store_true", help="Use clearly labelled demo/calibration data")
    parser.add_argument("--no-kimi", action="store_true", help="Skip Kimi API and use deterministic rules")
    return parser


def main() -> None:
    payload = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": payload["meta"]["mode"],
                "candidates": len(payload["candidates"]),
                "output": "docs/index.html",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
