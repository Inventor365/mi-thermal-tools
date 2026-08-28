from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QTreeView, QLabel, QMenu, QMessageBox)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from PySide6.QtCore import Qt, Signal
from pathlib import Path

from ..core.crypto import scan_thermal_files, load_thermal_file, is_printable_text
from ..core.analyzer import analyze_thermal_config

class FileBrowserWidget(QWidget):
    file_selected = Signal(Path)
    file_export_requested = Signal(Path)
    file_inject_requested = Signal(Path)
    
    def __init__(self):
        super().__init__()
        self.current_dir = Path.home()
        self.loaded_files = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("Thermal Explorer")
        header.setStyleSheet("font-weight: bold; font-size: 14pt; padding: 4px;")
        layout.addWidget(header)
        
        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.returnPressed.connect(self.on_dir_input_changed)
        dir_layout.addWidget(self.dir_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        # We will connect this externally or handle via QFileDialog later
        dir_layout.addWidget(btn_browse)
        layout.addLayout(dir_layout)
        
        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter files...")
        self.filter_input.textChanged.connect(self.apply_filter)
        layout.addWidget(self.filter_input)
        
        # Tree View
        self.tree = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "Status", "Profile"])
        self.tree.setModel(self.model)
        self.tree.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.on_double_click)
        layout.addWidget(self.tree)

    def set_directory(self, path: Path):
        self.current_dir = Path(path)
        self.dir_input.setText(str(self.current_dir))
        self.refresh()

    def on_dir_input_changed(self):
        new_path = Path(self.dir_input.text())
        if new_path.is_dir():
            self.set_directory(new_path)
        else:
            QMessageBox.warning(self, "Invalid Directory", f"Directory not found: {new_path}")

    def refresh(self):
        self.model.removeRows(0, self.model.rowCount())
        if not self.current_dir.is_dir():
            return
            
        self.loaded_files = scan_thermal_files(str(self.current_dir))
        self.apply_filter()

    def apply_filter(self):
        query = self.filter_input.text().lower()
        self.model.removeRows(0, self.model.rowCount())
        
        for fpath in self.loaded_files:
            if query and query not in fpath.name.lower():
                continue
                
            # Quick status peek
            try:
                with open(fpath, "rb") as fp:
                    header = fp.read(32)
                is_enc = (len(header) > 0 and not is_printable_text(header[:16].decode("utf-8", "ignore")))
            except Exception:
                is_enc = False
                
            status_str = "🔒 Encrypted" if is_enc else "📄 Plaintext"
            
            # Create row
            i_name = QStandardItem(fpath.name)
            i_name.setData(fpath, Qt.UserRole)
            i_status = QStandardItem(status_str)
            i_profile = QStandardItem("") # Loaded when actually parsed
            
            self.model.appendRow([i_name, i_status, i_profile])
            
        self.tree.resizeColumnToContents(0)

    def on_double_click(self, index):
        item = self.model.itemFromIndex(index.siblingAtColumn(0))
        if item:
            path = item.data(Qt.UserRole)
            self.file_selected.emit(path)

    def show_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
            
        item = self.model.itemFromIndex(index.siblingAtColumn(0))
        path = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        
        act_open = menu.addAction("Open")
        act_open.triggered.connect(lambda: self.file_selected.emit(path))
        
        act_export = menu.addAction("Export...")
        act_export.triggered.connect(lambda: self.file_export_requested.emit(path))
        
        menu.addSeparator()
        
        act_inject = menu.addAction("Inject to Device...")
        act_inject.triggered.connect(lambda: self.file_inject_requested.emit(path))
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
