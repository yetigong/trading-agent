from typing import Optional

from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.signals.sources import summarize_sector_rotation


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

    if conditions.sector_etfs:
        sector_summary = summarize_sector_rotation(conditions.sector_etfs)
        if sector_summary:
            lines.append(f"- Sector Rotation: {sector_summary}")
        lines.append("- Sector ETFs (5d vs SPY):")
        for symbol, data in conditions.sector_etfs.items():
            if isinstance(data, dict):
                vs_spy = data.get("vs_spy_5d", "N/A")
                ret_5d = data.get("return_5d", "N/A")
                lines.append(f"  - {symbol}: return_5d={ret_5d}%, vs_spy_5d={vs_spy}%")

    return "\n".join(lines)
