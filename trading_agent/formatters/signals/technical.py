from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.technical import TechnicalPayload


def format_technical(source: SignalSourceResult) -> str:
    lines = [
        f"=== Signal Source: {source.source_id} ===",
        f"Status: {source.status.value} | Symbols: {', '.join(source.symbols) or 'N/A'}",
    ]
    if source.error:
        lines.append(f"Error: {source.error}")
        return "\n".join(lines)

    payload = source.payload
    if not isinstance(payload, TechnicalPayload) or not payload.symbols:
        lines.append("No technical indicator data available.")
        return "\n".join(lines)

    for ind in payload.symbols:
        rsi = f"{ind.rsi:.1f}" if ind.rsi is not None else "N/A"
        macd = f"{ind.macd:.3f}" if ind.macd is not None else "N/A"
        lines.append(
            f"- {ind.symbol}: trend={ind.trend}, RSI={rsi}, MACD={macd}, "
            f"SMA20={ind.sma20 or 'N/A'}, SMA50={ind.sma50 or 'N/A'}"
        )

    return "\n".join(lines)
