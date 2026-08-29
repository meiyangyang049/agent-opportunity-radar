from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.models import Candidate
from src.processing.pipeline import deduplicate, enrich_keywords, is_relevant, select_shortlist
from src.scoring.kimi import apply_kimi_scores
from src.scoring.rules import apply_rule_score
from src.utils import clean_text, truncate_text


CONFIG = {
    "keywords": {
        "agent": ["ai agent", "browser agent", "tool calling", "multi-agent"],
        "commercialization": ["pricing", "enterprise", "api", "subscription"],
        "ecosystem": ["open source", "plugin", "skill", "self-hosted"],
    },
    "scoring": {
        "weights": {
            "growth_speed": 0.25,
            "agent_innovation": 0.20,
            "community_signal": 0.20,
            "api_consumption_potential": 0.15,
            "commercialization": 0.10,
            "kimi_strategic_fit": 0.10,
        },
        "action_thresholds": {"contact_now": 75, "watch": 55},
    },
}


class PipelineTests(unittest.TestCase):
    def candidate(self, **overrides) -> Candidate:
        values = {
            "id": "github-1",
            "source": "GitHub",
            "name": "Agent Gateway",
            "url": "https://github.com/example/agent-gateway",
            "description": "Open source AI agent with plugins and tool calling",
            "metrics": {"stars": 3000, "forks": 350},
            "raw_text": "open source ai agent plugin tool calling API enterprise pricing",
        }
        values.update(overrides)
        return Candidate(**values)

    def test_agent_keywords_make_candidate_relevant(self) -> None:
        candidate = enrich_keywords(self.candidate(), CONFIG)
        self.assertTrue(is_relevant(candidate))
        self.assertIn("ai agent", candidate.metadata["agent_keyword_hits"])

    def test_rule_score_is_bounded_and_actionable(self) -> None:
        candidate = enrich_keywords(self.candidate(), CONFIG)
        scored = apply_rule_score(candidate, CONFIG)
        self.assertGreaterEqual(scored.score, 0)
        self.assertLessEqual(scored.score, 100)
        self.assertIn(scored.recommended_action, {"立即联系", "持续观察", "暂不跟进"})
        self.assertEqual(scored.opportunity_type, "OpenClaw型")

    def test_deduplication_uses_canonical_url(self) -> None:
        first = self.candidate(id="one")
        second = self.candidate(id="two", url=first.url + "?utm_source=test")
        self.assertEqual(len(deduplicate([first, second])), 1)

    def test_shortlist_reserves_both_primary_archetypes(self) -> None:
        open_candidates = [
            self.candidate(id=f"open-{index}", score=90 - index, opportunity_type="OpenClaw型")
            for index in range(8)
        ]
        manus_candidates = [
            self.candidate(id=f"manus-{index}", score=60 - index, opportunity_type="Manus型")
            for index in range(5)
        ]
        shortlist = select_shortlist(open_candidates + manus_candidates, 10, 4)
        self.assertEqual(len(shortlist), 10)
        self.assertGreaterEqual(
            sum(item.opportunity_type == "Manus型" for item in shortlist), 4
        )

    def test_feed_text_is_unescaped_and_bounded(self) -> None:
        cleaned = clean_text("<p>Anthropic&#x27;s &amp; Goose</p>")
        self.assertEqual(cleaned, "Anthropic's & Goose")
        self.assertEqual(len(truncate_text("x" * 500, 100)), 100)

    def test_kimi_k26_uses_supported_parameters(self) -> None:
        config = {
            "scoring": {
                "kimi": {
                    "enabled": True,
                    "model": "kimi-k2.6",
                    "max_candidates": 1,
                    "batch_size": 10,
                    "max_completion_tokens": 4096,
                    "base_url": "https://api.moonshot.cn/v1",
                }
            }
        }
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"results":[{"id":"github-1",'
                            '"candidate_name":"Agent Gateway",'
                            '"opportunity_type":"OpenClaw型","score_adjustment":3,'
                            '"recommended_action":"持续观察",'
                            '"reason_to_contact_now":"3000 GitHub stars",'
                            '"commercial_summary":"开发者生态机会",'
                            '"confidence":"medium"}]}'
                        )
                    )
                )
            ]
        )

        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-key"}), patch(
            "src.scoring.kimi.OpenAI"
        ) as openai_client:
            openai_client.return_value.chat.completions.create.return_value = response
            candidates, notice = apply_kimi_scores([self.candidate()], config)

        call_kwargs = openai_client.return_value.chat.completions.create.call_args.kwargs
        self.assertIsNone(notice)
        self.assertNotIn("temperature", call_kwargs)
        self.assertEqual(call_kwargs["max_completion_tokens"], 4096)
        self.assertEqual(call_kwargs["extra_body"], {"thinking": {"type": "disabled"}})
        self.assertEqual(call_kwargs["response_format"], {"type": "json_object"})
        self.assertIn("kimi-k2.6", candidates[0].scoring_mode)

    def test_kimi_batches_twenty_candidates_into_two_requests(self) -> None:
        config = {
            "scoring": {
                "kimi": {
                    "enabled": True,
                    "model": "kimi-k2.6",
                    "max_candidates": 20,
                    "batch_size": 10,
                    "max_completion_tokens": 4096,
                    "base_url": "https://api.moonshot.cn/v1",
                }
            }
        }
        candidates = [
            self.candidate(id=f"github-{index}", name=f"Agent {index}")
            for index in range(20)
        ]

        def response_for_call(*args, **kwargs):
            projects = __import__("json").loads(kwargs["messages"][1]["content"])["projects"]
            results = [
                {
                    "id": project["id"],
                    "candidate_name": project["name"],
                    "opportunity_type": "OpenClaw型",
                    "score_adjustment": 1,
                    "recommended_action": "持续观察",
                    "reason_to_contact_now": "公开证据",
                    "commercial_summary": "生态机会",
                    "confidence": "medium",
                }
                for project in projects
            ]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=__import__("json").dumps({"results": results})
                        )
                    )
                ]
            )

        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-key"}), patch(
            "src.scoring.kimi.OpenAI"
        ) as openai_client:
            create = openai_client.return_value.chat.completions.create
            create.side_effect = response_for_call
            scored, notice = apply_kimi_scores(candidates, config)

        self.assertIsNone(notice)
        self.assertEqual(create.call_count, 2)
        self.assertTrue(all("kimi-k2.6" in item.scoring_mode for item in scored))


if __name__ == "__main__":
    unittest.main()
