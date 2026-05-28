"""Centralized visual theme helpers for the PySide6 GUI."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget


@dataclass(frozen=True)
class ThemeColors:
    """Color tokens inspired by the generated Cyber-Metric design system."""

    background: str = "#08090a"
    surface: str = "#121315"
    surface_dim: str = "#0d0e10"
    surface_low: str = "#1b1c1e"
    surface_container: str = "#1f2022"
    surface_high: str = "#292a2c"
    surface_highest: str = "#343537"
    on_surface: str = "#e3e2e4"
    on_surface_variant: str = "#bfc8ce"
    muted: str = "#899298"
    outline: str = "#899298"
    outline_variant: str = "#40484d"
    primary: str = "#92d9ff"
    primary_soft: str = "#d8f0ff"
    primary_dim: str = "#88cff5"
    on_primary: str = "#003548"
    secondary: str = "#d4bbff"
    secondary_container: str = "#533e78"
    success: str = "#9ff2bd"
    warning: str = "#ffd98a"
    error: str = "#ffb4ab"


@dataclass(frozen=True)
class ThemeSpacing:
    """Spacing and dimension tokens using a 4px rhythm."""

    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    sidebar_width: int = 280
    footer_height: int = 48
    topbar_height: int = 64
    card_radius: int = 4
    panel_radius: int = 8


@dataclass(frozen=True)
class ThemeTypography:
    """Font tokens for regular UI and technical text."""

    ui_family: str = "Hanken Grotesk"
    mono_family: str = "JetBrains Mono"
    ui_fallback: str = "Inter, Segoe UI, Arial, sans-serif"
    mono_fallback: str = "Cascadia Mono, Consolas, monospace"
    body_size: int = 14
    body_large_size: int = 16
    headline_size: int = 24
    label_size: int = 12
    code_size: int = 13


COLORS = ThemeColors()
SPACING = ThemeSpacing()
TYPOGRAPHY = ThemeTypography()


def set_theme_role(widget: QWidget, role: str) -> None:
    """Assign a reusable QSS role and refresh the widget style."""
    widget.setProperty("themeRole", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_active(widget: QWidget, active: bool) -> None:
    """Mark a themed widget as active and refresh its style."""
    widget.setProperty("active", active)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def app_stylesheet() -> str:
    """Build the global QSS from the centralized design tokens."""
    c = COLORS
    s = SPACING
    t = TYPOGRAPHY
    ui_fonts = f'"{t.ui_family}", {t.ui_fallback}'
    mono_fonts = f'"{t.mono_family}", {t.mono_fallback}'

    return f"""
    * {{
        outline: none;
        selection-background-color: {c.primary};
        selection-color: {c.on_primary};
    }}

    QWidget {{
        background-color: {c.background};
        color: {c.on_surface};
        font-family: {ui_fonts};
        font-size: {t.body_size}px;
    }}

    QMainWindow, QWidget[themeRole="appShell"], QStackedWidget {{
        background-color: {c.background};
    }}

    QScrollArea {{
        background-color: {c.background};
        border: 0;
    }}

    QScrollArea > QWidget > QWidget {{
        background-color: {c.background};
    }}

    QWidget[themeRole="sidebar"] {{
        background-color: {c.surface_low};
        border-right: 1px solid {c.outline_variant};
    }}

    QWidget[themeRole="topbar"] {{
        background-color: {c.surface};
        border-bottom: 1px solid {c.outline_variant};
    }}

    QWidget[themeRole="footer"] {{
        background-color: {c.surface_dim};
        border-top: 1px solid {c.outline_variant};
    }}

    QWidget[themeRole="page"] {{
        background-color: {c.background};
    }}

    QWidget[themeRole="card"] {{
        background-color: {c.surface_low};
        border: 1px solid {c.outline_variant};
        border-radius: {s.card_radius}px;
    }}

    QWidget[themeRole="heroCard"] {{
        background-color: {c.primary};
        border: 1px solid {c.primary_dim};
        border-radius: {s.card_radius}px;
    }}

    QWidget[themeRole="consolePanel"] {{
        background-color: {c.surface_dim};
        border: 1px solid {c.outline_variant};
        border-radius: {s.card_radius}px;
    }}

    QLabel {{
        background: transparent;
        color: {c.on_surface};
    }}

    QLabel[themeRole="brand"] {{
        color: {c.on_surface};
        font-size: {t.headline_size}px;
        font-weight: 700;
    }}

    QLabel[themeRole="headline"] {{
        color: {c.on_surface};
        font-size: {t.headline_size}px;
        font-weight: 700;
    }}

    QLabel[themeRole="sectionLabel"] {{
        color: {c.on_surface_variant};
        font-family: {mono_fonts};
        font-size: {t.label_size}px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}

    QLabel[themeRole="metadata"] {{
        color: {c.primary_dim};
        font-family: {mono_fonts};
        font-size: {t.code_size}px;
        letter-spacing: 1px;
    }}

    QLabel[themeRole="muted"] {{
        color: {c.muted};
    }}

    QLabel[themeRole="metric"] {{
        color: {c.on_surface};
        font-size: 36px;
        font-weight: 700;
    }}

    QLabel[themeRole="code"] {{
        color: {c.on_surface_variant};
        font-family: {mono_fonts};
        font-size: {t.code_size}px;
    }}

    QLabel[themeRole="badge"] {{
        background-color: {c.surface_high};
        border: 1px solid {c.outline_variant};
        border-radius: {s.card_radius}px;
        color: {c.on_surface_variant};
        font-family: {mono_fonts};
        font-size: 11px;
        padding: 3px 8px;
    }}

    QLabel[themeRole="badgePrimary"] {{
        background-color: rgba(146, 217, 255, 0.10);
        border: 1px solid {c.primary_dim};
        border-radius: {s.card_radius}px;
        color: {c.primary};
        font-family: {mono_fonts};
        font-size: 11px;
        padding: 3px 8px;
    }}

    QLabel[themeRole="heroTitle"] {{
        color: {c.on_primary};
        font-size: 22px;
        font-weight: 700;
    }}

    QLabel[themeRole="heroText"] {{
        color: #075a77;
        font-size: {t.body_large_size}px;
    }}

    QPushButton {{
        background-color: {c.surface_container};
        border: 1px solid {c.outline_variant};
        border-radius: {s.card_radius}px;
        color: {c.on_surface};
        font-family: {mono_fonts};
        font-size: {t.label_size}px;
        font-weight: 600;
        padding: 8px 14px;
    }}

    QPushButton:hover {{
        background-color: {c.surface_high};
        border-color: {c.primary_dim};
        color: {c.primary_soft};
    }}

    QPushButton:pressed {{
        background-color: {c.surface_highest};
    }}

    QPushButton[themeRole="primaryButton"] {{
        background-color: {c.primary};
        border-color: {c.primary};
        color: {c.on_primary};
    }}

    QPushButton[themeRole="primaryButton"]:hover {{
        background-color: {c.primary_soft};
        border-color: {c.primary_soft};
    }}

    QPushButton[themeRole="secondaryButton"] {{
        background-color: transparent;
        border-color: {c.outline_variant};
        color: {c.on_surface};
    }}

    QPushButton[themeRole="navButton"] {{
        background-color: transparent;
        border: 0;
        border-left: 4px solid transparent;
        border-radius: 0;
        color: {c.on_surface_variant};
        padding: 11px 16px;
        text-align: left;
    }}

    QPushButton[themeRole="navButton"]:hover {{
        background-color: {c.surface_high};
        color: {c.on_surface};
    }}

    QPushButton[themeRole="navButton"][active="true"] {{
        background-color: rgba(146, 217, 255, 0.10);
        border-left-color: {c.primary};
        color: {c.on_surface};
    }}

    QLineEdit, QComboBox, QPlainTextEdit {{
        background-color: {c.surface_low};
        border: 1px solid {c.outline_variant};
        border-radius: {s.card_radius}px;
        color: {c.on_surface};
        padding: 7px 9px;
    }}

    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{
        border-color: {c.primary};
    }}

    QComboBox::drop-down {{
        border: 0;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c.surface_low};
        border: 1px solid {c.outline_variant};
        color: {c.on_surface};
        selection-background-color: {c.surface_high};
        selection-color: {c.primary};
    }}

    QCheckBox {{
        background: transparent;
        color: {c.on_surface_variant};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        background-color: {c.surface_low};
        border: 1px solid {c.outline_variant};
        border-radius: 2px;
        height: 15px;
        width: 15px;
    }}

    QCheckBox::indicator:checked {{
        background-color: {c.primary};
        border-color: {c.primary};
    }}

    QProgressBar {{
        background-color: {c.surface_highest};
        border: 0;
        border-radius: 3px;
        height: 6px;
        max-height: 6px;
        min-height: 6px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c.primary};
        border-radius: 3px;
    }}

    QProgressBar[themeRole="secondaryProgress"]::chunk {{
        background-color: {c.secondary};
    }}

    QPlainTextEdit[themeRole="logPanel"] {{
        background-color: {c.surface_dim};
        border: 0;
        color: {c.primary_soft};
        font-family: {mono_fonts};
        font-size: {t.code_size}px;
        line-height: 20px;
    }}

    QScrollBar:vertical {{
        background-color: {c.surface};
        width: 8px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c.outline_variant};
        border-radius: 4px;
        min-height: 24px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QMessageBox {{
        background-color: {c.surface};
    }}
    """


def apply_app_theme(app: QApplication) -> None:
    """Apply the global application style sheet and base font."""
    app.setFont(QFont(TYPOGRAPHY.ui_family, TYPOGRAPHY.body_size))
    app.setStyleSheet(app_stylesheet())
