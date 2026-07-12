from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BrokerageConfig:
    provider: str = "alpaca"
    paper_mode: bool = True
    account_label: str = "default"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrokerageConfig":
        return cls(
            provider=str(data.get("provider", "alpaca")).lower(),
            paper_mode=bool(data.get("paper_mode", True)),
            account_label=str(data.get("account_label", "default")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "paper_mode": self.paper_mode,
            "account_label": self.account_label,
        }
