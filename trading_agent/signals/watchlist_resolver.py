from typing import List, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.user.watchlist import Watchlist


def resolve_watchlist(
    portfolio: PortfolioSnapshot,
    watchlist: Watchlist,
    sector_peers: Optional[List[str]] = None,
) -> List[str]:
    """Merge configured symbols with portfolio positions and optional sector peers."""
    symbols: List[str] = []

    if watchlist.include_portfolio_positions:
        symbols.extend(portfolio.positions)

    symbols.extend(watchlist.symbols)

    if watchlist.include_sector_peers and sector_peers:
        symbols.extend(sector_peers)

    seen = set()
    deduped: List[str] = []
    for sym in symbols:
        upper = sym.upper()
        if upper not in seen:
            seen.add(upper)
            deduped.append(upper)

    return deduped[: watchlist.max_symbols]
