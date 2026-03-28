"""
ui/pages/dashboard_page.py
───────────────────────────
Live dashboard: shows real-time LTP + change for all subscribed instruments.
Data comes from DhanWsFeed (WebSocket) via Qt signals.
Also shows 1-min candles for selected instruments.
"""

from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QSizePolicy,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont

from core.dhan_ws import DhanWsFeed
from config import DEFAULT_INSTRUMENTS
from ui.styles import COLOR_UP, COLOR_DOWN, COLOR_NEUTRAL


# ─────────────────────────────────────────────────────────────────────────────
# Single instrument row widget
# ─────────────────────────────────────────────────────────────────────────────

class InstrumentRow(QFrame):
    def __init__(self, name: str, seg: str, sec_id: str, display_prec: int = 2):
        super().__init__()
        self.setObjectName("instrument_row")
        self.name         = name
        self.sec_id       = sec_id
        self.display_prec = display_prec

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        # Name + badge
        left = QVBoxLayout()
        left.setSpacing(4)
        self.lbl_name = QLabel(name)
        self.lbl_name.setObjectName("inst_name")

        seg_badge = QLabel(seg)
        seg_badge.setObjectName("inst_seg")
        seg_badge.setFixedHeight(18)
        seg_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        left.addWidget(self.lbl_name)
        left.addWidget(seg_badge)
        layout.addLayout(left)
        layout.addStretch()

        # LTP + change
        right = QVBoxLayout()
        right.setSpacing(2)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_ltp = QLabel("--")
        self.lbl_ltp.setObjectName("inst_ltp_neutral")
        self.lbl_ltp.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_chg = QLabel("")
        self.lbl_chg.setObjectName("inst_chg_up")
        self.lbl_chg.setAlignment(Qt.AlignmentFlag.AlignRight)

        right.addWidget(self.lbl_ltp)
        right.addWidget(self.lbl_chg)
        layout.addLayout(right)

        # Candle info (current 1m)
        candle_frame = QFrame()
        candle_frame.setFixedWidth(220)
        cl = QHBoxLayout(candle_frame)
        cl.setContentsMargins(12, 0, 0, 0)
        cl.setSpacing(12)

        self.lbl_open  = self._candle_lbl("O: --")
        self.lbl_high  = self._candle_lbl("H: --")
        self.lbl_low   = self._candle_lbl("L: --")
        self.lbl_close = self._candle_lbl("C: --")

        for w in [self.lbl_open, self.lbl_high, self.lbl_low, self.lbl_close]:
            cl.addWidget(w)

        layout.addWidget(candle_frame)

        # Last tick time
        self.lbl_time = QLabel("--:--:--")
        self.lbl_time.setFixedWidth(70)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(self.lbl_time)

    def _candle_lbl(self, txt):
        lbl = QLabel(txt)
        lbl.setStyleSheet("color: #4a5568; font-size: 11px;")
        return lbl

    def update_from_snapshot(self, snap: dict):
        prec = snap.get("display_prec", 2)
        ltp  = snap.get("ltp")
        chg  = snap.get("chg")
        chgp = snap.get("chg_pct")

        # LTP colour
        if ltp is not None:
            ltp_txt = f"{ltp:,.{prec}f}"
            if chg is None or chg == 0:
                self.lbl_ltp.setObjectName("inst_ltp_neutral")
                color = COLOR_NEUTRAL
            elif chg > 0:
                self.lbl_ltp.setObjectName("inst_ltp_up")
                color = COLOR_UP
            else:
                self.lbl_ltp.setObjectName("inst_ltp_down")
                color = COLOR_DOWN
            self.lbl_ltp.setText(ltp_txt)
            self.lbl_ltp.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")

        if chg is not None and chgp is not None:
            arrow  = "▲" if chg >= 0 else "▼"
            color  = COLOR_UP if chg >= 0 else COLOR_DOWN
            chg_txt = f"{arrow} {abs(chg):,.{prec}f}  ({abs(chgp):.2f}%)"
            self.lbl_chg.setText(chg_txt)
            self.lbl_chg.setStyleSheet(f"color: {color}; font-size: 12px;")

        # Current 1m candle
        cur = snap.get("current")
        if cur:
            p = prec
            self.lbl_open.setText(f"O: {cur['open']:,.{p}f}")
            self.lbl_high.setText(f"H: {cur['high']:,.{p}f}")
            self.lbl_low.setText( f"L: {cur['low']:,.{p}f}")
            self.lbl_close.setText(f"C: {cur['close']:,.{p}f}")

        self.lbl_time.setText(snap.get("ltt_str", "--:--:--"))


