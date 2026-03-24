# Questrade Price Fetcher (Python)

A GitHub Copilot–assisted Python project for retrieving real-time security
prices from the Questrade API.

## Target Securities

| Symbol  | Name                                          | Exchange |
|---------|-----------------------------------------------|----------|
| MSFT    | Microsoft Corporation                         | NASDAQ   |
| FIE.TO  | iShares Canadian Financial Monthly Income ETF | TSX      |
| XEQT.TO | iShares Core Equity ETF Portfolio             | TSX      |

> **Note:** TSX-listed securities require the `.TO` suffix in the Questrade API
> (e.g. `FIE.TO` not `FIE`). This is already configured in `src/questrade/config.py`.

## GitHub Copilot Customization Files

| File | Type | Purpose |
|------|------|---------|
| `.github/copilot-instructions.md` | Always-on instructions | Project-wide rules for every Copilot session |
| `AGENTS.md` | Agent instructions | Copilot CLI, Coding Agent, and multi-agent guidance |
| `.github/instructions/api.instructions.md` | Path-specific | Rules for `src/questrade/api/` files |
| `.github/instructions/python.instructions.md` | Path-specific | Python coding standards |
| `.github/instructions/testing.instructions.md` | Path-specific | pytest patterns and rules |
| `.github/prompts/fetch-quotes.prompt.md` | Reusable prompt | Trigger a full price-fetch workflow |
| `.github/prompts/add-symbol.prompt.md` | Reusable prompt | Scaffold a new security symbol |
| `.github/prompts/refresh-token.prompt.md` | Reusable prompt | Implement OAuth token refresh logic |
| `.github/prompts/error-handling.prompt.md` | Reusable prompt | Generate typed exception hierarchy |
| `.github/agents/questrade-agent.agent.md` | Custom agent | Autonomous end-to-end quote retrieval |
| `.github/skills/questrade-api/SKILL.md` | Skill | Reusable Questrade API knowledge capsule |

## Setup

### Option A — Virtual environment (recommended for all platforms)

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m questrade.main
```

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m questrade.main
```

### Option B — No virtual environment (Windows quick-start)

```powershell
pip install httpx pydantic
$env:PYTHONPATH = "src"
python -m questrade.main
```

### Configure credentials

```bash
cp .env.example .env
# Edit .env and add your QUESTRADE_REFRESH_TOKEN
```

## Commands

```bash
python -m questrade.main             # Fetch live quotes
pytest                               # Run all tests
pytest --cov=src                     # Run with coverage
ruff check src tests                 # Lint
mypy src                             # Type check
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'questrade'` | No venv, `PYTHONPATH` not set | Use `$env:PYTHONPATH = "src"` (PowerShell) or `PYTHONPATH=src` (bash) |
| `ValidationError` on `bidPrice`/`askPrice` | Markets closed, API returns `None` | Already fixed — `bid_price`/`ask_price` are `float \| None` |
| `SymbolNotFoundError` for FIE or XEQT | Missing `.TO` suffix | Use `FIE.TO` and `XEQT.TO` — configured in `config.py` |
| `BackendUnavailable: setuptools.backends.legacy` | Python 3.14 pip issue | Already fixed in `pyproject.toml` |

## Authentication

Questrade uses OAuth 2.0 with short-lived access tokens (30 min) and
long-lived refresh tokens. Store your initial refresh token in `.env` —
the application rotates it automatically after every successful refresh.

## Resources

- [Questrade API Docs](https://www.questrade.com/api/documentation/getting-started)
- [GitHub Copilot Custom Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
