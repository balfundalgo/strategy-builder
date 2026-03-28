"""
config.py — App-wide constants and settings paths
"""

import os
from pathlib import Path

APP_NAME    = "Balfund Strategy Builder"
APP_VERSION = "1.0.0"

# Credentials stored in user's AppData so the .exe doesn't need a .env file
APPDATA_DIR   = Path(os.getenv("APPDATA", Path.home())) / "BalfundStrategyBuilder"
CREDS_FILE    = APPDATA_DIR / "credentials.json"
SETTINGS_FILE = APPDATA_DIR / "settings.json"

APPDATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Dhan API endpoints ────────────────────────────────────────────────────────
DHAN_AUTH_URL       = "https://auth.dhan.co/app/generateAccessToken"
DHAN_RENEW_URL      = "https://api.dhan.co/v2/RenewToken"
DHAN_PROFILE_URL    = "https://api.dhan.co/v2/profile"
DHAN_INTRADAY_URL   = "https://api.dhan.co/v2/charts/intraday"
DHAN_HISTORICAL_URL = "https://api.dhan.co/v2/charts/historical"

DHAN_WS_URL_TEMPLATE = (
    "wss://api-feed.dhan.co?version=2"
    "&token={token}&clientId={client_id}&authType=2"
)
INSTRUMENT_CSV_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

# ── Dhan WS packet codes ──────────────────────────────────────────────────────
REQ_SUB_TICKER  = 15
RESP_TICKER     = 2
RESP_PREV_CLOSE = 6
RESP_DISCONNECT = 50

# ── Default instruments to show on dashboard ─────────────────────────────────
DEFAULT_INSTRUMENTS = [
    {"name": "NIFTY 50",   "exchange": "IDX_I", "security_id": "13", "display_prec": 2},
    {"name": "BANK NIFTY", "exchange": "IDX_I", "security_id": "25", "display_prec": 2},
    {"name": "SENSEX",     "exchange": "IDX_I", "security_id": "51", "display_prec": 2},
    {"name": "FINNIFTY",   "exchange": "IDX_I", "security_id": "27", "display_prec": 2},
    {"name": "MIDCPNIFTY", "exchange": "IDX_I", "security_id": "442", "display_prec": 2},
]

# ── Exchange segment map (Dhan numeric → name) ────────────────────────────────
EXCH_SEG_MAP = {
    0: "IDX_I", 1: "NSE_EQ", 2: "NSE_FNO",
    3: "NSE_CURRENCY", 4: "BSE_EQ", 5: "MCX_COMM",
    7: "BSE_CURRENCY", 8: "BSE_FNO",
}

# ── Timeframes ────────────────────────────────────────────────────────────────
TIMEFRAMES = {
    "1 min":  "1",
    "3 min":  "3",
    "5 min":  "5",
    "15 min": "15",
    "25 min": "25",
    "1 Hour": "60",
}
