"""Shared helpers for durable per-provider historical caches."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.storage.paths import get_cache_dir

logger = logging.getLogger(__name__)


def load_manifest(cache_dir: Path) -> Dict[str, Any]:
    path = cache_dir / "manifest.json"
    if not path.exists():
        return {"symbols": {}, "updated_at": None}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"symbols": {}, "updated_at": None}
        data.setdefault("symbols", {})
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read manifest %s: %s", path, exc)
        return {"symbols": {}, "updated_at": None}


def save_manifest(cache_dir: Path, manifest: Dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = dict(manifest)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = cache_dir / "manifest.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def update_symbol_coverage(
    manifest: Dict[str, Any],
    symbol: str,
    earliest: date,
    latest: date,
) -> None:
    symbols = manifest.setdefault("symbols", {})
    existing = symbols.get(symbol.upper(), {})
    prev_earliest = existing.get("earliest")
    prev_latest = existing.get("latest")

    new_earliest = earliest.isoformat()
    new_latest = latest.isoformat()
    if prev_earliest and prev_earliest < new_earliest:
        new_earliest = prev_earliest
    if prev_latest and prev_latest > new_latest:
        new_latest = prev_latest

    symbols[symbol.upper()] = {
        "earliest": new_earliest,
        "latest": new_latest,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def coverage_contains(
    manifest: Dict[str, Any],
    symbol: str,
    start: date,
    end: date,
) -> bool:
    entry = manifest.get("symbols", {}).get(symbol.upper())
    if not entry:
        return False
    earliest = entry.get("earliest")
    latest = entry.get("latest")
    if not earliest or not latest:
        return False
    return earliest <= start.isoformat() and latest >= end.isoformat()


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def get_provider_cache_dir(name: str) -> Path:
    return get_cache_dir(name)
