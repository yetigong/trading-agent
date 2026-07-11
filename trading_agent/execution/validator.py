from typing import List, Union

from trading_agent.domain.cycle import AdjustedTrade, SkippedTrade, TradePreparationResult, TradingDecision
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot


class TradeValidator:
    """Validate and clip trading decisions against portfolio constraints."""

    def validate(
        self,
        decisions: List[TradingDecision],
        portfolio: PortfolioSnapshot,
        user_preferences=None,
    ) -> TradePreparationResult:
        max_position_size = 0.1
        if user_preferences is not None:
            max_position_size = getattr(user_preferences, "max_position_size", 0.1)

        executable: List[TradingDecision] = []
        adjusted: List[AdjustedTrade] = []
        skipped: List[SkippedTrade] = []

        for decision in decisions:
            action = decision.action.upper()
            symbol = decision.symbol.upper()

            if action == "BUY" and decision.quantity == "ALL":
                skipped.append(SkippedTrade(decision, '"ALL" is invalid for BUY'))
                continue

            if portfolio.open_order_for(symbol, action):
                skipped.append(SkippedTrade(decision, "Conflicting open order (wash trade risk)"))
                continue

            if action == "SELL":
                result = self._validate_sell(decision, portfolio)
            else:
                result = self._validate_buy(decision, portfolio, max_position_size)

            if result is None:
                skipped.append(SkippedTrade(decision, self._skip_reason(decision, portfolio)))
            elif isinstance(result, AdjustedTrade):
                adjusted.append(result)
                executable.append(result.final)
            else:
                executable.append(result)

        sells = [d for d in executable if d.action == "SELL"]
        buys = [d for d in executable if d.action == "BUY"]
        ordered = sells + buys

        return TradePreparationResult(
            raw=list(decisions),
            consolidated=list(decisions),
            executable=ordered,
            adjusted=adjusted,
            skipped=skipped,
        )

    def _validate_sell(
        self,
        decision: TradingDecision,
        portfolio: PortfolioSnapshot,
    ) -> Union[TradingDecision, AdjustedTrade, None]:
        position = portfolio.position_for(decision.symbol)
        available = position.available_qty if position else 0.0

        if available <= 0:
            return None

        if decision.quantity == "ALL":
            final_qty = int(available)
            if final_qty <= 0:
                return None
            if final_qty == available:
                return TradingDecision(
                    action=decision.action,
                    symbol=decision.symbol,
                    quantity=final_qty,
                    reasoning=decision.reasoning,
                    risk_level=decision.risk_level,
                    source=decision.source,
                )
            return AdjustedTrade(
                original=decision,
                final=TradingDecision(
                    action=decision.action,
                    symbol=decision.symbol,
                    quantity=final_qty,
                    reasoning=decision.reasoning,
                    risk_level=decision.risk_level,
                    source=decision.source,
                ),
                reason=f"SELL ALL resolved to {final_qty} available shares",
            )

        try:
            requested = int(decision.quantity)
        except (TypeError, ValueError):
            return None

        if requested <= 0:
            return None
        if requested <= available:
            return decision

        final_qty = int(available)
        return AdjustedTrade(
            original=decision,
            final=TradingDecision(
                action=decision.action,
                symbol=decision.symbol,
                quantity=final_qty,
                reasoning=decision.reasoning,
                risk_level=decision.risk_level,
                source=decision.source,
            ),
            reason=f"Clipped SELL from {requested} to {final_qty} available shares",
        )

    def _validate_buy(
        self,
        decision: TradingDecision,
        portfolio: PortfolioSnapshot,
        max_position_size: float,
    ) -> Union[TradingDecision, AdjustedTrade, None]:
        try:
            requested = int(decision.quantity)
        except (TypeError, ValueError):
            return None

        if requested <= 0:
            return None

        price = self._estimate_price(decision.symbol, portfolio)
        if price <= 0:
            return decision

        buying_power = portfolio.account.buying_power
        if buying_power <= 0:
            return None

        affordable = int(buying_power // price)
        if affordable <= 0:
            return None

        portfolio_value = portfolio.account.portfolio_value or portfolio.account.equity
        max_notional = portfolio_value * max_position_size
        position = portfolio.position_for(decision.symbol)
        current_value = position.market_value if position else 0.0
        remaining_notional = max(0.0, max_notional - current_value)
        max_shares_by_size = int(remaining_notional // price) if remaining_notional > 0 else 0

        final_qty = min(requested, affordable, max_shares_by_size or affordable)
        if final_qty <= 0:
            return None

        if final_qty == requested:
            return decision

        return AdjustedTrade(
            original=decision,
            final=TradingDecision(
                action=decision.action,
                symbol=decision.symbol,
                quantity=final_qty,
                reasoning=decision.reasoning,
                risk_level=decision.risk_level,
                source=decision.source,
            ),
            reason=f"Clipped BUY from {requested} to {final_qty} (buying_power/position size)",
        )

    def _estimate_price(self, symbol: str, portfolio: PortfolioSnapshot) -> float:
        position = portfolio.position_for(symbol)
        if position and position.current_price > 0:
            return position.current_price
        return 0.0

    def _skip_reason(self, decision: TradingDecision, portfolio: PortfolioSnapshot) -> str:
        if decision.action == "SELL":
            position = portfolio.position_for(decision.symbol)
            if not position or position.available_qty <= 0:
                return "No shares available to sell"
            return "Invalid sell quantity"
        if portfolio.account.buying_power <= 0:
            return "Insufficient buying power"
        return "Invalid buy quantity"
