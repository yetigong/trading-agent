"""TradingAgent orchestrator — facade over Phase 4 CycleCoordinator."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from trading_agent.agents.coordinator import CycleCoordinator
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.registry import AgentRegistry, build_default_registry
from trading_agent.broker.alpaca_client import AlpacaTradingClient
from trading_agent.analysis.runner import AnalysisRunner
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.execution import (
    PortfolioSnapshotBuilder,
    TradeExecutor,
    TradePreparer,
)
from trading_agent.execution.validator import TradeValidator
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider
from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider
from trading_agent.market_data.fundamentals_base import FundamentalDataProvider
from trading_agent.market_data.news_base import NewsDataProvider
from trading_agent.llm.client import LLMClient, build_llm_client, get_llm_client
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.strategies.general import GeneralTradingStrategy

logger = logging.getLogger(__name__)


def _price_lookup_from_provider(provider: MarketDataProvider):
    def lookup(symbol: str) -> Optional[float]:
        if hasattr(provider, "get_close_price"):
            price = provider.get_close_price(symbol)
            if price is not None and price > 0:
                return float(price)
        bars = provider.get_bars(symbol, days=5)
        if bars is not None and not bars.empty and "close" in bars.columns:
            value = bars["close"].iloc[-1]
            if value is not None and float(value) > 0:
                return float(value)
        return None

    return lookup


class TradingAgent:
    def __init__(
        self,
        risk_tolerance: str = "moderate",
        investment_goal: str = "growth",
        max_position_size: float = 0.25,
        llm_client: Optional[LLMClient] = None,
        client_type: str = "openai",
        market_data_provider: Optional[MarketDataProvider] = None,
        alpaca_client: Optional[Any] = None,
        news_provider: Optional[NewsDataProvider] = None,
        fundamentals_provider: Optional[FundamentalDataProvider] = None,
        registry: Optional[AgentRegistry] = None,
        coordinator: Optional[CycleCoordinator] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        write_artifact: bool = False,
        log_dir: Optional[Path] = None,
        universe_symbols: Optional[List[str]] = None,
        **kwargs,
    ):
        load_dotenv()

        if llm_client is not None:
            self.llm_client = llm_client
        elif kwargs:
            # Explicit constructor kwargs (e.g. model=) → single provider
            self.llm_client = get_llm_client(client_type, **kwargs)
        else:
            self.llm_client = build_llm_client(provider=client_type)

        self.analysis_runner = AnalysisRunner(llm_client=self.llm_client)
        self.trading_strategy = GeneralTradingStrategy(llm_client=self.llm_client)
        self.portfolio_rebalancer = PortfolioRebalancer(llm_client=self.llm_client)
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        self.news_provider = news_provider or FinnhubNewsProvider()
        self.fundamentals_provider = fundamentals_provider or FMPFundamentalsProvider()
        self.universe_symbols = [s.upper() for s in (universe_symbols or [])]
        self.signal_aggregator = SignalAggregator(
            self.market_data_provider,
            self.news_provider,
            self.fundamentals_provider,
            universe_symbols=self.universe_symbols,
        )
        self.alpaca_client = alpaca_client or AlpacaTradingClient()
        self.snapshot_builder = PortfolioSnapshotBuilder()
        self.trade_preparer = TradePreparer(
            validator=TradeValidator(
                price_lookup=_price_lookup_from_provider(self.market_data_provider),
            )
        )
        self.trade_executor = TradeExecutor(self.alpaca_client)

        self.user_preferences = UserPreferences(
            risk_tolerance=risk_tolerance,
            investment_goal=investment_goal,
            max_position_size=max_position_size,
        )

        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.registry = registry or build_default_registry(
            llm_client=self.llm_client,
            market_data_provider=self.market_data_provider,
            alpaca_client=self.alpaca_client,
            signal_aggregator=self.signal_aggregator,
            user_preferences=self.user_preferences,
            analysis_runner=self.analysis_runner,
            trading_strategy=self.trading_strategy,
            portfolio_rebalancer=self.portfolio_rebalancer,
            snapshot_builder=self.snapshot_builder,
            trade_preparer=self.trade_preparer,
            trade_executor=self.trade_executor,
            knowledge_base=self.knowledge_base,
            log_dir=log_dir,
            write_artifact=write_artifact,
        )
        self.coordinator = coordinator or CycleCoordinator(self.registry)

        self.last_market_analysis = None
        self.last_rebalancing = None
        self.last_market_conditions = None
        self.last_portfolio = None

    def run_trading_cycle(
        self,
        analysis_params: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        rebalance_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.coordinator.run(
            analysis_params=analysis_params,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params,
        )

        ctx = self.coordinator.last_ctx or {}
        self.last_market_conditions = ctx.get("market_conditions")
        self.last_market_analysis = ctx.get("market_analysis")
        self.last_portfolio = ctx.get("portfolio")
        self.last_rebalancing = ctx.get("rebalancing")

        return result
