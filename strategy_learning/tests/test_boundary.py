"""Boundary tests: strategy_learning must not write trading_agent configs."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

FORBIDDEN_MODULES = frozenset(
    {
        "trading_agent.storage.strategy_config_store",
        "trading_agent.storage.preferences_store",
        "trading_agent.storage.rebalance_config_store",
        "trading_agent.agents.promotion",
    }
)
FORBIDDEN_NAMES = frozenset(
    {
        "StrategyConfigStore",
        "PreferencesStore",
        "RebalanceConfigStore",
        "apply_proposed_changes",
        "approve_recommendation",
    }
)

# strategy_learning/ (package root; this file lives under strategy_learning/tests/)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        yield path


def _imported_modules_and_names(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.add(module)
            for alias in node.names:
                names.add(alias.name)
    return modules, names


class TestStrategyLearningBoundary(unittest.TestCase):
    def test_package_does_not_import_config_apply_paths(self):
        violations = []
        for path in _iter_python_files(PACKAGE_ROOT):
            modules, names = _imported_modules_and_names(path)
            bad_modules = modules & FORBIDDEN_MODULES
            bad_names = names & FORBIDDEN_NAMES
            if bad_modules or bad_names:
                violations.append(
                    f"{path.relative_to(PACKAGE_ROOT.parent)}: "
                    f"modules={sorted(bad_modules)} names={sorted(bad_names)}"
                )
        self.assertEqual(
            violations,
            [],
            "strategy_learning must not import config stores or promotion apply helpers:\n"
            + "\n".join(violations),
        )

    def test_package_may_use_json_file_store_only(self):
        # KnowledgeBase persistence is allowed via JsonFileStore / paths.
        store_path = PACKAGE_ROOT / "knowledge" / "store.py"
        source = store_path.read_text(encoding="utf-8")
        self.assertIn("JsonFileStore", source)
        self.assertNotIn("StrategyConfigStore", source)


if __name__ == "__main__":
    unittest.main()
