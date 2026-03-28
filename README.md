# Balfund Strategy Builder

A professional algorithmic trading strategy builder for NIFTY/SENSEX options via Dhan API.

## Project Structure

```
strategy-builder/
├── main.py                        # Entry point
├── config.py                      # App-wide constants
├── requirements.txt
├── strategy_builder.spec          # PyInstaller build spec
├── .github/workflows/build.yml    # Auto .exe build via GitHub Actions
│
├── core/
│   ├── dhan_client.py             # Token management + REST data fetch
│   └── dhan_ws.py                 # WebSocket live feed (PyQt6 signals)
│
└── ui/
    ├── styles.py                  # Dark theme stylesheet
    ├── main_window.py             # Main window + sidebar navigation
    └── pages/
        ├── dashboard_page.py      # Live market data display
        ├── settings_page.py       # API credential input + connect
        └── placeholder_page.py    # Coming-soon pages for future milestones
```

## Milestone Status

| # | Feature | Status |
|---|---|---|
| M1 | Foundation + Dhan connection + Live Dashboard | ✅ Done |
| M2 | Indicator Engine (RSI, EMA, MACD, Supertrend…) | 🔜 Next |
| M3 | Strategy Builder UI | 🔜 |
| M4 | Charting (Dhan data) | 🔜 |
| M5 | Backtesting Engine | 🔜 |
| M6 | Paper Trading | 🔜 |
| M7 | Live Trading | 🔜 |
| M8 | Packaging + Polish | 🔜 |

## Running Locally (Development)

```bash
pip install -r requirements.txt
python main.py
```

## Building the EXE

### Via GitHub Actions (Recommended)
Push to `main` branch → Actions tab → Download artifact from the latest run.

### Locally on Windows
```bash
pyinstaller strategy_builder.spec --clean
# Output: dist/BalfundStrategyBuilder.exe
```

## Dhan Credentials Setup

1. Go to [web.dhan.co](https://web.dhan.co) → Profile → API Access
2. Enable TOTP — copy the secret key shown
3. Open the app → Settings → Enter Client ID, PIN, TOTP Secret → Click Connect

Credentials are saved in `%APPDATA%\BalfundStrategyBuilder\credentials.json` on the client machine.

## Notes

- No `.env` file needed — credentials are stored in Windows AppData
- Token is auto-renewed on each app start
- WebSocket auto-reconnects on disconnect with 3-second backoff
