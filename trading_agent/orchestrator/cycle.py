import json
import logging
from datetime import datetime

from dotenv import load_dotenv

from alpaca_client import AlpacaTradingClient
from trading_agent.config import config_summary, get_config
from trading_agent.llm.client import get_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.models import trade_result_detail
from trading_agent.orchestrator.agent import TradingAgent


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
                self.logger.info("Analysis: %s", results.get("analysis", {}).get("analysis", ""))

                if results.get("hold"):
                    self.logger.info("Decision: HOLD (no trades recommended)")

                for decision in results.get("decisions", []):
                    self.logger.info("Trading decision: %s", json.dumps(decision, indent=2))

                preparation = results.get("preparation")
                if preparation:
                    for adj in preparation.get("adjusted", []):
                        self.logger.info("Adjusted trade: %s", json.dumps(adj, indent=2))
                    for skip in preparation.get("skipped", []):
                        self.logger.info("Skipped trade: %s", json.dumps(skip, indent=2))

                if results.get("rebalancing"):
                    self.logger.info("Portfolio rebalancing: %s", json.dumps(results["rebalancing"], indent=2))

                for trade in results.get("executed_trades", []):
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
                preparation = results.get("preparation") or {}
                self.logger.info("\nOperations Summary:")
                self.logger.info("- Analysis: all strategies (general + technical + fundamental)")
                self.logger.info("- Raw Decisions: %d", len(preparation.get("raw", results.get("decisions", []))))
                self.logger.info("- Consolidated Decisions: %d", len(results.get("decisions", [])))
                self.logger.info("- Executable Trades: %d", len(preparation.get("executable", [])))
                self.logger.info("- Adjusted Trades: %d", len(preparation.get("adjusted", [])))
                self.logger.info("- Skipped Trades: %d", len(preparation.get("skipped", [])))
                self.logger.info("- Hold: %s", results.get("hold", False))
                self.logger.info("- Portfolio Rebalancing: %s", "Yes" if results.get("rebalancing") else "No")
                self.logger.info("- Executed Trades: %d", len(results.get("executed_trades", [])))

                successful_trades = sum(
                    1 for trade in results.get("executed_trades", []) if trade["status"] == "executed"
                )
                failed_trades = sum(
                    1 for trade in results.get("executed_trades", []) if trade["status"] == "failed"
                )
                skipped_trades = sum(
                    1 for trade in results.get("executed_trades", []) if trade["status"] == "skipped"
                )
                self.logger.info("- Successful Trades: %d", successful_trades)
                self.logger.info("- Failed Trades: %d", failed_trades)
                self.logger.info("- Skipped at Execution: %d", skipped_trades)
                for trade in results.get("executed_trades", []):
                    if trade["status"] in {"failed", "skipped"}:
                        self.logger.info(
                            "- %s: %s %s %s — %s",
                            trade["status"].upper(),
                            trade["action"],
                            trade["quantity"],
                            trade["symbol"],
                            trade_result_detail(trade),
                        )

            self.logger.info("=" * 80)
            self.logger.info("Trading cycle completed")
            self.logger.info("=" * 80)

            return results

        except Exception as exc:
            self.logger.error("Error in trading cycle: %s", exc)
            import traceback
            self.logger.error("Traceback: %s", traceback.format_exc())
            raise
