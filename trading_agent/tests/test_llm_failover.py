"""Tests for FailoverLLMClient retry and provider failover."""

import unittest
from typing import Any, Dict, List, Optional

from trading_agent.llm.base import LLMClient
from trading_agent.llm.failover_client import FailoverLLMClient
from trading_agent.llm.retry import (
    compute_backoff_seconds,
    extract_retry_after_seconds,
    is_auth_error,
    is_insufficient_quota_error,
    is_rate_limit_error,
    is_retryable_error,
)


class ScriptedLLM(LLMClient):
    def __init__(self, outcomes: List[Any], name: str = "scripted"):
        self.outcomes = list(outcomes)
        self.name = name
        self.calls = 0

    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        self.calls += 1
        if not self.outcomes:
            raise RuntimeError(f"{self.name} has no scripted outcomes left")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return str(outcome)


class TestRetryHelpers(unittest.TestCase):
    def test_detect_rate_limit_and_retry_after(self):
        exc = Exception("429 Please retry in 37.25s. Quota exceeded")
        self.assertTrue(is_rate_limit_error(exc))
        self.assertAlmostEqual(extract_retry_after_seconds(exc), 37.25)
        delay = compute_backoff_seconds(1, exc, max_seconds=60)
        self.assertGreaterEqual(delay, 37.25)
        self.assertLessEqual(delay, 39.0)

    def test_detect_auth(self):
        self.assertTrue(is_auth_error(Exception("401 invalid_api_key")))

    def test_insufficient_quota_is_not_retryable(self):
        exc = Exception(
            "Error code: 429 - {'error': {'type': 'insufficient_quota', "
            "'code': 'insufficient_quota'}}"
        )
        self.assertTrue(is_insufficient_quota_error(exc))
        self.assertTrue(is_rate_limit_error(exc))
        self.assertFalse(is_retryable_error(exc))


class TestFailoverLLMClient(unittest.TestCase):
    def test_primary_succeeds_after_retry(self):
        sleeps: List[float] = []
        primary = ScriptedLLM(
            [Exception("429 rate limit"), "ok-primary"],
            name="openai",
        )
        secondary = ScriptedLLM(["ok-secondary"], name="gemini")
        client = FailoverLLMClient(
            primary,
            secondary,
            max_retries=3,
            primary_name="openai",
            secondary_name="gemini",
            sleeper=sleeps.append,
        )
        self.assertEqual(client.generate_response("prompt"), "ok-primary")
        self.assertEqual(primary.calls, 2)
        self.assertEqual(secondary.calls, 0)
        self.assertEqual(client.last_provider, "openai")
        self.assertEqual(len(sleeps), 1)

    def test_failover_to_secondary_after_primary_exhausted(self):
        sleeps: List[float] = []
        primary = ScriptedLLM(
            [Exception("429 quota"), Exception("429 quota"), Exception("429 quota")],
            name="openai",
        )
        secondary = ScriptedLLM(["ok-secondary"], name="gemini")
        client = FailoverLLMClient(
            primary,
            secondary,
            max_retries=3,
            primary_name="openai",
            secondary_name="gemini",
            sleeper=sleeps.append,
        )
        self.assertEqual(client.generate_response("prompt"), "ok-secondary")
        self.assertEqual(primary.calls, 3)
        self.assertEqual(secondary.calls, 1)
        self.assertEqual(client.failover_count, 1)
        self.assertEqual(client.last_provider, "gemini")
        self.assertEqual(len(sleeps), 2)

    def test_both_exhausted_raises(self):
        primary = ScriptedLLM(
            [Exception("429 a"), Exception("429 b"), Exception("429 c")],
            name="openai",
        )
        secondary = ScriptedLLM(
            [Exception("429 d"), Exception("429 e"), Exception("429 f")],
            name="gemini",
        )
        client = FailoverLLMClient(
            primary,
            secondary,
            max_retries=3,
            sleeper=lambda _delay: None,
        )
        with self.assertRaises(Exception):
            client.generate_response("prompt")
        self.assertEqual(primary.calls, 3)
        self.assertEqual(secondary.calls, 3)

    def test_non_retryable_primary_moves_to_secondary(self):
        primary = ScriptedLLM([Exception("401 unauthorized api key")], name="openai")
        secondary = ScriptedLLM(["ok-secondary"], name="gemini")
        client = FailoverLLMClient(
            primary,
            secondary,
            max_retries=3,
            primary_name="openai",
            secondary_name="gemini",
            sleeper=lambda _delay: None,
        )
        self.assertEqual(client.generate_response("prompt"), "ok-secondary")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(secondary.calls, 1)
        self.assertEqual(client.failover_count, 1)

    def test_insufficient_quota_fails_over_without_retries(self):
        sleeps: List[float] = []
        primary = ScriptedLLM(
            [Exception("429 insufficient_quota")],
            name="openai",
        )
        secondary = ScriptedLLM(["ok-secondary"], name="gemini")
        client = FailoverLLMClient(
            primary,
            secondary,
            max_retries=3,
            primary_name="openai",
            secondary_name="gemini",
            sleeper=sleeps.append,
        )
        self.assertEqual(client.generate_response("prompt"), "ok-secondary")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(secondary.calls, 1)
        self.assertEqual(sleeps, [])


if __name__ == "__main__":
    unittest.main()
