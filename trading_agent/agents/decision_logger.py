"""Decision Logger — build DecisionLog and optionally write cycle artifact."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.agents.base import ConfigurableAgent
from trading_agent.agents.messages import DecisionLog
from trading_agent.domain.cycle import CycleResult
from trading_agent.models import serialize_for_json

logger = logging.getLogger(__name__)


class DecisionLoggerAgent(ConfigurableAgent):
    name = "decision_logger"

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        write_artifact: bool = True,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.write_artifact = write_artifact

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        cycle_id = ctx["cycle_id"]
        timestamp = ctx["timestamp"]
        status = ctx.get("status", "success")
        error = ctx.get("error")

        market_summary = ctx.get("market_summary")
        strategy_plan = ctx.get("strategy_plan")
        execution_report = ctx.get("execution_report")
        preparation = ctx.get("preparation")
        decisions = ctx.get("decisions") or []
        executed = ctx.get("executed_trades") or []
        hold = bool(ctx.get("hold"))
        rebalancing = ctx.get("rebalancing")

        if status == "success":
            result = CycleResult(
                status="success",
                cycle_id=cycle_id,
                timestamp=timestamp,
                market_conditions=ctx.get("market_conditions"),
                market_analysis=ctx.get("market_analysis"),
                decisions=[
                    d.to_dict() if hasattr(d, "to_dict") else d
                    for d in (
                        preparation.consolidated if preparation else decisions
                    )
                ],
                hold=hold,
                rebalancing=rebalancing,
                preparation=preparation,
                executed_trades=executed,
            )
        else:
            result = CycleResult(
                status="failed",
                cycle_id=cycle_id,
                timestamp=timestamp,
                error=error or "cycle failed",
                market_conditions=ctx.get("market_conditions"),
                market_analysis=ctx.get("market_analysis"),
            )

        cycle_dict = result.to_dict()
        if market_summary is not None:
            cycle_dict["agents"] = {
                "market_summary": market_summary.to_dict()
                if hasattr(market_summary, "to_dict")
                else market_summary,
                "strategy_plan": strategy_plan.to_dict()
                if strategy_plan is not None and hasattr(strategy_plan, "to_dict")
                else strategy_plan,
                "execution_report": execution_report.to_dict()
                if execution_report is not None and hasattr(execution_report, "to_dict")
                else execution_report,
            }

        artifact_path = None
        if self.write_artifact:
            artifact_path = self._write_artifact(cycle_dict)
            cycle_dict["artifact_path"] = str(artifact_path)

        decision_log = DecisionLog(
            cycle_id=cycle_id,
            timestamp=timestamp,
            market_summary=cycle_dict.get("agents", {}).get("market_summary"),
            strategy_plan=cycle_dict.get("agents", {}).get("strategy_plan"),
            execution_report=cycle_dict.get("agents", {}).get("execution_report"),
            artifact_path=str(artifact_path) if artifact_path else None,
        )

        ctx["cycle_result"] = cycle_dict
        ctx["decision_log"] = decision_log
        return {"decision_log": decision_log, "cycle_result": cycle_dict}

    def _write_artifact(self, cycle_dict: Dict[str, Any]) -> Path:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle_id = cycle_dict.get("cycle_id", "unknown")
        path = self.log_dir / f"cycle_{stamp}_{str(cycle_id)[:8]}.json"
        payload = serialize_for_json(cycle_dict)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("Decision logger wrote cycle artifact to %s", path)
        return path
