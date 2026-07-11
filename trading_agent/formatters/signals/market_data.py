from trading_agent.domain.signals.market_data import MarketDataPayload
from trading_agent.domain.signals.signal_source_result import SignalSourceResult


def format_market_data(source: SignalSourceResult) -> str:
    lines = [
        f"=== Signal Source: {source.source_id} ===",
        f"Status: {source.status.value} | Symbols: {', '.join(source.symbols) or 'N/A'}",
    ]
    if source.error:
        lines.append(f"Error: {source.error}")
        return "\n".join(lines)

    payload = source.payload
    if not isinstance(payload, MarketDataPayload):
        lines.append("No market data available.")
        return "\n".join(lines)

    lines.extend([
        f"- Volatility: {payload.volatility}",
        f"- Trend: {payload.trend}",
        f"- Economic Cycle: {payload.economic_cycle}",
        f"- Market Phase: {payload.market_phase}",
    ])
    if payload.sentiment:
        lines.append(f"- Sentiment: {payload.sentiment}")

    if payload.indices:
        lines.append("- Index Snapshot:")
        for idx in payload.indices:
            lines.append(
                f"  - {idx.symbol}: price={idx.current_price}, daily_change={idx.daily_change:.2f}%"
            )

    if payload.sector_etfs:
        lines.append("- Sector ETFs (daily change %):")
        for etf in payload.sector_etfs:
            lines.append(f"  - {etf.symbol}: {etf.daily_change:.2f}%")

    return "\n".join(lines)
