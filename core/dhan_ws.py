"""
core/dhan_ws.py
───────────────
Dhan WebSocket feed adapted for PyQt6.
Emits Qt signals instead of printing to terminal.

Reuses binary parsing logic from dhan_ws_1m_dashboard.py
with the Dhan epoch normalization fix included.
"""

import time
import json
import struct
import threading
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

import websocket
from PyQt6.QtCore import QObject, pyqtSignal

from config import (
    DHAN_WS_URL_TEMPLATE,
    REQ_SUB_TICKER, RESP_TICKER, RESP_PREV_CLOSE, RESP_DISCONNECT,
    DEFAULT_INSTRUMENTS,
)

log = logging.getLogger("DhanWS")

CANDLE_HISTORY = 50  # completed candles kept per instrument


# ─────────────────────────────────────────────────────────────────────────────
# Dhan epoch normalization  (IST offset bug in some Dhan WS payloads)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_epoch(ts: int) -> int:
    ts = int(ts)
    diff = ts - int(time.time())
    if int(4.5 * 3600) <= diff <= int(6.5 * 3600):
        ts -= 19800
    return ts


def _minute_bucket(epoch: int) -> int:
    epoch = _normalize_epoch(int(epoch))
    return epoch - (epoch % 60)


def _epoch_to_str(ts: Optional[int]) -> str:
    if not ts:
        return "--:--:--"
    ts = _normalize_epoch(int(ts))
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# Binary packet parsers  (Dhan WS v2 protocol)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_header(data: bytes) -> Optional[Dict[str, Any]]:
    """Parse 8-byte Dhan WS header → {resp_code, exchange_segment, security_id, payload}"""
    if len(data) < 8:
        return None
    try:
        resp_code        = data[0]
        exchange_segment = data[1]
        security_id      = struct.unpack(">I", data[2:6])[0]   # big-endian uint32
        # bytes 6-7 = packet length (we ignore, payload = data[8:])
        return {
            "resp_code":        resp_code,
            "exchange_segment": exchange_segment,
            "security_id":      str(security_id),
            "payload":          data[8:],
        }
    except Exception:
        return None


def _parse_ticker(payload: bytes) -> Optional[Dict[str, Any]]:
    """Parse ticker payload (RESP_TICKER=2) → {ltp, ltt_epoch}"""
    if len(payload) < 8:
        return None
    try:
        ltp       = struct.unpack(">f", payload[0:4])[0]   # float32
        ltt_epoch = struct.unpack(">I", payload[4:8])[0]   # uint32
        return {"ltp": ltp, "ltt_epoch": ltt_epoch}
    except Exception:
        return None


def _parse_prev_close(payload: bytes) -> Optional[Dict[str, Any]]:
    """Parse prev-close payload (RESP_PREV_CLOSE=6) → {prev_close}"""
    if len(payload) < 4:
        return None
    try:
        prev_close = struct.unpack(">f", payload[0:4])[0]
        return {"prev_close": prev_close}
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Candle Engine  (builds 1-min OHLCV from raw ticks)
# ─────────────────────────────────────────────────────────────────────────────

class CandleEngine:
    def __init__(self, sec_id: str, name: str, seg: str, display_prec: int = 2):
        self.sec_id       = sec_id
        self.name         = name
        self.seg          = seg
        self.display_prec = display_prec
        self.lock         = threading.Lock()

        self.prev_close:    Optional[float] = None
        self.last_ltp:      Optional[float] = None
        self.last_ltt:      Optional[int]   = None

        self.current:   Optional[Dict] = None
        self.completed: deque          = deque(maxlen=CANDLE_HISTORY)

    def update_prev_close(self, val: float):
        with self.lock:
            self.prev_close = float(val)

    def on_tick(self, ltp: float, ltt_epoch: int):
        ltp        = float(ltp)
        ltt_epoch  = _normalize_epoch(int(ltt_epoch))
        bucket     = _minute_bucket(ltt_epoch)

        with self.lock:
            self.last_ltp = ltp
            self.last_ltt = ltt_epoch

            if self.current is None:
                self.current = {"bucket": bucket, "open": ltp, "high": ltp, "low": ltp, "close": ltp, "ticks": 1}
                return

            if bucket == self.current["bucket"]:
                self.current["high"]  = max(self.current["high"], ltp)
                self.current["low"]   = min(self.current["low"],  ltp)
                self.current["close"] = ltp
                self.current["ticks"] += 1

            elif bucket > self.current["bucket"]:
                self.completed.append(dict(self.current))
                self.current = {"bucket": bucket, "open": ltp, "high": ltp, "low": ltp, "close": ltp, "ticks": 1}
            # older ticks ignored

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            ltp   = self.last_ltp
            pc    = self.prev_close
            chg   = round(ltp - pc, 2)         if (ltp and pc) else None
            chg_p = round((chg / pc) * 100, 2) if (chg is not None and pc) else None
            return {
                "sec_id":       self.sec_id,
                "name":         self.name,
                "seg":          self.seg,
                "display_prec": self.display_prec,
                "ltp":          ltp,
                "prev_close":   pc,
                "chg":          chg,
                "chg_pct":      chg_p,
                "ltt_str":      _epoch_to_str(self.last_ltt),
                "current":      dict(self.current) if self.current else None,
                "history":      list(self.completed),
            }


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Feed  (Qt-signal based)
# ─────────────────────────────────────────────────────────────────────────────

