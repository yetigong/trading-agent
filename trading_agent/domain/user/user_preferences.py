from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class UserPreferences:
    risk_tolerance: str = "moderate"
    investment_goal: str = "growth"
    max_position_size: float = 0.25
    investment_horizon: str = "medium-term"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        return cls(
            risk_tolerance=data.get("risk_tolerance", "moderate"),
            investment_goal=data.get("investment_goal", "growth"),
            max_position_size=float(data.get("max_position_size", 0.25)),
            investment_horizon=data.get("investment_horizon", "medium-term"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_tolerance": self.risk_tolerance,
            "investment_goal": self.investment_goal,
            "max_position_size": self.max_position_size,
            "investment_horizon": self.investment_horizon,
        }
