from dataclasses import dataclass, field
from typing import Any, Dict, List

DEFAULT_SECTOR_ETFS = [
    "XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
]
DEFAULT_ENABLED_SOURCES = ["market_data", "technical", "news", "fundamentals"]


@dataclass
class SignalConfig:
    sector_etfs: List[str] = field(default_factory=lambda: list(DEFAULT_SECTOR_ETFS))
    enabled_sources: List[str] = field(default_factory=lambda: list(DEFAULT_ENABLED_SOURCES))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalConfig":
        sector_etfs = data.get("sector_etfs") or list(DEFAULT_SECTOR_ETFS)
        enabled_sources = data.get("enabled_sources") or list(DEFAULT_ENABLED_SOURCES)
        return cls(
            sector_etfs=list(sector_etfs),
            enabled_sources=list(enabled_sources),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_etfs": self.sector_etfs,
            "enabled_sources": self.enabled_sources,
        }
