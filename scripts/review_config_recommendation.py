#!/usr/bin/env python3
"""Human-in-the-loop review for pending KB config recommendations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.promotion import (
    approve_recommendation,
    defer_recommendation,
    format_pending_diff,
    reject_recommendation,
    review_status,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review pending knowledge-base config recommendations"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Exit 0 if none pending, exit 1 if pending (CI-friendly)",
    )
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--reject", action="store_true")
    parser.add_argument("--defer", action="store_true")
    parser.add_argument("--recommendation-id", help="Specific recommendation id")
    parser.add_argument("--reason", default="", help="Reject reason")
    parser.add_argument(
        "--require-validate-window",
        action="store_true",
        help="Walk-forward gate: require --validate-artifact before approve",
    )
    parser.add_argument(
        "--validate-artifact",
        help="Held-out backtest artifact path (required with --require-validate-window)",
    )
    parser.add_argument("--data-dir", type=Path, help="Override data directory")
    args = parser.parse_args()

    kb_kwargs = {}
    if args.data_dir:
        kb_kwargs["data_dir"] = args.data_dir
    kb = KnowledgeBase(**kb_kwargs)

    status = review_status(kb)
    pending = status.get("recommendation")

    if args.status:
        if pending:
            print(f"pending: {pending.get('id')}")
            raise SystemExit(1)
        print("none pending")
        raise SystemExit(0)

    actions = sum(bool(x) for x in (args.approve, args.reject, args.defer))
    if actions > 1:
        parser.error("Use only one of --approve / --reject / --defer")

    if not pending and not actions:
        print("No pending_review recommendation.")
        return

    if pending and not actions:
        print(format_pending_diff(pending))
        return

    if not pending:
        print("No pending_review recommendation.", file=sys.stderr)
        raise SystemExit(1)

    if args.approve:
        result = approve_recommendation(
            args.recommendation_id,
            kb=kb,
            require_validate_window=args.require_validate_window,
            validate_artifact=args.validate_artifact,
        )
        print(f"Approved {result['recommendation']['id']}")
        print(f"Applied: {result['applied_changes']}")
        print(f"Audit: {result['audit_path']}")
        return

    if args.reject:
        result = reject_recommendation(
            args.recommendation_id,
            reason=args.reason,
            kb=kb,
        )
        print(f"Rejected {result['recommendation']['id']}")
        print(f"Audit: {result['audit_path']}")
        return

    if args.defer:
        result = defer_recommendation(args.recommendation_id, kb=kb)
        print(f"Deferred {result['recommendation']['id']}")


if __name__ == "__main__":
    main()
