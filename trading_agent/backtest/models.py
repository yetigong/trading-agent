"""Backtest domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class EquityPoint:
    date: str
    equity: float
    cash: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradeLogEntry:
    date: str
    symbol: str
    side: str
    qty: int
    price: float
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    name: str
    total_return: float
    cagr: float
    max_drawdown: float
    volatility: float
    sharpe: float
    alpha_vs_spy: Optional[float] = None
    beta_vs_spy: Optional[float] = None
    trade_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestConfig:
    start: date
    end: date
    initial_cash: float = 100_000.0
    rebalance_frequency: str = "weekly"  # weekly | daily
    run_label: str = "default"
    symbols: List[str] = field(default_factory=list)
    seed_positions: Dict[str, int] = field(default_factory=dict)
    risk_free_rate: float = 0.04
    refresh_cache: bool = False
    skip_llm: bool = False
    analysis_params: Dict[str, Any] = field(default_factory=dict)
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    rebalance_params: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    signal_config: Dict[str, Any] = field(default_factory=dict)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_fallback_provider: Optional[str] = None
    llm_fallback_model: Optional[str] = None
    llm_max_retries: int = 3
    llm_pause_seconds: float = 0.0
    alpaca_cache_dir: Optional[str] = None
    finnhub_cache_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "initial_cash": self.initial_cash,
            "rebalance_frequency": self.rebalance_frequency,
            "run_label": self.run_label,
            "symbols": list(self.symbols),
            "seed_positions": dict(self.seed_positions),
            "risk_free_rate": self.risk_free_rate,
            "refresh_cache": self.refresh_cache,
            "skip_llm": self.skip_llm,
            "analysis_params": dict(self.analysis_params),
            "strategy_params": dict(self.strategy_params),
            "rebalance_params": dict(self.rebalance_params),
            "preferences": dict(self.preferences),
            "signal_config": dict(self.signal_config),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_fallback_provider": self.llm_fallback_provider,
            "llm_fallback_model": self.llm_fallback_model,
            "llm_max_retries": self.llm_max_retries,
            "llm_pause_seconds": self.llm_pause_seconds,
        }


@dataclass
class BacktestRun:
    run_id: str
    timestamp: str
    config: Dict[str, Any]
    status: str
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    trade_log: List[Dict[str, Any]] = field(default_factory=list)
    cycle_summaries: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    benchmarks: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "config": self.config,
            "status": self.status,
            "equity_curve": self.equity_curve,
            "trade_log": self.trade_log,
            "cycle_summaries": self.cycle_summaries,
            "metrics": self.metrics,
            "benchmarks": self.benchmarks,
            "notes": self.notes,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestRun":
        return cls(
            run_id=data.get("run_id", ""),
            timestamp=data.get("timestamp", ""),
            config=data.get("config") or {},
            status=data.get("status", "unknown"),
            equity_curve=list(data.get("equity_curve") or []),
            trade_log=list(data.get("trade_log") or []),
            cycle_summaries=list(data.get("cycle_summaries") or []),
            metrics=data.get("metrics") or {},
            benchmarks=list(data.get("benchmarks") or []),
            notes=list(data.get("notes") or []),
            error=data.get("error"),
        )
