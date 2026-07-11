from trader import TradingAgent
from trading_agent.config import config_summary, get_config
from trading_agent.llm.client import get_llm_client
from trading_agent.models import trade_result_detail
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from alpaca_client import AlpacaTradingClient
import json
from datetime import datetime
from dotenv import load_dotenv
import logging

class TradingCycle:
    """Handles the execution of a single trading cycle."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        self.config = get_config()

        self.analysis_params = {
            "time_horizon": "medium-term",
            "focus_areas": "tech, healthcare",
            "regions": "US",
        }

        self.strategy_params = {
            "timeframe": "immediate",
            "risk_management": "standard",
            "position_sizing": "dynamic",
        }

        self.rebalance_params = {
            "target_allocation": "balanced",
            "threshold": 5,
            "sector_weights": "market_cap",
        }

    def initialize_components(self):
        self.logger.info("Initializing components...")
        self.logger.info("Config: %s", json.dumps(config_summary(self.config)))

        self.logger.info("Initializing LLM client (%s)...", self.config.llm_provider)
        self.llm_client = get_llm_client(
            self.config.llm_provider,
            model=self.config.llm_model,
        )

        self.logger.info("Initializing market data provider...")
        self.market_data_provider = AlpacaMarketDataProvider()

        self.logger.info("Initializing Alpaca client...")
        self.alpaca_client = AlpacaTradingClient()

        self.logger.info("Creating trading agent...")
        self.agent = TradingAgent(
            risk_tolerance="moderate",
            investment_goal="growth",
            max_position_size=0.1,
            llm_client=self.llm_client,
            market_data_provider=self.market_data_provider,
            alpaca_client=self.alpaca_client,
        )

    def execute(self):
        cycle_start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("Starting new trading cycle at %s", cycle_start_time)
        self.logger.info("=" * 80)

        try:
            self.initialize_components()

            self.logger.info("Analysis parameters: %s", json.dumps(self.analysis_params, indent=2))
            self.logger.info("Strategy parameters: %s", json.dumps(self.strategy_params, indent=2))
            self.logger.info("Rebalancing parameters: %s", json.dumps(self.rebalance_params, indent=2))

            results = self.agent.run_trading_cycle(
                analysis_params=self.analysis_params,
                strategy_params=self.strategy_params,
                rebalance_params=self.rebalance_params,
            )

            self.logger.info("Trading cycle completed with status: %s", results["status"])

            if results["status"] == "success":
                self.logger.info("Cycle ID: %s", results.get("cycle_id"))
                self.logger.info("Selected analysis strategy: %s", results["analysis_strategy"])
                self.logger.info("Market analysis: %s", results["analysis"]["analysis"])

                if results.get("hold"):
                    self.logger.info("Decision: HOLD (no trades recommended)")

                for decision in results["decisions"]:
                    self.logger.info("Trading decision: %s", json.dumps(decision, indent=2))

                if results["rebalancing"]:
                    self.logger.info("Portfolio rebalancing: %s", json.dumps(results["rebalancing"], indent=2))

                for trade in results["executed_trades"]:
                    self.logger.info("Executed trade: %s", json.dumps(trade, indent=2))
            else:
                self.logger.error("Trading cycle failed: %s", results.get("error", "Unknown error"))

            cycle_end_time = datetime.now()
            cycle_duration = cycle_end_time - cycle_start_time

            self.logger.info("=" * 80)
            self.logger.info("TRADING CYCLE SUMMARY")
            self.logger.info("=" * 80)
            self.logger.info("Start Time: %s", cycle_start_time)
            self.logger.info("End Time: %s", cycle_end_time)
            self.logger.info("Duration: %s", cycle_duration)
            self.logger.info("Status: %s", results["status"])

            if results["status"] == "success":
                self.logger.info("\nOperations Summary:")
                self.logger.info("- Analysis Strategy: %s", results["analysis_strategy"])
                self.logger.info("- Number of Trading Decisions: %d", len(results["decisions"]))
                self.logger.info("- Hold: %s", results.get("hold", False))
                self.logger.info("- Portfolio Rebalancing: %s", "Yes" if results["rebalancing"] else "No")
                self.logger.info("- Number of Executed Trades: %d", len(results["executed_trades"]))

                successful_trades = sum(1 for trade in results["executed_trades"] if trade["status"] == "executed")
                failed_trades = sum(1 for trade in results["executed_trades"] if trade["status"] == "failed")
                self.logger.info("- Successful Trades: %d", successful_trades)
                self.logger.info("- Failed Trades: %d", failed_trades)
                for trade in results["executed_trades"]:
                    if trade["status"] == "failed":
                        self.logger.info(
                            "- Failed: %s %s %s — %s",
                            trade["action"],
                            trade["quantity"],
                            trade["symbol"],
                            trade_result_detail(trade),
                        )

            self.logger.info("=" * 80)
            self.logger.info("Trading cycle completed")
            self.logger.info("=" * 80)

            return results

        except Exception as e:
            self.logger.error("Error in trading cycle: %s", e)
            import traceback
            self.logger.error("Traceback: %s", traceback.format_exc())

            cycle_end_time = datetime.now()
            cycle_duration = cycle_end_time - cycle_start_time

            self.logger.info("=" * 80)
            self.logger.info("TRADING CYCLE FAILED")
            self.logger.info("=" * 80)
            self.logger.info("Start Time: %s", cycle_start_time)
            self.logger.info("End Time: %s", cycle_end_time)
            self.logger.info("Duration: %s", cycle_duration)
            self.logger.info("Error: %s", e)
            self.logger.info("=" * 80)

            raise
