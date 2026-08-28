from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QSplitter, QTabWidget, QToolBar, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QSize
import sys

from .styles import DARK_THEME
from .file_browser import FileBrowserWidget
from .editor import EditorWidget
from .analyzer_panel import AnalyzerWidget
from .diff_viewer import DiffViewer
from .batch_panel import BatchPanel
from ..services.adb_service import ADBManager

class MainWindow(QMainWindow):
    def __init__(self, initial_dir=None):
        super().__init__()
        self.setWindowTitle("Mi Thermal Editor")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_THEME)
        
        self.adb = ADBManager()
        self._setup_ui()
        
        if initial_dir:
            self.browser.set_directory(initial_dir)
            
    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ToolBar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        act_open = toolbar.addAction("📂 Open Workspace")
        act_open.triggered.connect(self.action_open_workspace)
        
        act_adb = toolbar.addAction("📱 Connect Device")
        act_adb.triggered.connect(self.action_connect_device)
        
        toolbar.addSeparator()
        act_batch = toolbar.addAction("📦 Batch Operations")
        act_batch.triggered.connect(lambda: self.tabs.setCurrentWidget(self.batch_tab))
        
        # Splitter Layout
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel (Browser)
        self.browser = FileBrowserWidget()
        self.browser.file_selected.connect(self.on_file_selected)
        self.browser.file_export_requested.connect(self.on_file_export_requested)
        self.browser.file_inject_requested.connect(self.on_file_inject_requested)
        splitter.addWidget(self.browser)
        
        # Right Panel (Tabs)
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        
        self.editor = EditorWidget()
        self.editor.content_changed.connect(self.sync_editor_content)
        self.tabs.addTab(self.editor, "📝 Editor")
        
        self.analyzer = AnalyzerWidget()
        self.tabs.addTab(self.analyzer, "📊 Analyzer")
        
        self.diff = DiffViewer()
        self.tabs.addTab(self.diff, "⚖️ Compare")
        
        self.batch_tab = BatchPanel()
        self.tabs.addTab(self.batch_tab, "📦 Batch")
        
        splitter.setSizes([300, 900])

    def action_open_workspace(self):
        d = QFileDialog.getExistingDirectory(self, "Open Workspace")
        if d: self.browser.set_directory(d)

    def action_connect_device(self):
        devices = self.adb.list_devices()
        if not devices:
            QMessageBox.warning(self, "No Devices", "No ADB devices found.")
            return
            
        dev = devices[0]
        sconfig = self.adb.get_active_sconfig(serial=dev.serial)
        root = self.adb.check_root(serial=dev.serial)
        
        msg = f"Connected to {dev.serial}\nModel: {dev.model}\nRoot: {root}\nSCONFIG: {sconfig}\n\nPull thermal configs to current workspace?"
        if QMessageBox.question(self, "Device", msg) == QMessageBox.Yes:
            # Quick sync to /tmp or current workspace
            out_dir = self.browser.current_dir
            files_map = self.adb.scan_device_thermal_files(serial=dev.serial)
            pulled = 0
            for sdir, flist in files_map.items():
                for f in flist:
                    rpath = f"{sdir}/{f}"
                    succ, d, e = self.adb.pull_thermal_file(rpath, serial=dev.serial)
                    if succ:
                        with open(out_dir / f, "wb") as local_f:
                            local_f.write(d)
                        pulled += 1
            self.browser.refresh()
            QMessageBox.information(self, "Success", f"Pulled {pulled} files.")

    def on_file_selected(self, path):
        self.editor.load_file(path)
        self.tabs.setCurrentWidget(self.editor)
        self.sync_editor_content()
        self.diff.set_base(self.editor.get_content(), path.name)

    def sync_editor_content(self):
        content = self.editor.get_content()
        fname = self.editor.lbl_title.text()
        self.analyzer.analyze_content(content, fname)
        self.diff.set_base(content, fname)

    def on_file_export_requested(self, path):
        self.on_file_selected(path)
        self.editor.on_export()

    def on_file_inject_requested(self, path):
        devices = self.adb.list_devices()
        if not devices:
            QMessageBox.warning(self, "No Devices", "No ADB devices connected.")
            return
            
        dev = devices[0]
        rpath = f"/odm/etc/{path.name}"
        msg = f"Inject {path.name} to device {dev.serial} at {rpath}?\nThis will create a backup (.bak) on the device if rooted."
        if QMessageBox.question(self, "Inject?", msg) == QMessageBox.Yes:
            from ..core.crypto import load_thermal_file, encrypt_data
            try:
                tf = load_thermal_file(path)
                enc_data = encrypt_data(tf.content)
                s, e = self.adb.inject_thermal_file(rpath, enc_data, serial=dev.serial)
                if s: QMessageBox.information(self, "Success", "Injection payload succeeded.")
                else: QMessageBox.critical(self, "Failed", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

def launch_gui(initial_dir=None):
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Modern smooth fonts
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    
    win = MainWindow(initial_dir)
    win.show()
    sys.exit(app.exec())
