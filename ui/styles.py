"""
ui/styles.py — Dark theme for Balfund Strategy Builder
"""

DARK_THEME = """
/* ── Global ─────────────────────────────────────────────────────── */
QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f1117;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
#sidebar {
    background-color: #1a1d27;
    border-right: 1px solid #2d3148;
    min-width: 220px;
    max-width: 220px;
}

#sidebar_logo {
    color: #7c6af7;
    font-size: 16px;
    font-weight: bold;
    padding: 20px 16px 8px 16px;
    letter-spacing: 1px;
}

#sidebar_version {
    color: #4a5568;
    font-size: 10px;
    padding: 0px 16px 20px 16px;
}

QPushButton#nav_btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    margin: 2px 8px;
}

QPushButton#nav_btn:hover {
    background-color: #252840;
    color: #e2e8f0;
}

QPushButton#nav_btn[active="true"] {
    background-color: #2d3254;
    color: #7c6af7;
    font-weight: bold;
    border-left: 3px solid #7c6af7;
}

QPushButton#nav_btn:disabled {
    color: #2d3748;
}

/* ── Content area ────────────────────────────────────────────────── */
#content_area {
    background-color: #0f1117;
    padding: 0px;
}

#page_title {
    color: #e2e8f0;
    font-size: 22px;
    font-weight: bold;
    padding: 24px 28px 8px 28px;
}

#page_subtitle {
    color: #64748b;
    font-size: 12px;
    padding: 0px 28px 20px 28px;
}

/* ── Cards ───────────────────────────────────────────────────────── */
QFrame#card {
    background-color: #1a1d27;
    border: 1px solid #2d3148;
    border-radius: 12px;
    padding: 16px;
}

QFrame#card_green {
    background-color: #0d1f12;
    border: 1px solid #1a472a;
    border-radius: 12px;
    padding: 16px;
}

QFrame#card_red {
    background-color: #1f0d0d;
    border: 1px solid #472a2a;
    border-radius: 12px;
    padding: 16px;
}

/* ── Instrument rows ─────────────────────────────────────────────── */
QFrame#instrument_row {
    background-color: #1a1d27;
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 3px 0px;
}

QFrame#instrument_row:hover {
    background-color: #20243a;
    border: 1px solid #3d4268;
}

QLabel#inst_name {
    color: #e2e8f0;
    font-weight: bold;
    font-size: 14px;
}

QLabel#inst_ltp_up {
    color: #4ade80;
    font-size: 16px;
    font-weight: bold;
}

QLabel#inst_ltp_down {
    color: #f87171;
    font-size: 16px;
    font-weight: bold;
}

QLabel#inst_ltp_neutral {
    color: #94a3b8;
    font-size: 16px;
    font-weight: bold;
}

QLabel#inst_chg_up {
    color: #4ade80;
    font-size: 12px;
}

QLabel#inst_chg_down {
    color: #f87171;
    font-size: 12px;
}

QLabel#inst_seg {
    color: #475569;
    font-size: 10px;
    background-color: #252840;
    border-radius: 4px;
    padding: 2px 6px;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #1a1d27;
    border: 1px solid #2d3148;
    border-radius: 8px;
    padding: 10px 12px;
    color: #e2e8f0;
    font-size: 13px;
    selection-background-color: #7c6af7;
}

QLineEdit:focus {
    border: 1px solid #7c6af7;
    background-color: #1e2035;
}

QLineEdit:disabled {
    background-color: #141620;
    color: #3d4268;
    border: 1px solid #1e2035;
}

QLabel {
    color: #94a3b8;
    font-size: 12px;
}

QLabel#label_bold {
    color: #e2e8f0;
    font-weight: bold;
    font-size: 13px;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton#btn_primary {
    background-color: #7c6af7;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#btn_primary:hover {
    background-color: #6b5ce7;
}

QPushButton#btn_primary:pressed {
    background-color: #5a4bd6;
}

QPushButton#btn_primary:disabled {
    background-color: #2d3148;
    color: #4a5568;
}

QPushButton#btn_danger {
    background-color: #dc2626;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#btn_danger:hover {
    background-color: #b91c1c;
}

QPushButton#btn_success {
    background-color: #16a34a;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#btn_success:hover {
    background-color: #15803d;
}

QPushButton#btn_secondary {
    background-color: #252840;
    color: #94a3b8;
    border: 1px solid #2d3148;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
}

QPushButton#btn_secondary:hover {
    background-color: #2d3254;
    color: #e2e8f0;
}

/* ── Status indicator ────────────────────────────────────────────── */
QLabel#status_connected {
    color: #4ade80;
    font-size: 12px;
    font-weight: bold;
}

QLabel#status_disconnected {
    color: #f87171;
    font-size: 12px;
    font-weight: bold;
}

QLabel#status_connecting {
    color: #facc15;
    font-size: 12px;
    font-weight: bold;
}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #1a1d27;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #2d3148;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #3d4268;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ── Divider ─────────────────────────────────────────────────────── */
QFrame#divider {
    background-color: #2d3148;
    max-height: 1px;
    margin: 8px 0px;
}

/* ── Combo box ───────────────────────────────────────────────────── */
QComboBox {
    background-color: #1a1d27;
    border: 1px solid #2d3148;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    font-size: 13px;
    min-width: 140px;
}
QComboBox:focus {
    border: 1px solid #7c6af7;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox QAbstractItemView {
    background-color: #1a1d27;
    border: 1px solid #2d3148;
    selection-background-color: #2d3254;
    color: #e2e8f0;
    padding: 4px;
}

/* ── Progress / spinner area ─────────────────────────────────────── */
QLabel#loading_text {
    color: #64748b;
    font-size: 12px;
    font-style: italic;
}

/* ── Tooltip ─────────────────────────────────────────────────────── */
QToolTip {
    background-color: #252840;
    color: #e2e8f0;
    border: 1px solid #3d4268;
    border-radius: 6px;
    padding: 6px 10px;
}
"""

# Colours used in Python code (match stylesheet)
COLOR_UP      = "#4ade80"
COLOR_DOWN    = "#f87171"
COLOR_NEUTRAL = "#94a3b8"
COLOR_ACCENT  = "#7c6af7"
COLOR_BG      = "#0f1117"
COLOR_CARD    = "#1a1d27"
COLOR_BORDER  = "#2d3148"
