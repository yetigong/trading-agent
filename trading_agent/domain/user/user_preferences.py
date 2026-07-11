from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class UserPreferences:
    schema_version: int = 1
    risk_tolerance: str = "moderate"
    investment_goal: str = "growth"
    investment_horizon: str = "medium-term"
    max_position_size: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "risk_tolerance": self.risk_tolerance,
            "investment_goal": self.investment_goal,
            "investment_horizon": self.investment_horizon,
            "max_position_size": self.max_position_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            risk_tolerance=data.get("risk_tolerance", "moderate"),
            investment_goal=data.get("investment_goal", "growth"),
            investment_horizon=data.get("investment_horizon", "medium-term"),
            max_position_size=float(data.get("max_position_size", 0.1)),
        )

    @classmethod
    def default(cls) -> "UserPreferences":
        return cls()

    def to_legacy_dict(self) -> Dict[str, Any]:
        return {
            "risk_tolerance": self.risk_tolerance,
            "investment_goal": self.investment_goal,
            "investment_horizon": self.investment_horizon,
            "max_position_size": self.max_position_size,
        }