# ─────────────────────────────────────────────────────────────────────────────
# Header row (column labels)
# ─────────────────────────────────────────────────────────────────────────────

class TableHeader(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(0)

        def hdr(txt, align=Qt.AlignmentFlag.AlignLeft):
            lbl = QLabel(txt)
            lbl.setStyleSheet("color: #475569; font-size: 11px; font-weight: bold; text-transform: uppercase;")
            lbl.setAlignment(align)
            return lbl

        layout.addWidget(hdr("Instrument"))
        layout.addStretch()
        layout.addWidget(hdr("LTP / Change", Qt.AlignmentFlag.AlignRight))
        w = QWidget(); w.setFixedWidth(220)
        wl = QHBoxLayout(w); wl.setContentsMargins(12,0,0,0); wl.setSpacing(12)
        for t in ["Open","High","Low","Close"]:
            wl.addWidget(hdr(t))
        layout.addWidget(w)
        t = hdr("Last Tick", Qt.AlignmentFlag.AlignRight); t.setFixedWidth(70)
        layout.addWidget(t)


# ─────────────────────────────────────────────────────────────────────────────
# Stats bar at the top
# ─────────────────────────────────────────────────────────────────────────────

class StatsBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setFixedHeight(70)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(0)

        self.lbl_ws_status  = self._stat("WS Status", "--")
        self.lbl_tickers    = self._stat("Ticker Packets", "0")
        self.lbl_instruments= self._stat("Instruments", "0")
        self.lbl_time       = self._stat("Local Time", "--:--:--")

        for w in [self.lbl_ws_status, self.lbl_tickers, self.lbl_instruments, self.lbl_time]:
            layout.addWidget(w)
            if w is not self.lbl_time:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color: #2d3148; margin: 8px 24px;")
                layout.addWidget(sep)

    def _stat(self, label, value):
        frame = QFrame()
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0,0,0,0)
        fl.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748b; font-size: 10px; text-transform: uppercase;")
        val = QLabel(value)
        val.setObjectName("stat_value")
        val.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: bold;")
        fl.addWidget(lbl)
        fl.addWidget(val)
        frame._val_lbl = val
        return frame

    def update_ws_status(self, status: str):
        color = "#4ade80" if "Connected" in status else "#facc15" if "Reconnect" in status else "#f87171"
        self.lbl_ws_status._val_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        self.lbl_ws_status._val_lbl.setText(status)

    def update_tickers(self, count: int):
        self.lbl_tickers._val_lbl.setText(f"{count:,}")

    def update_instruments(self, count: int):
        self.lbl_instruments._val_lbl.setText(str(count))

    def update_time(self):
        self.lbl_time._val_lbl.setText(datetime.now().strftime("%H:%M:%S"))


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Page
# ─────────────────────────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ws_feed: Optional[DhanWsFeed] = None
        self._rows: Dict[str, InstrumentRow] = {}
        self._build_ui()

        # Clock timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Live Dashboard")
        title.setObjectName("page_title")
        title.setContentsMargins(0,0,0,0)
        hdr.addWidget(title)
        hdr.addStretch()

        self.btn_reconnect = QPushButton("↺  Reconnect")
        self.btn_reconnect.setObjectName("btn_secondary")
        self.btn_reconnect.setFixedHeight(36)
        self.btn_reconnect.setVisible(False)
        self.btn_reconnect.clicked.connect(self._reconnect)
        hdr.addWidget(self.btn_reconnect)
        root.addLayout(hdr)

        sub = QLabel("Real-time indices feed via Dhan WebSocket. 1-minute candles built locally from tick data.")
        sub.setObjectName("page_subtitle")
        sub.setContentsMargins(0,0,0,0)
        root.addWidget(sub)

        # ── Stats bar ─────────────────────────────────────────────────
        self.stats_bar = StatsBar()
        root.addWidget(self.stats_bar)

        # ── Not connected placeholder ─────────────────────────────────
        self.placeholder = QFrame()
        self.placeholder.setObjectName("card")
        ph_layout = QVBoxLayout(self.placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lbl = QLabel("⚡  Not connected\n\nGo to Settings and enter your Dhan credentials to start receiving live data.")
        ph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lbl.setStyleSheet("color: #475569; font-size: 14px; line-height: 1.6;")
        ph_layout.addWidget(ph_lbl)
        root.addWidget(self.placeholder)

        # ── Instrument table ──────────────────────────────────────────
        self.table_container = QWidget()
        self.table_container.setVisible(False)
        tbl_layout = QVBoxLayout(self.table_container)
        tbl_layout.setContentsMargins(0,0,0,0)
        tbl_layout.setSpacing(4)

        tbl_layout.addWidget(TableHeader())

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        tbl_layout.addWidget(divider)

        # Instrument rows
        self._rows_container = QVBoxLayout()
        self._rows_container.setSpacing(4)
        tbl_layout.addLayout(self._rows_container)

        root.addWidget(self.table_container)
        root.addStretch()

    # ── Called from MainWindow when connection is established ─────────────────

    def start_feed(self, client_id: str, access_token: str):
        """Start WebSocket feed with given credentials."""
        # Stop previous feed if any
        self.stop_feed()

        self._ws_feed = DhanWsFeed(client_id, access_token)
        self._ws_feed.tick_update.connect(self._on_tick)
        self._ws_feed.ws_status.connect(self._on_ws_status)

        self._build_rows()
        self._ws_feed.start()

        self.placeholder.setVisible(False)
        self.table_container.setVisible(True)
        self.stats_bar.update_instruments(len(DEFAULT_INSTRUMENTS))

    def stop_feed(self):
        if self._ws_feed:
            self._ws_feed.stop()
            self._ws_feed = None
        self.placeholder.setVisible(True)
        self.table_container.setVisible(False)
        self.stats_bar.update_ws_status("Disconnected")

    def _build_rows(self):
        # Clear existing rows
        while self._rows_container.count():
            item = self._rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

        for inst in DEFAULT_INSTRUMENTS:
            row = InstrumentRow(
                name         = inst["name"],
                seg          = inst["exchange"],
                sec_id       = str(inst["security_id"]),
                display_prec = inst.get("display_prec", 2),
            )
            self._rows[str(inst["security_id"])] = row
            self._rows_container.addWidget(row)

    @pyqtSlot(str, dict)
    def _on_tick(self, sec_id: str, snap: dict):
        row = self._rows.get(sec_id)
        if row:
            row.update_from_snapshot(snap)
        # Update ticker count
        if self._ws_feed:
            count = self._ws_feed.packet_counts.get(2, 0)  # RESP_TICKER = 2
            self.stats_bar.update_tickers(count)

    @pyqtSlot(str)
    def _on_ws_status(self, status: str):
        self.stats_bar.update_ws_status(status)
        self.btn_reconnect.setVisible("Error" in status or "Disconnect" in status)

    def _reconnect(self):
        if self._ws_feed:
            self._ws_feed.stop()
            self._ws_feed.start()
            self.btn_reconnect.setVisible(False)

    def _tick_clock(self):
        self.stats_bar.update_time()
