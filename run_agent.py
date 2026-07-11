import json
import logging
from datetime import datetime
from pathlib import Path

from agent.trading_cycle import TradingCycle
from trading_agent.config import config_summary, get_config, validate_config
from trading_agent.models import serialize_for_json, trade_result_detail

LOG_DIR = Path("logs")


def setup_logging(log_level: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "trading_agent.log"),
        ],
        force=True,
    )


def print_cycle_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print("TRADING CYCLE SUMMARY")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Cycle ID: {results.get('cycle_id', 'N/A')}")

    if results["status"] != "success":
        print(f"Error: {results.get('error', 'Unknown error')}")
        return

    print(f"Analysis Strategy: {results.get('analysis_strategy')}")
    print(f"Hold: {results.get('hold', False)}")
    print(f"Decisions: {len(results.get('decisions', []))}")
    print(f"Executed Trades: {len(results.get('executed_trades', []))}")

    trades = results.get("executed_trades", [])
    if trades:
        print(f"\n  {'Action':<6} {'Qty':>5}  {'Symbol':<6} {'Status':<9} Details")
        print(f"  {'-' * 6} {'-' * 5}  {'-' * 6} {'-' * 9} {'-' * 40}")
        for trade in trades:
            qty = trade.get("quantity", "")
            print(
                f"  {trade['action']:<6} {str(qty):>5}  "
                f"{trade['symbol']:<6} {trade['status']:<9} {trade_result_detail(trade)}"
            )

    print("=" * 60)


def save_cycle_artifact(results: dict) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cycle_id = results.get("cycle_id", "unknown")
    artifact_path = LOG_DIR / f"cycle_{timestamp}_{cycle_id[:8]}.json"

    payload = serialize_for_json(results)
    with artifact_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return artifact_path


def main():
    config = get_config()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    try:
        validate_config(config)
        logger.info("Starting MVP trading cycle with config: %s", config_summary(config))

        cycle = TradingCycle()
        results = cycle.execute()

        artifact_path = save_cycle_artifact(results)
        logger.info("Cycle artifact saved to %s", artifact_path)
        print_cycle_summary(results)

        if results["status"] != "success":
            raise SystemExit(1)

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise SystemExit(1) from e
    except Exception as e:
        logger.error("Trading agent failed: %s", e)
        raise


if __name__ == "__main__":
    main()
