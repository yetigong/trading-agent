"""Shared LLM retry classification and backoff helpers."""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

_RATE_LIMIT_MARKERS = (
    "429",
    "rate limit",
    "rate-limit",
    "quota",
    "too many requests",
    "resource_exhausted",
    "resource exhausted",
)

_AUTH_MARKERS = (
    "401",
    "403",
    "api key",
    "invalid_api_key",
    "authentication",
    "unauthorized",
    "permission denied",
)

_TRANSIENT_MARKERS = (
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "connection reset",
    "connection aborted",
)


def is_rate_limit_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def is_auth_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _AUTH_MARKERS)


def is_insufficient_quota_error(exc: BaseException) -> bool:
    """Billing/quota exhaustion — retries on the same key will not help."""
    return "insufficient_quota" in str(exc).lower()


def is_retryable_error(exc: BaseException) -> bool:
    if is_insufficient_quota_error(exc):
        return False
    return is_rate_limit_error(exc) or any(
        marker in str(exc).lower() for marker in _TRANSIENT_MARKERS
    )


def extract_retry_after_seconds(exc: BaseException) -> Optional[float]:
    """Parse Retry-After or provider retry_delay from an exception message."""
    text = str(exc)

    retry_after = re.search(r"retry[- ]after[:\s]*([0-9]+(?:\.[0-9]+)?)", text, re.I)
    if retry_after:
        return float(retry_after.group(1))

    please_retry = re.search(
        r"please retry in\s+([0-9]+(?:\.[0-9]+)?)\s*s",
        text,
        re.I,
    )
    if please_retry:
        return float(please_retry.group(1))

    delay_field = re.search(r"retry_delay\s*\{[^}]*seconds:\s*([0-9]+)", text, re.I)
    if delay_field:
        return float(delay_field.group(1))

    return None


def compute_backoff_seconds(
    attempt: int,
    exc: Optional[BaseException] = None,
    base_seconds: float = 1.0,
    max_seconds: float = 60.0,
) -> float:
    """Exponential backoff with jitter; prefer provider retry hint when present."""
    hinted = extract_retry_after_seconds(exc) if exc is not None else None
    if hinted is not None and hinted > 0:
        return min(max_seconds, hinted + random.uniform(0, 1.0))

    delay = base_seconds * (2 ** max(0, attempt - 1))
    delay = min(max_seconds, delay)
    return delay + random.uniform(0, 0.5)


def sleep_backoff(
    attempt: int,
    exc: Optional[BaseException] = None,
    *,
    sleeper=time.sleep,
) -> float:
    delay = compute_backoff_seconds(attempt, exc)
    logger.warning("LLM backoff sleeping %.2fs (attempt %s)", delay, attempt)
    sleeper(delay)
    return delay
