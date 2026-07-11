from typing import Dict, List, Union

from trading_agent.domain.cycle import TradingDecision


class TradeConsolidator:
    """Merge trading decisions by symbol and net opposing actions."""

    def consolidate(self, decisions: List[TradingDecision]) -> List[TradingDecision]:
        by_symbol: Dict[str, Dict[str, TradingDecision]] = {}

        for decision in decisions:
            symbol = decision.symbol.upper()
            action = decision.action.upper()
            bucket = by_symbol.setdefault(symbol, {})

            if action not in {"BUY", "SELL"}:
                continue

            if action not in bucket:
                bucket[action] = TradingDecision(
                    action=action,
                    symbol=symbol,
                    quantity=decision.quantity,
                    reasoning=decision.reasoning,
                    risk_level=decision.risk_level,
                    source=decision.source,
                )
                continue

            existing = bucket[action]
            if decision.quantity == "ALL" or existing.quantity == "ALL":
                existing.quantity = "ALL"
            else:
                try:
                    existing.quantity = int(existing.quantity) + int(decision.quantity)
                except (TypeError, ValueError):
                    existing.quantity = decision.quantity
            existing.reasoning = f"{existing.reasoning}; {decision.reasoning}".strip("; ")

        consolidated: List[TradingDecision] = []
        for symbol, actions in by_symbol.items():
            buy = actions.get("BUY")
            sell = actions.get("SELL")
            if buy and sell:
                net = self._net_decision(symbol, buy, sell)
                if net:
                    consolidated.append(net)
            elif buy:
                consolidated.append(buy)
            elif sell:
                consolidated.append(sell)

        return consolidated

    def _net_decision(
        self,
        symbol: str,
        buy: TradingDecision,
        sell: TradingDecision,
    ) -> Union[TradingDecision, None]:
        if buy.quantity == "ALL" or sell.quantity == "ALL":
            return sell

        try:
            buy_qty = int(buy.quantity)
            sell_qty = int(sell.quantity)
        except (TypeError, ValueError):
            return sell

        net_qty = sell_qty - buy_qty
        if net_qty == 0:
            return None
        if net_qty > 0:
            return TradingDecision(
                action="SELL",
                symbol=symbol,
                quantity=net_qty,
                reasoning=f"Net of sells and buys: {sell.reasoning}",
                risk_level=sell.risk_level,
                source=sell.source,
            )
        return TradingDecision(
            action="BUY",
            symbol=symbol,
            quantity=abs(net_qty),
            reasoning=f"Net of buys and sells: {buy.reasoning}",
            risk_level=buy.risk_level,
            source=buy.source,
        )
