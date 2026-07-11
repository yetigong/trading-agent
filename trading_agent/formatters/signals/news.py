from trading_agent.domain.signals.news import NewsPayload
from trading_agent.domain.signals.signal_source_result import SignalSourceResult


def format_news(source: SignalSourceResult) -> str:
    lines = [
        f"=== Signal Source: {source.source_id} ===",
        f"Status: {source.status.value} | Symbols: {', '.join(source.symbols) or 'N/A'}",
    ]
    if source.error:
        lines.append(f"Error: {source.error}")
        return "\n".join(lines)

    payload = source.payload
    if not isinstance(payload, NewsPayload):
        lines.append("No news data available.")
        return "\n".join(lines)

    if payload.sentiment:
        score = payload.sentiment.score
        score_str = f"{score:.2f}" if score is not None else "N/A"
        lines.append(
            f"- Overall Sentiment: {payload.sentiment.overall} (score={score_str})"
        )

    if payload.market_articles:
        lines.append("- Market News:")
        for article in payload.market_articles[:5]:
            lines.append(f"  - [{article.source}] {article.headline}")

    for sym_news in payload.symbol_news:
        if sym_news.articles:
            lines.append(f"- {sym_news.symbol} News:")
            for article in sym_news.articles[:3]:
                lines.append(f"  - {article.headline}")

    if len(lines) == 2:
        lines.append("No recent news articles found.")

    return "\n".join(lines)
