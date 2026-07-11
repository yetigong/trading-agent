from datetime import datetime
from typing import List, Optional

from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.user.signal_config import SignalConfig
from trading_agent.signals.base import SignalProvider


class SignalAggregator:
    def __init__(
        self,
        providers: List[SignalProvider],
        signal_config: Optional[SignalConfig] = None,
    ):
        self.providers = {p.source_id: p for p in providers}
        self.signal_config = signal_config or SignalConfig.default()

    def collect(self, watchlist: List[str]) -> MarketSignals:
        now = datetime.now()
        enabled = set(self.signal_config.enabled_sources)
        sources = []
        for source_id in self.signal_config.enabled_sources:
            provider = self.providers.get(source_id)
            if not provider:
                continue
            sources.append(provider.fetch(watchlist))
        return MarketSignals(watchlist=watchlist, sources=sources, collected_at=now)
