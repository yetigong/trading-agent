"""Primary/secondary LLM client with per-provider retry backoff."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from trading_agent.llm.base import LLMClient
from trading_agent.llm.retry import (
    is_auth_error,
    is_retryable_error,
    sleep_backoff,
)

logger = logging.getLogger(__name__)


class FailoverLLMClient(LLMClient):
    """Try primary with retries, then secondary with retries."""

    def __init__(
        self,
        primary: LLMClient,
        secondary: Optional[LLMClient] = None,
        *,
        max_retries: int = 3,
        primary_name: str = "primary",
        secondary_name: str = "secondary",
        sleeper=None,
    ):
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self.primary = primary
        self.secondary = secondary
        self.max_retries = max_retries
        self.primary_name = primary_name
        self.secondary_name = secondary_name
        self._sleeper = sleeper
        self.last_provider: Optional[str] = None
        self.failover_count = 0
        self.primary_failures = 0
        self.secondary_failures = 0

    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        providers = [(self.primary_name, self.primary)]
        if self.secondary is not None:
            providers.append((self.secondary_name, self.secondary))

        errors: list[str] = []
        for index, (name, client) in enumerate(providers):
            try:
                text = self._generate_with_retries(name, client, prompt, context)
                self.last_provider = name
                if index > 0:
                    self.failover_count += 1
                return text
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                if index == 0:
                    self.primary_failures += 1
                    if self.secondary is not None:
                        logger.warning(
                            "LLM primary (%s) exhausted; failing over to %s: %s",
                            name,
                            self.secondary_name,
                            exc,
                        )
                        continue
                else:
                    self.secondary_failures += 1
                raise

        raise Exception(
            "All LLM providers failed: " + "; ".join(errors) if errors else "No LLM providers"
        )

    def _generate_with_retries(
        self,
        name: str,
        client: LLMClient,
        prompt: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return client.generate_response(prompt, context)
            except Exception as exc:
                last_exc = exc
                if is_auth_error(exc) or not is_retryable_error(exc):
                    logger.error("LLM %s non-retryable error: %s", name, exc)
                    raise
                if attempt >= self.max_retries:
                    logger.error(
                        "LLM %s exhausted %s retries: %s",
                        name,
                        self.max_retries,
                        exc,
                    )
                    raise
                logger.warning(
                    "LLM %s attempt %s/%s failed (%s); backing off",
                    name,
                    attempt,
                    self.max_retries,
                    exc,
                )
                kwargs = {}
                if self._sleeper is not None:
                    kwargs["sleeper"] = self._sleeper
                sleep_backoff(attempt, exc, **kwargs)

        assert last_exc is not None
        raise last_exc

    def stats(self) -> Dict[str, Any]:
        return {
            "last_provider": self.last_provider,
            "failover_count": self.failover_count,
            "primary_failures": self.primary_failures,
            "secondary_failures": self.secondary_failures,
            "primary_name": self.primary_name,
            "secondary_name": self.secondary_name,
            "max_retries": self.max_retries,
        }
