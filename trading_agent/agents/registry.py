"""Agent registry — construct and configure the default Phase 4 agent set."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from trading_agent.agents.base import Agent
from trading_agent.agents.decision_logger import DecisionLoggerAgent
from trading_agent.agents.executor import TradeExecutorAgent
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.learner import LearnerAgent
from trading_agent.agents.market_analyzer import MarketAnalyzerAgent
from trading_agent.agents.strategizer import TradingStrategizerAgent
from trading_agent.analysis.runner import AnalysisRunner
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.execution.executor import TradeExecutor
from trading_agent.execution.preparer import TradePreparer
from trading_agent.execution.snapshot_builder import PortfolioSnapshotBuilder
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.strategies.general import GeneralTradingStrategy


@dataclass
class AgentRegistry:
    agents: Dict[str, Agent] = field(default_factory=dict)
    knowledge_base: Optional[KnowledgeBase] = None

    def get(self, name: str) -> Optional[Agent]:
        return self.agents.get(name)

    def enabled_pipeline(self) -> List[Agent]:
        order = [
            "market_analyzer",
            "trading_strategizer",
            "trade_executor",
            "decision_logger",
            "learner",
        ]
        return [
            self.agents[name]
            for name in order
            if name in self.agents and self.agents[name].is_enabled()
        ]


def build_default_registry(
    *,
    llm_client,
    market_data_provider,
    alpaca_client,
    signal_aggregator: SignalAggregator,
    user_preferences: UserPreferences,
    analysis_runner: Optional[AnalysisRunner] = None,
    trading_strategy: Optional[GeneralTradingStrategy] = None,
    portfolio_rebalancer: Optional[PortfolioRebalancer] = None,
    snapshot_builder: Optional[PortfolioSnapshotBuilder] = None,
    trade_preparer: Optional[TradePreparer] = None,
    trade_executor: Optional[TradeExecutor] = None,
    knowledge_base: Optional[KnowledgeBase] = None,
    log_dir: Optional[Path] = None,
    write_artifact: bool = False,
    disabled: Optional[List[str]] = None,
) -> AgentRegistry:
    disabled_set = set(disabled or [])
    kb = knowledge_base or KnowledgeBase()
    analysis_runner = analysis_runner or AnalysisRunner(llm_client=llm_client)
    trading_strategy = trading_strategy or GeneralTradingStrategy(llm_client=llm_client)
    portfolio_rebalancer = portfolio_rebalancer or PortfolioRebalancer(llm_client=llm_client)
    snapshot_builder = snapshot_builder or PortfolioSnapshotBuilder()
    trade_preparer = trade_preparer or TradePreparer()
    trade_executor = trade_executor or TradeExecutor(alpaca_client)

    agents: Dict[str, Agent] = {
        "market_analyzer": MarketAnalyzerAgent(
            signal_aggregator=signal_aggregator,
            analysis_runner=analysis_runner,
            snapshot_builder=snapshot_builder,
            market_data_provider=market_data_provider,
            alpaca_client=alpaca_client,
            user_preferences=user_preferences,
            knowledge_base=kb,
            enabled="market_analyzer" not in disabled_set,
        ),
        "trading_strategizer": TradingStrategizerAgent(
            trading_strategy=trading_strategy,
            portfolio_rebalancer=portfolio_rebalancer,
            user_preferences=user_preferences,
            knowledge_base=kb,
            enabled="trading_strategizer" not in disabled_set,
        ),
        "trade_executor": TradeExecutorAgent(
            trade_preparer=trade_preparer,
            trade_executor=trade_executor,
            user_preferences=user_preferences,
            enabled="trade_executor" not in disabled_set,
        ),
        "decision_logger": DecisionLoggerAgent(
            log_dir=log_dir,
            write_artifact=write_artifact,
            enabled="decision_logger" not in disabled_set,
        ),
        "learner": LearnerAgent(
            knowledge_base=kb,
            enabled="learner" not in disabled_set,
        ),
    }
    return AgentRegistry(agents=agents, knowledge_base=kb)
