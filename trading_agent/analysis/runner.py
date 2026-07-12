import logging
from datetime import datetime
from typing import Any, Dict, Optional

from trading_agent.analysis.fundamental import FundamentalAnalysisStrategy
from trading_agent.analysis.general import GeneralAnalysisStrategy
from trading_agent.analysis.technical import TechnicalAnalysisStrategy
from trading_agent.domain.cycle import AnalysisResult, MarketAnalysis
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.llm.client import LLMClient

logger = logging.getLogger(__name__)


class AnalysisRunner:
    """Run all analysis strategies and aggregate into MarketAnalysis."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.strategies = [
            GeneralAnalysisStrategy(llm_client=llm_client),
            TechnicalAnalysisStrategy(llm_client=llm_client),
            FundamentalAnalysisStrategy(llm_client=llm_client),
        ]

    def run(
        self,
        portfolio: PortfolioSnapshot,
        signals: MarketSignals,
        market_conditions: MarketConditions,
        user_preferences: UserPreferences,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> MarketAnalysis:
        merged_params = dict(analysis_params or {})
        merged_params["market_conditions"] = market_conditions
        merged_params["signals"] = signals

        results: Dict[str, AnalysisResult] = {}
        for strategy in self.strategies:
            key = self._strategy_key(strategy.get_strategy_name())
            if key == "fundamental" and not self._has_fundamental_metrics(signals):
                results[key] = AnalysisResult(
                    strategy_name=strategy.get_strategy_name(),
                    status="skipped",
                    summary="Skipped: no fundamental metrics available",
                    timestamp=datetime.now(),
                )
                continue
            try:
                raw = strategy.analyze(
                    portfolio=portfolio,
                    user_preferences=user_preferences,
                    analysis_params=merged_params,
                )
                results[key] = self._to_result(strategy.get_strategy_name(), raw)
            except Exception as exc:
                logger.error("Analysis failed for %s: %s", strategy.get_strategy_name(), exc)
                results[key] = AnalysisResult(
                    strategy_name=strategy.get_strategy_name(),
                    status="failed",
                    error=str(exc),
                    timestamp=datetime.now(),
                )

        return MarketAnalysis(
            general=results.get("general"),
            technical=results.get("technical"),
            fundamental=results.get("fundamental"),
            signals=signals,
        )

    @staticmethod
    def _has_fundamental_metrics(signals: MarketSignals) -> bool:
        metrics = getattr(getattr(signals, "fundamentals", None), "metrics", None) or {}
        return bool(metrics)

    def _strategy_key(self, strategy_name: str) -> str:
        name = strategy_name.lower()
        if "technical" in name:
            return "technical"
        if "fundamental" in name:
            return "fundamental"
        return "general"

    def _to_result(self, strategy_name: str, raw: Dict[str, Any]) -> AnalysisResult:
        status = raw.get("status", "failed")
        return AnalysisResult(
            strategy_name=strategy_name,
            status=status,
            summary=raw.get("analysis", ""),
            structured=raw.get("structured") or {},
            timestamp=raw.get("timestamp", datetime.now()),
            error=raw.get("error"),
        )
