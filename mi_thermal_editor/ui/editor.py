from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QPlainTextEdit, QLabel, QMessageBox, QFileDialog, QCheckBox)
from PySide6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import Qt, QRegularExpression, Signal

from ..core.crypto import load_thermal_file, save_thermal_file, encrypt_data

class ThermalHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        
        fmt_section = QTextCharFormat()
        fmt_section.setForeground(QColor("#00E5FF"))
        fmt_section.setFontWeight(QFont.Bold)
        self.rules.append((QRegularExpression(r"^\s*\[.*\]\s*$"), fmt_section))
        
        fmt_comment = QTextCharFormat()
        fmt_comment.setForeground(QColor("#757575"))
        fmt_comment.setFontItalic(True)
        self.rules.append((QRegularExpression(r"#.*"), fmt_comment))
        
        fmt_keyword = QTextCharFormat()
        fmt_keyword.setForeground(QColor("#BB86FC"))
        keywords = ["algo_type", "sensor", "device", "trig", "clr", "target", "polling", "set_point"]
        for k in keywords:
            self.rules.append((QRegularExpression(rf"\b{k}\b"), fmt_keyword))
            
        fmt_number = QTextCharFormat()
        fmt_number.setForeground(QColor("#FFB74D"))
        self.rules.append((QRegularExpression(r"\b-?\d+\b"), fmt_number))

    def highlightBlock(self, text):
        for regex, fmt in self.rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class EditorWidget(QWidget):
    content_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_title = QLabel("No file open")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #00E5FF;")
        toolbar.addWidget(self.lbl_title)
        
        self.lbl_status = QLabel("")
        toolbar.addWidget(self.lbl_status)
        
        toolbar.addStretch()
        
        self.chk_encrypt = QCheckBox("Save Encrypted")
        self.chk_encrypt.setChecked(True)
        toolbar.addWidget(self.chk_encrypt)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("AccentButton")
        self.btn_save.clicked.connect(self.on_save)
        toolbar.addWidget(self.btn_save)
        
        self.btn_export = QPushButton("Export...")
        self.btn_export.clicked.connect(self.on_export)
        toolbar.addWidget(self.btn_export)
        
        layout.addLayout(toolbar)
        
        # Editor
        self.editor = QPlainTextEdit()
        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.Monospace)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self.content_changed.emit)
        
        self.highlighter = ThermalHighlighter(self.editor.document())
        layout.addWidget(self.editor)

    def load_file(self, path):
        try:
            self.current_file = load_thermal_file(path)
            self.lbl_title.setText(self.current_file.name)
            self.editor.setPlainText(self.current_file.content)
            
            if self.current_file.is_encrypted:
                self.lbl_status.setText("🔒 AES-128-CBC")
                self.chk_encrypt.setChecked(True)
            else:
                self.lbl_status.setText("📄 Plaintext")
                self.chk_encrypt.setChecked(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
            
    def set_content(self, title, content):
        self.current_file = None
        self.lbl_title.setText(title)
        self.lbl_status.setText("")
        self.editor.setPlainText(content)

    def get_content(self):
        return self.editor.toPlainText()

    def on_save(self):
        if not self.current_file:
            QMessageBox.warning(self, "No Context", "Please use Export for unbacked contents or open a file first.")
            return
            
        try:
            encrypt = self.chk_encrypt.isChecked()
            saved, backup = save_thermal_file(
                self.current_file.source_path,
                self.get_content(),
                encrypt=encrypt,
                create_backup=True
            )
            QMessageBox.information(self, "Saved", f"Saved successfully to:\n{saved}\nBackup:\n{backup}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    def on_export(self):
        content = self.get_content()
        path, filt = QFileDialog.getSaveFileName(self, "Export Thermal Config", "", "Thermal Config (*.conf);;All Files (*.*)")
        if not path: return
        
        try:
            encrypt = self.chk_encrypt.isChecked()
            if encrypt:
                data = encrypt_data(content)
                with open(path, "wb") as f:
                    f.write(data)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            QMessageBox.information(self, "Success", f"Exported successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
