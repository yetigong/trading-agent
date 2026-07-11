from typing import Any, Dict, Optional


def format_market_conditions(conditions: Optional[Dict[str, Any]]) -> str:
    """Format market conditions dict for LLM prompts (Phase 1 compat)."""
    if not conditions:
        return "Market conditions: unavailable"

    lines = [
        "Current Market Conditions:",
        f"- Volatility: {conditions.get('volatility', 'unknown')}",
        f"- Trend: {conditions.get('trend', 'unknown')}",
        f"- Economic Cycle: {conditions.get('economic_cycle', 'unknown')}",
        f"- Market Phase: {conditions.get('market_phase', 'unknown')}",
    ]

    sentiment = conditions.get("sentiment")
    if sentiment:
        lines.append(f"- Sentiment: {sentiment}")

    indices = conditions.get("indices") or {}
    if indices:
        lines.append("- Index Snapshot:")
        for symbol, data in indices.items():
            if isinstance(data, dict):
                price = data.get("current_price", "N/A")
                change = data.get("daily_change", "N/A")
                lines.append(f"  - {symbol}: price={price}, daily_change={change}")

    sectors = conditions.get("sector_performance") or {}
    if sectors:
        lines.append("- Sector ETF Performance (daily %):")
        for symbol, change in sectors.items():
            lines.append(f"  - {symbol}: {change}")

    return "\n".join(lines)
