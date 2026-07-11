from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Union


@dataclass
class TradingDecision:
    action: str
    symbol: str
    quantity: Union[int, str]
    reasoning: str
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingDecision":
        return cls(
            action=data["action"],
            symbol=data["symbol"],
            quantity=data["quantity"],
            reasoning=data["reasoning"],
            risk_level=data["risk_level"],
        )
