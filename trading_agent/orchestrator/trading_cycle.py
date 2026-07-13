import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from trading_agent.broker.factory import build_broker_client
from trading_agent.config import config_summary, get_config
from trading_agent.llm.client import build_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.models import trade_result_detail
from trading_agent.orchestrator.agent_run import LiveAgentRun
from trading_agent.storage import (
    AnalysisConfigStore,
    BrokerageConfigStore,
    PreferencesStore,
    RebalanceConfigStore,
    SignalConfigStore,
    StrategyConfigStore,
    WatchlistStore,
)

LOG_DIR = Path("logs")


class TradingCycle:
    """Handles the execution of a single trading cycle."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        self.config = get_config()

        self.preferences_store = PreferencesStore()
        self.brokerage_config_store = BrokerageConfigStore()
        self.analysis_config_store = AnalysisConfigStore()
        self.strategy_config_store = StrategyConfigStore()
        self.rebalance_config_store = RebalanceConfigStore()
        self.signal_config_store = SignalConfigStore()
        self.watchlist_store = WatchlistStore()

        self.user_preferences = self.preferences_store.load_preferences()
        self.brokerage_config = self.brokerage_config_store.load_config()
        self.analysis_params = self.analysis_config_store.load()
        self.strategy_params = self.strategy_config_store.load()
        self.rebalance_params = self.rebalance_config_store.load()
        self.signal_config = self.signal_config_store.load_config()
        self.watchlist = self.watchlist_store.load_watchlist()

    def initialize_components(self):
        self.logger.info("Initializing components...")
        self.logger.info("Config: %s", json.dumps(config_summary(self.config)))

        self.logger.info("Initializing LLM client (%s, fallback=%s)...",
                         self.config.llm_provider, self.config.llm_fallback_provider)
        self.llm_client = build_llm_client(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            fallback_provider=self.config.llm_fallback_provider,
            fallback_model=self.config.llm_fallback_model,
            max_retries=self.config.llm_max_retries,
        )

        self.logger.info("Initializing market data provider...")
        self.market_data_provider = AlpacaMarketDataProvider(
            sector_etfs=self.signal_config.sector_etfs,
        )

        self.logger.info("Initializing broker client (%s)...", self.config.broker_provider)
        self.broker_client = build_broker_client(
            config=self.config,
            brokerage_config=self.brokerage_config,
        )

        self.logger.info("Creating live agent run...")
        self.agent = LiveAgentRun(
            risk_tolerance=self.user_preferences.risk_tolerance,
            investment_goal=self.user_preferences.investment_goal,
            max_position_size=self.user_preferences.max_position_size,
            llm_client=self.llm_client,
            market_data_provider=self.market_data_provider,
            broker_client=self.broker_client,
            universe_symbols=list(self.watchlist.symbols or []),
        )

    def execute(self):
        cycle_start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("Starting new trading cycle at %s", cycle_start_time)
        self.logger.info("=" * 80)

        try:
            self.initialize_components()

            self.logger.info("User preferences: %s", json.dumps(self.user_preferences.to_dict(), indent=2))
            self.logger.info("Signal config: %s", json.dumps(self.signal_config.to_dict(), indent=2))
            self.logger.info("Watchlist: %s", json.dumps(self.watchlist.to_dict(), indent=2))
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

                self._maybe_emit_retrospection(results)
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

    def _maybe_emit_retrospection(self, results: Dict[str, Any]) -> None:
        """Evaluate live underperformance and emit an out-of-band signal if needed.

        Failures here are logged and never fail the trading cycle.
        """
        try:
            from strategy_learning.retrospection import (
                RetrospectionDetector,
                cooldown_active,
                default_thresholds,
                has_pending_trigger,
                load_recent_cycle_summaries,
            )

            thresholds = default_thresholds()
            log_dir = LOG_DIR
            pending = has_pending_trigger(log_dir)
            cooling = cooldown_active(
                log_dir,
                cooldown_days=int(thresholds["cooldown_days"]),
            )
            window_days = int(thresholds["window_days"])
            equity_points = self._portfolio_equity_points(window_days=window_days)
            spy_closes = self._spy_closes(window_days=window_days)
            summaries = load_recent_cycle_summaries(log_dir, limit=20)
            detector = RetrospectionDetector(
                window_days=window_days,
                spy_lag_pp=float(thresholds["spy_lag_pp"]),
                hold_streak=int(thresholds["hold_streak"]),
            )
            evaluation = detector.evaluate(
                equity_points=equity_points,
                spy_closes=spy_closes,
                cycle_summaries=summaries,
                cycle_id=results.get("cycle_id"),
                cooldown_active=cooling,
                pending_trigger_exists=pending,
            )
            if evaluation.skipped_reason:
                self.logger.info(
                    "Retrospection skipped (%s)", evaluation.skipped_reason
                )
                return
            if not evaluation.triggered:
                self.logger.debug(
                    "Retrospection not triggered (equity_return=%s spy_return=%s)",
                    evaluation.metrics.get("equity_return"),
                    evaluation.metrics.get("spy_return"),
                )
                return
            path = self.agent.emit_retrospection_signal(
                eval=evaluation,
                log_dir=str(log_dir),
                cycle_artifact_path=results.get("artifact_path"),
            )
            if path:
                self.logger.info(
                    "Retrospection trigger emitted (%s) → %s",
                    "; ".join(evaluation.reasons),
                    path,
                )
        except Exception as exc:
            self.logger.warning(
                "Retrospection evaluation failed (cycle continues): %s", exc
            )

    def _portfolio_equity_points(self, *, window_days: int = 30) -> List[Dict[str, Any]]:
        from strategy_learning.retrospection import portfolio_history_period_for_window
        from trading_agent.domain.broker import PortfolioHistory

        period = portfolio_history_period_for_window(window_days)
        history = self.broker_client.get_portfolio_history(period=period, timeframe="1D")
        if not isinstance(history, PortfolioHistory):
            return []
        points: List[Dict[str, Any]] = []
        for idx, ts in enumerate(history.timestamps or []):
            equity = float(history.equity[idx]) if idx < len(history.equity) else 0.0
            points.append(
                {
                    "timestamp": datetime.fromtimestamp(int(ts), tz=timezone.utc),
                    "equity": equity,
                }
            )
        return points

    def _spy_closes(self, *, window_days: int = 30) -> List[Dict[str, Any]]:
        provider = getattr(self, "market_data_provider", None)
        if provider is None or not hasattr(provider, "get_bars"):
            return []
        # Fetch a few extra calendar days so the rolling window has enough bars.
        bars = provider.get_bars("SPY", days=max(window_days + 5, 35))
        if bars is None or getattr(bars, "empty", True):
            return []
        closes: List[Dict[str, Any]] = []
        close_col = "close" if "close" in bars.columns else bars.columns[-1]
        for idx, row in bars.iterrows():
            ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            closes.append({"timestamp": ts, "close": float(row[close_col])})
        return closes
