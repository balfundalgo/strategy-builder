"""
ui/pages/settings_page.py
──────────────────────────
Settings screen: enter Dhan credentials, connect, verify token.
Credentials are saved to AppData (not .env).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from core.dhan_client import load_credentials, save_credentials, get_fresh_token


# ─────────────────────────────────────────────────────────────────────────────
# Worker thread — so the UI doesn't freeze during token fetch
# ─────────────────────────────────────────────────────────────────────────────

class ConnectWorker(QObject):
    finished = pyqtSignal(dict)   # {"success": bool, "access_token": str, "error": str, ...}

    def __init__(self, client_id, pin, totp_secret, existing_token=""):
        super().__init__()
        self.client_id      = client_id
        self.pin            = pin
        self.totp_secret    = totp_secret
        self.existing_token = existing_token

    def run(self):
        result = get_fresh_token(
            client_id      = self.client_id,
            pin            = self.pin,
            totp_secret    = self.totp_secret,
            existing_token = self.existing_token,
        )
        self.finished.emit(result)


# ─────────────────────────────────────────────────────────────────────────────
# Settings Page
# ─────────────────────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """
    Emits connected(client_id, access_token) when successfully connected.
    Parent (MainWindow) listens and unlocks the rest of the app.
    """
    connected    = pyqtSignal(str, str)   # client_id, access_token
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: QThread  = None
        self._worker           = None
        self._is_connected     = False
        self._access_token     = ""
        self._client_id        = ""
        self._build_ui()
        self._load_saved_creds()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # ── Page header ──────────────────────────────────────────────
        title = QLabel("Settings")
        title.setObjectName("page_title")
        root.addWidget(title)

        sub = QLabel("Configure your Dhan API credentials to connect to live market data.")
        sub.setObjectName("page_subtitle")
        root.addWidget(sub)

        # ── Content card ─────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Section title
        section_lbl = QLabel("Dhan API Credentials")
        section_lbl.setObjectName("label_bold")
        card_layout.addWidget(section_lbl)

        hint = QLabel(
            "Find these at  web.dhan.co → Profile → API Access\n"
            "Enable TOTP and copy the secret key shown."
        )
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        card_layout.addWidget(divider)

        # ── Form fields ──────────────────────────────────────────────
        self.field_client_id   = self._field(card_layout, "Client ID",    "Your 10-digit Dhan Client ID")
        self.field_pin         = self._field(card_layout, "PIN",          "Your 4-digit trading PIN", echo=True)
        self.field_totp        = self._field(card_layout, "TOTP Secret",  "TOTP secret from web.dhan.co (e.g. LETTKFD…)")

        # ── Buttons ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_connect = QPushButton("🔗  Connect to Dhan")
        self.btn_connect.setObjectName("btn_primary")
        self.btn_connect.setFixedHeight(44)
        self.btn_connect.clicked.connect(self._on_connect)
        btn_row.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("btn_danger")
        self.btn_disconnect.setFixedHeight(44)
        self.btn_disconnect.setVisible(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        btn_row.addWidget(self.btn_disconnect)

        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        # ── Status message ───────────────────────────────────────────
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        card_layout.addWidget(self.lbl_status)

        root.addWidget(card)

        # ── Token info card (shown after connect) ────────────────────
        self.token_card = QFrame()
        self.token_card.setObjectName("card")
        self.token_card.setVisible(False)
        tc_layout = QVBoxLayout(self.token_card)
        tc_layout.setContentsMargins(24, 20, 24, 20)
        tc_layout.setSpacing(8)

        self.lbl_token_title = QLabel("✅  Connected Successfully")
        self.lbl_token_title.setObjectName("label_bold")
        self.lbl_token_title.setStyleSheet("color: #4ade80; font-size: 15px;")
        tc_layout.addWidget(self.lbl_token_title)

        self.lbl_token_detail = QLabel("")
        self.lbl_token_detail.setWordWrap(True)
        tc_layout.addWidget(self.lbl_token_detail)

        root.addSpacing(16)
        root.addWidget(self.token_card)
        root.addStretch()

    def _field(self, layout, label_text, placeholder, echo=False):
        lbl = QLabel(label_text)
        lbl.setObjectName("label_bold")
        layout.addWidget(lbl)
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(42)
        if echo:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(field)
        return field

    def _load_saved_creds(self):
        creds = load_credentials()
        if creds.get("client_id"):
            self.field_client_id.setText(creds["client_id"])
        if creds.get("pin"):
            self.field_pin.setText(creds["pin"])
        if creds.get("totp_secret"):
            self.field_totp.setText(creds["totp_secret"])

    # ── Connect ───────────────────────────────────────────────────────────────

    def _on_connect(self):
        client_id   = self.field_client_id.text().strip()
        pin         = self.field_pin.text().strip()
        totp_secret = self.field_totp.text().strip()

        if not client_id:
            self._set_status("❌  Client ID is required.", error=True)
            return
        if not pin:
            self._set_status("❌  PIN is required.", error=True)
            return
        if not totp_secret:
            self._set_status("❌  TOTP Secret is required.", error=True)
            return

        # Save immediately (so token gets persisted on success)
        save_credentials(client_id, pin, totp_secret)

        self._set_status("⏳  Connecting to Dhan API…", connecting=True)
        self.btn_connect.setEnabled(False)
        self._set_fields_enabled(False)

        # Load existing token if available
        from core.dhan_client import load_credentials as lc
        existing = lc().get("access_token", "")

        # Spin off worker thread
        self._worker = ConnectWorker(client_id, pin, totp_secret, existing)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_connect_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_connect_finished(self, result: dict):
        self.btn_connect.setEnabled(True)
        self._set_fields_enabled(True)

        if result.get("success"):
            self._access_token = result["access_token"]
            self._client_id    = self.field_client_id.text().strip()
            self._is_connected = True

            self.btn_connect.setVisible(False)
            self.btn_disconnect.setVisible(True)

            # Save with token
            save_credentials(
                client_id    = self._client_id,
                pin          = self.field_pin.text().strip(),
                totp_secret  = self.field_totp.text().strip(),
                access_token = self._access_token,
                expiry       = result.get("expiry", ""),
            )

            token_preview = self._access_token[:24] + "…"
            expiry        = result.get("expiry", "N/A")
            client_name   = result.get("client_name", "")

            self._set_status("")
            self.token_card.setVisible(True)
            detail = f"Client ID: {self._client_id}"
            if client_name:
                detail += f"  •  Name: {client_name}"
            detail += f"\nToken: {token_preview}\nExpires: {expiry}"
            self.lbl_token_detail.setText(detail)

            self.connected.emit(self._client_id, self._access_token)

        else:
            err = result.get("error", "Unknown error")
            self._set_status(f"❌  Connection failed: {err}", error=True)

    def _on_disconnect(self):
        self._is_connected = False
        self._access_token = ""
        self.btn_disconnect.setVisible(False)
        self.btn_connect.setVisible(True)
        self.token_card.setVisible(False)
        self._set_status("")
        self._set_fields_enabled(True)
        self.disconnected.emit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, msg, error=False, connecting=False):
        self.lbl_status.setText(msg)
        if error:
            self.lbl_status.setStyleSheet("color: #f87171; font-size: 12px;")
        elif connecting:
            self.lbl_status.setStyleSheet("color: #facc15; font-size: 12px;")
        else:
            self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")

    def _set_fields_enabled(self, enabled: bool):
        for f in [self.field_client_id, self.field_pin, self.field_totp]:
            f.setEnabled(enabled)
