import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from trading_agent.domain.signals.fundamentals import (
    CompanyProfile,
    FinancialRatios,
    FundamentalsPayload,
    FundamentalsSnapshot,
    QuarterlyEarnings,
    UpcomingEarnings,
)
from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.signal_status import SignalStatus
from trading_agent.signals.base import SignalProvider
from trading_agent.signals.news import FinnhubClient

logger = logging.getLogger(__name__)


class FundamentalsSignalProvider(SignalProvider):
    def __init__(self, finnhub: Optional[FinnhubClient] = None):
        self.finnhub = finnhub or FinnhubClient()
        self._peer_cache: Dict[str, List[str]] = {}

    @property
    def source_id(self) -> str:
        return "fundamentals"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        if not self.finnhub.configured:
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.FAILED,
                timestamp=now,
                symbols=symbols,
                payload=FundamentalsPayload(),
                error="FINNHUB_API_KEY not configured",
            )

        snapshots: List[FundamentalsSnapshot] = []
        errors = 0
        for symbol in symbols[:10]:
            try:
                snapshots.append(self._fetch_symbol(symbol))
            except Exception:
                errors += 1
                logger.exception("Fundamentals fetch failed for %s", symbol)

        status = SignalStatus.SUCCESS
        if errors and snapshots:
            status = SignalStatus.PARTIAL
        elif errors and not snapshots:
            status = SignalStatus.FAILED

        return SignalSourceResult(
            source_id=self.source_id,
            status=status,
            timestamp=now,
            symbols=symbols,
            payload=FundamentalsPayload(symbols=snapshots),
            error=f"{errors} symbol(s) failed" if errors else None,
        )

    def discover_sector_peers(self, symbols: List[str], limit_per_symbol: int = 2) -> List[str]:
        peers: List[str] = []
        for symbol in symbols:
            try:
                profile = self.finnhub._get("/stock/profile2", {"symbol": symbol})
                sector = profile.get("finnhubIndustry") or profile.get("gsector")
                if not sector:
                    continue
                # Finnhub lacks direct peer API on free tier; use sector label as placeholder peers
                # In production, swap for a peers endpoint or screener.
                cached = self._peer_cache.get(sector, [])
                for p in cached:
                    if p not in symbols and p not in peers:
                        peers.append(p)
                        if len([x for x in peers if x.startswith(sector)]) >= limit_per_symbol:
                            break
            except Exception:
                continue
        return peers

    def _fetch_symbol(self, symbol: str) -> FundamentalsSnapshot:
        profile_data = self.finnhub._get("/stock/profile2", {"symbol": symbol})
        metrics = self.finnhub._get("/stock/metric", {"symbol": symbol, "metric": "all"})
        earnings = self._latest_earnings(symbol)
        upcoming = self._upcoming_earnings(symbol)

        metric = metrics.get("metric") or {}
        return FundamentalsSnapshot(
            symbol=symbol,
            profile=CompanyProfile(
                sector=profile_data.get("finnhubIndustry") or profile_data.get("gsector"),
                industry=profile_data.get("finnhubIndustry"),
                market_cap=profile_data.get("marketCapitalization"),
            ),
            ratios=FinancialRatios(
                pe=metric.get("peBasicExclExtraTTM") or metric.get("peTTM"),
                pb=metric.get("pbQuarterly"),
                roe=metric.get("roeTTM"),
                debt_to_equity=metric.get("totalDebt/totalEquityQuarterly"),
            ),
            latest_quarterly_earnings=earnings,
            upcoming_earnings=upcoming,
            peers_analyzed=[],
        )

    def _latest_earnings(self, symbol: str) -> Optional[QuarterlyEarnings]:
        try:
            data = self.finnhub._get("/stock/earnings", {"symbol": symbol})
            if not data:
                return None
            latest = data[0]
            actual = latest.get("actual")
            estimate = latest.get("estimate")
            surprise = None
            if actual is not None and estimate not in (None, 0):
                surprise = ((actual - estimate) / abs(estimate)) * 100
            period = latest.get("period", "")
            return QuarterlyEarnings(
                period=period,
                report_date=str(latest.get("date", ""))[:10] or None,
                eps_actual=actual,
                eps_estimate=estimate,
                eps_surprise_pct=surprise,
                revenue_actual=latest.get("revenue"),
                revenue_estimate=latest.get("revenueEstimate"),
                summary=latest.get("summary") or latest.get("headline"),
            )
        except Exception:
            return None

    def _upcoming_earnings(self, symbol: str) -> Optional[UpcomingEarnings]:
        try:
            from datetime import date, timedelta

            start = date.today()
            end = start + timedelta(days=90)
            cal = self.finnhub._get(
                "/calendar/earnings",
                {"from": start.isoformat(), "to": end.isoformat(), "symbol": symbol},
            )
            items = cal.get("earningsCalendar") or []
            for item in items:
                if item.get("symbol") == symbol:
                    return UpcomingEarnings(
                        date=str(item.get("date", ""))[:10],
                        eps_estimate=item.get("epsEstimate"),
                    )
        except Exception:
            pass
        return None
