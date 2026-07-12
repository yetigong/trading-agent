"""Format knowledge-base fields for LLM prompts."""

from typing import Any, Dict, List, Optional, Sequence, Union


def format_knowledge_lessons(lessons: Optional[Sequence[Union[str, Dict[str, Any]]]]) -> str:
    if not lessons:
        return ""
    lines = ["Knowledge Lessons (recent):"]
    for lesson in lessons:
        if isinstance(lesson, dict):
            text = lesson.get("summary") or lesson.get("text") or str(lesson)
        else:
            text = str(lesson)
        text = text.strip()
        if text:
            lines.append(f"- {text}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def format_signal_weights(weights: Optional[Dict[str, Any]]) -> str:
    if not weights:
        return ""
    parts = []
    for key in sorted(weights.keys()):
        try:
            parts.append(f"{key}={float(weights[key]):.2f}")
        except (TypeError, ValueError):
            parts.append(f"{key}={weights[key]}")
    return f"Signal Weights (relative emphasis): {', '.join(parts)}"


def format_trade_bias(bias: Any) -> str:
    if bias is None:
        return ""
    try:
        value = float(bias)
    except (TypeError, ValueError):
        return ""
    if value > 0.05:
        hint = "prefer actionable trades over HOLD when analysis is neutral"
    elif value < -0.05:
        hint = "prefer HOLD / caution when signals are mixed"
    else:
        hint = "neutral — no strong trade/hold preference from recent cycles"
    return f"Recent Trade Bias: {value:+.2f} ({hint})"


def format_analysis_knowledge_block(analysis_params: Optional[Dict[str, Any]]) -> str:
    """KB soft-context block for analysis prompts."""
    params = analysis_params or {}
    sections: List[str] = []
    lessons = format_knowledge_lessons(params.get("knowledge_lessons"))
    if lessons:
        sections.append(lessons)
    weights = format_signal_weights(params.get("signal_weights"))
    if weights:
        sections.append(weights)
    if not sections:
        return ""
    return "\n\n        ".join(sections)


def format_strategy_knowledge_block(strategy_params: Optional[Dict[str, Any]]) -> str:
    """KB soft-context block for strategy prompts (bias is KB-only)."""
    params = strategy_params or {}
    sections: List[str] = []
    bias = format_trade_bias(params.get("recent_trade_bias"))
    if bias:
        sections.append(bias)
    lessons = format_knowledge_lessons(params.get("knowledge_lessons"))
    if lessons:
        sections.append(lessons)
    validation = params.get("backtest_validation_summary")
    if validation:
        sections.append(f"Last Validated Backtest: {validation}")
    if not sections:
        return ""
    return "\n        ".join(sections)
