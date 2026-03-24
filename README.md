# Questrade Quote Fetcher

Real-time security prices from the Questrade API, with both CLI and GUI interfaces.

![Questrade Quote Fetcher GUI](docs/screenshot.png)

## Getting Started

### 1. Get a Questrade API Token

Questrade uses OAuth 2.0 with short-lived access tokens (30 min) and long-lived refresh tokens. You will need a refresh token to authenticate.

1. Log in to your [Questrade account](https://www.questrade.com/api/documentation/getting-started) and generate an API refresh token.
2. Copy the example environment file and paste your token in:

```cmd
copy .env.example .env
```

Open `.env` and set your token:

```
QUESTRADE_REFRESH_TOKEN=your_token_here
```

The app rotates the refresh token automatically after each use — no manual renewal needed.

### 2. Install Dependencies

Create a virtual environment, activate it, and install packages:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

### 3. Configure Your Watchlist

Edit `symbols.json` in the project root to add or remove securities:

```json
[
  { "symbol": "AAPL",  "exchange": "NASDAQ", "name": "Apple Inc." },
  { "symbol": "AMZN",  "exchange": "NASDAQ", "name": "Amazon.com Inc." },
  { "symbol": "GOOGL", "exchange": "NASDAQ", "name": "Alphabet Inc." },
  { "symbol": "MSFT",  "exchange": "NASDAQ", "name": "Microsoft Corporation" }
]
```

For TSX-listed securities, add the `.TO` suffix (e.g. `FIE.TO`).

### 4. Run

```cmd
python -m questrade.main     # Fetch quotes in the terminal (CLI)
python -m questrade --gui    # Launch the GUI window
```

The GUI includes a refresh button and an auto-refresh toggle (10-second interval).

## Development

```cmd
pytest                   # Run tests
pytest --cov=src         # Run with coverage
ruff check src tests     # Lint
mypy src                 # Type check
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: questrade` | Activate the venv, or set `PYTHONPATH=src` |
| `ValidationError` on bid/ask | Markets are closed — `None` values are expected |
| `SymbolNotFoundError` for TSX symbols | Use the `.TO` suffix (e.g. `FIE.TO`) |

## Resources

- [Questrade API Documentation](https://www.questrade.com/api/documentation/getting-started)
