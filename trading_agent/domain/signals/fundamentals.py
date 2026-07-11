from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..serialization import parse_date


@dataclass
class CompanyProfile:
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"sector": self.sector, "industry": self.industry, "market_cap": self.market_cap}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanyProfile":
        return cls(
            sector=data.get("sector"),
            industry=data.get("industry"),
            market_cap=data.get("market_cap"),
        )


@dataclass
class FinancialRatios:
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"pe": self.pe, "pb": self.pb, "roe": self.roe, "debt_to_equity": self.debt_to_equity}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinancialRatios":
        return cls(
            pe=data.get("pe"),
            pb=data.get("pb"),
            roe=data.get("roe"),
            debt_to_equity=data.get("debt_to_equity"),
        )


@dataclass
class QuarterlyEarnings:
    period: str
    report_date: Optional[str] = None
    eps_actual: Optional[float] = None
    eps_estimate: Optional[float] = None
    eps_surprise_pct: Optional[float] = None
    revenue_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "report_date": self.report_date,
            "eps_actual": self.eps_actual,
            "eps_estimate": self.eps_estimate,
            "eps_surprise_pct": self.eps_surprise_pct,
            "revenue_actual": self.revenue_actual,
            "revenue_estimate": self.revenue_estimate,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuarterlyEarnings":
        return cls(
            period=data.get("period", ""),
            report_date=data.get("report_date"),
            eps_actual=data.get("eps_actual"),
            eps_estimate=data.get("eps_estimate"),
            eps_surprise_pct=data.get("eps_surprise_pct"),
            revenue_actual=data.get("revenue_actual"),
            revenue_estimate=data.get("revenue_estimate"),
            summary=data.get("summary"),
        )


@dataclass
class UpcomingEarnings:
    date: str
    eps_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"date": self.date, "eps_estimate": self.eps_estimate}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpcomingEarnings":
        return cls(date=data["date"], eps_estimate=data.get("eps_estimate"))


@dataclass
class FundamentalsSnapshot:
    symbol: str
    profile: CompanyProfile = field(default_factory=CompanyProfile)
    ratios: FinancialRatios = field(default_factory=FinancialRatios)
    latest_quarterly_earnings: Optional[QuarterlyEarnings] = None
    upcoming_earnings: Optional[UpcomingEarnings] = None
    peers_analyzed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "profile": self.profile.to_dict(),
            "ratios": self.ratios.to_dict(),
            "latest_quarterly_earnings": (
                self.latest_quarterly_earnings.to_dict() if self.latest_quarterly_earnings else None
            ),
            "upcoming_earnings": (
                self.upcoming_earnings.to_dict() if self.upcoming_earnings else None
            ),
            "peers_analyzed": self.peers_analyzed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FundamentalsSnapshot":
        latest = data.get("latest_quarterly_earnings")
        upcoming = data.get("upcoming_earnings")
        return cls(
            symbol=data["symbol"],
            profile=CompanyProfile.from_dict(data.get("profile") or {}),
            ratios=FinancialRatios.from_dict(data.get("ratios") or {}),
            latest_quarterly_earnings=QuarterlyEarnings.from_dict(latest) if latest else None,
            upcoming_earnings=UpcomingEarnings.from_dict(upcoming) if upcoming else None,
            peers_analyzed=list(data.get("peers_analyzed") or []),
        )


@dataclass
class FundamentalsPayload:
    symbols: List[FundamentalsSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"symbols": [s.to_dict() for s in self.symbols]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FundamentalsPayload":
        return cls(symbols=[FundamentalsSnapshot.from_dict(s) for s in data.get("symbols", [])])
