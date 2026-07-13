"""Smoke tests for the strategy_learning package (Phase 4.5.3)."""

from __future__ import annotations

import unittest


class TestStrategyLearningPackage(unittest.TestCase):
    def test_package_exports(self) -> None:
        import strategy_learning

        self.assertTrue(hasattr(strategy_learning, "__all__"))
        from strategy_learning import (
            BacktestFeedbackAgent,
            KnowledgeBase,
            KnowledgeBaseError,
            format_feedback_banner,
        )

        self.assertTrue(callable(KnowledgeBase))
        self.assertTrue(callable(BacktestFeedbackAgent))
        self.assertTrue(issubclass(KnowledgeBaseError, ValueError))
        self.assertTrue(callable(format_feedback_banner))

    def test_knowledge_subpackage_exports(self) -> None:
        from strategy_learning.knowledge import (
            BacktestFeedbackAgent,
            KnowledgeBase,
            KnowledgeBaseError,
            config_hash,
            make_event_ref,
        )

        self.assertTrue(callable(KnowledgeBase))
        self.assertTrue(callable(BacktestFeedbackAgent))
        self.assertTrue(callable(make_event_ref))
        self.assertTrue(callable(config_hash))
        self.assertTrue(issubclass(KnowledgeBaseError, ValueError))

    def test_placeholder_subpackages_importable(self) -> None:
        import strategy_learning.retrospection  # noqa: F401
        import strategy_learning.sweep  # noqa: F401


if __name__ == "__main__":
    unittest.main()
