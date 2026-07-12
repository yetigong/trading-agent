"""TradingAgent orchestrator — wires data, analysis, strategy, and execution layers."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from trading_agent.broker.alpaca_client import AlpacaTradingClient
from trading_agent.analysis.runner import AnalysisRunner
from trading_agent.domain.cycle import CycleResult, StrategyContext, TradingDecision
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.execution import (
    PortfolioSnapshotBuilder,
    TradeExecutor,
    TradePreparer,
)
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider
from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider
from trading_agent.market_data.fundamentals_base import FundamentalDataProvider
from trading_agent.market_data.news_base import NewsDataProvider
from trading_agent.llm.client import get_llm_client, LLMClient
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.strategies.general import GeneralTradingStrategy

logger = logging.getLogger(__name__)


class TradingAgent:
    def __init__(
        self,
        risk_tolerance: str = "moderate",
        investment_goal: str = "growth",
        max_position_size: float = 0.1,
        llm_client: Optional[LLMClient] = None,
        client_type: str = "openai",
        market_data_provider: Optional[MarketDataProvider] = None,
        alpaca_client: Optional[Any] = None,
        news_provider: Optional[NewsDataProvider] = None,
        fundamentals_provider: Optional[FundamentalDataProvider] = None,
        **kwargs,
    ):
        load_dotenv()

        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        self.analysis_runner = AnalysisRunner(llm_client=self.llm_client)
        self.trading_strategy = GeneralTradingStrategy(llm_client=self.llm_client)
        self.portfolio_rebalancer = PortfolioRebalancer(llm_client=self.llm_client)
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        self.news_provider = news_provider or FinnhubNewsProvider()
        self.fundamentals_provider = fundamentals_provider or FMPFundamentalsProvider()
        self.signal_aggregator = SignalAggregator(
            self.market_data_provider,
            self.news_provider,
            self.fundamentals_provider,
        )
        self.alpaca_client = alpaca_client or AlpacaTradingClient()
        self.snapshot_builder = PortfolioSnapshotBuilder()
        self.trade_preparer = TradePreparer()
        self.trade_executor = TradeExecutor(self.alpaca_client)

        self.user_preferences = UserPreferences(
            risk_tolerance=risk_tolerance,
            investment_goal=investment_goal,
            max_position_size=max_position_size,
        )

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
        cycle_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        try:
            raw_conditions = self.market_data_provider.get_market_conditions()
            market_conditions = self.signal_aggregator.market_conditions_from_dict(raw_conditions)
            self.last_market_conditions = market_conditions

            portfolio = self.snapshot_builder.build(self.alpaca_client)
            self.last_portfolio = portfolio

            signals = self.signal_aggregator.collect(market_conditions, portfolio)
            market_analysis = self.analysis_runner.run(
                portfolio=portfolio,
                signals=signals,
                market_conditions=market_conditions,
                user_preferences=self.user_preferences,
                analysis_params=analysis_params,
            )
            self.last_market_analysis = market_analysis

            if market_analysis.has_failure():
                return CycleResult(
                    status="failed",
                    cycle_id=cycle_id,
                    timestamp=timestamp,
                    error="All market analysis strategies failed",
                ).to_dict()

            context = StrategyContext(
                market_conditions=market_conditions,
                market_analysis=market_analysis,
                portfolio=portfolio,
                user_preferences=self.user_preferences,
                strategy_params=strategy_params or {},
                rebalance_params=rebalance_params or {},
                analysis_params=analysis_params or {},
            )

            decisions = self.trading_strategy.make_decisions(context)
            strategy_hold = len(decisions) == 0

            rebalancing = self.portfolio_rebalancer.rebalance_portfolio(context)
            self.last_rebalancing = rebalancing
            if rebalancing.get("status") == "success":
                rebalance_orders = self.portfolio_rebalancer.generate_rebalancing_orders(
                    context, rebalancing
                )
                decisions.extend(rebalance_orders)

            preparation = self.trade_preparer.prepare(
                decisions, portfolio, self.user_preferences
            ) if decisions else None

            executed = []
            if preparation and preparation.executable:
                executed = [
                    t.to_dict()
                    for t in self.trade_executor.execute(preparation.executable)
                ]

            hold = strategy_hold and len(executed) == 0

            result = CycleResult(
                status="success",
                cycle_id=cycle_id,
                timestamp=timestamp,
                market_conditions=market_conditions,
                market_analysis=market_analysis,
                decisions=[d.to_dict() for d in (preparation.consolidated if preparation else decisions)],
                hold=hold,
                rebalancing=rebalancing,
                preparation=preparation,
                executed_trades=executed,
            )
            return result.to_dict()

        except Exception as exc:
            logger.error("Trading cycle failed: %s", exc)
            return CycleResult(
                status="failed",
                cycle_id=cycle_id,
                timestamp=timestamp,
                error=str(exc),
            ).to_dict()
