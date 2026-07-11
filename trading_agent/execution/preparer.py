from trading_agent.domain.cycle import TradePreparationResult, TradingDecision
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.execution.consolidator import TradeConsolidator
from trading_agent.execution.validator import TradeValidator


class TradePreparer:
    """Consolidate and validate decisions before broker submission."""

    def __init__(
        self,
        consolidator: TradeConsolidator = None,
        validator: TradeValidator = None,
    ):
        self.consolidator = consolidator or TradeConsolidator()
        self.validator = validator or TradeValidator()

    def prepare(
        self,
        decisions: list,
        portfolio: PortfolioSnapshot,
        user_preferences=None,
    ) -> TradePreparationResult:
        typed = [
            d if isinstance(d, TradingDecision) else TradingDecision.from_dict(d)
            for d in decisions
        ]
        consolidated = self.consolidator.consolidate(typed)
        result = self.validator.validate(consolidated, portfolio, user_preferences)
        result.raw = typed
        result.consolidated = consolidated
        return result
