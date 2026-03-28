"""
ui/main_window.py
──────────────────
Main application window.
  - Sidebar navigation
  - Page switcher (stacked widget)
  - Connects Settings signals to Dashboard feed start/stop
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

from ui.styles import DARK_THEME
from ui.pages.settings_page import SettingsPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.placeholder_page import PlaceholderPage
from config import APP_NAME, APP_VERSION


# ─────────────────────────────────────────────────────────────────────────────
# Nav button
# ─────────────────────────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}   {label}", parent)
        self.setObjectName("nav_btn")
        self.setCheckable(False)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1200, 760)
        self.resize(1360, 820)

        # Apply dark theme
        self.setStyleSheet(DARK_THEME)

        self._active_idx = 0
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Logo
        logo = QLabel(f"⚡ {APP_NAME.split()[0]}")
        logo.setObjectName("sidebar_logo")
        sb_layout.addWidget(logo)

        version = QLabel(f"Strategy Builder  v{APP_VERSION}")
        version.setObjectName("sidebar_version")
        sb_layout.addWidget(version)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        sb_layout.addWidget(divider)
        sb_layout.addSpacing(8)

        # Nav items: (icon, label, enabled_by_default)
        nav_items = [
            ("📊", "Dashboard",        True),
            ("🔧", "Strategy Builder", False),
            ("📈", "Backtester",        False),
            ("▶️",  "Paper Trading",    False),
            ("🚀", "Live Trading",      False),
            ("⚙️",  "Settings",         True),
        ]

        self._nav_buttons = []
        for icon, label, enabled in nav_items:
            btn = NavButton(icon, label)
            btn.setEnabled(enabled)
            if not enabled:
                btn.setToolTip("Available in a future milestone")
            self._nav_buttons.append(btn)
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Connection status at bottom of sidebar
        sb_layout.addWidget(QFrame(objectName="divider"))
        self.lbl_conn_status = QLabel("● Disconnected")
        self.lbl_conn_status.setObjectName("status_disconnected")
        self.lbl_conn_status.setContentsMargins(16, 8, 16, 16)
        sb_layout.addWidget(self.lbl_conn_status)

        main_layout.addWidget(sidebar)

        # ── Pages (stacked widget) ─────────────────────────────────────
        self.pages = QStackedWidget()
        self.pages.setObjectName("content_area")

        # Page 0 — Dashboard
        self.page_dashboard = DashboardPage()
        self.pages.addWidget(self.page_dashboard)

        # Page 1 — Strategy Builder (placeholder)
        self.pages.addWidget(PlaceholderPage(
            "Strategy Builder",
            "Build multi-indicator trading strategies with a visual drag-and-drop interface.\n"
            "Select indicators, set parameters, define entry/exit conditions.",
            "Coming in Milestone 3",
        ))

        # Page 2 — Backtester (placeholder)
        self.pages.addWidget(PlaceholderPage(
            "Backtester",
            "Run your strategies on historical NIFTY/SENSEX options data.\n"
            "See P&L, win rate, drawdown, equity curve and trade log.",
            "Coming in Milestone 5",
        ))

        # Page 3 — Paper Trading (placeholder)
        self.pages.addWidget(PlaceholderPage(
            "Paper Trading",
            "Run your strategy live on real market data without placing real orders.\n"
            "Simulate fills and track live P&L in real time.",
            "Coming in Milestone 6",
        ))

        # Page 4 — Live Trading (placeholder)
        self.pages.addWidget(PlaceholderPage(
            "Live Trading",
            "Execute real orders on NIFTY/SENSEX options via Dhan API.\n"
            "Full safety controls, daily loss limits, and kill switch.",
            "Coming in Milestone 7",
        ))

        # Page 5 — Settings
        self.page_settings = SettingsPage()
        self.pages.addWidget(self.page_settings)

        main_layout.addWidget(self.pages)

        # ── Wire nav buttons ──────────────────────────────────────────
        for idx, btn in enumerate(self._nav_buttons):
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))

        self._switch_page(0)   # start on Dashboard

        # ── Wire Settings → Dashboard ─────────────────────────────────
        self.page_settings.connected.connect(self._on_connected)
        self.page_settings.disconnected.connect(self._on_disconnected)

    def _switch_page(self, idx: int):
        self._active_idx = idx
        self.pages.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == idx)

    def _on_connected(self, client_id: str, access_token: str):
        self.page_dashboard.start_feed(client_id, access_token)
        self.lbl_conn_status.setText("● Connected")
        self.lbl_conn_status.setObjectName("status_connected")
        self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
        self.lbl_conn_status.style().polish(self.lbl_conn_status)
        # Switch to dashboard automatically
        self._switch_page(0)

    def _on_disconnected(self):
        self.page_dashboard.stop_feed()
        self.lbl_conn_status.setText("● Disconnected")
        self.lbl_conn_status.setObjectName("status_disconnected")
        self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
        self.lbl_conn_status.style().polish(self.lbl_conn_status)

    def closeEvent(self, event):
        """Clean up WS threads on close."""
        self.page_dashboard.stop_feed()
        super().closeEvent(event)
