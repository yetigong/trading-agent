"""Smoke tests for the strategy_learning package scaffold (Phase 4.5.1)."""

from __future__ import annotations

import unittest


class TestStrategyLearningScaffold(unittest.TestCase):
    def test_package_importable(self) -> None:
        import strategy_learning

        self.assertTrue(hasattr(strategy_learning, "__all__"))

    def test_placeholder_subpackages_importable(self) -> None:
        import strategy_learning.knowledge  # noqa: F401
        import strategy_learning.retrospection  # noqa: F401
        import strategy_learning.sweep  # noqa: F401


if __name__ == "__main__":
    unittest.main()
