from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QMessageBox, QRadioButton, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal
import os

from ..core.crypto import batch_decrypt_directory, batch_encrypt_directory

class WorkerThread(QThread):
    finished_sig = Signal(list, str)
    error_sig = Signal(str)

    def __init__(self, op_type, src, dst):
        super().__init__()
        self.op_type = op_type
        self.src = src
        self.dst = dst

    def run(self):
        try:
            if self.op_type == "decrypt":
                res = batch_decrypt_directory(self.src, self.dst)
            else:
                res = batch_encrypt_directory(self.src, self.dst)
            self.finished_sig.emit(res, self.dst)
        except Exception as e:
            self.error_sig.emit(str(e))

class BatchPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Batch Directory Operations")
        lbl.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(lbl)
        
        # Operation type
        op_layout = QHBoxLayout()
        self.rb_decrypt = QRadioButton("Batch Decrypt")
        self.rb_encrypt = QRadioButton("Batch Encrypt")
        self.rb_decrypt.setChecked(True)
        op_layout.addWidget(self.rb_decrypt)
        op_layout.addWidget(self.rb_encrypt)
        op_layout.addStretch()
        layout.addLayout(op_layout)
        
        # Source
        src_layout = QHBoxLayout()
        self.le_src = QLineEdit()
        self.le_src.setPlaceholderText("Source Directory...")
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(lambda: self._browse(self.le_src))
        src_layout.addWidget(self.le_src)
        src_layout.addWidget(btn_src)
        layout.addLayout(src_layout)
        
        # Destination
        dst_layout = QHBoxLayout()
        self.le_dst = QLineEdit()
        self.le_dst.setPlaceholderText("Destination Directory...")
        btn_dst = QPushButton("Browse...")
        btn_dst.clicked.connect(lambda: self._browse(self.le_dst))
        dst_layout.addWidget(self.le_dst)
        dst_layout.addWidget(btn_dst)
        layout.addLayout(dst_layout)
        
        # Action
        self.btn_run = QPushButton("Start Batch Operation")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.clicked.connect(self.run_batch)
        layout.addWidget(self.btn_run)
        
        layout.addStretch()

    def _browse(self, linedit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d: linedit.setText(d)

    def run_batch(self):
        src = self.le_src.text()
        dst = self.le_dst.text()
        if not src or not dst or not os.path.isdir(src):
            QMessageBox.warning(self, "Invalid Inputs", "Please select valid directories.")
            return
            
        op = "decrypt" if self.rb_decrypt.isChecked() else "encrypt"
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Processing...")
        
        self.worker = WorkerThread(op, src, dst)
        self.worker.finished_sig.connect(self._on_finished)
        self.worker.error_sig.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, results, dst):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Start Batch Operation")
        QMessageBox.information(self, "Batch Complete", f"Processed {len(results)} files into:\n{dst}")

    def _on_error(self, err):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Start Batch Operation")
        QMessageBox.critical(self, "Batch Error", f"Failed:\n{err}")
