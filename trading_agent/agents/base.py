"""Agent ABC — each specialized agent implements run() on a shared cycle context."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Agent(ABC):
    """Base contract for Phase 4 agents."""

    name: str = "agent"

    @abstractmethod
    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this agent's step. Mutates/extends ctx and returns a result payload."""

    def is_enabled(self) -> bool:
        return True


class ConfigurableAgent(Agent):
    """Agent that can be disabled via constructor flag."""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled
