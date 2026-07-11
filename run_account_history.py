import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from trading_agent.config import get_config
from trading_agent.domain.account.account_history import AccountHistoryQuery
from trading_agent.models import serialize_for_json
from trading_agent.orchestrator.account_history import AccountHistoryMode

LOG_DIR = Path("logs")


def setup_logging(log_level: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "account_history.log"),
        ],
        force=True,
    )


def print_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print("ACCOUNT HISTORY SUMMARY")
    print("=" * 60)
    print(f"Status: {results['status']}")

    if results["status"] != "success":
        print(f"Error: {results.get('error', 'Unknown error')}")
        return

    snapshot = results.get("snapshot") or {}
    query = results.get("query") or {}
    history = results.get("history") or []

    print(f"Account: {snapshot.get('account_number', 'N/A')} ({snapshot.get('status', 'N/A')})")
    print(f"Period: {query.get('period', 'N/A')}  Timeframe: {results.get('timeframe', 'N/A')}")
    group_by = results.get("group_by") or query.get("group_by")
    if group_by:
        print(f"Grouped by: {group_by}")
    print()
    print(f"Equity (total assets):     ${snapshot.get('equity', 0):>14,.2f}")
    print(f"Portfolio value:           ${snapshot.get('portfolio_value', 0):>14,.2f}")
    print(f"Cash:                      ${snapshot.get('cash', 0):>14,.2f}")
    margin_debt = snapshot.get("margin_debt", 0)
    if margin_debt:
        print(f"Margin debt (borrowed):    ${margin_debt:>14,.2f}")
    print(f"Long market value:         ${snapshot.get('long_market_value', 0):>14,.2f}")
    print(f"Buying power:              ${snapshot.get('buying_power', 0):>14,.2f}")
    print(f"Today's equity change:     ${snapshot.get('daily_equity_change', 0):>14,.2f}")
    print()
    print(f"Period equity change:      ${results.get('period_change', 0):>14,.2f}")
    print(f"Period change (%):          {results.get('period_change_pct', 0) * 100:>14.2f}%")
    print(f"History points:            {len(history):>14}")

    if history:
        print()
        label = "Monthly equity" if group_by == "month" else "Recent equity (last 5 points)"
        print(f"{label}:")
        rows = history if group_by == "month" else history[-5:]
        for point in rows:
            ts = point.get("timestamp", "")[:10]
            if group_by == "month" and len(ts) >= 7:
                ts = ts[:7]
            equity = point.get("equity", 0)
            pnl = point.get("profit_loss", 0)
            pnl_pct = point.get("profit_loss_pct", 0) * 100
            if group_by == "month":
                print(f"  {ts}  equity=${equity:,.2f}  month_change=${pnl:,.2f} ({pnl_pct:+.2f}%)")
            else:
                print(f"  {ts}  equity=${equity:,.2f}  pnl=${pnl:,.2f}")

    print("=" * 60)


def save_artifact(results: dict) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_path = LOG_DIR / f"account_history_{timestamp}.json"

    payload = serialize_for_json(results)
    with artifact_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return artifact_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Alpaca account snapshot and portfolio equity history."
    )
    parser.add_argument(
        "--period",
        default="1M",
        help="History window: 1D, 1W, 1M, 3M, 1A (or 1Y alias for 1 year). Default: 1M",
    )
    parser.add_argument(
        "--timeframe",
        default=None,
        help="Alpaca bar size: 1Min, 5Min, 15Min, 1H, 1D. Not 1M — use --group-by month for monthly breakdown.",
    )
    parser.add_argument(
        "--group-by",
        choices=["month"],
        default=None,
        help="Aggregate daily history into monthly end-of-month equity points.",
    )
    parser.add_argument(
        "--date-end",
        default=None,
        help="End date YYYY-MM-DD (default: current market date)",
    )
    parser.add_argument(
        "--extended-hours",
        action="store_true",
        help="Include extended hours for intraday timeframes",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = get_config()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    query = AccountHistoryQuery(
        period=args.period,
        timeframe=args.timeframe,
        date_end=args.date_end,
        extended_hours=args.extended_hours,
        group_by=args.group_by,
    )

    try:
        mode = AccountHistoryMode(query=query)
        results = mode.execute()

        artifact_path = save_artifact(results)
        logger.info("Account history artifact saved to %s", artifact_path)
        print_summary(results)

        if results["status"] != "success":
            raise SystemExit(1)

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise SystemExit(1) from e
    except Exception as e:
        logger.error("Account history fetch failed: %s", e)
        raise


if __name__ == "__main__":
    main()
