# Repository Guidelines

## Project Structure & Module Organization
- `core/`: event bus, models, signal processor, trading engine.
- `api/`: exchange clients (`binance/`, `bybit/`, `websocket/`), plus `base_api.py`.
- `gui/`: PyQt5 app (main window, tabs, dialogs, widgets).
- `conditions/`: pluggable entry/exit rules and factories.
- `risk/`: risk manager and related logic.
- `config/`: `settings.py`, `settings_manager.py`, `constants.py`, `config.json`.
- `utils/`: logging and helpers. `tests/` and top‑level `test_*.py` contain test suites.

## Build, Test, and Development Commands
- Run GUI: `python main.py` — launches the app (reads `config/config.json`).
- Monitor only: `python monitor_trading.py` — headless monitoring loop.
- Tests: `pytest -q` (all) or `pytest -q tests -k futures` (subset).
- Logs (Windows): `type trading_system.log` — inspect recent activity.
Use absolute imports (e.g., `from core.engine import TradingEngine`). Prefer virtual envs and Python 3.10+.

## Coding Style & Naming Conventions
- Language: Python, 4‑space indent, PEP 8.
- Naming: `snake_case` (functions/modules), `PascalCase` (classes), `UPPER_SNAKE` (constants).
- Type hints and docstrings for public APIs.
- Imports: absolute within top‑level packages (`core.*`, `api.*`, ...).
- Logging: use `utils/logger.py`; avoid `print()` in production paths.

## Testing Guidelines
- Framework: `pytest` with deterministic tests; mock exchange/network I/O.
- Location: under `tests/` or top‑level `test_*.py` files.
- Running: `pytest -q`; add regression tests for bug fixes.
- Avoid placing live orders; prefer testnet fixtures.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`). Scope narrowly and write imperative messages.
- PRs: include purpose, what/why, linked issues, and screenshots for GUI changes. Add/adjust tests for new behavior and update docs/config examples when relevant.

## Security & Configuration Tips
- Never commit real API keys. `SettingsManager` reads keys from `config/config.json`.
- For experimentation, set `testnet: true` and validate risk settings before enabling live trading.
- Keep secrets in environment variables or local, untracked config files.

## Architecture Overview
- Flow: `core/data_manager` → `core/signal_processor` → `core/trading_engine` → `risk/` → `api/*` (orders) → GUI updates.
- GUI wiring: `main.py` instantiates `TradingEngine` and passes it to `gui/main_window.py`, which connects Qt signals (`status_changed`, `signal_generated`, etc.) and controls `start()/stop()`.
- Tabs (Entry/Exit/Risk/Time) call engine setters and reflect engine state via timers and signals.

## Testnet How‑To
1) In `config/config.json`, set each enabled exchange `testnet: true` and add API keys with futures permission.
2) Run: `python main.py` (GUI) or `python monitor_trading.py` (headless).
3) Confirm testnet in logs: `type trading_system.log` and check exchange endpoints and “testnet” flags.
4) Start trading from GUI; verify no live orders are placed before switching off testnet.

## PR Template (Use This Checklist)
- Purpose/What & Why; linked Issue ID.
- Changes summary and risk areas; screenshots for GUI.
- Tests: added/updated; run `pytest -q` locally and passed.
- Config/docs: updated examples if behavior or settings changed.
- Security: no secrets committed; testnet covered where applicable.

## CI & Coverage
- Goal: ≥80% line coverage on business logic; mock network/exchange calls.
- Install: `pip install pytest-cov` (optional plugin).
- Local check: `pytest -q --maxfail=1 --cov=core --cov=conditions`.
