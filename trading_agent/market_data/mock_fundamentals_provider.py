from typing import Any, Dict, List

from .fundamentals_base import FundamentalDataProvider


class MockFundamentalsProvider(FundamentalDataProvider):
    """Mock fundamentals provider for tests."""

    def __init__(self, metrics: Dict[str, Any] = None):
        self.metrics = metrics or {
            "AAPL": {
                "pe": 28.5,
                "pb": 45.2,
                "roe": 147.0,
                "revenue_growth_yoy": 4.8,
                "eps": 6.42,
                "latest_earnings": "2026-04-30 EPS 1.65 (beat est 1.62)",
            },
        }

    def get_fundamentals(self, symbols: List[str]) -> Dict[str, Any]:
        filtered = {s: self.metrics[s] for s in symbols if s in self.metrics}
        return {"metrics": filtered, "symbols": symbols}

    def get_summary(self, symbols: List[str], data: Dict[str, Any] = None) -> str:
        payload = data if data is not None else self.get_fundamentals(symbols)
        metrics = payload.get("metrics") or {}
        if not metrics:
            return "No fundamental metrics available."
        parts = []
        for symbol, m in metrics.items():
            parts.append(f"{symbol}: PE={m.get('pe')}, rev growth={m.get('revenue_growth_yoy')}%")
        return "; ".join(parts)
