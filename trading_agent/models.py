import json
import re
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


@dataclass
class TradingDecision:
    action: str
    symbol: str
    quantity: Union[int, str]
    reasoning: str
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CycleResult:
    status: str
    analysis: Optional[Dict[str, Any]] = None
    analysis_strategy: Optional[str] = None
    market_conditions: Optional[Dict[str, Any]] = None
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    hold: bool = False
    rebalancing: Optional[Dict[str, Any]] = None
    executed_trades: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    cycle_id: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    """Extract and parse a JSON object from an LLM response."""
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
    """Parse structured trading decisions from an LLM JSON response."""
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


def format_market_conditions(conditions: Optional[Dict[str, Any]]) -> str:
    """Format market conditions for inclusion in LLM prompts."""
    if not conditions:
        return "Market conditions: unavailable"

    lines = [
        "Current Market Conditions:",
        f"- Volatility: {conditions.get('volatility', 'unknown')}",
        f"- Trend: {conditions.get('trend', 'unknown')}",
        f"- Economic Cycle: {conditions.get('economic_cycle', 'unknown')}",
        f"- Market Phase: {conditions.get('market_phase', 'unknown')}",
    ]

    indices = conditions.get("indices") or {}
    if indices:
        lines.append("- Index Snapshot:")
        for symbol, data in indices.items():
            if isinstance(data, dict):
                price = data.get("current_price", "N/A")
                change = data.get("daily_change", "N/A")
                lines.append(f"  - {symbol}: price={price}, daily_change={change}")

    return "\n".join(lines)


def format_trade_failure(error: Optional[str]) -> str:
    """Turn Alpaca/API error payloads into a short human-readable message."""
    if not error:
        return "unknown error"

    try:
        data = json.loads(error)
    except json.JSONDecodeError:
        return error

    if not isinstance(data, dict):
        return error

    message = data.get("message") or error
    if "available" in data and "existing_qty" in data:
        return (
            f"{message} "
            f"(owned: {data['existing_qty']}, available: {data['available']})"
        )
    if "buying_power" in data:
        return f"{message} (buying_power: ${data['buying_power']})"
    return message


def trade_result_detail(trade: Dict[str, Any]) -> str:
    """Detail column for a trade result row."""
    if trade.get("status") == "executed":
        order_id = trade.get("order_id")
        return f"order_id={order_id}" if order_id else "—"
    if trade.get("status") == "skipped":
        return trade.get("failure_detail") or "skipped"
    return trade.get("failure_detail") or format_trade_failure(trade.get("error"))


def serialize_for_json(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if is_dataclass(obj):
        return {k: serialize_for_json(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    return obj
