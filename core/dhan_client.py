"""
core/dhan_client.py
───────────────────
Handles:
  • Credential save/load  (AppData JSON, never plain-text .env)
  • Token generation via TOTP  (Method 1)
  • Token renewal             (Method 2)
  • Token verification
  • Historical OHLCV fetch    (intraday + daily)
  • Options chain fetch       (for strategy builder)
"""

import json
import time
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests
import pyotp

from config import (
    CREDS_FILE, APPDATA_DIR,
    DHAN_AUTH_URL, DHAN_RENEW_URL, DHAN_PROFILE_URL,
    DHAN_INTRADAY_URL, DHAN_HISTORICAL_URL,
)

log = logging.getLogger("DhanClient")


# ─────────────────────────────────────────────────────────────────────────────
# Credential storage  (AppData JSON)
# ─────────────────────────────────────────────────────────────────────────────

def save_credentials(client_id: str, pin: str, totp_secret: str, access_token: str = "", expiry: str = ""):
    data = {
        "client_id":    client_id,
        "pin":          pin,
        "totp_secret":  totp_secret,
        "access_token": access_token,
        "token_expiry": expiry,
    }
    CREDS_FILE.write_text(json.dumps(data, indent=2))
    log.info(f"Credentials saved to {CREDS_FILE}")


def load_credentials() -> dict:
    if not CREDS_FILE.exists():
        return {}
    try:
        return json.loads(CREDS_FILE.read_text())
    except Exception:
        return {}


def update_token_in_creds(access_token: str, expiry: str = ""):
    creds = load_credentials()
    creds["access_token"] = access_token
    creds["token_expiry"] = expiry
    CREDS_FILE.write_text(json.dumps(creds, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# TOTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def generate_totp(totp_secret: str) -> str:
    totp = pyotp.TOTP(totp_secret)
    code = totp.now()
    log.info(f"TOTP generated: {code} (valid {30 - (int(time.time()) % 30)}s)")
    return code


# ─────────────────────────────────────────────────────────────────────────────
# Token generation / renewal / verification
# ─────────────────────────────────────────────────────────────────────────────

def generate_token_via_totp(client_id: str, pin: str, totp_secret: str) -> dict:
    """
    POST https://auth.dhan.co/app/generateAccessToken
         ?dhanClientId=&pin=&totp=
    """
    totp_code = generate_totp(totp_secret)
    url = f"{DHAN_AUTH_URL}?dhanClientId={client_id}&pin={pin}&totp={totp_code}"
    try:
        resp = requests.post(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "accessToken" in data:
            log.info(f"Token generated. Client: {data.get('dhanClientName', '')}  Expires: {data.get('expiryTime', '')}")
            return {
                "success":      True,
                "access_token": data["accessToken"],
                "expiry":       data.get("expiryTime", ""),
                "client_name":  data.get("dhanClientName", ""),
            }
        return {"success": False, "error": str(data)}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def renew_token(client_id: str, access_token: str) -> dict:
    """GET https://api.dhan.co/v2/RenewToken"""
    headers = {"access-token": access_token, "dhanClientId": client_id, "Content-Type": "application/json"}
    try:
        resp = requests.get(DHAN_RENEW_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "accessToken" in data:
            return {"success": True, "access_token": data["accessToken"], "expiry": data.get("expiryTime", "")}
        return {"success": False, "error": str(data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_token(client_id: str, access_token: str) -> bool:
    if not access_token:
        return False
    headers = {"access-token": access_token, "client-id": client_id}
    try:
        resp = requests.get(DHAN_PROFILE_URL, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def get_fresh_token(client_id: str, pin: str, totp_secret: str, existing_token: str = "") -> dict:
    """
    Smart token manager:
    1. Try to renew existing token (if present and valid)
    2. Else generate fresh via TOTP
    Returns {"success": bool, "access_token": str, "expiry": str, "error": str}
    """
    # Step 1: try renew
    if existing_token:
        if verify_token(client_id, existing_token):
            result = renew_token(client_id, existing_token)
            if result["success"]:
                update_token_in_creds(result["access_token"], result.get("expiry", ""))
                return result

    # Step 2: generate via TOTP
    if totp_secret and pin:
        result = generate_token_via_totp(client_id, pin, totp_secret)
        if result["success"]:
            update_token_in_creds(result["access_token"], result.get("expiry", ""))
        return result

    return {"success": False, "error": "Missing PIN or TOTP secret"}


# ─────────────────────────────────────────────────────────────────────────────
# Historical OHLCV  (Dhan REST)
# ─────────────────────────────────────────────────────────────────────────────

def _dhan_headers(client_id: str, access_token: str) -> dict:
    return {
        "access-token": access_token,
        "client-id":    client_id,
        "Content-Type": "application/json",
    }


def fetch_intraday_ohlcv(
    client_id: str,
    access_token: str,
    security_id: str,
    exchange_segment: str,   # e.g. "IDX_I", "NSE_FNO"
    instrument: str,         # "INDEX", "EQUITY", "FUTIDX", "OPTIDX"
    interval: str = "1",     # "1","3","5","15","25","60"
) -> dict:
    """
    POST /v2/charts/intraday — returns today's intraday candles.
    Returns {"success": bool, "data": DataFrame or None, "error": str}
    """
    import pandas as pd

    payload = {
        "securityId":      security_id,
        "exchangeSegment": exchange_segment,
        "instrument":      instrument,
        "interval":        interval,
        "oi":              False,
    }
    try:
        resp = requests.post(
            DHAN_INTRADAY_URL,
            headers=_dhan_headers(client_id, access_token),
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json()

        # Dhan returns {"open":[], "high":[], "low":[], "close":[], "volume":[], "timestamp":[]}
        if not isinstance(raw, dict) or "timestamp" not in raw:
            return {"success": False, "error": f"Unexpected response: {raw}"}

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(raw["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata"),
            "open":      raw["open"],
            "high":      raw["high"],
            "low":       raw["low"],
            "close":     raw["close"],
            "volume":    raw.get("volume", [0] * len(raw["timestamp"])),
        })
        df.set_index("timestamp", inplace=True)
        return {"success": True, "data": df}

    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_historical_ohlcv(
    client_id: str,
    access_token: str,
    security_id: str,
    exchange_segment: str,
    instrument: str,
    from_date: str,   # "YYYY-MM-DD"
    to_date: str,     # "YYYY-MM-DD"
    expiry_code: int = 0,  # 0=current month, 1=next month
) -> dict:
    """
    POST /v2/charts/historical — returns daily candles for a date range.
    """
    import pandas as pd

    payload = {
        "securityId":      security_id,
        "exchangeSegment": exchange_segment,
        "instrument":      instrument,
        "expiryCode":      expiry_code,
        "fromDate":        from_date,
        "toDate":          to_date,
    }
    try:
        resp = requests.post(
            DHAN_HISTORICAL_URL,
            headers=_dhan_headers(client_id, access_token),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()

        if not isinstance(raw, dict) or "timestamp" not in raw:
            return {"success": False, "error": f"Unexpected response: {raw}"}

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(raw["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata"),
            "open":      raw["open"],
            "high":      raw["high"],
            "low":       raw["low"],
            "close":     raw["close"],
            "volume":    raw.get("volume", [0] * len(raw["timestamp"])),
        })
        df.set_index("timestamp", inplace=True)
        return {"success": True, "data": df}

    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
