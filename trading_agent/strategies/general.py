import logging
from typing import Dict, List

from trading_agent.domain.cycle import StrategyContext, TradingDecision
from trading_agent.formatters.strategy_context import format_strategy_context
from trading_agent.llm.client import get_llm_client, LLMClient
from trading_agent.models import TRADING_DECISIONS_JSON_PROMPT, parse_trading_decisions
from .base import TradingStrategy

logger = logging.getLogger(__name__)


class GeneralTradingStrategy(TradingStrategy):
    """General trading strategy using LLM."""

    def __init__(self, llm_client=None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def make_decisions(self, context: StrategyContext) -> List[TradingDecision]:
        strategy_params = context.strategy_params or {}
        context_block = format_strategy_context(context)

        prompt = f"""
        {context_block}

        Strategy Parameters:
        - Decision Timeframe: {strategy_params.get('timeframe', 'immediate')}
        - Risk Management: {strategy_params.get('risk_management', 'standard')}
        - Position Sizing: {strategy_params.get('position_sizing', 'dynamic')}

        Synthesize general, technical, and fundamental analysis above with portfolio
        constraints to produce realistic, executable trades.
        Prefer staying invested when growth is the goal: avoid large idle cash
        unless risk management clearly requires it. Prefer fewer fillable orders
        within buying power and max position size over oversized tickets.

        Deployment rules:
        - In risk-on / growth regimes, target >=85% invested after any trims;
          redeploy freed cash in the same cycle (do not leave large idle cash).
        - Prefer liquid core ETFs already in the universe (e.g. SPY/QQQ/XLK)
          unless multi-horizon signals strongly favor rotation.
        - Only trade symbols from the Tradable Universe list when it is present
          in the context above.

        {TRADING_DECISIONS_JSON_PROMPT}
        """

        try:
            response = self.llm_client.generate_response(prompt)
            raw = parse_trading_decisions(response)
            decisions = [
                TradingDecision(
                    action=d["action"],
                    symbol=d["symbol"],
                    quantity=d["quantity"],
                    reasoning=d.get("reasoning", ""),
                    risk_level=d.get("risk_level", "medium"),
                    source="strategy",
                )
                for d in raw
            ]
            return self.validate_decisions(decisions)
        except Exception as exc:
            logger.error("Error in making trading decisions: %s", exc)
            return []

    def get_strategy_name(self) -> str:
        return "General Trading Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "timeframe": "Decision timeframe (immediate, short-term, long-term)",
            "risk_management": "Risk management approach",
            "position_sizing": "Position sizing method",
        }

    def validate_decisions(self, decisions: List[TradingDecision]) -> List[TradingDecision]:
        validated: List[TradingDecision] = []

        for decision in decisions:
            if decision.action not in {"BUY", "SELL"}:
                continue
            if not decision.symbol:
                continue

            if decision.quantity != "ALL":
                try:
                    qty = int(decision.quantity)
                    if qty <= 0:
                        continue
                    decision.quantity = qty
                except (TypeError, ValueError):
                    continue

            if decision.risk_level not in {"low", "medium", "high"}:
                decision.risk_level = "medium"

            validated.append(decision)

        return validated
