DARK_THEME = """
QWidget {
    background-color: #121212;
    color: #FFFFFF;
    font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', sans-serif;
    font-size: 10pt;
}

QMainWindow {
    background-color: #0E0E0E;
}

QSplitter::handle {
    background-color: #2D2D2D;
    width: 2px;
}

QTabWidget::pane {
    border: 1px solid #3A3A3A;
    background-color: #1E1E1E;
}

QTabBar::tab {
    background-color: #252525;
    color: #AAAAAA;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #00E5FF;
    border-bottom: 2px solid #00E5FF;
}

QPushButton {
    background-color: #252525;
    border: 1px solid #3A3A3A;
    padding: 6px 16px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #2D2D2D;
    border-color: #555555;
}
QPushButton:pressed {
    background-color: #00E5FF;
    color: #000000;
}
QPushButton#AccentButton {
    background-color: #00E5FF;
    color: #000000;
    font-weight: bold;
    border: none;
}
QPushButton#AccentButton:hover {
    background-color: #00B4D8;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1E1E1E;
    border: 1px solid #3A3A3A;
    border-radius: 4px;
    padding: 4px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00E5FF;
}

QTreeView, QListView, QTableWidget, QTableView {
    background-color: #1E1E1E;
    border: 1px solid #3A3A3A;
    border-radius: 4px;
    alternate-background-color: #252525;
    gridline-color: #2D2D2D;
}
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
    background-color: #004D40;
    color: #00E5FF;
}
QHeaderView::section {
    background-color: #252525;
    color: #FFFFFF;
    padding: 4px;
    border: none;
    border-right: 1px solid #3A3A3A;
    border-bottom: 1px solid #3A3A3A;
    font-weight: bold;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background-color: #121212;
    width: 14px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #3A3A3A;
    min-height: 20px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #121212;
    height: 14px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #3A3A3A;
    min-width: 20px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #555555;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
