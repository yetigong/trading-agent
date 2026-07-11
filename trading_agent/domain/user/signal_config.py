from dataclasses import dataclass, field
from typing import Any, Dict, List

DEFAULT_ENABLED_SOURCES = ["market_data", "technical", "news", "fundamentals"]


@dataclass
class SignalConfig:
    schema_version: int = 1
    enabled_sources: List[str] = field(default_factory=lambda: list(DEFAULT_ENABLED_SOURCES))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled_sources": self.enabled_sources,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalConfig":
        sources = data.get("enabled_sources") or DEFAULT_ENABLED_SOURCES
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            enabled_sources=list(sources),
        )

    @classmethod
    def default(cls) -> "SignalConfig":
        return cls()
