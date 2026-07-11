from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Watchlist:
    symbols: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Watchlist":
        symbols = data.get("symbols") or []
        return cls(symbols=[str(s) for s in symbols])

    def to_dict(self) -> Dict[str, Any]:
        return {"symbols": self.symbols}
