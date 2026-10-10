"""浅色主题。

本机 Windows 处于深色模式时，Qt 默认调色板会把控件绘制成深色，
导致浅色背景文字不可读。这里强制使用 Fusion 风格 + 浅色调色板，
保证界面始终为"浅色背景 + 深色文字"。
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# 常用颜色
WINDOW_BG = QColor(0xF5, 0xF6, 0xFA)
TEXT_COLOR = QColor(0x1F, 0x24, 0x2E)
BASE_BG = QColor(0xFF, 0xFF, 0xFF)
HIGHLIGHT = QColor(0x2F, 0x74, 0xE8)
DISABLED_TEXT = QColor(0x9A, 0xA0, 0xAA)

# 附加样式表：让按钮、卡片更清晰
LIGHT_STYLESHEET = """
QWidget { font-size: 14px; }
QLineEdit, QComboBox, QDateEdit, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #C9CFDA;
    border-radius: 6px;
    padding: 5px 8px;
    color: #1F242E;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #2F74E8;
}
QPushButton {
    background-color: #2F74E8;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
}
QPushButton:hover { background-color: #4A88F0; }
QPushButton:disabled { background-color: #B9C6E2; color: #F0F2F7; }
QFrame#WeatherCard {
    background-color: #FFFFFF;
    border: 1px solid #DFE4EC;
    border-radius: 10px;
}
QLabel#CardTitle { font-size: 20px; font-weight: 600; color: #1F242E; }
QLabel#CardIcon  { font-size: 40px; }
QLabel#FieldKey  { color: #6B7280; }
QLabel#FieldValue { font-weight: 600; color: #1F242E; }
"""


def apply_light_theme(app: QApplication) -> None:
    """强制应用 Fusion 浅色主题。

    Args:
        app: 当前 QApplication 实例。
    """
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, WINDOW_BG)
    palette.setColor(QPalette.ColorRole.WindowText, TEXT_COLOR)
    palette.setColor(QPalette.ColorRole.Base, BASE_BG)
    palette.setColor(QPalette.ColorRole.AlternateBase, WINDOW_BG)
    palette.setColor(QPalette.ColorRole.ToolTipBase, BASE_BG)
    palette.setColor(QPalette.ColorRole.ToolTipText, TEXT_COLOR)
    palette.setColor(QPalette.ColorRole.Text, TEXT_COLOR)
    palette.setColor(QPalette.ColorRole.Button, WINDOW_BG)
    palette.setColor(QPalette.ColorRole.ButtonText, TEXT_COLOR)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(0xD1, 0x3A, 0x3A))
    palette.setColor(QPalette.ColorRole.Link, HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.Highlight, HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0xFF, 0xFF, 0xFF))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, DISABLED_TEXT
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED_TEXT
    )
    app.setPalette(palette)
    app.setStyleSheet(LIGHT_STYLESHEET)