import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from .fmp_cache import read_cache, write_cache
from .fundamentals_base import FundamentalDataProvider

logger = logging.getLogger(__name__)

# FMP legacy /api/v3 paths return 403 for new API keys (Aug 2025+).
FMP_BASE_URL = "https://financialmodelingprep.com/stable"
MAX_SYMBOLS = 13


class FMPFundamentalsProvider(FundamentalDataProvider):
    """Financial Modeling Prep fundamentals provider (stable API)."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")

    def get_fundamentals(self, symbols: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            return {"metrics": {}, "note": "FMP API key not configured"}

        capped = symbols[:MAX_SYMBOLS]
        earnings_by_symbol = self._fetch_recent_earnings(capped)

        metrics: Dict[str, Any] = {}
        for symbol in capped:
            symbol_metrics = self._fetch_symbol_metrics(
                symbol, earnings_by_symbol.get(symbol)
            )
            if symbol_metrics:
                metrics[symbol] = symbol_metrics

        return {"metrics": metrics, "symbols": capped}

    def get_summary(
        self,
        symbols: List[str],
        data: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload = data if data is not None else self.get_fundamentals(symbols)
        if payload.get("note"):
            return payload["note"]

        metrics = payload.get("metrics") or {}
        if not metrics:
            return "No fundamental metrics available."

        parts = []
        for symbol, m in metrics.items():
            pe = m.get("pe")
            growth = m.get("revenue_growth_yoy")
            earnings = m.get("latest_earnings")
            snippet = f"{symbol}: PE={pe}" if pe is not None else symbol
            if growth is not None:
                snippet += f", rev growth={growth}%"
            if earnings:
                snippet += f", earnings={earnings}"
            parts.append(snippet)

        return "; ".join(parts)

    def _fetch_symbol_metrics(
        self,
        symbol: str,
        earnings_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ratios = self._get_json("ratios-ttm", symbol=symbol)
        key_metrics = self._get_json("key-metrics-ttm", symbol=symbol)
        growth = self._get_json("financial-growth", symbol=symbol, limit=1)

        result: Dict[str, Any] = {}
        ratio_row = _first_record(ratios)
        if ratio_row:
            result["pe"] = _safe_float(
                ratio_row.get("priceToEarningsRatioTTM")
                or ratio_row.get("peRatioTTM")
            )
            result["pb"] = _safe_float(ratio_row.get("priceToBookRatioTTM"))
            result["eps"] = _safe_float(ratio_row.get("netIncomePerShareTTM"))

        km_row = _first_record(key_metrics)
        if km_row:
            result["roe"] = _safe_float(km_row.get("returnOnEquityTTM"))
            if result["roe"] is not None:
                result["roe"] = round(result["roe"] * 100, 2)
            if result.get("eps") is None:
                result["eps"] = _safe_float(km_row.get("netIncomePerShareTTM"))

        growth_row = _first_record(growth)
        if growth_row:
            rev_growth = _safe_float(growth_row.get("revenueGrowth"))
            if rev_growth is not None:
                result["revenue_growth_yoy"] = round(rev_growth * 100, 2)

        if earnings_row:
            eps_est = _safe_float(earnings_row.get("epsEstimated"))
            eps_act = _safe_float(earnings_row.get("eps"))
            if eps_est is not None and eps_act is not None:
                beat = "beat" if eps_act >= eps_est else "miss"
                result["latest_earnings"] = (
                    f"{earnings_row.get('date', 'recent')} EPS {eps_act} "
                    f"({beat} est {eps_est})"
                )
            elif earnings_row.get("date"):
                result["latest_earnings"] = str(earnings_row.get("date"))

        return result

    def _fetch_recent_earnings(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        if not symbols:
            return {}

        end = date.today()
        start = end - timedelta(days=90)
        calendar = self._get_json(
            "earnings-calendar",
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        if not isinstance(calendar, list):
            return {}

        wanted = set(symbols)
        by_symbol: Dict[str, Dict[str, Any]] = {}
        for row in calendar:
            sym = row.get("symbol")
            if sym in wanted and sym not in by_symbol:
                by_symbol[sym] = row
        return by_symbol

    def _get_json(self, endpoint: str, **params: Any) -> Any:
        cached = read_cache(endpoint, **params)
        if cached is not None:
            return cached

        query = dict(params)
        query["apikey"] = self.api_key
        url = f"{FMP_BASE_URL}/{endpoint}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (402, 403) and endpoint == "earnings-calendar":
                logger.debug(
                    "FMP earnings calendar unavailable on current plan (%s)",
                    exc.code,
                )
            elif exc.code == 403:
                logger.warning(
                    "FMP request forbidden for %s — verify FMP_API_KEY and stable endpoint access",
                    endpoint,
                )
            else:
                logger.warning("FMP request failed for %s: %s", endpoint, exc)
            return None
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.warning("FMP request failed for %s: %s", endpoint, exc)
            return None

        write_cache(endpoint, payload, **params)
        return payload


def _first_record(data: Any) -> Optional[Dict[str, Any]]:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict):
        return data
    return None


def _safe_float(value: Any) -> Any:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
