"""OpenAI GPT / reasoning model client."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import openai
from dotenv import load_dotenv

from trading_agent.llm.base import LLMClient

_JSON_SYSTEM_PROMPT = (
    "You are a trading assistant. Follow the user's schema exactly. "
    "When asked for JSON, respond with JSON only (no markdown fences)."
)


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""

    DEFAULT_MODEL = "o4-mini"

    AVAILABLE_MODELS = {
        "general": "o4-mini",
        "financial": "o4-mini",
        "reasoning": "o4-mini",
        "code": "gpt-4.1",
        "small": "gpt-4o-mini",
        "large": "o3",
    }

    def __init__(self, model: str = None, api_key: str = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        resolved = model or self.DEFAULT_MODEL
        self.model = self.AVAILABLE_MODELS.get(resolved, resolved)
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            formatted_prompt = self._format_prompt(prompt, context)
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _JSON_SYSTEM_PROMPT},
                    {"role": "user", "content": formatted_prompt},
                ],
            }
            # Reasoning models generally reject temperature; keep default for chat models.
            if not self._is_reasoning_model(self.model):
                kwargs["temperature"] = 0.7

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned empty content")
            return content
        except Exception as e:
            raise Exception(f"Error generating response from OpenAI: {str(e)}") from e

    @staticmethod
    def _is_reasoning_model(model: str) -> bool:
        name = (model or "").lower()
        return name.startswith(("o1", "o3", "o4")) or "reasoning" in name

    def _format_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not context:
            return prompt
        context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
        return f"Context:\n{context_str}\n\nTask:\n{prompt}"

    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        return {
            "general": "o4-mini reasoning model (default)",
            "financial": "o4-mini reasoning model (default)",
            "reasoning": "o4-mini reasoning model",
            "code": "gpt-4.1",
            "small": "gpt-4o-mini",
            "large": "o3 reasoning model",
        }
