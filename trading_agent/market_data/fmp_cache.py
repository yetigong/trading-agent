import json
import logging
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.market_data.historical_cache import (
    load_manifest,
    save_manifest,
    update_symbol_coverage,
)
from trading_agent.storage.paths import get_cache_dir

logger = logging.getLogger(__name__)

_CACHE_ENABLED_VALUES = {"1", "true", "yes"}


def is_cache_enabled() -> bool:
    value = os.getenv("FMP_CACHE_ENABLED", "true").lower()
    return value in _CACHE_ENABLED_VALUES


def get_fmp_cache_dir() -> Path:
    override = os.getenv("FMP_CACHE_DIR")
    if override:
        return Path(override)
    return get_cache_dir("fmp")


def build_cache_key(endpoint: str, **params: Any) -> str:
    filtered = {
        k: v for k, v in sorted(params.items())
        if k != "apikey" and v is not None
    }
    parts = [endpoint]
    for key, value in filtered.items():
        safe_value = re.sub(r"[^A-Za-z0-9._-]", "_", str(value))
        parts.append(f"{key}_{safe_value}")
    return "__".join(parts)


def cache_file_path(endpoint: str, day: date, **params: Any) -> Path:
    key = build_cache_key(endpoint, **params)
    return get_fmp_cache_dir() / day.isoformat() / f"{key}.json"


def read_cache(endpoint: str, day: Optional[date] = None, **params: Any) -> Optional[Any]:
    if not is_cache_enabled():
        return None

    day = day or datetime.now(timezone.utc).date()
    path = cache_file_path(endpoint, day, **params)
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as f:
            envelope = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read FMP cache %s: %s", path, exc)
        return None

    fetched_at = envelope.get("fetched_at")
    if not fetched_at:
        return None

    try:
        fetched_date = datetime.fromisoformat(fetched_at).date()
    except ValueError:
        return None

    if fetched_date != day:
        return None

    logger.debug("FMP cache hit: %s", endpoint)
    return envelope.get("payload")


def write_cache(endpoint: str, payload: Any, day: Optional[date] = None, **params: Any) -> None:
    if not is_cache_enabled():
        return

    day = day or datetime.now(timezone.utc).date()
    path = cache_file_path(endpoint, day, **params)
    path.parent.mkdir(parents=True, exist_ok=True)

    envelope = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "params": {k: v for k, v in params.items() if k != "apikey"},
        "payload": payload,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)
        f.write("\n")

    symbol = params.get("symbol")
    if symbol:
        record_symbol_coverage(str(symbol), day)


def record_symbol_coverage(symbol: str, day: date) -> None:
    """Track that FMP data was fetched for symbol on day (TTM, not true PIT)."""
    cache_dir = get_fmp_cache_dir()
    manifest = load_manifest(cache_dir)
    update_symbol_coverage(manifest, symbol, day, day)
    manifest["note"] = (
        "FMP stable endpoints are TTM/current — not true point-in-time historical fundamentals."
    )
    save_manifest(cache_dir, manifest)
