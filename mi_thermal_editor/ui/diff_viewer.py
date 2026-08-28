from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QFileDialog, QMessageBox
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter
from PySide6.QtCore import QRegularExpression

from ..core.diff_engine import compute_thermal_diff
from ..core.crypto import load_thermal_file

class DiffHighlighter(QSyntaxHighlighter):
    def __init__(self, document, is_dark_mode=True):
        super().__init__(document)
        self.rules = []
        self.set_theme(is_dark_mode)

    def set_theme(self, is_dark_mode):
        self.rules.clear()
        
        fmt_add = QTextCharFormat()
        if is_dark_mode:
            fmt_add.setForeground(QColor("#03DAC6"))
            fmt_add.setBackground(QColor("#003828"))
        else:
            fmt_add.setForeground(QColor("#006600"))
            fmt_add.setBackground(QColor("#E6FFE6"))
        self.rules.append((QRegularExpression(r"^\+.*"), fmt_add))
        
        fmt_del = QTextCharFormat()
        if is_dark_mode:
            fmt_del.setForeground(QColor("#CF6679"))
            fmt_del.setBackground(QColor("#380008"))
        else:
            fmt_del.setForeground(QColor("#CC0000"))
            fmt_del.setBackground(QColor("#FFE6E6"))
        self.rules.append((QRegularExpression(r"^\-.*"), fmt_del))
        
        fmt_header = QTextCharFormat()
        if is_dark_mode:
            fmt_header.setForeground(QColor("#BB86FC"))
        else:
            fmt_header.setForeground(QColor("#8A2BE2"))
            
        self.rules.append((QRegularExpression(r"^@@.*@@"), fmt_header))
        self.rules.append((QRegularExpression(r"^===.*==="), fmt_header))
        self.rehighlight()

    def highlightBlock(self, text):
        for regex, fmt in self.rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                match = it.next()
                if match.capturedStart() == 0:
                    self.setFormat(0, match.capturedLength(), fmt)

class DiffViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.base_content = ""
        self.base_name = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar = QHBoxLayout()
        self.lbl_info = QLabel("Diff Viewer - Select a file to compare against")
        toolbar.addWidget(self.lbl_info)
        
        toolbar.addStretch()
        
        btn_compare = QPushButton("Load Target to Compare...")
        btn_compare.clicked.connect(self.on_load_target)
        toolbar.addWidget(btn_compare)
        
        layout.addLayout(toolbar)
        
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.Monospace)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        self.highlighter = DiffHighlighter(self.editor.document())
        layout.addWidget(self.editor)

    def set_theme(self, is_dark_mode):
        self.highlighter.set_theme(is_dark_mode)

    def set_base(self, content, name):
        self.base_content = content
        self.base_name = name
        self.lbl_info.setText(f"Comparing base: {name}")

    def on_load_target(self):
        if not self.base_content:
            QMessageBox.warning(self, "No Base", "No base content loaded yet.")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Select Modified File")
        if not path:
            return
            
        try:
            target_f = load_thermal_file(path)
            diff_res = compute_thermal_diff(self.base_content, target_f.content, 
                                            name_a=self.base_name, name_b=target_f.name)
            
            lines = [f"=== {diff_res.summary} ==="]
            lines.extend(diff_res.unified_diff_lines)
            
            self.editor.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Diff Error", str(e))
