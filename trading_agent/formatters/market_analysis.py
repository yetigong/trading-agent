from typing import Optional

from trading_agent.domain.cycle import MarketAnalysis
from trading_agent.domain.signals.market_signals import MarketSignals


def format_market_signals(signals: Optional[MarketSignals]) -> str:
    if not signals:
        return "Market signals: unavailable"

    lines = ["Market Signals:"]
    if signals.market_data.summary or signals.market_data.indices:
        lines.append(f"- Market Data: {signals.market_data.summary or 'indices available'}")
    if signals.technical.summary or signals.technical.indicators:
        lines.append(f"- Technical: {signals.technical.summary or str(signals.technical.indicators)}")
    if signals.news.sentiment_summary or signals.news.headlines:
        lines.append(f"- News: {signals.news.sentiment_summary or f'{len(signals.news.headlines)} headlines'}")
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
