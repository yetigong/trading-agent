from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Watchlist:
    schema_version: int = 1
    symbols: List[str] = field(default_factory=list)
    include_portfolio_positions: bool = True
    include_sector_peers: bool = True
    sector_peer_limit: int = 2
    max_symbols: int = 15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "symbols": self.symbols,
            "include_portfolio_positions": self.include_portfolio_positions,
            "include_sector_peers": self.include_sector_peers,
            "sector_peer_limit": self.sector_peer_limit,
            "max_symbols": self.max_symbols,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Watchlist":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            symbols=[s.upper() for s in data.get("symbols", [])],
            include_portfolio_positions=bool(data.get("include_portfolio_positions", True)),
            include_sector_peers=bool(data.get("include_sector_peers", True)),
            sector_peer_limit=int(data.get("sector_peer_limit", 2)),
            max_symbols=int(data.get("max_symbols", 15)),
        )

    @classmethod
    def default(cls) -> "Watchlist":
        return cls()
