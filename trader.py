import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from alpaca_client import AlpacaTradingClient
from alpaca.trading.enums import OrderSide
from trading_agent.analysis.selector import AnalysisStrategySelector
from trading_agent.strategies.general import GeneralTradingStrategy
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.llm.client import get_llm_client, LLMClient
from trading_agent.models import format_trade_failure

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
        **kwargs,
    ):
        load_dotenv()

        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        self.strategy_selector = AnalysisStrategySelector(llm_client=self.llm_client)
        self.trading_strategy = GeneralTradingStrategy(llm_client=self.llm_client)
        self.portfolio_rebalancer = PortfolioRebalancer(llm_client=self.llm_client)
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        self.alpaca_client = alpaca_client or AlpacaTradingClient()

        self.user_preferences = {
            "risk_tolerance": risk_tolerance,
            "investment_goal": investment_goal,
            "max_position_size": max_position_size,
            "investment_horizon": "medium-term",
        }

        self.portfolio = {}
        self.last_analysis = None
        self.last_rebalancing = None
        self.current_analysis_strategy = None
        self.last_market_conditions = None

    def get_portfolio_data(self) -> Dict[str, Any]:
        account = self.alpaca_client.get_account()
        positions = self.alpaca_client.get_positions()

        return {
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "positions": [p.symbol for p in positions],
            "timestamp": datetime.now(),
        }

    def get_market_conditions(self) -> Dict[str, Any]:
        return self.market_data_provider.get_market_conditions()

    def analyze_market_conditions(self, analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        portfolio_data = self.get_portfolio_data()
        market_conditions = self.get_market_conditions()
        self.last_market_conditions = market_conditions

        merged_params = dict(analysis_params or {})
        merged_params["market_conditions"] = market_conditions

        strategy_class = self.strategy_selector.select_strategy(
            market_conditions=market_conditions,
            user_preferences=self.user_preferences,
            selection_params=merged_params,
        )

        strategy = strategy_class(llm_client=self.llm_client)
        self.current_analysis_strategy = strategy.get_strategy_name()

        analysis = strategy.analyze(
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            analysis_params=merged_params,
        )

        self.last_analysis = analysis
        return analysis

    def make_trading_decisions(
        self,
        market_analysis: Dict[str, Any],
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        portfolio_data = self.get_portfolio_data()
        merged_params = dict(strategy_params or {})
        merged_params["market_conditions"] = self.last_market_conditions

        return self.trading_strategy.make_decisions(
            market_analysis=market_analysis,
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            strategy_params=merged_params,
        )

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

        analysis = self.analyze_market_conditions(analysis_params)
        if not analysis or analysis.get("status") == "failed":
            return {
                "status": "failed",
                "error": analysis.get("error", "Market analysis failed") if analysis else "Market analysis failed",
                "cycle_id": cycle_id,
                "timestamp": timestamp,
            }

        decisions = self.make_trading_decisions(analysis, strategy_params)
        hold = len(decisions) == 0

        rebalancing = self.rebalance_portfolio(rebalance_params)
        if rebalancing and rebalancing.get("status") == "success":
            rebalancing_orders = self.portfolio_rebalancer.generate_rebalancing_orders(
                rebalancing_plan=rebalancing,
                portfolio_data=self.get_portfolio_data(),
            )
            decisions.extend(rebalancing_orders)

        executed_trades = self.execute_trades(decisions) if decisions else []

        return {
            "status": "success",
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "analysis": analysis,
            "analysis_strategy": self.current_analysis_strategy,
            "market_conditions": self.last_market_conditions,
            "decisions": decisions,
            "hold": hold and len(executed_trades) == 0,
            "rebalancing": rebalancing,
            "executed_trades": executed_trades,
        }
