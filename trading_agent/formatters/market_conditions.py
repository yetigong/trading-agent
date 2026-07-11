from typing import Optional

from trading_agent.domain.signals.market_conditions import MarketConditions


def format_market_conditions(conditions: Optional[MarketConditions]) -> str:
    if not conditions:
        return "Market conditions: unavailable"

    lines = [
        "Current Market Conditions:",
        f"- Volatility: {conditions.volatility}",
        f"- Trend: {conditions.trend}",
        f"- Economic Cycle: {conditions.economic_cycle}",
        f"- Market Phase: {conditions.market_phase}",
    ]

    if conditions.indices:
        lines.append("- Index Snapshot:")
        for symbol, data in conditions.indices.items():
            if isinstance(data, dict):
                price = data.get("current_price", "N/A")
                change = data.get("daily_change", "N/A")
                lines.append(f"  - {symbol}: price={price}, daily_change={change}%")

    return "\n".join(lines)
