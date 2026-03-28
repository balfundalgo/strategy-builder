"""
ui/pages/placeholder_page.py
─────────────────────────────
Generic "Coming Soon" page used for milestones not yet built.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, milestone: str, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        t = QLabel(title)
        t.setObjectName("page_title")
        root.addWidget(t)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 60, 40, 60)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🚧")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(icon)

        cl.addSpacing(16)

        ms_lbl = QLabel(milestone)
        ms_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ms_lbl.setStyleSheet("color: #7c6af7; font-size: 13px; font-weight: bold;")
        cl.addWidget(ms_lbl)

        cl.addSpacing(8)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #64748b; font-size: 14px; line-height: 1.6;")
        cl.addWidget(desc)

        root.addSpacing(24)
        root.addWidget(card)
        root.addStretch()
