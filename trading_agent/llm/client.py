"""LLM client factory."""

from __future__ import annotations

import logging
import os
from typing import Optional

from trading_agent.llm.base import LLMClient
from trading_agent.llm.claude_client import ClaudeClient
from trading_agent.llm.failover_client import FailoverLLMClient
from trading_agent.llm.gemini_client import GeminiClient
from trading_agent.llm.huggingface_client import HuggingFaceClient
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.llm.openai_client import OpenAIClient

__all__ = [
    "LLMClient",
    "get_llm_client",
    "build_llm_client",
    "FailoverLLMClient",
]

logger = logging.getLogger(__name__)

_CLIENTS = {
    "openai": OpenAIClient,
    "huggingface": HuggingFaceClient,
    "claude": ClaudeClient,
    "gemini": GeminiClient,
    "mock": MockLLMClient,
}


def get_llm_client(client_type: str = "claude", **kwargs) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.

    Args:
        client_type: Type of LLM client ("openai", "huggingface", "claude", "gemini", or "mock")
        **kwargs: Additional arguments to pass to the client constructor

    Returns:
        An instance of the requested LLM client
    """
    client_type = (client_type or "").lower()
    if client_type not in _CLIENTS:
        raise ValueError(f"Unsupported LLM client type: {client_type}")
    return _CLIENTS[client_type](**kwargs)


def build_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
    max_retries: int = 3,
) -> LLMClient:
    """
    Build a single-provider or primary/secondary failover LLM client.

    Defaults come from environment when args are omitted:
    LLM_PROVIDER (default openai), LLM_MODEL, LLM_FALLBACK_PROVIDER (default gemini),
    LLM_FALLBACK_MODEL, LLM_MAX_RETRIES.
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
    model = model if model is not None else os.getenv("LLM_MODEL", "financial")

    fallback_raw = (
        fallback_provider
        if fallback_provider is not None
        else os.getenv("LLM_FALLBACK_PROVIDER", "gemini")
    )
    fallback_provider = (fallback_raw or "").strip().lower() or None
    if fallback_provider in ("none", "off", "disabled"):
        fallback_provider = None

    fallback_model = (
        fallback_model
        if fallback_model is not None
        else os.getenv("LLM_FALLBACK_MODEL", "financial")
    )
    try:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", str(max_retries)))
    except ValueError:
        max_retries = 3

    primary = get_llm_client(provider, model=model)
    if not fallback_provider or fallback_provider == provider:
        return primary

    secondary = get_llm_client(fallback_provider, model=fallback_model)
    logger.info(
        "LLM failover enabled: primary=%s/%s secondary=%s/%s max_retries=%s",
        provider,
        model,
        fallback_provider,
        fallback_model,
        max_retries,
    )
    return FailoverLLMClient(
        primary=primary,
        secondary=secondary,
        max_retries=max_retries,
        primary_name=provider,
        secondary_name=fallback_provider,
    )
