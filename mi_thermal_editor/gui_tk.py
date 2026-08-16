"""
Mi Thermal Editor - Native Desktop GUI (Tkinter)
Modern dark-themed UI matching Pandemonium Kernel Manager's Mi Thermal Editor.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from .adb import ADBManager, ConnectedDevice
from .analyzer import analyze_thermal_config
from .crypto import (
    DEFAULT_KEY,
    DEFAULT_IV,
    ThermalFile,
    batch_decrypt_directory,
    batch_encrypt_directory,
    decrypt_data,
    encrypt_data,
    is_printable_text,
    load_thermal_file,
    save_thermal_file,
    scan_thermal_files,
)
from .diff_engine import compute_thermal_diff
from .parser import parse_thermal_config


# Color Palette (Material Dark & Cyan Accent)
BG_DARK = "#121212"
BG_SURFACE = "#1E1E1E"
BG_CARD = "#252525"
BG_INPUT = "#2D2D2D"
ACCENT_CYAN = "#00E5FF"
ACCENT_PURPLE = "#BB86FC"
ACCENT_GREEN = "#03DAC6"
ACCENT_RED = "#CF6679"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#AAAAAA"
TEXT_MUTED = "#666666"
BORDER_COLOR = "#3A3A3A"


class SyntaxHighlighter:
    """Provides syntax highlighting for Xiaomi/Qualcomm thermal conf syntax."""

    def __init__(self, text_widget: tk.Text):
        self.text = text_widget
        self.setup_tags()

    def setup_tags(self):
        self.text.tag_configure("section", foreground="#00E5FF", font=("JetBrains Mono", 10, "bold"))
        self.text.tag_configure("comment", foreground="#757575", font=("JetBrains Mono", 10, "italic"))
        self.text.tag_configure("keyword", foreground="#BB86FC", font=("JetBrains Mono", 10, "bold"))
        self.text.tag_configure("number", foreground="#FFB74D")
        self.text.tag_configure("sensor", foreground="#81C784")
        self.text.tag_configure("device", foreground="#4DD0E1")
        self.text.tag_configure("match", background="#FFB300", foreground="#000000")

    def highlight(self):
        content = self.text.get("1.0", tk.END)
        # Clear existing tags
        for tag in ("section", "comment", "keyword", "number", "sensor", "device"):
            self.text.tag_remove(tag, "1.0", tk.END)

        lines = content.splitlines()
        keywords = {"algo_type", "sampling", "polling", "set_point", "set_point_clr",
                    "trig", "clr", "target", "weight", "weights", "weight_sum",
                    "compensation", "action", "actions", "thresholds"}

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Comments
            if stripped.startswith("#"):
                self.text.tag_add("comment", f"{i}.0", f"{i}.end")
                continue

            # Section Headers [SECTION]
            if stripped.startswith("[") and stripped.endswith("]"):
                self.text.tag_add("section", f"{i}.0", f"{i}.end")
                continue

            # Keywords & tokens
            tokens = line.split()
            idx = 0
            for token in tokens:
                pos = line.find(token, idx)
                if pos != -1:
                    idx = pos + len(token)
                    start_idx = f"{i}.{pos}"
                    end_idx = f"{i}.{idx}"

                    token_lower = token.lower()
                    if token_lower in keywords:
                        self.text.tag_add("keyword", start_idx, end_idx)
                    elif token_lower.isdigit() or (token_lower.startswith("-") and token_lower[1:].isdigit()):
                        self.text.tag_add("number", start_idx, end_idx)
                    elif "therm" in token_lower or "sensor" in token_lower or "battery" in token_lower:
                        self.text.tag_add("sensor", start_idx, end_idx)
                    elif "cpu" in token_lower or "gpu" in token_lower or "cluster" in token_lower:
                        self.text.tag_add("device", start_idx, end_idx)


class MiThermalEditorTk:
    """Main Tkinter Desktop GUI Application."""

    def __init__(self, root: tk.Tk, initial_dir: Optional[str] = None):
        self.root = root
        self.root.title("Mi Thermal Editor - Linux")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG_DARK)

        self.adb = ADBManager()
        self.current_file: Optional[ThermalFile] = None
        self.current_source_dir = initial_dir or self._detect_default_dir()
        self.loaded_files: List[Path] = []

        self.apply_theme()
        self.build_ui()

        if self.current_source_dir and os.path.isdir(self.current_source_dir):
            self.refresh_file_list()

    def _detect_default_dir(self) -> str:
        # Check standard system paths or local peridot directory
        repo_odm = "/serverhive/yukia/luna/vendor/xiaomi/peridot/proprietary/odm/etc"
        if os.path.isdir(repo_odm):
            return repo_odm
        for p in ("/odm/etc", "/vendor/etc", "/system/etc"):
            if os.path.isdir(p):
                return p
        return os.getcwd()

    def apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Sans", 9))
        style.configure("TFrame", background=BG_DARK)
        style.configure("Surface.TFrame", background=BG_SURFACE)
        style.configure("Card.TFrame", background=BG_CARD, relief="flat")

        style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Sans", 9))
        style.configure("Header.TLabel", font=("Sans", 12, "bold"), foreground=ACCENT_CYAN, background=BG_SURFACE)
        style.configure("SubHeader.TLabel", font=("Sans", 9, "bold"), foreground=TEXT_SECONDARY, background=BG_SURFACE)
        style.configure("BadgeEnc.TLabel", background="#382100", foreground="#FFA726", font=("Sans", 8, "bold"), padding=3)
        style.configure("BadgeDec.TLabel", background="#003828", foreground="#03DAC6", font=("Sans", 8, "bold"), padding=3)

        style.configure("TButton", background=BG_CARD, foreground=TEXT_PRIMARY, borderwidth=1, relief="flat", padding=6)
        style.map("TButton", background=[("active", BG_INPUT), ("pressed", ACCENT_PURPLE)])

        style.configure("Accent.TButton", background=ACCENT_CYAN, foreground="#000000", font=("Sans", 9, "bold"), padding=6)
        style.map("Accent.TButton", background=[("active", "#00B4D8")])

        style.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT_PRIMARY, insertcolor=TEXT_PRIMARY, padding=5)
        style.configure("TCombobox", fieldbackground=BG_INPUT, foreground=TEXT_PRIMARY, background=BG_CARD, padding=5)

        style.configure("Treeview", background=BG_SURFACE, foreground=TEXT_PRIMARY, fieldbackground=BG_SURFACE, borderwidth=0, rowheight=26)
        style.map("Treeview", background=[("selected", "#004D40")], foreground=[("selected", ACCENT_CYAN)])
        style.configure("Treeview.Heading", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Sans", 9, "bold"))

        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT_SECONDARY, padding=[12, 6], font=("Sans", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", BG_SURFACE)], foreground=[("selected", ACCENT_CYAN)])

    def build_ui(self):
        # Top Header Bar
        top_bar = ttk.Frame(self.root, style="Surface.TFrame", padding=(15, 10))
        top_bar.pack(fill=tk.X, side=tk.TOP)

        title_label = ttk.Label(top_bar, text="🔥 Mi Thermal Editor", style="Header.TLabel")
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(top_bar, text="Xiaomi / HyperOS Thermal Decryptor & Analyzer", font=("Sans", 8), foreground=TEXT_SECONDARY, background=BG_SURFACE)
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

        # Top Action Buttons
        btn_box = ttk.Frame(top_bar, style="Surface.TFrame")
        btn_box.pack(side=tk.RIGHT)

        ttk.Button(btn_box, text="📂 Open File...", command=self.action_open_single_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_box, text="📦 Batch Decrypt...", command=self.action_batch_decrypt).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_box, text="🔒 Batch Encrypt...", command=self.action_batch_encrypt).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_box, text="📱 ADB Sync...", command=self.action_open_adb_dialog).pack(side=tk.LEFT, padx=3)

        # Main Paned Layout
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BORDER_COLOR, bd=0, sashwidth=4)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left Sidebar: Source Directory & File List
        sidebar_frame = ttk.Frame(main_pane, style="Surface.TFrame", padding=10)
        main_pane.add(sidebar_frame, minsize=300, width=350)

        # Source Dir Selector
        ttk.Label(sidebar_frame, text="THERMAL SOURCE DIRECTORY", style="SubHeader.TLabel").pack(anchor=tk.W, pady=(0, 4))
        dir_box = ttk.Frame(sidebar_frame, style="Surface.TFrame")
        dir_box.pack(fill=tk.X, pady=(0, 8))

        self.dir_entry = ttk.Entry(dir_box)
        self.dir_entry.insert(0, self.current_source_dir)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.dir_entry.bind("<Return>", lambda e: self.on_dir_changed())

        ttk.Button(dir_box, text="Browse", width=7, command=self.action_browse_dir).pack(side=tk.RIGHT)

        # Quick Preset Directories
        preset_box = ttk.Frame(sidebar_frame, style="Surface.TFrame")
        preset_box.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(preset_box, text="Presets:", font=("Sans", 8), foreground=TEXT_MUTED, background=BG_SURFACE).pack(side=tk.LEFT)
        for name, p in [("ODM", "/odm/etc"), ("Vendor", "/vendor/etc"), ("System", "/system/etc")]:
            btn = ttk.Button(preset_box, text=name, width=6, command=lambda path=p: self.set_preset_dir(path))
            btn.pack(side=tk.LEFT, padx=2)

        # Search Filter
        filter_box = ttk.Frame(sidebar_frame, style="Surface.TFrame")
        filter_box.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filter_box, text="Filter:", font=("Sans", 8), foreground=TEXT_SECONDARY, background=BG_SURFACE).pack(side=tk.LEFT, padx=(0, 4))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *args: self.filter_file_list())
        filter_entry = ttk.Entry(filter_box, textvariable=self.filter_var)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File List Table (Treeview)
        tree_frame = ttk.Frame(sidebar_frame, style="Surface.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "status", "size")
        self.file_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.file_tree.heading("name", text="Thermal Config", anchor=tk.W)
        self.file_tree.heading("status", text="Crypt", anchor=tk.CENTER)
        self.file_tree.heading("size", text="Size", anchor=tk.E)

        self.file_tree.column("name", width=180, anchor=tk.W)
        self.file_tree.column("status", width=70, anchor=tk.CENTER)
        self.file_tree.column("size", width=60, anchor=tk.E)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scroll.set)

        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_selected)

        # Right Area: Tabbed Views (Editor, Analyzer, Diff Viewer)
        right_frame = ttk.Frame(main_pane, style="Surface.TFrame", padding=10)
        main_pane.add(right_frame, minsize=500)

        # Tab Notebook
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Code Editor & Controls
        self.editor_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=8)
        self.notebook.add(self.editor_tab, text="📝 Thermal Editor")

        # Tab 2: Visual Rules & Trip Point Analyzer
        self.analyzer_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=8)
        self.notebook.add(self.analyzer_tab, text="📊 Thermal Analyzer")

        # Tab 3: Diff & Comparison
        self.diff_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=8)
        self.notebook.add(self.diff_tab, text="⚖️ Diff & Compare")

        self.build_editor_tab()
        self.build_analyzer_tab()
        self.build_diff_tab()

    def build_editor_tab(self):
        # File Info Banner
        info_bar = ttk.Frame(self.editor_tab, style="Card.TFrame", padding=8)
        info_bar.pack(fill=tk.X, pady=(0, 8))

        self.lbl_file_name = ttk.Label(info_bar, text="No file selected", font=("Sans", 10, "bold"), background=BG_CARD, foreground=ACCENT_CYAN)
        self.lbl_file_name.pack(side=tk.LEFT)

        self.lbl_status_badge = ttk.Label(info_bar, text="[IDLE]", style="BadgeDec.TLabel")
        self.lbl_status_badge.pack(side=tk.LEFT, padx=10)

        self.lbl_file_path = ttk.Label(info_bar, text="", font=("Sans", 8), foreground=TEXT_SECONDARY, background=BG_CARD)
        self.lbl_file_path.pack(side=tk.LEFT, padx=10)

        # Editor Toolbar
        toolbar = ttk.Frame(self.editor_tab, style="Surface.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 6))

        self.encrypt_toggle_var = tk.BooleanVar(value=True)
        self.chk_encrypt = tk.Checkbutton(
            toolbar, text="Save as Encrypted (AES-128-CBC)",
            variable=self.encrypt_toggle_var,
            bg=BG_SURFACE, fg=TEXT_PRIMARY, selectcolor=BG_INPUT,
            activebackground=BG_SURFACE, activeforeground=ACCENT_CYAN,
            font=("Sans", 9)
        )
        self.chk_encrypt.pack(side=tk.LEFT)

        ttk.Button(toolbar, text="💾 Save", style="Accent.TButton", command=self.action_save_current).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="💾 Save As...", command=self.action_save_as).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="📤 Export Plaintext", command=self.action_export_plaintext).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="📦 Export Encrypted", command=self.action_export_encrypted).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="📲 Inject to Device", command=self.action_inject_to_device).pack(side=tk.RIGHT, padx=3)

        # Text Editor with Line Numbers & Highlighting
        editor_container = ttk.Frame(self.editor_tab, style="Surface.TFrame")
        editor_container.pack(fill=tk.BOTH, expand=True)

        self.text_editor = tk.Text(
            editor_container,
            wrap=tk.NONE,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=ACCENT_CYAN,
            selectbackground="#004D40",
            selectforeground=TEXT_PRIMARY,
            font=("JetBrains Mono", 10),
            undo=True,
            maxundo=50,
            padx=10,
            pady=10,
            bd=0
        )
        self.highlighter = SyntaxHighlighter(self.text_editor)

        v_scroll = ttk.Scrollbar(editor_container, orient=tk.VERTICAL, command=self.text_editor.yview)
        h_scroll = ttk.Scrollbar(editor_container, orient=tk.HORIZONTAL, command=self.text_editor.xview)
        self.text_editor.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_editor.bind("<KeyRelease>", lambda e: self.highlighter.highlight())

    def build_analyzer_tab(self):
        # Top overview
        top_info = ttk.Frame(self.analyzer_tab, style="Card.TFrame", padding=10)
        top_info.pack(fill=tk.X, pady=(0, 8))

        self.lbl_analysis_title = ttk.Label(top_info, text="Thermal Rules & Mitigation Curve Analyzer", font=("Sans", 10, "bold"), background=BG_CARD, foreground=ACCENT_CYAN)
        self.lbl_analysis_title.pack(anchor=tk.W)

        self.lbl_analysis_summary = ttk.Label(top_info, text="Select a thermal configuration to analyze trip points, sensors, and cooling policies.", font=("Sans", 9), background=BG_CARD, foreground=TEXT_SECONDARY)
        self.lbl_analysis_summary.pack(anchor=tk.W, pady=(4, 0))

        # Tables for Rules / Trip points
        analysis_paned = tk.PanedWindow(self.analyzer_tab, orient=tk.VERTICAL, bg=BORDER_COLOR, bd=0, sashwidth=4)
        analysis_paned.pack(fill=tk.BOTH, expand=True)

        # Sensors Table
        sensor_frame = ttk.Frame(analysis_paned, style="Surface.TFrame", padding=4)
        analysis_paned.add(sensor_frame, minsize=150, height=180)

        ttk.Label(sensor_frame, text="SENSOR POLICIES & THRESHOLDS", style="SubHeader.TLabel").pack(anchor=tk.W, pady=(0, 2))
        sensor_cols = ("name", "type", "min_t", "max_t", "sections")
        self.sensor_tree = ttk.Treeview(sensor_frame, columns=sensor_cols, show="headings", height=5)
        self.sensor_tree.heading("name", text="Sensor Name", anchor=tk.W)
        self.sensor_tree.heading("type", text="Kind", anchor=tk.CENTER)
        self.sensor_tree.heading("min_t", text="Min Trip (°C)", anchor=tk.E)
        self.sensor_tree.heading("max_t", text="Max Trip (°C)", anchor=tk.E)
        self.sensor_tree.heading("sections", text="Referencing Rules", anchor=tk.W)

        self.sensor_tree.column("name", width=180, anchor=tk.W)
        self.sensor_tree.column("type", width=100, anchor=tk.CENTER)
        self.sensor_tree.column("min_t", width=100, anchor=tk.E)
        self.sensor_tree.column("max_t", width=100, anchor=tk.E)
        self.sensor_tree.column("sections", width=300, anchor=tk.W)
        self.sensor_tree.pack(fill=tk.BOTH, expand=True)

        # Device Mitigation Rules Table
        rules_frame = ttk.Frame(analysis_paned, style="Surface.TFrame", padding=4)
        analysis_paned.add(rules_frame, minsize=180)

        ttk.Label(rules_frame, text="DEVICE THROTTLING & COOLING MITIGATIONS", style="SubHeader.TLabel").pack(anchor=tk.W, pady=(0, 2))
        rule_cols = ("device", "section", "trig", "clr", "action")
        self.rules_tree = ttk.Treeview(rules_frame, columns=rule_cols, show="headings")
        self.rules_tree.heading("device", text="Cooling Device", anchor=tk.W)
        self.rules_tree.heading("section", text="Rule / Section", anchor=tk.W)
        self.rules_tree.heading("trig", text="Trigger (°C)", anchor=tk.E)
        self.rules_tree.heading("clr", text="Clear (°C)", anchor=tk.E)
        self.rules_tree.heading("action", text="Throttle Action / Target Freq", anchor=tk.W)

        self.rules_tree.column("device", width=140, anchor=tk.W)
        self.rules_tree.column("section", width=200, anchor=tk.W)
        self.rules_tree.column("trig", width=100, anchor=tk.E)
        self.rules_tree.column("clr", width=100, anchor=tk.E)
        self.rules_tree.column("action", width=300, anchor=tk.W)
        self.rules_tree.pack(fill=tk.BOTH, expand=True)

    def build_diff_tab(self):
        # Diff Selection Controls
        ctrl_bar = ttk.Frame(self.diff_tab, style="Card.TFrame", padding=8)
        ctrl_bar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(ctrl_bar, text="Compare Current File with:", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Sans", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.compare_path_entry = ttk.Entry(ctrl_bar)
        self.compare_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(ctrl_bar, text="Browse...", command=self.action_browse_diff_target).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl_bar, text="⚡ Run Diff", style="Accent.TButton", command=self.action_run_diff).pack(side=tk.LEFT, padx=3)

        # Diff Output Text View
        diff_container = ttk.Frame(self.diff_tab, style="Surface.TFrame")
        diff_container.pack(fill=tk.BOTH, expand=True)

        self.diff_text = tk.Text(
            diff_container,
            wrap=tk.NONE,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            font=("JetBrains Mono", 10),
            padx=10,
            pady=10,
            bd=0
        )
        self.diff_text.tag_configure("diff_add", foreground="#03DAC6", background="#003828")
        self.diff_text.tag_configure("diff_del", foreground="#CF6679", background="#380008")
        self.diff_text.tag_configure("diff_header", foreground=ACCENT_CYAN, font=("JetBrains Mono", 10, "bold"))
        self.diff_text.tag_configure("diff_section", foreground=ACCENT_PURPLE, font=("JetBrains Mono", 10, "bold"))

        d_v_scroll = ttk.Scrollbar(diff_container, orient=tk.VERTICAL, command=self.diff_text.yview)
        d_h_scroll = ttk.Scrollbar(diff_container, orient=tk.HORIZONTAL, command=self.diff_text.xview)
        self.diff_text.configure(yscrollcommand=d_v_scroll.set, xscrollcommand=d_h_scroll.set)

        d_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        d_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.diff_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # --- Actions & Event Handlers ---

    def on_dir_changed(self):
        new_dir = self.dir_entry.get().strip()
        if os.path.isdir(new_dir):
            self.current_source_dir = new_dir
            self.refresh_file_list()
        else:
            messagebox.showerror("Invalid Directory", f"Directory does not exist:\n{new_dir}")

    def set_preset_dir(self, path: str):
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, path)
        self.on_dir_changed()

    def action_browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.current_source_dir, title="Select Thermal Source Directory")
        if chosen:
            self.set_preset_dir(chosen)

    def refresh_file_list(self):
        if not os.path.isdir(self.current_source_dir):
            return

        self.loaded_files = scan_thermal_files(self.current_source_dir)
        self.filter_file_list()

    def filter_file_list(self):
        query = self.filter_var.get().lower().strip()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        for fpath in self.loaded_files:
            if query and query not in fpath.name.lower():
                continue

            # Quick detect encryption
            try:
                with open(fpath, "rb") as fp:
                    header = fp.read(32)
                is_enc = (len(header) > 0 and not is_printable_text(header[:16].decode("utf-8", errors="ignore")))
            except Exception:
                is_enc = False

            status_str = "🔒 Encrypted" if is_enc else "📄 Plain"
            size_kb = f"{fpath.stat().st_size / 1024:.1f} KB"

            self.file_tree.insert("", tk.END, iid=str(fpath), values=(fpath.name, status_str, size_kb))

    def on_file_selected(self, event):
        selected = self.file_tree.selection()
        if not selected:
            return

        fpath = selected[0]
        self.load_file(fpath)

    def load_file(self, file_path: str):
        try:
            self.current_file = load_thermal_file(file_path)
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Failed to load thermal file:\n{e}")
            return

        self.lbl_file_name.configure(text=self.current_file.name)
        self.lbl_file_path.configure(text=self.current_file.source_path)

        if self.current_file.is_encrypted:
            self.lbl_status_badge.configure(text="🔒 ENCRYPTED (AES-128-CBC)", style="BadgeEnc.TLabel")
            self.encrypt_toggle_var.set(True)
        else:
            self.lbl_status_badge.configure(text="📄 PLAINTEXT", style="BadgeDec.TLabel")
            self.encrypt_toggle_var.set(False)

        # Fill Editor Text
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", self.current_file.content)
        self.highlighter.highlight()

        # Update Analyzer
        self.update_analyzer(self.current_file)

    def update_analyzer(self, thermal_file: ThermalFile):
        report = analyze_thermal_config(thermal_file.content, filename=thermal_file.name)

        # Clear existing
        for item in self.sensor_tree.get_children():
            self.sensor_tree.delete(item)
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Populate header info
        sconfig_desc = ""
        if report.matched_sconfig:
            sconfig_desc = f" | SCONFIG [{report.matched_sconfig['id']}]: {report.matched_sconfig['name']} ({report.matched_sconfig['category']})"

        self.lbl_analysis_title.configure(text=f"Thermal Analysis: {thermal_file.name}{sconfig_desc}")
        self.lbl_analysis_summary.configure(
            text=f"Total Sections: {report.total_sections} | Sensors: {len(report.sensors)} | "
                 f"Temp Range: {f'{report.lowest_throttle_temp:.1f}°C' if report.lowest_throttle_temp else 'N/A'} -> "
                 f"{f'{report.highest_throttle_temp:.1f}°C' if report.highest_throttle_temp else 'N/A'}"
        )

        # Populate Sensors
        for s in report.sensors:
            stype = "Virtual Sensor" if s.is_virtual else "Physical Sensor"
            min_t = f"{s.min_trigger_temp:.1f}°C" if s.min_trigger_temp is not None else "-"
            max_t = f"{s.max_trigger_temp:.1f}°C" if s.max_trigger_temp is not None else "-"
            secs = ", ".join(s.used_in_sections[:5])
            self.sensor_tree.insert("", tk.END, values=(s.sensor_name, stype, min_t, max_t, secs))

        # Populate Device Mitigations
        for d in report.devices:
            for rule in d.trip_points:
                trig_str = f"{rule['trigger']:.1f}°C" if rule['trigger'] is not None else "-"
                clr_str = f"{rule['clear']:.1f}°C" if rule['clear'] is not None else "-"
                action_str = str(rule['action']) if rule['action'] else "-"
                self.rules_tree.insert("", tk.END, values=(d.device_name, rule['section'], trig_str, clr_str, action_str))

    def action_save_current(self):
        if not self.current_file:
            messagebox.showwarning("No File", "Please select a thermal file to save.")
            return

        content = self.text_editor.get("1.0", "end-1c")
        encrypt = self.encrypt_toggle_var.get()

        try:
            saved_p, bck_p = save_thermal_file(
                self.current_file.source_path,
                content,
                encrypt=encrypt,
                create_backup=True
            )
            msg = f"Saved thermal file successfully!\nPath: {saved_p}"
            if bck_p:
                msg += f"\nBackup: {bck_p}"
            messagebox.showinfo("Saved", msg)
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{e}")

    def action_save_as(self):
        content = self.text_editor.get("1.0", "end-1c")
        encrypt = self.encrypt_toggle_var.get()

        default_name = self.current_file.name if self.current_file else "thermal-custom.conf"
        target = filedialog.asksaveasfilename(
            initialdir=self.current_source_dir,
            initialfile=default_name,
            filetypes=[("Thermal Config", "*.conf"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not target:
            return

        try:
            saved_p, _ = save_thermal_file(target, content, encrypt=encrypt, create_backup=False)
            messagebox.showinfo("Saved", f"File saved as:\n{saved_p}")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{e}")

    def action_export_plaintext(self):
        content = self.text_editor.get("1.0", "end-1c")
        default_name = (self.current_file.name if self.current_file else "thermal.conf")
        if not default_name.endswith(".conf") and not default_name.endswith(".txt"):
            default_name += ".conf"

        target = filedialog.asksaveasfilename(
            initialfile=f"decrypted_{default_name}",
            filetypes=[("Thermal Config (.conf)", "*.conf"), ("Text File (.txt)", "*.txt"), ("All Files", "*.*")]
        )
        if not target:
            return

        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Export Plaintext", f"Exported plaintext thermal file:\n{target}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")

    def action_export_encrypted(self):
        content = self.text_editor.get("1.0", "end-1c")
        default_name = (self.current_file.name if self.current_file else "thermal.conf")

        target = filedialog.asksaveasfilename(
            initialfile=f"encrypted_{default_name}",
            filetypes=[("Thermal Config (.conf)", "*.conf"), ("All Files", "*.*")]
        )
        if not target:
            return

        try:
            enc_bytes = encrypt_data(content)
            with open(target, "wb") as f:
                f.write(enc_bytes)
            messagebox.showinfo("Export Encrypted", f"Exported encrypted thermal binary:\n{target}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")

    def action_open_single_file(self):
        chosen = filedialog.askopenfilename(
            title="Open Thermal File",
            filetypes=[("Thermal Files", "*.conf *.json *.sconfig"), ("All Files", "*.*")]
        )
        if chosen:
            self.load_file(chosen)

    def action_batch_decrypt(self):
        src_dir = filedialog.askdirectory(title="Select Source Folder with Encrypted Thermal Files")
        if not src_dir:
            return
        dst_dir = filedialog.askdirectory(title="Select Destination Folder for Decrypted Plaintext")
        if not dst_dir:
            return

        try:
            results = batch_decrypt_directory(src_dir, dst_dir)
            enc_count = sum(1 for _, _, is_enc in results if is_enc)
            messagebox.showinfo(
                "Batch Decrypt Finished",
                f"Successfully processed {len(results)} files ({enc_count} decrypted from AES-128-CBC) into:\n{dst_dir}"
            )
        except Exception as e:
            messagebox.showerror("Batch Decrypt Error", f"Error during batch decryption:\n{e}")

    def action_batch_encrypt(self):
        src_dir = filedialog.askdirectory(title="Select Source Folder with Plaintext Thermal Files")
        if not src_dir:
            return
        dst_dir = filedialog.askdirectory(title="Select Destination Folder for Encrypted Files")
        if not dst_dir:
            return

        try:
            results = batch_encrypt_directory(src_dir, dst_dir)
            messagebox.showinfo(
                "Batch Encrypt Finished",
                f"Successfully encrypted {len(results)} files with AES-128-CBC into:\n{dst_dir}"
            )
        except Exception as e:
            messagebox.showerror("Batch Encrypt Error", f"Error during batch encryption:\n{e}")

    def action_browse_diff_target(self):
        chosen = filedialog.askopenfilename(
            title="Select File to Compare",
            filetypes=[("Thermal Config", "*.conf *.json *.sconfig"), ("All Files", "*.*")]
        )
        if chosen:
            self.compare_path_entry.delete(0, tk.END)
            self.compare_path_entry.insert(0, chosen)
            self.action_run_diff()

    def action_run_diff(self):
        target_path = self.compare_path_entry.get().strip()
        if not os.path.isfile(target_path):
            messagebox.showerror("Invalid File", "Please select a valid comparison file.")
            return

        content_curr = self.text_editor.get("1.0", "end-1c")
        curr_name = self.current_file.name if self.current_file else "Current Editor"

        try:
            other_obj = load_thermal_file(target_path)
            content_other = other_obj.content
            other_name = other_obj.name
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load comparison file:\n{e}")
            return

        diff_res = compute_thermal_diff(content_curr, content_other, name_a=curr_name, name_b=other_name)

        self.diff_text.delete("1.0", tk.END)
        self.diff_text.insert(tk.END, f"=== {diff_res.summary} ===\n\n", "diff_header")

        if diff_res.added_sections:
            self.diff_text.insert(tk.END, f"[+] Added Sections in {other_name}:\n", "diff_add")
            for sec in diff_res.added_sections:
                self.diff_text.insert(tk.END, f"    + [{sec}]\n", "diff_add")
            self.diff_text.insert(tk.END, "\n")

        if diff_res.removed_sections:
            self.diff_text.insert(tk.END, f"[-] Removed Sections from {other_name}:\n", "diff_del")
            for sec in diff_res.removed_sections:
                self.diff_text.insert(tk.END, f"    - [{sec}]\n", "diff_del")
            self.diff_text.insert(tk.END, "\n")

        if diff_res.modified_sections:
            self.diff_text.insert(tk.END, "[~] Modified Sections:\n", "diff_section")
            for s_diff in diff_res.modified_sections:
                self.diff_text.insert(tk.END, f"  Section [{s_diff.section_name}]:\n", "diff_section")
                for ch in s_diff.changes:
                    self.diff_text.insert(tk.END, f"    * {ch}\n")
            self.diff_text.insert(tk.END, "\n")

        self.diff_text.insert(tk.END, "=== Unified Line Diff ===\n", "diff_header")
        for line in diff_res.unified_diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                self.diff_text.insert(tk.END, line, "diff_add")
            elif line.startswith("-") and not line.startswith("---"):
                self.diff_text.insert(tk.END, line, "diff_del")
            elif line.startswith("@@"):
                self.diff_text.insert(tk.END, line, "diff_section")
            else:
                self.diff_text.insert(tk.END, line)

        self.notebook.select(self.diff_tab)

    def action_inject_to_device(self):
        devices = self.adb.list_devices()
        if not devices:
            messagebox.showwarning("No Device", "No ADB devices connected. Please connect your Xiaomi device with ADB enabled.")
            return

        target_remote_path = ""
        if self.current_file and self.current_file.source_path.startswith(("/odm/", "/vendor/", "/system/")):
            target_remote_path = self.current_file.source_path
        else:
            filename = self.current_file.name if self.current_file else "thermal-normal.conf"
            target_remote_path = f"/odm/etc/{filename}"

        # Ask user confirmation
        confirm = messagebox.askyesno(
            "Confirm Device Injection",
            f"Are you sure you want to inject this thermal configuration to the connected device?\n\n"
            f"Target Path: {target_remote_path}\n\n"
            f"This will:\n"
            f"1. Remount the partition as RW with root\n"
            f"2. Create a backup as {target_remote_path}.bak\n"
            f"3. Overwrite with encrypted AES-128-CBC thermal data\n"
            f"4. Restore root permissions (0644 root:root)"
        )
        if not confirm:
            return

        content = self.text_editor.get("1.0", "end-1c")
        enc_bytes = encrypt_data(content)

        success, msg = self.adb.inject_thermal_file(target_remote_path, enc_bytes)
        if success:
            messagebox.showinfo("Injection Success", msg)
        else:
            messagebox.showerror("Injection Error", f"Injection failed:\n{msg}")

    def action_open_adb_dialog(self):
        AdbSyncDialog(self.root, self.adb, on_file_pulled=self.load_file)


class AdbSyncDialog:
    """Dialog for scanning and pulling thermal files directly from connected devices."""

    def __init__(self, parent: tk.Tk, adb: ADBManager, on_file_pulled):
        self.adb = adb
        self.on_file_pulled = on_file_pulled

        self.dlg = tk.Toplevel(parent)
        self.dlg.title("ADB Thermal Device Sync")
        self.dlg.geometry("700x500")
        self.dlg.configure(bg=BG_DARK)
        self.dlg.transient(parent)
        self.dlg.grab_set()

        self.build_ui()
        self.refresh_devices()

    def build_ui(self):
        header = ttk.Frame(self.dlg, style="Surface.TFrame", padding=10)
        header.pack(fill=tk.X)
        ttk.Label(header, text="📱 Connected Xiaomi / Android Devices", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="🔄 Refresh", command=self.refresh_devices).pack(side=tk.RIGHT)

        # Device selector
        dev_frame = ttk.Frame(self.dlg, style="Surface.TFrame", padding=10)
        dev_frame.pack(fill=tk.X)
        ttk.Label(dev_frame, text="Device:").pack(side=tk.LEFT, padx=(0, 6))
        self.dev_combo = ttk.Combobox(dev_frame, state="readonly", width=40)
        self.dev_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(dev_frame, text="Scan Thermal Files", command=self.scan_device_files).pack(side=tk.RIGHT)

        # Live Sconfig & status
        self.lbl_sconfig = ttk.Label(self.dlg, text="Active SCONFIG Profile: Unknown | Root: Checking...", font=("Sans", 9), foreground=ACCENT_CYAN)
        self.lbl_sconfig.pack(fill=tk.X, padx=15, pady=4)

        # File List
        list_frame = ttk.Frame(self.dlg, style="Surface.TFrame", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("dir", "file")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.tree.heading("dir", text="Directory", anchor=tk.W)
        self.tree.heading("file", text="Thermal Config File", anchor=tk.W)
        self.tree.column("dir", width=180, anchor=tk.W)
        self.tree.column("file", width=400, anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_bar = ttk.Frame(self.dlg, style="Surface.TFrame", padding=10)
        btn_bar.pack(fill=tk.X)
        ttk.Button(btn_bar, text="📥 Pull & Open in Editor", style="Accent.TButton", command=self.pull_selected_file).pack(side=tk.RIGHT)

    def refresh_devices(self):
        devices = self.adb.list_devices()
        values = []
        for d in devices:
            root_str = " (ROOT AVAILABLE)" if d.is_root else " (No Root)"
            values.append(f"{d.serial} - {d.model or d.device}{root_str}")

        self.dev_combo["values"] = values
        if values:
            self.dev_combo.current(0)
            self.update_device_info()
        else:
            self.lbl_sconfig.configure(text="No ADB devices detected. Connect device with USB debugging enabled.")

    def update_device_info(self):
        s = self.get_selected_serial()
        if not s:
            return
        sconfig = self.adb.get_active_sconfig(serial=s)
        is_root = self.adb.check_root(serial=s)
        sconfig_str = str(sconfig) if sconfig is not None else "N/A"
        root_str = "YES (Rooted)" if is_root else "NO (Root Required for /odm/etc write)"
        self.lbl_sconfig.configure(text=f"Active SCONFIG: {sconfig_str} | Root Access: {root_str}")

    def get_selected_serial(self) -> Optional[str]:
        val = self.dev_combo.get()
        if val:
            return val.split(" - ")[0].strip()
        return None

    def scan_device_files(self):
        s = self.get_selected_serial()
        if not s:
            return

        self.update_device_info()
        for item in self.tree.get_children():
            self.tree.delete(item)

        results = self.adb.scan_device_thermal_files(serial=s)
        for sdir, files in results.items():
            for f in files:
                self.tree.insert("", tk.END, values=(sdir, f))

    def pull_selected_file(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a thermal file to pull.")
            return

        sdir, fname = self.tree.item(selected[0], "values")
        remote_path = f"{sdir}/{fname}"
        serial = self.get_selected_serial()

        success, data, err = self.adb.pull_thermal_file(remote_path, serial=serial)
        if not success:
            messagebox.showerror("Pull Error", f"Failed to pull {remote_path}:\n{err}")
            return

        # Save to local temporary cache
        cache_dir = Path("/tmp/mi_thermal_pulled")
        cache_dir.mkdir(parents=True, exist_ok=True)
        local_path = cache_dir / fname
        with open(local_path, "wb") as fp:
            fp.write(data)

        self.dlg.destroy()
        self.on_file_pulled(str(local_path))


def launch_gui(initial_dir: Optional[str] = None):
    """Launches the native Tkinter GUI."""
    root = tk.Tk()
    app = MiThermalEditorTk(root, initial_dir=initial_dir)
    root.mainloop()
