"""Structured payloads exchanged between Phase 4 agents."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from trading_agent.domain.cycle import (
    MarketAnalysis,
    TradePreparationResult,
    TradingDecision,
)
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions


@dataclass
class MarketSummary:
    """Output of MarketAnalyzer — MarketAnalysis plus compact structured fields."""

    market_conditions: MarketConditions
    market_analysis: MarketAnalysis
    portfolio: PortfolioSnapshot
    trend: str = "unknown"
    sentiment: str = "neutral"
    risks: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    lessons_applied: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        from trading_agent.domain.serialization import to_dict

        return {
            "trend": self.trend,
            "sentiment": self.sentiment,
            "risks": list(self.risks),
            "themes": list(self.themes),
            "lessons_applied": list(self.lessons_applied),
            "market_conditions": to_dict(self.market_conditions),
            "market_analysis": to_dict(self.market_analysis),
            "portfolio": to_dict(self.portfolio),
        }


@dataclass
class StrategyOption:
    name: str
    rationale: str
    trade_offs: str = ""
    decisions: List[TradingDecision] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rationale": self.rationale,
            "trade_offs": self.trade_offs,
            "decisions": [d.to_dict() for d in self.decisions],
        }


@dataclass
class StrategyPlan:
    """Output of TradingStrategizer."""

    options: List[StrategyOption]
    selected: StrategyOption
    decisions: List[TradingDecision]
    rebalancing: Optional[Dict[str, Any]] = None
    strategy_hold: bool = False
    preferences_applied: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "options": [o.to_dict() for o in self.options],
            "selected": self.selected.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "rebalancing": self.rebalancing,
            "strategy_hold": self.strategy_hold,
            "preferences_applied": self.preferences_applied,
        }


@dataclass
class ExecutionReport:
    """Output of TradeExecutorAgent."""

    preparation: Optional[TradePreparationResult]
    executed_trades: List[Dict[str, Any]] = field(default_factory=list)
    hold: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preparation": self.preparation.to_dict() if self.preparation else None,
            "executed_trades": list(self.executed_trades),
            "hold": self.hold,
        }


@dataclass
class DecisionLog:
    """Append-only style record for one cycle (feeds Phase 6 persistence)."""

    cycle_id: str
    timestamp: str
    market_summary: Optional[Dict[str, Any]] = None
    strategy_plan: Optional[Dict[str, Any]] = None
    execution_report: Optional[Dict[str, Any]] = None
    artifact_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "market_summary": self.market_summary,
            "strategy_plan": self.strategy_plan,
            "execution_report": self.execution_report,
            "artifact_path": self.artifact_path,
        }


@dataclass
class LessonsUpdate:
    """Output of Learner agent."""

    lessons_added: List[str] = field(default_factory=list)
    signal_weights: Dict[str, float] = field(default_factory=dict)
    strategy_preferences: Dict[str, Any] = field(default_factory=dict)
    lesson_records: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lessons_added": list(self.lessons_added),
            "signal_weights": dict(self.signal_weights),
            "strategy_preferences": dict(self.strategy_preferences),
            "lesson_records": list(self.lesson_records),
        }
