from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
                               QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None, default_filename="thermal-custom.conf", was_encrypted=True):
        super().__init__(parent)
        self.setWindowTitle("Export Thermal Configuration")
        self.setMinimumWidth(400)
        self.default_filename = default_filename
        self.was_encrypted = was_encrypted
        
        self.result_format = "plaintext"
        self.result_path = ""
        self.result_backup = False
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("Export Configuration")
        lbl_info.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 8px;")
        layout.addWidget(lbl_info)
        
        # Format Group
        lbl_fmt = QLabel("Format:")
        lbl_fmt.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_fmt)
        
        self.rb_plain = QRadioButton("Plaintext .conf (Readable / Editable)")
        self.rb_enc = QRadioButton("Encrypted Xiaomi thermal binary (AES-128-CBC)")
        
        if self.was_encrypted:
            self.rb_plain.setChecked(True) # Force to plain by default as it's the most common intent for export
        else:
            self.rb_plain.setChecked(True)
            
        layout.addWidget(self.rb_plain)
        layout.addWidget(self.rb_enc)
        
        # Path Group
        lbl_path = QLabel("Destination:")
        lbl_path.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_path)
        
        path_layout = QHBoxLayout()
        self.le_path = QLineEdit()
        self.le_path.setText(self.default_filename)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse)
        
        path_layout.addWidget(self.le_path)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        
        # Options
        lbl_opt = QLabel("Options:")
        lbl_opt.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_opt)
        
        self.chk_backup = QCheckBox("Create backup (.bak) if file exists")
        self.chk_backup.setChecked(True)
        layout.addWidget(self.chk_backup)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_export = QPushButton("Export")
        btn_export.setObjectName("AccentButton")
        btn_export.clicked.connect(self._accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Thermal Config", 
                                            self.le_path.text(), "Thermal Config (*.conf);;All Files (*.*)")
        if path:
            self.le_path.setText(path)

    def _accept(self):
        path = self.le_path.text().strip()
        if not path:
            return
            
        self.result_path = path
        self.result_format = "encrypted" if self.rb_enc.isChecked() else "plaintext"
        self.result_backup = self.chk_backup.isChecked()
        self.accept()
