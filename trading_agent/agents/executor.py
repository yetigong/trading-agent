"""Trade Executor agent — prepare and submit orders."""

from typing import Any, Dict, List

from trading_agent.agents.base import ConfigurableAgent
from trading_agent.agents.messages import ExecutionReport
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.execution.executor import TradeExecutor
from trading_agent.execution.preparer import TradePreparer


class TradeExecutorAgent(ConfigurableAgent):
    name = "trade_executor"

    def __init__(
        self,
        trade_preparer: TradePreparer,
        trade_executor: TradeExecutor,
        user_preferences: UserPreferences,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.trade_preparer = trade_preparer
        self.trade_executor = trade_executor
        self.user_preferences = user_preferences

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        decisions = list(ctx.get("decisions") or [])
        portfolio = ctx["portfolio"]
        strategy_hold = bool(ctx.get("strategy_hold"))

        preparation = (
            self.trade_preparer.prepare(decisions, portfolio, self.user_preferences)
            if decisions
            else None
        )

        executed: List[Dict[str, Any]] = []
        if preparation and preparation.executable:
            executed = [
                t.to_dict() for t in self.trade_executor.execute(preparation.executable)
            ]

        hold = strategy_hold and len(executed) == 0
        report = ExecutionReport(
            preparation=preparation,
            executed_trades=executed,
            hold=hold,
        )

        ctx["preparation"] = preparation
        ctx["executed_trades"] = executed
        ctx["hold"] = hold
        ctx["execution_report"] = report
        return {"execution_report": report}
