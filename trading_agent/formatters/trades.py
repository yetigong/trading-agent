import json
from typing import Any, Dict, Optional


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
    return trade.get("failure_detail") or format_trade_failure(trade.get("error"))
