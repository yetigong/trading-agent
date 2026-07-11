from trading_agent.domain.signals.fundamentals import FundamentalsPayload
from trading_agent.domain.signals.signal_source_result import SignalSourceResult


def format_fundamentals(source: SignalSourceResult) -> str:
    lines = [
        f"=== Signal Source: {source.source_id} ===",
        f"Status: {source.status.value} | Symbols: {', '.join(source.symbols) or 'N/A'}",
    ]
    if source.error:
        lines.append(f"Error: {source.error}")
        return "\n".join(lines)

    payload = source.payload
    if not isinstance(payload, FundamentalsPayload) or not payload.symbols:
        lines.append("No fundamentals data available.")
        return "\n".join(lines)

    for snap in payload.symbols:
        sector = snap.profile.sector or "Unknown"
        industry = snap.profile.industry or "Unknown"
        pe = f"{snap.ratios.pe:.1f}" if snap.ratios.pe is not None else "N/A"
        roe = f"{snap.ratios.roe:.1f}%" if snap.ratios.roe is not None else "N/A"
        lines.append(f"\n{snap.symbol} ({sector} / {industry})")
        lines.append(f"- PE: {pe} | ROE: {roe}")

        earnings = snap.latest_quarterly_earnings
        if earnings:
            eps_a = earnings.eps_actual
            eps_e = earnings.eps_estimate
            surprise = earnings.eps_surprise_pct
            lines.append(
                f"- Latest Q: {earnings.period} ({earnings.report_date or 'N/A'})"
            )
            if eps_a is not None and eps_e is not None:
                sur_str = f" ({surprise:+.1f}%)" if surprise is not None else ""
                lines.append(f"  EPS: {eps_a} vs est {eps_e}{sur_str}")
            if earnings.summary:
                lines.append(f"  Summary: {earnings.summary}")

        if snap.upcoming_earnings:
            ue = snap.upcoming_earnings
            est = f", est EPS {ue.eps_estimate}" if ue.eps_estimate else ""
            lines.append(f"- Next earnings: {ue.date}{est}")

        if snap.peers_analyzed:
            lines.append(f"- Sector peers: {', '.join(snap.peers_analyzed)}")

    return "\n".join(lines)
