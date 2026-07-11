"""Shared context and helpers for signal collection."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions

MAX_SYMBOLS = 5
BAR_LOOKBACK_DAYS = 100


@dataclass
class SignalCollectionContext:
    market_conditions: MarketConditions
    portfolio: Optional[PortfolioSnapshot] = None
    symbols: List[str] = field(default_factory=list)
    bar_cache: Dict[str, pd.DataFrame] = field(default_factory=dict)

    @classmethod
    def from_inputs(
        cls,
        market_conditions: MarketConditions,
        portfolio: Optional[PortfolioSnapshot] = None,
    ) -> "SignalCollectionContext":
        symbols: List[str] = []
        if portfolio:
            symbols = [p.symbol for p in portfolio.positions[:MAX_SYMBOLS]]
        return cls(market_conditions=market_conditions, portfolio=portfolio, symbols=symbols)


def summarize_sector_rotation(sector_etfs: Dict[str, Any]) -> str:
    """Summarize top/bottom sectors by 5d relative strength vs SPY."""
    if not sector_etfs:
        return ""

    ranked = []
    for symbol, data in sector_etfs.items():
        if not isinstance(data, dict):
            continue
        vs_spy = data.get("vs_spy_5d")
        ret_5d = data.get("return_5d")
        if vs_spy is not None:
            ranked.append((symbol, vs_spy, ret_5d))

    if not ranked:
        return ""

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[0]
    bottom = ranked[-1]
    parts = [
        f"Leading sector: {top[0]} ({top[1]:+.1f}% vs SPY over 5d)",
        f"Lagging sector: {bottom[0]} ({bottom[1]:+.1f}% vs SPY over 5d)",
    ]
    return "; ".join(parts)
