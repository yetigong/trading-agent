from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.formatters.signals.fundamentals import format_fundamentals
from trading_agent.formatters.signals.market_data import format_market_data
from trading_agent.formatters.signals.news import format_news
from trading_agent.formatters.signals.technical import format_technical

SOURCE_ORDER = ["market_data", "technical", "news", "fundamentals"]
FORMATTERS = {
    "market_data": format_market_data,
    "technical": format_technical,
    "news": format_news,
    "fundamentals": format_fundamentals,
}


def format_market_signals(signals: MarketSignals) -> str:
    blocks = []
    for source_id in SOURCE_ORDER:
        source = signals.get_source(source_id)
        if source:
            formatter = FORMATTERS.get(source_id)
            if formatter:
                blocks.append(formatter(source))
    return "\n\n".join(blocks) if blocks else "Market signals: unavailable"
