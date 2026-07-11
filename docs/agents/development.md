# Development guide

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Alpaca paper keys and GOOGLE_API_KEY (or other LLM key)
```

Always use the venv: `.venv/bin/python …`

## Run locally

**Single paper-trading cycle (MVP):**

```bash
.venv/bin/python run_agent.py
```

**Scheduled service:**

```bash
.venv/bin/python trading_service.py
```

**Verify Gemini API / model:**

```bash
.venv/bin/python scripts/verify_gemini_setup.py
```

## Tests

```bash
.venv/bin/python -m unittest discover tests -v
```

Integration tests use `LLM_PROVIDER=mock` and injected mocks — no live API keys required.

Root-level `test_*.py` files are manual smoke scripts, not part of CI discovery.

## Coding conventions

- **Python 3.9+** compatible (match existing style)
- **Logging** over `print()` in library/orchestration code
- **Env config** — add new settings to `config.py` + `.env.example`, validate in `validate_config()`
- **LLM decisions** — JSON array under `"decisions"` key; parsed by `parse_trading_decisions()`
- **Errors from Alpaca** — store on trade dict as `error` + human `failure_detail` via `format_trade_failure()`
- **JSON artifacts** — use `serialize_for_json()` for UUID/datetime safety

## Git / PR workflow

- Branch from `main`; keep PRs focused
- Follow [pr-description.md](pr-description.md) for PR body format
- Do not commit `.env`, credentials, or `logs/` cycle artifacts with secrets
- Run tests before pushing

## Docker

```bash
podman build -t trading-agent -f aws/deployment/Dockerfile .
```

See `aws/deployment/README.md` for ECS deployment.