class DhanWsFeed(QObject):
    """
    Runs Dhan WS in a background thread.
    Emits Qt signals for the UI thread to consume.

    Signals:
        tick_update  (str security_id, dict snapshot)  — fires on every tick
        ws_status    (str status_msg)                   — "Connected", "Disconnected", error text
        error        (str message)
    """
    tick_update = pyqtSignal(str, dict)
    ws_status   = pyqtSignal(str)
    error       = pyqtSignal(str)

    def __init__(self, client_id: str, access_token: str, instruments: Optional[List[Dict]] = None):
        super().__init__()
        self.client_id    = client_id
        self.access_token = access_token
        self.instruments  = instruments or DEFAULT_INSTRUMENTS

        self._stop = threading.Event()
        self._ws:   Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread]     = None

        # Build engines
        self.engines: Dict[str, CandleEngine] = {}
        for inst in self.instruments:
            sid = str(inst["security_id"])
            self.engines[sid] = CandleEngine(
                sec_id       = sid,
                name         = inst["name"],
                seg          = inst["exchange"],
                display_prec = inst.get("display_prec", 2),
            )

        # Stats
        self._stats_lock  = threading.Lock()
        self.packet_counts: Dict[Any, int] = {RESP_TICKER: 0, RESP_PREV_CLOSE: 0, RESP_DISCONNECT: 0, "other": 0}
        self.is_connected  = False
        self.last_error:   Optional[str] = None

    # ── WS callbacks ─────────────────────────────────────────────────────────

    def _on_open(self, ws):
        self.is_connected = True
        self.ws_status.emit("Connected")
        log.info("Dhan WS connected — subscribing instruments")

        sub = {
            "RequestCode":     REQ_SUB_TICKER,
            "InstrumentCount": len(self.instruments),
            "InstrumentList":  [
                {"ExchangeSegment": str(i["exchange"]), "SecurityId": str(i["security_id"])}
                for i in self.instruments
            ],
        }
        ws.send(json.dumps(sub))

    def _on_message(self, ws, message):
        if isinstance(message, str):
            return
        data = bytes(message)
        hdr  = _parse_header(data)
        if not hdr:
            return

        code   = hdr["resp_code"]
        sec_id = hdr["security_id"]
        engine = self.engines.get(sec_id)
        if engine is None:
            return

        if code == RESP_TICKER:
            t = _parse_ticker(hdr["payload"])
            if t:
                engine.on_tick(t["ltp"], t["ltt_epoch"])
                snap = engine.snapshot()
                self.tick_update.emit(sec_id, snap)
                with self._stats_lock:
                    self.packet_counts[RESP_TICKER] += 1

        elif code == RESP_PREV_CLOSE:
            p = _parse_prev_close(hdr["payload"])
            if p:
                engine.update_prev_close(p["prev_close"])
                with self._stats_lock:
                    self.packet_counts[RESP_PREV_CLOSE] += 1

        elif code == RESP_DISCONNECT:
            with self._stats_lock:
                self.packet_counts[RESP_DISCONNECT] += 1

        else:
            with self._stats_lock:
                self.packet_counts["other"] += 1

    def _on_error(self, ws, err):
        msg = str(err)
        self.last_error = msg
        self.ws_status.emit(f"Error: {msg}")
        self.error.emit(msg)
        log.error(f"WS error: {msg}")

    def _on_close(self, ws, code, msg):
        self.is_connected = False
        if not self._stop.is_set():
            self.ws_status.emit("Reconnecting…")
        log.info(f"WS closed: {code} {msg}")

    # ── Run loop (auto-reconnect) ─────────────────────────────────────────────

    def _run_loop(self):
        url = DHAN_WS_URL_TEMPLATE.format(token=self.access_token, client_id=self.client_id)
        websocket.enableTrace(False)

        while not self._stop.is_set():
            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_open    = self._on_open,
                    on_message = self._on_message,
                    on_error   = self._on_error,
                    on_close   = self._on_close,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                log.error(f"WS loop exception: {e}")
            finally:
                self.is_connected = False
                if not self._stop.is_set():
                    time.sleep(3)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info("DhanWsFeed started")

    def stop(self):
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self.is_connected = False
        self.ws_status.emit("Disconnected")
        log.info("DhanWsFeed stopped")

    def get_all_snapshots(self) -> Dict[str, Dict]:
        return {sid: eng.snapshot() for sid, eng in self.engines.items()}
