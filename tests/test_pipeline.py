from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.models import Candidate
from src.processing.pipeline import deduplicate, enrich_keywords, is_relevant
from src.scoring.kimi import apply_kimi_scores
from src.scoring.rules import apply_rule_score


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

    def test_kimi_k26_uses_supported_parameters(self) -> None:
        config = {
            "scoring": {
                "kimi": {
                    "enabled": True,
                    "model": "kimi-k2.6",
                    "max_candidates": 1,
                    "max_completion_tokens": 512,
                    "base_url": "https://api.moonshot.cn/v1",
                }
            }
        }
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"opportunity_type":"OpenClaw型","score_adjustment":3,'
                            '"recommended_action":"持续观察",'
                            '"reason_to_contact_now":"3000 GitHub stars",'
                            '"commercial_summary":"开发者生态机会",'
                            '"confidence":"medium"}'
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
        self.assertEqual(call_kwargs["max_completion_tokens"], 512)
        self.assertEqual(call_kwargs["extra_body"], {"thinking": {"type": "disabled"}})
        self.assertEqual(call_kwargs["response_format"], {"type": "json_object"})
        self.assertIn("kimi-k2.6", candidates[0].scoring_mode)


if __name__ == "__main__":
    unittest.main()
