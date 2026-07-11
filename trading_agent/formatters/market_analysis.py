from typing import Optional

from trading_agent.domain.cycle import MarketAnalysis
from trading_agent.domain.signals.market_signals import MarketSignals


def _format_technical_indicators(indicators: dict) -> str:
    if not indicators:
        return "unavailable"
    lines = []
    for symbol, data in indicators.items():
        if not isinstance(data, dict):
            continue
        parts = []
        if "rsi_14" in data:
            parts.append(f"RSI(14)={data['rsi_14']}")
        macd = data.get("macd")
        if isinstance(macd, dict):
            if macd.get("macd") is not None:
                parts.append(f"MACD={macd['macd']}")
            if macd.get("histogram") is not None:
                parts.append(f"hist={macd['histogram']}")
        if "sma_20" in data:
            parts.append(f"SMA20={data['sma_20']}")
        if "sma_50" in data:
            parts.append(f"SMA50={data['sma_50']}")
        if parts:
            lines.append(f"  {symbol}: {', '.join(parts)}")
    return "\n".join(lines) if lines else "unavailable"


def format_market_signals(signals: Optional[MarketSignals]) -> str:
    if not signals:
        return "Market signals: unavailable"

    lines = ["Market Signals:"]
    if signals.market_data.summary or signals.market_data.indices:
        lines.append(f"- Market Data: {signals.market_data.summary or 'indices available'}")
    if signals.market_data.sector_etfs:
        lines.append(f"- Sectors: {len(signals.market_data.sector_etfs)} sector ETFs tracked")
    if signals.technical.summary or signals.technical.indicators:
        lines.append(f"- Technical Summary: {signals.technical.summary}")
        if signals.technical.indicators:
            lines.append("- Technical Indicators:")
            lines.append(_format_technical_indicators(signals.technical.indicators))
    if signals.news.sentiment_summary or signals.news.headlines:
        lines.append(f"- News: {signals.news.sentiment_summary or f'{len(signals.news.headlines)} headlines'}")
        for headline in signals.news.headlines[:5]:
            title = headline.get("title", "")
            symbol = headline.get("symbol", "")
            prefix = f"[{symbol}] " if symbol else ""
            lines.append(f"  - {prefix}{title}")
    if signals.fundamentals.summary or signals.fundamentals.metrics:
        lines.append(f"- Fundamentals: {signals.fundamentals.summary or str(signals.fundamentals.metrics)}")
    return "\n".join(lines)


def format_market_analysis(analysis: Optional[MarketAnalysis]) -> str:
    if not analysis:
        return "Market analysis: unavailable"

    parts = [format_market_signals(analysis.signals)]
    for result in analysis.all_results():
        if result.status == "success" and result.summary:
            parts.append(f"### {result.strategy_name}\n{result.summary}")
        elif result.status == "failed":
            parts.append(f"### {result.strategy_name}\nAnalysis failed: {result.error or 'unknown error'}")
    return "\n\n".join(parts)
