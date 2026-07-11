import logging
from typing import Dict, List, Optional

from trading_agent.domain.cycle.strategy_context import StrategyContext
from trading_agent.formatters.strategy_context import format_strategy_context
from trading_agent.llm.client import get_llm_client, LLMClient
from trading_agent.models import TRADING_DECISIONS_JSON_PROMPT, parse_trading_decisions
from .base import TradingStrategy

logger = logging.getLogger(__name__)


class GeneralTradingStrategy(TradingStrategy):
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def make_decisions(self, context: StrategyContext) -> List[Dict]:
        prompt = f"""
        {format_strategy_context(context)}

        {TRADING_DECISIONS_JSON_PROMPT}
        """

        try:
            response = self.llm_client.generate_response(prompt)
            decisions = parse_trading_decisions(response)
            return self.validate_decisions(decisions)
        except Exception as e:
            logger.error("Error in making trading decisions: %s", e)
            return []

    def get_strategy_name(self) -> str:
        return "General Trading Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "timeframe": "Decision timeframe (immediate, short-term, long-term)",
            "risk_management": "Risk management approach (conservative, standard, aggressive)",
            "position_sizing": "Position sizing method (fixed, dynamic, percentage-based)",
        }

    def validate_decisions(self, decisions: List[Dict]) -> List[Dict]:
        validated_decisions = []

        for decision in decisions:
            if not all(k in decision for k in ["action", "symbol", "quantity", "reasoning", "risk_level"]):
                continue

            if decision["action"] not in ["BUY", "SELL"]:
                continue

            if decision["quantity"] != "ALL":
                try:
                    decision["quantity"] = int(decision["quantity"])
                    if decision["quantity"] <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

            if decision["risk_level"] not in ["low", "medium", "high"]:
                continue

            validated_decisions.append(decision)

        return validated_decisions
