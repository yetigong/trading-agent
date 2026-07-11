"""Compatibility shim — domain types and JSON parsing helpers."""

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from trading_agent.domain.cycle.trading_decision import TradingDecision
from trading_agent.formatters.market_conditions import format_market_conditions
from trading_agent.formatters.trades import format_trade_failure, trade_result_detail

# Re-export domain types for backward compatibility
__all__ = [
    "TradingDecision",
    "TRADING_DECISIONS_JSON_PROMPT",
    "extract_json_object",
    "format_market_conditions",
    "format_trade_failure",
    "parse_trading_decisions",
    "serialize_for_json",
    "trade_result_detail",
]


TRADING_DECISIONS_JSON_PROMPT = """
Respond with a JSON object only (no markdown fences), using this schema:
{
  "decisions": [
    {
      "action": "BUY" or "SELL",
      "symbol": "TICKER",
      "quantity": <integer or "ALL">,
      "reasoning": "<brief explanation>",
      "risk_level": "low" | "medium" | "high"
    }
  ]
}

If no trades are recommended, return {"decisions": []}.
"""


def extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")

    return json.loads(cleaned[start : end + 1])


def parse_trading_decisions(response: str) -> List[Dict[str, Any]]:
    payload = extract_json_object(response)
    raw_decisions = payload.get("decisions", [])
    if not isinstance(raw_decisions, list):
        raise ValueError("'decisions' must be a list")

    decisions = []
    for item in raw_decisions:
        if not isinstance(item, dict):
            continue
        decisions.append(
            {
                "action": str(item.get("action", "")).upper(),
                "symbol": str(item.get("symbol", "")).upper(),
                "quantity": item.get("quantity"),
                "reasoning": str(item.get("reasoning", "")),
                "risk_level": str(item.get("risk_level", "")).lower(),
            }
        )
    return decisions


def serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    return obj
