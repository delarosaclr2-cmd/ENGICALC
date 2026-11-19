"""Tema visual de la aplicación (Qt Style Sheet)."""

NAVY = "#14213D"
NAVY2 = "#1D2B4F"
ACCENT = "#2a78d6"
SURFACE = "#fcfcfb"
PAGE = "#f4f5f7"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
BORDER = "#dcdde1"

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", "DejaVu Sans", sans-serif; font-size: 10pt; color: {INK}; }}
QMainWindow, QWidget#central {{ background: {PAGE}; }}
QWidget#sidebar {{ background: {NAVY}; }}
QLabel#appTitle {{ color: white; font-size: 12.5pt; font-weight: 700; padding: 14px 14px 2px 14px; }}
QLabel#appSub {{ color: #9fb0d0; font-size: 8.5pt; padding: 0 14px 12px 14px; }}
QListWidget#nav {{ background: {NAVY}; border: none; outline: 0; padding: 4px; }}
QListWidget#nav::item {{ color: #d7deeb; padding: 9px 12px; border-radius: 6px; margin: 1px 4px; }}
QListWidget#nav::item:hover {{ background: {NAVY2}; color: white; }}
QListWidget#nav::item:selected {{ background: {ACCENT}; color: white; font-weight: 600; }}
QWidget#topbar {{ background: white; border-bottom: 1px solid {BORDER}; }}
QLabel#pageTitle {{ font-size: 15pt; font-weight: 700; color: {NAVY}; }}
QLabel#pageSub {{ color: {INK2}; font-size: 9pt; }}
QLabel#projectName {{ font-weight: 600; color: {INK2}; }}
QGroupBox {{ background: white; border: 1px solid {BORDER}; border-radius: 8px; margin-top: 14px; padding: 10px 10px 8px 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {NAVY}; font-weight: 700; }}
QPushButton {{ background: white; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #1f63b5; color: white; }}
QPushButton#danger {{ color: #B42318; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ background: white; border: 1px solid {BORDER}; border-radius: 5px; padding: 4px 6px; min-height: 20px; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit[invalid="true"] {{ border-color: #B42318; background: #fff4f2; }}
QTextEdit, QPlainTextEdit, QTextBrowser {{ background: white; border: 1px solid {BORDER}; border-radius: 6px; }}
QTableWidget {{ background: white; border: 1px solid {BORDER}; border-radius: 6px; gridline-color: #ececef; selection-background-color: #dbe8fa; selection-color: {INK}; }}
QHeaderView::section {{ background: #eef1f6; border: none; border-right: 1px solid #e2e5ea; border-bottom: 1px solid #c9d1de; padding: 5px; font-weight: 600; color: {NAVY}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; background: white; top: -1px; }}
QTabBar::tab {{ background: #eceef2; padding: 6px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; color: {INK2}; }}
QTabBar::tab:selected {{ background: white; color: {NAVY}; font-weight: 600; }}
QScrollArea {{ border: none; background: transparent; }}
QFrame#card {{ background: white; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#kpiTitle {{ color: {INK2}; font-size: 8.5pt; }}
QLabel#kpiValue {{ font-size: 16pt; font-weight: 700; color: {INK}; }}
QLabel#kpiSub {{ color: {MUTED}; font-size: 8pt; }}
QLabel#badge {{ border-radius: 9px; padding: 2px 9px; color: white; font-weight: 600; font-size: 8.5pt; }}
QLabel#note {{ color: {INK2}; font-size: 8.5pt; }}
QStatusBar {{ background: white; border-top: 1px solid {BORDER}; }}
QToolTip {{ background: {NAVY}; color: white; border: none; padding: 5px; }}
QSplitter::handle {{ background: {PAGE}; }}
"""
