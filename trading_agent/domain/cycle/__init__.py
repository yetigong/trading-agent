from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..portfolio.portfolio_snapshot import PortfolioSnapshot
from ..signals.market_conditions import MarketConditions
from ..signals.market_signals import MarketSignals
from ..user.user_preferences import UserPreferences


@dataclass
class AnalysisResult:
    strategy_name: str
    status: str
    summary: str = ""
    structured: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            strategy_name=data.get("strategy_name", ""),
            status=data.get("status", "failed"),
            summary=data.get("summary", data.get("analysis", "")),
            structured=data.get("structured") or {},
            timestamp=ts,
            error=data.get("error"),
        )


@dataclass
class MarketAnalysis:
    general: Optional[AnalysisResult] = None
    technical: Optional[AnalysisResult] = None
    fundamental: Optional[AnalysisResult] = None
    signals: Optional[MarketSignals] = None

    def all_results(self) -> List[AnalysisResult]:
        return [r for r in (self.general, self.technical, self.fundamental) if r is not None]

    def has_failure(self) -> bool:
        """True when no analysis strategy produced a successful result.

        Skipped strategies (e.g. empty fundamentals) do not count as success,
        so general+technical failures still fail the cycle.
        """
        results = self.all_results()
        if not results:
            return True
        return not any(r.status == "success" for r in results)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketAnalysis":
        return cls(
            general=AnalysisResult.from_dict(data["general"]) if data.get("general") else None,
            technical=AnalysisResult.from_dict(data["technical"]) if data.get("technical") else None,
            fundamental=AnalysisResult.from_dict(data["fundamental"]) if data.get("fundamental") else None,
            signals=MarketSignals.from_dict(data.get("signals")),
        )


@dataclass
class StrategyContext:
    market_conditions: MarketConditions
    market_analysis: MarketAnalysis
    portfolio: PortfolioSnapshot
    user_preferences: UserPreferences
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    rebalance_params: Dict[str, Any] = field(default_factory=dict)
    analysis_params: Dict[str, Any] = field(default_factory=dict)
    universe_symbols: List[str] = field(default_factory=list)


@dataclass
class TradingDecision:
    action: str
    symbol: str
    quantity: Union[int, str]
    reasoning: str = ""
    risk_level: str = "medium"
    source: str = "strategy"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingDecision":
        return cls(
            action=str(data.get("action", "")).upper(),
            symbol=str(data.get("symbol", "")).upper(),
            quantity=data.get("quantity"),
            reasoning=str(data.get("reasoning", data.get("reason", ""))),
            risk_level=str(data.get("risk_level", "medium")).lower(),
            source=str(data.get("source", "strategy")),
        )


@dataclass
class AdjustedTrade:
    original: TradingDecision
    final: TradingDecision
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original.to_dict(),
            "final": self.final.to_dict(),
            "reason": self.reason,
        }


@dataclass
class SkippedTrade:
    decision: TradingDecision
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"decision": self.decision.to_dict(), "reason": self.reason}


@dataclass
class ExecutedTrade:
    symbol: str
    action: str
    quantity: Union[int, str]
    status: str
    order_id: Optional[str] = None
    error: Optional[str] = None
    failure_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "status": self.status,
            "order_id": self.order_id,
            "error": self.error,
            "failure_detail": self.failure_detail,
        }


@dataclass
class TradePreparationResult:
    raw: List[TradingDecision] = field(default_factory=list)
    consolidated: List[TradingDecision] = field(default_factory=list)
    executable: List[TradingDecision] = field(default_factory=list)
    adjusted: List[AdjustedTrade] = field(default_factory=list)
    skipped: List[SkippedTrade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": [d.to_dict() for d in self.raw],
            "consolidated": [d.to_dict() for d in self.consolidated],
            "executable": [d.to_dict() for d in self.executable],
            "adjusted": [a.to_dict() for a in self.adjusted],
            "skipped": [s.to_dict() for s in self.skipped],
        }


@dataclass
class CycleResult:
    status: str
    cycle_id: str
    timestamp: str
    market_conditions: Optional[MarketConditions] = None
    market_analysis: Optional[MarketAnalysis] = None
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    hold: bool = False
    rebalancing: Optional[Dict[str, Any]] = None
    preparation: Optional[TradePreparationResult] = None
    executed_trades: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        from ..serialization import to_dict

        payload = {
            "status": self.status,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "market_conditions": to_dict(self.market_conditions),
            "market_analysis": to_dict(self.market_analysis),
            "analysis_strategy": "All Analysis Strategies",
            "analysis": {
                "status": "success" if self.market_analysis and not self.market_analysis.has_failure() else "failed",
                "analysis": self._analysis_summary(),
            },
            "decisions": self.decisions,
            "hold": self.hold,
            "rebalancing": self.rebalancing,
            "preparation": self.preparation.to_dict() if self.preparation else None,
            "executed_trades": self.executed_trades,
            "error": self.error,
        }
        return payload

    def _analysis_summary(self) -> str:
        if not self.market_analysis:
            return ""
        parts = []
        for result in self.market_analysis.all_results():
            if result and result.summary:
                parts.append(f"## {result.strategy_name}\n{result.summary}")
        return "\n\n".join(parts)
