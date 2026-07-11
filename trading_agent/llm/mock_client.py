import json
from typing import Dict, Any, Optional

from .base import LLMClient


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and development."""

    def __init__(self, responses: Dict[str, str] = None, smart_defaults: bool = True):
        self.responses = responses or {}
        self.smart_defaults = smart_defaults

    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        if prompt in self.responses:
            return self.responses[prompt]

        if not self.smart_defaults:
            return "This is a mock response. Please implement actual LLM integration."

        prompt_lower = prompt.lower()

        if "select the most appropriate strategy" in prompt_lower:
            return "general"

        if "rebalancing plan" in prompt_lower and "specific orders" not in prompt_lower:
            return (
                "1. Target Allocation\nBalanced portfolio\n"
                "2. Required Changes\nNo changes needed\n"
                "3. Reasoning\nPortfolio is within target allocation"
            )

        if "specific orders" in prompt_lower:
            return ""

        if '"decisions"' in prompt_lower or "json object only" in prompt_lower:
            return json.dumps(
                {
                    "decisions": [
                        {
                            "action": "BUY",
                            "symbol": "AAPL",
                            "quantity": 1,
                            "reasoning": "Mock integration test buy signal",
                            "risk_level": "low",
                        }
                    ]
                }
            )

        if "comprehensive market analysis" in prompt_lower or "market analysis" in prompt_lower:
            return (
                "1. Market Overview\nMarkets are stable with moderate bullish trend.\n"
                "2. Sector Analysis\nTechnology showing strength.\n"
                "3. Risk Assessment\nLow to moderate risk.\n"
                "4. Opportunities\nLarge-cap tech names.\n"
                "5. Trading Recommendations\nHold current positions."
            )

        return "Mock LLM response"
