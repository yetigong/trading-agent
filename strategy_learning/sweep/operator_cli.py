"""Shared helpers for operator sweep / retrospection CLIs."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.models import serialize_for_json

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


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_json_arg(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def default_sweep_window(*, lookback_days: int = 90) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    return start, end


def save_sweep_artifact(payload: Dict[str, Any], run_label: str, *, log_dir: Path = LOG_DIR) -> Path:
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_label) or "sweep"
    path = log_dir / f"sweep_{timestamp}_{safe_label}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialize_for_json(payload), f, indent=2)
        f.write("\n")
    return path


def save_backtest_artifact(run_dict: Dict[str, Any], run_label: str, *, log_dir: Path = LOG_DIR) -> Path:
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_label) or "run"
    path = log_dir / f"backtest_{timestamp}_{safe_label}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialize_for_json(run_dict), f, indent=2)
        f.write("\n")
    return path
