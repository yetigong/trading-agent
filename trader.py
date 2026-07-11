import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from alpaca_client import AlpacaTradingClient
from alpaca.trading.enums import OrderSide

from trading_agent.analysis.selector import AnalysisStrategySelector
from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.domain.cycle.market_analysis import MarketAnalysisResult
from trading_agent.domain.cycle.strategy_context import StrategyContext
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.formatters.trades import format_trade_failure
from trading_agent.llm.client import get_llm_client, LLMClient
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.signals.factory import build_signal_providers
from trading_agent.signals.watchlist_resolver import resolve_watchlist
from trading_agent.storage import PreferencesStore, SignalConfigStore, WatchlistStore
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
        signal_aggregator: Optional[SignalAggregator] = None,
        userdata_dir: Optional[Path] = None,
        use_mock_signals: bool = False,
        **kwargs,
    ):
        load_dotenv()

        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        self.strategy_selector = AnalysisStrategySelector(llm_client=self.llm_client)
        self.trading_strategy = GeneralTradingStrategy(llm_client=self.llm_client)
        self.portfolio_rebalancer = PortfolioRebalancer(llm_client=self.llm_client)
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        self.alpaca_client = alpaca_client or AlpacaTradingClient()

        self.watchlist_store = WatchlistStore(userdata_dir)
        self.preferences_store = PreferencesStore(userdata_dir)
        self.signal_config_store = SignalConfigStore(userdata_dir)
        self.preferences_store.ensure_exists()
        self.watchlist_store.ensure_exists()
        self.signal_config_store.ensure_exists()

        prefs = self.preferences_store.load()
        if risk_tolerance != "moderate" or investment_goal != "growth":
            prefs = prefs
        self.user_preferences_model = prefs

        providers = build_signal_providers(self.market_data_provider, use_mock=use_mock_signals)
        self.signal_aggregator = signal_aggregator or SignalAggregator(
            providers=providers,
            signal_config=self.signal_config_store.load(),
        )

        self.portfolio = {}
        self.last_analysis = None
        self.last_rebalancing = None
        self.current_analysis_strategy = None
        self.last_market_conditions = None
        self.last_market_signals: Optional[MarketSignals] = None

    @property
    def user_preferences(self) -> Dict[str, Any]:
        return self.user_preferences_model.to_legacy_dict()

    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        account = self.alpaca_client.get_account()
        positions = self.alpaca_client.get_positions()
        return PortfolioSnapshot(
            portfolio_value=float(account.portfolio_value),
            cash=float(account.cash),
            positions=[p.symbol for p in positions],
            timestamp=datetime.now(),
        )

    def get_portfolio_data(self) -> Dict[str, Any]:
        return self.get_portfolio_snapshot().to_dict()

    def collect_market_signals(self) -> MarketSignals:
        portfolio = self.get_portfolio_snapshot()
        watchlist_cfg = self.watchlist_store.load()
        symbols = resolve_watchlist(portfolio, watchlist_cfg)
        market_signals = self.signal_aggregator.collect(symbols)
        self.last_market_signals = market_signals
        self.last_market_conditions = market_signals.to_legacy_market_conditions()
        return market_signals

    def build_analysis_context(
        self,
        market_signals: MarketSignals,
        time_horizon: str = "medium-term",
        focus_areas: str = "all",
        regions: str = "US",
    ) -> AnalysisContext:
        return AnalysisContext(
            market_signals=market_signals,
            portfolio=self.get_portfolio_snapshot(),
            user_preferences=self.preferences_store.load(),
            time_horizon=time_horizon,
            focus_areas=focus_areas,
            regions=regions,
        )

    def analyze_market_conditions(
        self,
        analysis_context: Optional[AnalysisContext] = None,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = analysis_params or {}
        if analysis_context is None:
            market_signals = self.collect_market_signals()
            analysis_context = self.build_analysis_context(
                market_signals,
                time_horizon=params.get("time_horizon", "medium-term"),
                focus_areas=params.get("focus_areas", "all"),
                regions=params.get("regions", "US"),
            )
        else:
            self.last_market_signals = analysis_context.market_signals
            self.last_market_conditions = analysis_context.market_signals.to_legacy_market_conditions()

        strategy_class = self.strategy_selector.select_strategy(context=analysis_context)
        strategy = strategy_class(llm_client=self.llm_client)
        self.current_analysis_strategy = strategy.get_strategy_name()

        result = strategy.analyze(context=analysis_context)
        self.last_analysis = result.to_dict()
        return self.last_analysis

    def make_trading_decisions(
        self,
        market_analysis: Dict[str, Any],
        strategy_context: Optional[StrategyContext] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if strategy_context is None:
            params = strategy_params or {}
            market_signals = self.last_market_signals or self.collect_market_signals()
            strategy_context = StrategyContext(
                market_signals=market_signals,
                portfolio=self.get_portfolio_snapshot(),
                user_preferences=self.preferences_store.load(),
                market_analysis=MarketAnalysisResult.from_dict(market_analysis),
                timeframe=params.get("timeframe", "immediate"),
                risk_management=params.get("risk_management", "standard"),
                position_sizing=params.get("position_sizing", "dynamic"),
            )

        return self.trading_strategy.make_decisions(context=strategy_context)

    def rebalance_portfolio(self, rebalance_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        portfolio_data = self.get_portfolio_data()
        rebalancing_plan = self.portfolio_rebalancer.rebalance_portfolio(
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            rebalance_params=rebalance_params,
        )
        self.last_rebalancing = rebalancing_plan
        return rebalancing_plan

    def execute_trades(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        executed_trades = []

        for decision in decisions:
            try:
                quantity = decision["quantity"]
                if quantity == "ALL":
                    positions = self.alpaca_client.get_positions()
                    position = next((p for p in positions if p.symbol == decision["symbol"]), None)
                    if position:
                        quantity = int(float(position.qty))
                    else:
                        logger.warning("No position found for %s to sell ALL", decision["symbol"])
                        continue

                order = self.alpaca_client.place_market_order(
                    symbol=decision["symbol"],
                    qty=quantity,
                    side=OrderSide.BUY if decision["action"] == "BUY" else OrderSide.SELL,
                )

                executed_trades.append(
                    {
                        "symbol": decision["symbol"],
                        "action": decision["action"],
                        "quantity": quantity,
                        "status": "executed",
                        "order_id": str(order.id),
                    }
                )

            except Exception as e:
                error_str = str(e)
                executed_trades.append(
                    {
                        "symbol": decision["symbol"],
                        "action": decision["action"],
                        "quantity": decision["quantity"],
                        "status": "failed",
                        "error": error_str,
                        "failure_detail": format_trade_failure(error_str),
                    }
                )

        return executed_trades

    def run_trading_cycle(
        self,
        analysis_params: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        rebalance_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cycle_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        analysis = self.analyze_market_conditions(analysis_params=analysis_params)
        if not analysis or analysis.get("status") == "failed":
            return {
                "status": "failed",
                "error": analysis.get("error", "Market analysis failed") if analysis else "Market analysis failed",
                "cycle_id": cycle_id,
                "timestamp": timestamp,
            }

        decisions = self.make_trading_decisions(analysis, strategy_params=strategy_params)
        hold = len(decisions) == 0

        rebalancing = self.rebalance_portfolio(rebalance_params)
        if rebalancing and rebalancing.get("status") == "success":
            rebalancing_orders = self.portfolio_rebalancer.generate_rebalancing_orders(
                rebalancing_plan=rebalancing,
                portfolio_data=self.get_portfolio_data(),
            )
            decisions.extend(rebalancing_orders)

        executed_trades = self.execute_trades(decisions) if decisions else []

        result = {
            "status": "success",
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "analysis": analysis,
            "analysis_strategy": self.current_analysis_strategy,
            "market_conditions": self.last_market_conditions,
            "market_signals": self.last_market_signals.to_dict() if self.last_market_signals else None,
            "decisions": decisions,
            "hold": hold and len(executed_trades) == 0,
            "rebalancing": rebalancing,
            "executed_trades": executed_trades,
        }
        return result
