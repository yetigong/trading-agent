# Pull request description guide

Use this format for every PR. Reviewers should understand **why** the change exists and **what** changed in the main flows — without reading every file diff.

---

## Template

```markdown
## Summary

<1–2 short paragraphs: why we are making this change, and what the main change is.>

## Changes

- <Bullet: main flow or subsystem affected>
- <Bullet: key files or modules touched>
- <Optional: breaking changes or migration notes>

## Test plan

- [ ] <How you verified the change>
```

---

## Summary section (required)

Write **1–2 succinct paragraphs** that answer:

1. **Why** — What problem, gap, or goal motivated this PR?
2. **What** — What is the main outcome for users or the system?

### Good example

> Paper trading cycles were failing because the Gemini client still called `gemini-2.0-flash`, which Google shut down (free-tier quota is zero). This PR updates the default model to `gemini-3.1-flash-lite-preview` and improves cycle output so failed Alpaca orders show a readable reason in the summary and JSON artifact.
>
> No new API keys are required; existing `GOOGLE_API_KEY` values continue to work with the updated model list.

### Avoid

- Listing every renamed variable or import
- Copy-pasting the entire commit log
- Vague lines like "misc fixes" or "updated code"

---

## Changes section (required)

Use **bullets grouped by behavior**, not by file. Cover the main flows, subsystems, and important files — stay succinct (typically 3–8 bullets).

### Good example

```markdown
## Changes

- **LLM / Gemini** — Default model moved to `gemini-3.1-flash-lite-preview`; added `scripts/verify_gemini_setup.py` to probe model availability
- **Trading cycle output** — `run_agent.py` summary table includes a Details column; failed trades store `failure_detail` in cycle artifacts
- **Serialization** — `serialize_for_json()` handles UUID order ids from Alpaca
- **Tests** — Added `tests/test_trade_failure_formatting.py`
```

### Grouping tips

| If you changed… | Describe as… |
|-----------------|--------------|
| `run_agent.py`, `trading_agent/orchestrator/trading_cycle.py` | Entry point / cycle orchestration |
| `run_account_history.py`, `account/` | Account history mode |
| `trading_agent/execution/executor.py`, `execute_trades` | Trade execution flow |
| `trading_agent/models.py`, strategy prompts | LLM decision parsing / prompts |
| `trading_agent/config.py`, `.env.example` | Configuration |
| `tests/` | Test coverage (what behavior is now guarded) |

You do **not** need a bullet per file. Combine related edits into one line.

---

## Test requirements (every PR)

Every PR must meet these bars before merge. Doc-only PRs may skip runtime checks but must say so in the Test plan.

| Requirement | What to do |
|-------------|------------|
| Unit / mock suite green | Run `bash scripts/run_tests.sh` (or `.venv/bin/bash scripts/run_tests.sh`) locally; CI `test` job must pass |
| Coverage for changed logic | New or changed business logic has unit or mock-based tests under `tests/` that catch regressions |
| No root-level throwaways | No `test_*.py` at repo root; no committed ad-hoc debug scripts |
| Mocks for CI | Prefer `MockLLMClient` / `MockAlpacaTradingClient` / provider mocks so CI needs no API keys |
| Live APIs when relevant | If you changed Alpaca, LLM, Finnhub, or FMP clients, run `RUN_INTEGRATION=1 bash scripts/run_tests.sh` locally and confirm those tests were **not** skipped |
| Secrets / artifacts | Do not commit `.env`, credentials, `data/`, or `logs/` cycle artifacts |

Main components in a changed flow (orchestrator, execution, signals, strategies, etc.) should have **some** dedicated or end-to-end mock coverage — not 100% line coverage, but enough to catch correctness regressions.

## Test plan (required)

Checklist of what you ran or what reviewers should run. Be specific:

```markdown
## Test plan

- [x] `bash scripts/run_tests.sh`
- [x] (if touching LLM/Alpaca/Finnhub/FMP) `RUN_INTEGRATION=1 bash scripts/run_tests.sh` — integration tests ran, not skipped
- [x] New/changed logic covered under `tests/`
- [x] (optional) Manual smoke: `python run_agent.py` — cycle `Status: success`
```

For doc-only PRs:

```markdown
## Test plan

- [x] Docs only — no code/runtime changes; `bash scripts/run_tests.sh` not required
```

---

## Full example (Phase 1 MVP)

```markdown
## Summary

The trading agent could not reliably complete a paper-trading demo: LLM output was parsed from brittle numbered text, market context was omitted from prompts, and the cycle failed when the model returned no trades. This PR delivers a Phase 1 MVP — env-driven config, structured JSON decisions, HOLD on empty output, and a hardened `run_agent.py` that writes cycle artifacts and prints a human summary.

The goal is a reproducible end-to-end paper cycle on Alpaca with a configurable LLM provider, without requiring code changes to switch models or run a single demo.

## Changes

- **Configuration** — `trading_agent/config.py` and `.env.example` for `LLM_PROVIDER`, `LLM_MODEL`, cycle interval; startup validation
- **LLM loop** — JSON decision parsing in `models.py`; `GeneralTradingStrategy` prompt returns structured decisions; empty list = HOLD
- **Orchestration** — `TradingAgent` accepts injected Alpaca client; market conditions passed into analysis/strategy prompts
- **MVP entry** — `run_agent.py` saves `logs/cycle_*.json` and prints cycle summary
- **Tests** — Mock-based integration test for full cycle + HOLD path; decision parsing unit tests
- **Deploy/docs** — Fixed `docker-compose.yml` Dockerfile path; README MVP section

## Test plan

- [x] `python -m unittest discover tests -v` (6 tests)
- [x] Manual run: `python run_agent.py` with Alpaca paper + Gemini
```

---

## Title guidelines

- Imperative, scoped: **"Fix Gemini defaults and improve trade failure reporting"**
- Not: **"Updates"** or **"Phase 1 stuff"**

Match the **Summary** — if the PR is mostly one theme, the title should reflect that theme.
