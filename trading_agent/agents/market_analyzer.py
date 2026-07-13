"""Market Analyzer — synthesize signals + analysis into a MarketSummary."""

from typing import Any, Dict, List, Optional

from trading_agent.broker.base import BrokerClient
from trading_agent.agents.base import ConfigurableAgent
from strategy_learning.knowledge import KnowledgeBase
from trading_agent.agents.messages import MarketSummary
from trading_agent.analysis.runner import AnalysisRunner
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.execution.snapshot_builder import PortfolioSnapshotBuilder
from trading_agent.signals.aggregator import SignalAggregator


def _derive_trend(market_conditions) -> str:
    trend = getattr(market_conditions, "trend", None)
    if trend and trend != "unknown":
        return str(trend)
    indices = getattr(market_conditions, "indices", None) or {}
    spy = indices.get("SPY") if isinstance(indices, dict) else None
    if not isinstance(spy, dict):
        return "unknown"
    change = spy.get("change_pct", spy.get("change_percent"))
    if change is None:
        return "unknown"
    try:
        value = float(change)
    except (TypeError, ValueError):
        return "unknown"
    if value > 0.3:
        return "bullish"
    if value < -0.3:
        return "bearish"
    return "sideways"


def _derive_sentiment(market_analysis) -> str:
    if not market_analysis:
        return "neutral"
    text = " ".join(
        (r.summary or "").lower() for r in market_analysis.all_results() if r
    )
    bullish = sum(token in text for token in ("bullish", "uptrend", "positive", "rally"))
    bearish = sum(token in text for token in ("bearish", "downtrend", "negative", "sell-off"))
    if bullish > bearish:
        return "positive"
    if bearish > bullish:
        return "negative"
    return "neutral"


def _extract_themes(market_analysis) -> List[str]:
    themes: List[str] = []
    if not market_analysis:
        return themes
    for result in market_analysis.all_results():
        if result and result.strategy_name:
            themes.append(result.strategy_name)
    return themes[:5]


class MarketAnalyzerAgent(ConfigurableAgent):
    name = "market_analyzer"

    def __init__(
        self,
        signal_aggregator: SignalAggregator,
        analysis_runner: AnalysisRunner,
        snapshot_builder: PortfolioSnapshotBuilder,
        market_data_provider,
        broker_client: BrokerClient,
        user_preferences: UserPreferences,
        alpaca_client: Optional[BrokerClient] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.signal_aggregator = signal_aggregator
        self.analysis_runner = analysis_runner
        self.snapshot_builder = snapshot_builder
        self.market_data_provider = market_data_provider
        self.broker_client = broker_client or alpaca_client
        self.user_preferences = user_preferences
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        analysis_params = dict(ctx.get("analysis_params") or {})
        lessons = self.knowledge_base.lessons_for_prompt()
        weights = self.knowledge_base.signal_weights()
        if lessons:
            analysis_params["knowledge_lessons"] = lessons
        if weights:
            analysis_params["signal_weights"] = weights

        raw_conditions = self.market_data_provider.get_market_conditions()
        market_conditions = self.signal_aggregator.market_conditions_from_dict(raw_conditions)
        portfolio = self.snapshot_builder.build(self.broker_client)
        signals = self.signal_aggregator.collect(market_conditions, portfolio)
        market_analysis = self.analysis_runner.run(
            portfolio=portfolio,
            signals=signals,
            market_conditions=market_conditions,
            user_preferences=self.user_preferences,
            analysis_params=analysis_params,
        )

        summary = MarketSummary(
            market_conditions=market_conditions,
            market_analysis=market_analysis,
            portfolio=portfolio,
            trend=_derive_trend(market_conditions),
            sentiment=_derive_sentiment(market_analysis),
            risks=["analysis_failure"] if market_analysis.has_failure() else [],
            themes=_extract_themes(market_analysis),
            lessons_applied=lessons,
        )

        ctx["market_conditions"] = market_conditions
        ctx["portfolio"] = portfolio
        ctx["market_analysis"] = market_analysis
        ctx["market_summary"] = summary
        ctx["universe_symbols"] = list(self.signal_aggregator.universe_symbols or [])
        return {"market_summary": summary}
