"""
Mi Thermal Editor - Standalone Web GUI Server
Zero-dependency embedded Web GUI replicating Pandemonium Kernel Manager's Mi Thermal Editor.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from .services.adb_service import ADBManager
from .core.analyzer import XIAOMI_SCONFIG_DB, analyze_thermal_config
from .core.crypto import (
    DEFAULT_KEY,
    DEFAULT_IV,
    batch_decrypt_directory,
    batch_encrypt_directory,
    decrypt_data,
    encrypt_data,
    load_thermal_file,
    save_thermal_file,
    scan_thermal_files,
)
from .core.diff_engine import compute_thermal_diff
from .core.parser import parse_thermal_config


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Thermal Editor - Linux</title>
    <style>
        :root {
            --bg-dark: #121212;
            --bg-surface: #1E1E1E;
            --bg-card: #252525;
            --bg-input: #2D2D2D;
            --border-color: #383838;
            --accent-cyan: #00E5FF;
            --accent-purple: #BB86FC;
            --accent-green: #03DAC6;
            --accent-red: #CF6679;
            --accent-orange: #FFA726;
            --text-primary: #FFFFFF;
            --text-secondary: #B0B0B0;
            --text-muted: #757575;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            --font-mono: "JetBrains Mono", "Fira Code", "Courier New", monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 14px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        /* Top Header */
        header {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-title h1 {
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        .header-title span {
            font-size: 12px;
            color: var(--text-secondary);
            background: rgba(0, 229, 255, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            border: 1px solid rgba(0, 229, 255, 0.2);
        }
        .header-actions {
            display: flex;
            gap: 8px;
        }

        /* Buttons */
        button, .btn {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--font-sans);
        }
        button:hover {
            background: var(--bg-input);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }
        button.btn-primary {
            background: var(--accent-cyan);
            color: #000000;
            font-weight: 600;
            border: none;
        }
        button.btn-primary:hover {
            background: #26edff;
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
        }
        button.btn-accent {
            background: var(--accent-purple);
            color: #000000;
            font-weight: 600;
            border: none;
        }

        /* App Layout */
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: 340px;
            background: var(--bg-surface);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .sidebar-section {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
        }
        .sidebar-title {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .source-input-group {
            display: flex;
            gap: 6px;
        }
        input[type="text"] {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 7px 10px;
            border-radius: 6px;
            font-size: 13px;
            width: 100%;
            outline: none;
            font-family: var(--font-mono);
        }
        input[type="text"]:focus {
            border-color: var(--accent-cyan);
        }
        .preset-pills {
            display: flex;
            gap: 5px;
            margin-top: 8px;
        }
        .pill {
            font-size: 11px;
            padding: 3px 8px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            cursor: pointer;
            color: var(--text-secondary);
        }
        .pill:hover {
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
        }

        /* File List */
        .file-list-container {
            flex: 1;
            overflow-y: auto;
            padding: 6px;
        }
        .file-item {
            padding: 8px 12px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            margin-bottom: 4px;
            border: 1px solid transparent;
            transition: all 0.1s ease;
        }
        .file-item:hover {
            background: var(--bg-card);
        }
        .file-item.active {
            background: rgba(0, 229, 255, 0.12);
            border-color: var(--accent-cyan);
        }
        .file-info {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .file-name {
            font-weight: 500;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .file-meta {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .badge {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .badge-enc {
            background: rgba(255, 167, 38, 0.15);
            color: var(--accent-orange);
            border: 1px solid rgba(255, 167, 38, 0.3);
        }
        .badge-plain {
            background: rgba(3, 218, 198, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(3, 218, 198, 0.3);
        }

        /* Content Area */
        .content-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-dark);
            overflow: hidden;
        }

        /* Navigation Tabs */
        .tab-bar {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            padding: 0 16px;
            gap: 20px;
        }
        .tab-btn {
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            border-radius: 0;
            color: var(--text-secondary);
            padding: 12px 4px;
            font-size: 13px;
            font-weight: 600;
        }
        .tab-btn:hover {
            color: var(--text-primary);
            background: transparent;
            border-color: transparent;
        }
        .tab-btn.active {
            color: var(--accent-cyan);
            border-bottom-color: var(--accent-cyan);
        }

        /* Tab Panels */
        .tab-panel {
            display: none;
            flex: 1;
            flex-direction: column;
            overflow: hidden;
            padding: 14px;
        }
        .tab-panel.active {
            display: flex;
        }

        /* Editor Toolbar & Info */
        .editor-top-bar {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .editor-title-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .editor-title {
            font-family: var(--font-mono);
            font-weight: 700;
            color: var(--accent-cyan);
        }
        .editor-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: var(--text-secondary);
            cursor: pointer;
            margin-right: 8px;
        }

        /* Code Editor */
        .editor-wrapper {
            flex: 1;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            display: flex;
            overflow: hidden;
            position: relative;
        }
        textarea.code-editor {
            flex: 1;
            background: transparent;
            color: #E0E0E0;
            border: none;
            resize: none;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.5;
            outline: none;
            white-space: pre;
            overflow: auto;
            tab-size: 4;
        }

        /* Analyzer Styles */
        .analyzer-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
        }
        .analyzer-card h3 {
            font-size: 14px;
            color: var(--accent-cyan);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }
        .stat-box {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px;
        }
        .stat-box .stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        .stat-box .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-green);
            margin-top: 4px;
        }
        table.data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }
        table.data-table th, table.data-table td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        table.data-table th {
            background: var(--bg-card);
            color: var(--text-secondary);
            font-weight: 600;
        }
        table.data-table tr:hover td {
            background: var(--bg-card);
        }

        /* Diff Viewer */
        .diff-split {
            display: flex;
            gap: 12px;
            flex: 1;
            overflow: hidden;
        }
        .diff-side {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }
        .diff-side-header {
            background: var(--bg-card);
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
        }
        .diff-output {
            flex: 1;
            padding: 10px;
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.4;
            overflow: auto;
            white-space: pre;
        }
        .diff-line-add { background: rgba(3, 218, 198, 0.15); color: #03DAC6; }
        .diff-line-del { background: rgba(207, 102, 121, 0.15); color: #CF6679; }
        .diff-line-sec { color: var(--accent-purple); font-weight: 700; }

        /* Modal dialogs */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.7);
            z-index: 999;
            align-items: center;
            justify-content: center;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal-content {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            width: 550px;
            max-width: 90vw;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .modal-title {
            font-size: 16px;
            color: var(--accent-cyan);
            margin-bottom: 12px;
        }
        .modal-body {
            margin-bottom: 18px;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }

        /* Toast Notifications */
        #toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--bg-card);
            border: 1px solid var(--accent-cyan);
            color: var(--text-primary);
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            display: none;
            z-index: 10000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>🔥 Mi Thermal Editor</h1>
            <span>Linux GUI Edition</span>
        </div>
        <div class="header-actions">
            <button onclick="openModal('batchDecryptModal')">📦 Batch Decrypt</button>
            <button onclick="openModal('batchEncryptModal')">🔒 Batch Encrypt</button>
            <button onclick="openAdbModal()">📱 ADB Sync</button>
            <button class="btn-primary" onclick="saveCurrentFile()">💾 Save</button>
        </div>
    </header>

    <div class="main-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">Thermal Source Directory</div>
                <div class="source-input-group">
                    <input type="text" id="srcDirInput" placeholder="Folder or file path..." style="flex:1" />
                    <button onclick="fetchFiles()" title="Scan">🔍</button>
                    <button onclick="browseLocalFolder()" style="padding:6px; font-size:14px;" title="Browse Folder">📂</button>
                    <button onclick="browseLocalFile()" style="padding:6px; font-size:14px;" title="Browse File">📄</button>
                </div>
                <div style="margin-top: 8px;">
                    <label class="checkbox-label" style="font-size:12px;">
                        <input type="checkbox" id="recursiveScan" /> Scan Folders Recursively
                    </label>
                </div>
                <div class="preset-pills" style="margin-top: 8px;">
                    <span class="pill" onclick="setDir('/odm/etc')">/odm/etc</span>
                    <span class="pill" onclick="setDir('/vendor/etc')">/vendor/etc</span>
                    <span class="pill" onclick="setDir('/system/etc')">/system/etc</span>
                    <span class="pill" onclick="setDir('.')">Current Dir</span>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="sidebar-title">Search Thermal Configs</div>
                <input type="text" id="filterInput" placeholder="Filter by name (e.g. normal, mgame)..." oninput="renderFileList()" />
            </div>

            <div class="file-list-container" id="fileList">
                <div style="padding: 20px; text-align: center; color: var(--text-muted);">
                    Scanning for thermal files...
                </div>
            </div>
        </div>

        <!-- Main Content View -->
        <div class="content-area">
            <div class="tab-bar">
                <button class="tab-btn active" onclick="switchTab('editorTab', this)">📝 Code Editor</button>
                <button class="tab-btn" onclick="switchTab('analyzerTab', this)">📊 Thermal Analyzer</button>
                <button class="tab-btn" onclick="switchTab('diffTab', this)">⚖️ Compare & Diff</button>
                <button class="tab-btn" onclick="switchTab('sconfigTab', this)">📖 Xiaomi SCONFIG Profiles</button>
            </div>

            <!-- Tab 1: Editor -->
            <div id="editorTab" class="tab-panel active">
                <div class="editor-top-bar">
                    <div class="editor-title-box">
                        <span class="editor-title" id="currentFileName">No file selected</span>
                        <span class="badge badge-plain" id="cryptoBadge">Plaintext</span>
                    </div>
                    <div class="editor-actions">
                        <label class="checkbox-label">
                            <input type="checkbox" id="encryptOnSave" checked />
                            Encrypt with AES-128-CBC
                        </label>
                        <button onclick="exportPlaintext()">📤 Export Plain</button>
                        <button onclick="exportEncrypted()">📦 Export Encrypted</button>
                        <button class="btn-accent" onclick="injectToAdb()">📲 Inject ADB</button>
                    </div>
                </div>
                <div class="editor-wrapper">
                    <textarea class="code-editor" id="codeEditor" spellcheck="false" placeholder="Select a thermal file to view or edit..."></textarea>
                </div>
            </div>

            <!-- Tab 2: Analyzer -->
            <div id="analyzerTab" class="tab-panel" style="overflow-y: auto;">
                <div class="analyzer-card">
                    <h3 id="analyzerHeader">📈 Thermal Profile Overview</h3>
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-label">Total Sections</div>
                            <div class="stat-value" id="statSections">-</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Monitored Sensors</div>
                            <div class="stat-value" id="statSensors">-</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Min Trigger Temp</div>
                            <div class="stat-value" id="statMinTemp">-</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Max Trigger Temp</div>
                            <div class="stat-value" id="statMaxTemp">-</div>
                        </div>
                    </div>
                </div>

                <div class="analyzer-card">
                    <h3>🌡️ Sensor Policies & Thresholds</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Sensor Name</th>
                                <th>Type</th>
                                <th>Min Trip</th>
                                <th>Max Trip</th>
                                <th>Referenced In Sections</th>
                            </tr>
                        </thead>
                        <tbody id="sensorsTableBody">
                            <tr><td colspan="5" style="color: var(--text-muted);">No thermal file loaded.</td></tr>
                        </tbody>
                    </table>
                </div>

                <div class="analyzer-card">
                    <h3>🛡️ Device Throttling & Cooling Rules</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Target Device</th>
                                <th>Rule / Section</th>
                                <th>Trigger (°C)</th>
                                <th>Clear (°C)</th>
                                <th>Mitigation Action</th>
                            </tr>
                        </thead>
                        <tbody id="rulesTableBody">
                            <tr><td colspan="5" style="color: var(--text-muted);">No thermal file loaded.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tab 3: Diff Viewer -->
            <div id="diffTab" class="tab-panel">
                <div class="editor-top-bar">
                    <div style="display: flex; gap: 8px; align-items: center; width: 100%;">
                        <span style="font-weight: 600; color: var(--text-secondary);">Compare with:</span>
                        <input type="text" id="diffTargetInput" placeholder="Path to second thermal config file or select..." style="max-width: 400px;" />
                        <button onclick="runDiff()">Run Comparison</button>
                    </div>
                </div>
                <div class="diff-split">
                    <div class="diff-side">
                        <div class="diff-side-header" id="diffSummaryHeader">Diff Output</div>
                        <div class="diff-output" id="diffOutput">Select a file to compare.</div>
                    </div>
                </div>
            </div>

            <!-- Tab 4: Xiaomi Sconfig Profiles Knowledge Base -->
            <div id="sconfigTab" class="tab-panel" style="overflow-y: auto;">
                <div class="analyzer-card">
                    <h3>Xiaomi / HyperOS SCONFIG Profile Knowledge Base</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 12px;">
                        The kernel exposes <code>/sys/class/thermal/thermal_message/sconfig</code> which dynamically selects thermal policies.
                    </p>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>SCONFIG ID</th>
                                <th>Profile Name</th>
                                <th>Config File</th>
                                <th>Category</th>
                                <th>Description & Use Case</th>
                            </tr>
                        </thead>
                        <tbody id="sconfigTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Batch Decrypt Modal -->
    <div id="batchDecryptModal" class="modal-overlay">
        <div class="modal-content" style="max-height: 90vh; display: flex; flex-direction: column;">
            <h2 class="modal-title">📦 Decrypt Scanned Configurations</h2>
            <div class="modal-body" style="overflow-y: auto;">
                <p style="color: var(--text-secondary); margin-bottom: 10px;">
                    Select the configs you want to decrypt from the current scan.
                </p>
                <div style="margin-bottom: 10px;">
                    <label class="checkbox-label" style="font-size: 14px;">
                        <input type="checkbox" id="selectAllDecrypt" onchange="toggleSelectAllDecrypt(this)" />
                        Select All Encrypted Files
                    </label>
                </div>
                <div id="decryptChecklist" style="background: var(--bg-dark); padding: 10px; border-radius: 6px; max-height: 250px; overflow-y: auto; margin-bottom: 15px; border: 1px solid var(--border-color);">
                    <!-- Checkboxes injected here via JS -->
                </div>
                <div>
                    <label class="sidebar-title">Output Directory (Plaintext)</label>
                    <input type="text" id="batchDecDst" value="/tmp/decrypted_thermal" style="width: 100%; padding: 8px; background: var(--bg-input); color: #fff; border: 1px solid var(--border-color); border-radius: 6px;" />
                </div>
            </div>
            <div class="modal-actions" style="margin-top: auto; padding-top: 15px;">
                <button onclick="closeModal('batchDecryptModal')">Cancel</button>
                <button class="btn-primary" onclick="executeBatchDecrypt(false)">Decrypt Selected</button>
                <button class="btn-accent" onclick="executeBatchDecrypt(true)">Batch Decrypt All</button>
            </div>
        </div>
    </div>

    <!-- Batch Encrypt Modal -->
    <div id="batchEncryptModal" class="modal-overlay">
        <div class="modal-content">
            <h2 class="modal-title">🔒 Batch Encrypt Thermal Files</h2>
            <div class="modal-body">
                <p style="color: var(--text-secondary); margin-bottom: 10px;">
                    Encrypts all plaintext thermal files in a directory into Xiaomi AES-128-CBC.
                </p>
                <div style="margin-bottom: 10px;">
                    <label class="sidebar-title">Source Directory (Plaintext)</label>
                    <input type="text" id="batchEncSrc" />
                </div>
                <div>
                    <label class="sidebar-title">Output Directory (Encrypted)</label>
                    <input type="text" id="batchEncDst" value="/tmp/encrypted_thermal" />
                </div>
            </div>
            <div class="modal-actions">
                <button onclick="closeModal('batchEncryptModal')">Cancel</button>
                <button class="btn-primary" onclick="executeBatchEncrypt()">Start Encryption</button>
            </div>
        </div>
    </div>

    <!-- ADB Sync Modal -->
    <div id="adbModal" class="modal-overlay">
        <div class="modal-content" style="width: 700px;">
            <h2 class="modal-title">📱 ADB Device Thermal Sync</h2>
            <div class="modal-body">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div id="adbStatusText" style="color: var(--accent-cyan); font-size: 13px;">Checking devices...</div>
                    <button onclick="loadAdbDevices()">🔄 Refresh</button>
                </div>
                <div style="margin-bottom: 10px;">
                    <label class="sidebar-title">Select Connected Device</label>
                    <select id="adbDeviceSelect" style="width: 100%; padding: 8px; background: var(--bg-input); color: #fff; border: 1px solid var(--border-color); border-radius: 6px;" onchange="onAdbDeviceChanged()"></select>
                </div>
                <label class="sidebar-title">Available Thermal Files on Device</label>
                <div id="adbFilesList" style="max-height: 250px; overflow-y: auto; background: var(--bg-dark); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px;"></div>
            </div>
            <div class="modal-actions">
                <button onclick="closeModal('adbModal')">Close</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        let allFiles = [];
        let currentFileObj = null;

        function showToast(msg) {
            const toast = document.getElementById("toast");
            toast.innerText = msg;
            toast.style.display = "block";
            setTimeout(() => { toast.style.display = "none"; }, 3500);
        }

        function openModal(id) {
            if (id === 'batchDecryptModal') {
                populateDecryptChecklist();
            }
            document.getElementById(id).classList.add("active");
        }
        function closeModal(id) { document.getElementById(id).classList.remove("active"); }

        function toggleSelectAllDecrypt(cb) {
            const checkboxes = document.querySelectorAll('#decryptChecklist input[type="checkbox"]');
            checkboxes.forEach(c => c.checked = cb.checked);
        }

        function populateDecryptChecklist() {
            const container = document.getElementById("decryptChecklist");
            container.innerHTML = "";
            const encFiles = allFiles.filter(f => f.is_encrypted);
            if (encFiles.length === 0) {
                container.innerHTML = "<div style='color: var(--text-muted);'>No encrypted files found in the current scan.</div>";
                return;
            }
            encFiles.forEach(f => {
                const div = document.createElement("div");
                div.style.marginBottom = "6px";
                div.innerHTML = `
                    <label class="checkbox-label" style="display: flex; cursor: pointer; align-items: center; gap: 8px;">
                        <input type="checkbox" value="${f.path}" />
                        <span style="color: var(--accent-cyan); font-weight: 500;">${f.name}</span>
                        <span style="color: var(--text-muted); font-size: 11px;">(${f.path})</span>
                    </label>
                `;
                container.appendChild(div);
            });
            document.getElementById("selectAllDecrypt").checked = false;
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.getElementById(tabId).classList.add("active");
            if (btn) btn.classList.add("active");
        }

        function setDir(path) {
            document.getElementById("srcDirInput").value = path;
            fetchFiles();
        }

        async function browseLocalFile() {
            try {
                const res = await fetch("/api/browse?type=file");
                const data = await res.json();
                if (data.path) {
                    document.getElementById("srcDirInput").value = data.path;
                    fetchFiles();
                }
            } catch (err) { showToast("Error browsing for file."); }
        }

        async function browseLocalFolder() {
            try {
                const res = await fetch("/api/browse?type=folder");
                const data = await res.json();
                if (data.path) {
                    document.getElementById("srcDirInput").value = data.path;
                    fetchFiles();
                }
            } catch (err) { showToast("Error browsing for folder."); }
        }

        async function fetchFiles() {
            const dir = document.getElementById("srcDirInput").value.trim();
            const recEl = document.getElementById("recursiveScan");
            const recursive = recEl ? recEl.checked : false;
            const listEl = document.getElementById("fileList");
            listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Loading files...</div>';

            try {
                const res = await fetch(`/api/files?dir=${encodeURIComponent(dir)}&recursive=${recursive}`);
                const data = await res.json();
                allFiles = data.files || [];
                renderFileList();
                if (allFiles.length > 0) {
                    loadFile(allFiles[0].path);
                }
            } catch (err) {
                listEl.innerHTML = `<div style="padding: 20px; color: var(--accent-red);">Error: ${err.message}</div>`;
            }
        }

        function renderFileList() {
            const filter = document.getElementById("filterInput").value.toLowerCase().trim();
            const listEl = document.getElementById("fileList");
            listEl.innerHTML = "";

            const filtered = allFiles.filter(f => !filter || f.name.toLowerCase().includes(filter));

            if (filtered.length === 0) {
                listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No matching thermal files found.</div>';
                return;
            }

            filtered.forEach(f => {
                const div = document.createElement("div");
                div.className = "file-item" + (currentFileObj && currentFileObj.source_path === f.path ? " active" : "");
                div.onclick = () => loadFile(f.path);

                const badgeClass = f.is_encrypted ? "badge-enc" : "badge-plain";
                const badgeText = f.is_encrypted ? "🔒 AES" : "📄 PLAIN";

                div.innerHTML = `
                    <div class="file-info">
                        <span class="file-name">${f.name}</span>
                        <span class="file-meta">${(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <span class="badge ${badgeClass}">${badgeText}</span>
                `;
                listEl.appendChild(div);
            });
        }

        async function loadFile(filePath) {
            try {
                const res = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`);
                const data = await res.json();
                currentFileObj = data.file;

                document.getElementById("currentFileName").innerText = data.file.name;
                const badge = document.getElementById("cryptoBadge");
                if (data.file.is_encrypted) {
                    badge.className = "badge badge-enc";
                    badge.innerText = "🔒 AES-128-CBC ENCRYPTED";
                    document.getElementById("encryptOnSave").checked = true;
                } else {
                    badge.className = "badge badge-plain";
                    badge.innerText = "📄 PLAINTEXT";
                    document.getElementById("encryptOnSave").checked = false;
                }

                document.getElementById("codeEditor").value = data.file.content;
                renderAnalysis(data.analysis);
                renderFileList();
            } catch (err) {
                showToast("Error loading file: " + err.message);
            }
        }

        function renderAnalysis(report) {
            if (!report) return;
            document.getElementById("statSections").innerText = report.total_sections || 0;
            document.getElementById("statSensors").innerText = (report.sensors || []).length;
            document.getElementById("statMinTemp").innerText = report.lowest_throttle_temp ? `${report.lowest_throttle_temp.toFixed(1)}°C` : "-";
            document.getElementById("statMaxTemp").innerText = report.highest_throttle_temp ? `${report.highest_throttle_temp.toFixed(1)}°C` : "-";

            let sconfigTag = "";
            if (report.matched_sconfig) {
                sconfigTag = ` - SCONFIG [${report.matched_sconfig.id}]: ${report.matched_sconfig.name}`;
            }
            document.getElementById("analyzerHeader").innerText = `📈 Thermal Profile: ${report.filename}${sconfigTag}`;

            // Sensors Table
            const sBody = document.getElementById("sensorsTableBody");
            sBody.innerHTML = "";
            (report.sensors || []).forEach(s => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${s.sensor_name}</strong></td>
                    <td>${s.is_virtual ? '<span style="color:var(--accent-purple)">Virtual Sensor</span>' : 'Physical'}</td>
                    <td>${s.min_trigger_temp !== null ? `${s.min_trigger_temp.toFixed(1)}°C` : '-'}</td>
                    <td>${s.max_trigger_temp !== null ? `${s.max_trigger_temp.toFixed(1)}°C` : '-'}</td>
                    <td style="color:var(--text-secondary)">${(s.used_in_sections || []).join(", ")}</td>
                `;
                sBody.appendChild(tr);
            });

            // Rules Table
            const rBody = document.getElementById("rulesTableBody");
            rBody.innerHTML = "";
            (report.devices || []).forEach(d => {
                (d.trip_points || []).forEach(rule => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong style="color:var(--accent-cyan)">${d.device_name}</strong></td>
                        <td>${rule.section}</td>
                        <td>${rule.trigger !== null ? `${rule.trigger.toFixed(1)}°C` : '-'}</td>
                        <td>${rule.clear !== null ? `${rule.clear.toFixed(1)}°C` : '-'}</td>
                        <td style="color:var(--accent-orange); font-family:var(--font-mono)">${rule.action || '-'}</td>
                    `;
                    rBody.appendChild(tr);
                });
            });
        }

        async function saveCurrentFile() {
            if (!currentFileObj) {
                showToast("No file selected.");
                return;
            }
            const content = document.getElementById("codeEditor").value;
            const encrypt = document.getElementById("encryptOnSave").checked;

            try {
                const res = await fetch("/api/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        path: currentFileObj.source_path,
                        content: content,
                        encrypt: encrypt,
                        create_backup: true
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Thermal config saved successfully!");
                    fetchFiles();
                } else {
                    showToast("Error saving: " + data.error);
                }
            } catch (err) {
                showToast("Save failed: " + err.message);
            }
        }

        function exportPlaintext() {
            if (!currentFileObj) return;
            const content = document.getElementById("codeEditor").value;
            const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `decrypted_${currentFileObj.name}`;
            a.click();
            URL.revokeObjectURL(url);
        }

        async function exportEncrypted() {
            if (!currentFileObj) return;
            const content = document.getElementById("codeEditor").value;
            const res = await fetch("/api/encrypt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: content })
            });
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `encrypted_${currentFileObj.name}`;
            a.click();
            URL.revokeObjectURL(url);
        }

        async function runDiff() {
            const targetPath = document.getElementById("diffTargetInput").value.trim();
            if (!targetPath) {
                showToast("Please enter a comparison file path.");
                return;
            }
            const content = document.getElementById("codeEditor").value;

            try {
                const res = await fetch("/api/diff", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        content_a: content,
                        name_a: currentFileObj ? currentFileObj.name : "Editor",
                        path_b: targetPath
                    })
                });
                const data = await res.json();
                document.getElementById("diffSummaryHeader").innerText = data.summary;

                const out = document.getElementById("diffOutput");
                out.innerHTML = "";
                (data.unified_lines || []).forEach(line => {
                    const div = document.createElement("div");
                    if (line.startsWith("+") && !line.startsWith("+++")) div.className = "diff-line-add";
                    else if (line.startsWith("-") && !line.startsWith("---")) div.className = "diff-line-del";
                    else if (line.startsWith("@@")) div.className = "diff-line-sec";
                    div.innerText = line;
                    out.appendChild(div);
                });
            } catch (err) {
                showToast("Diff failed: " + err.message);
            }
        }

        async function loadSconfigDb() {
            const res = await fetch("/api/sconfig");
            const data = await res.json();
            const tbody = document.getElementById("sconfigTableBody");
            tbody.innerHTML = "";

            Object.keys(data).forEach(id => {
                const item = data[id];
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong style="color:var(--accent-cyan)">${id}</strong></td>
                    <td><strong>${item.name}</strong></td>
                    <td style="font-family:var(--font-mono)">${item.file}</td>
                    <td><span class="pill">${item.category}</span></td>
                    <td style="color:var(--text-secondary)">${item.desc}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function openAdbModal() {
            openModal("adbModal");
            await loadAdbDevices();
        }

        async function loadAdbDevices() {
            const statusEl = document.getElementById("adbStatusText");
            const selectEl = document.getElementById("adbDeviceSelect");
            statusEl.innerText = "Scanning ADB devices...";
            selectEl.innerHTML = "";

            try {
                const res = await fetch("/api/adb/devices");
                const data = await res.json();
                if (!data.devices || data.devices.length === 0) {
                    statusEl.innerText = "No connected ADB devices detected.";
                    return;
                }

                statusEl.innerText = `Found ${data.devices.length} connected device(s).`;
                data.devices.forEach(d => {
                    const opt = document.createElement("option");
                    opt.value = d.serial;
                    opt.innerText = `${d.serial} - ${d.model || d.device} (${d.is_root ? "ROOT AVAILABLE" : "NO ROOT"})`;
                    selectEl.appendChild(opt);
                });
                onAdbDeviceChanged();
            } catch (err) {
                statusEl.innerText = "ADB Scan Error: " + err.message;
            }
        }

        async function onAdbDeviceChanged() {
            const selectEl = document.getElementById("adbDeviceSelect");
            const serial = selectEl.value;
            const filesDiv = document.getElementById("adbFilesList");
            filesDiv.innerHTML = '<div style="padding: 10px; color: var(--text-muted);">Scanning thermal files on device...</div>';

            try {
                const res = await fetch(`/api/adb/scan?serial=${encodeURIComponent(serial)}`);
                const data = await res.json();
                filesDiv.innerHTML = "";

                let foundCount = 0;
                Object.keys(data.files || {}).forEach(dir => {
                    data.files[dir].forEach(f => {
                        foundCount++;
                        const item = document.createElement("div");
                        item.style.padding = "6px 10px";
                        item.style.display = "flex";
                        item.style.justifyContent = "space-between";
                        item.style.alignItems = "center";
                        item.style.borderBottom = "1px solid var(--border-color)";

                        item.innerHTML = `
                            <span><strong>${dir}/</strong>${f}</span>
                            <button onclick="pullAdbFile('${serial}', '${dir}/${f}')">📥 Pull & Edit</button>
                        `;
                        filesDiv.appendChild(item);
                    });
                });
                if (foundCount === 0) {
                    filesDiv.innerHTML = '<div style="padding: 10px; color: var(--text-muted);">No thermal files found in /odm/etc, /vendor/etc, /system/etc.</div>';
                }
            } catch (err) {
                filesDiv.innerHTML = `<div style="padding: 10px; color: var(--accent-red);">Error: ${err.message}</div>`;
            }
        }

        async function pullAdbFile(serial, path) {
            try {
                const res = await fetch(`/api/adb/pull?serial=${encodeURIComponent(serial)}&path=${encodeURIComponent(path)}`);
                const data = await res.json();
                if (data.file) {
                    currentFileObj = data.file;
                    document.getElementById("currentFileName").innerText = data.file.name;
                    document.getElementById("codeEditor").value = data.file.content;
                    closeModal("adbModal");
                    showToast(`Pulled ${data.file.name} from device!`);
                    renderAnalysis(data.analysis);
                } else {
                    showToast("Pull failed: " + data.error);
                }
            } catch (err) {
                showToast("ADB Pull Error: " + err.message);
            }
        }

        async function injectToAdb() {
            if (!currentFileObj) {
                showToast("No file loaded to inject.");
                return;
            }
            if (!confirm(`Inject ${currentFileObj.name} directly to device?\nThis will create a .bak backup and overwrite with encrypted AES thermal config.`)) {
                return;
            }

            const content = document.getElementById("codeEditor").value;
            const res = await fetch("/api/adb/inject", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    path: currentFileObj.source_path.startsWith("/") ? currentFileObj.source_path : `/odm/etc/${currentFileObj.name}`,
                    content: content
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message);
            } else {
                showToast("Injection failed: " + data.error);
            }
        }

        async function executeBatchDecrypt(decryptAll = false) {
            const dst = document.getElementById("batchDecDst").value.trim();
            if (!dst) {
                showToast("Please provide a destination folder.");
                return;
            }

            let selFiles = [];
            if (decryptAll) {
                selFiles = allFiles.filter(f => f.is_encrypted).map(f => f.path);
            } else {
                const checkboxes = document.querySelectorAll('#decryptChecklist input[type="checkbox"]:checked');
                checkboxes.forEach(c => selFiles.push(c.value));
            }

            if (selFiles.length === 0) {
                showToast("No encrypted files selected to decrypt.");
                return;
            }

            const res = await fetch("/api/batch-decrypt-selected", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ files: selFiles, dst: dst })
            });
            const data = await res.json();
            closeModal("batchDecryptModal");
            if (data.success) {
                showToast(`Successfully decrypted ${data.count || 0} files into ${dst}`);
            } else {
                showToast(`Batch decryption failed: ${data.error}`);
            }
        }

        async function executeBatchEncrypt() {
            const src = document.getElementById("batchEncSrc").value.trim();
            const dst = document.getElementById("batchEncDst").value.trim();
            if (!src || !dst) {
                showToast("Please provide both source and destination folders.");
                return;
            }

            const res = await fetch("/api/batch-encrypt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ src: src, dst: dst })
            });
            const data = await res.json();
            closeModal("batchEncryptModal");
            showToast(`Batch Encrypted ${data.count || 0} files into ${dst}`);
        }

        // Initialize on load
        window.onload = () => {
            const defaultDir = "/serverhive/yukia/luna/vendor/xiaomi/peridot/proprietary/odm/etc";
            document.getElementById("srcDirInput").value = defaultDir;
            const batchEncSrcEl = document.getElementById("batchEncSrc");
            if (batchEncSrcEl) batchEncSrcEl.value = "/tmp/decrypted_thermal";
            fetchFiles();
            loadSconfigDb();
        };
    </script>
</body>
</html>
"""


class MiThermalWebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for REST API and Web GUI."""

    adb = ADBManager()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        if path == "/api/sconfig":
            self.send_json(XIAOMI_SCONFIG_DB)
            return

        if path == "/api/browse":
            b_type = query.get("type", ["file"])[0]
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                def open_dialog():
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    if b_type == "folder":
                        res = filedialog.askdirectory(title="Select Folder")
                    else:
                        res = filedialog.askopenfilename(title="Select Thermal Config", filetypes=[("Conf Files", "*.conf"), ("All Files", "*.*")])
                    root.destroy()
                    return res
                    
                selected_path = open_dialog()
            except Exception as e:
                selected_path = ""
                
            self.send_json({"path": selected_path})
            return

        if path == "/api/files":
            src_dir = query.get("dir", ["."])[0]
            recursive = query.get("recursive", ["false"])[0].lower() == "true"
            files_list = []
            
            def add_file(p):
                try:
                    with open(p, "rb") as fp:
                        header = fp.read(32)
                    is_enc = (len(header) > 0 and len(header) % 16 == 0 and b"[" not in header[:4])
                except Exception:
                    is_enc = False
                files_list.append({
                    "name": p.name,
                    "path": str(p),
                    "size": p.stat().st_size,
                    "is_encrypted": is_enc
                })

            if os.path.isfile(src_dir):
                add_file(Path(src_dir))
            elif os.path.isdir(src_dir):
                for p in scan_thermal_files(src_dir, recursive=recursive):
                    add_file(p)
            self.send_json({"files": files_list})
            return

        if path == "/api/file":
            file_path = query.get("path", [""])[0]
            if not os.path.isfile(file_path):
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                return

            t_file = load_thermal_file(file_path)
            report = analyze_thermal_config(t_file.content, filename=t_file.name)

            self.send_json({
                "file": {
                    "name": t_file.name,
                    "source_path": t_file.source_path,
                    "source_dir": t_file.source_dir,
                    "content": t_file.content,
                    "is_encrypted": t_file.is_encrypted,
                    "size": t_file.file_size
                },
                "analysis": {
                    "filename": report.filename,
                    "total_sections": report.total_sections,
                    "lowest_throttle_temp": report.lowest_throttle_temp,
                    "highest_throttle_temp": report.highest_throttle_temp,
                    "matched_sconfig": report.matched_sconfig,
                    "sensors": [
                        {
                            "sensor_name": s.sensor_name,
                            "is_virtual": s.is_virtual,
                            "min_trigger_temp": s.min_trigger_temp,
                            "max_trigger_temp": s.max_trigger_temp,
                            "used_in_sections": s.used_in_sections
                        } for s in report.sensors
                    ],
                    "devices": [
                        {
                            "device_name": d.device_name,
                            "trip_points": d.trip_points
                        } for d in report.devices
                    ]
                }
            })
            return

        if path == "/api/adb/devices":
            devs = self.adb.list_devices()
            self.send_json({"devices": [
                {
                    "serial": d.serial,
                    "state": d.state,
                    "model": d.model,
                    "device": d.device,
                    "is_root": d.is_root
                } for d in devs
            ]})
            return

        if path == "/api/adb/scan":
            serial = query.get("serial", [None])[0]
            files_map = self.adb.scan_device_thermal_files(serial=serial)
            self.send_json({"files": files_map})
            return

        if path == "/api/adb/pull":
            serial = query.get("serial", [None])[0]
            r_path = query.get("path", [""])[0]
            success, raw_data, err = self.adb.pull_thermal_file(r_path, serial=serial)
            if not success:
                self.send_json({"error": err}, status=HTTPStatus.BAD_REQUEST)
                return

            text_content, is_enc = decrypt_data(raw_data)
            fname = Path(r_path).name
            report = analyze_thermal_config(text_content, filename=fname)

            self.send_json({
                "file": {
                    "name": fname,
                    "source_path": r_path,
                    "source_dir": str(Path(r_path).parent),
                    "content": text_content,
                    "is_encrypted": is_enc,
                    "size": len(raw_data)
                },
                "analysis": {
                    "filename": fname,
                    "total_sections": report.total_sections,
                    "lowest_throttle_temp": report.lowest_throttle_temp,
                    "highest_throttle_temp": report.highest_throttle_temp,
                    "matched_sconfig": report.matched_sconfig,
                    "sensors": [
                        {
                            "sensor_name": s.sensor_name,
                            "is_virtual": s.is_virtual,
                            "min_trigger_temp": s.min_trigger_temp,
                            "max_trigger_temp": s.max_trigger_temp,
                            "used_in_sections": s.used_in_sections
                        } for s in report.sensors
                    ],
                    "devices": [
                        {
                            "device_name": d.device_name,
                            "trip_points": d.trip_points
                        } for d in report.devices
                    ]
                }
            })
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path == "/api/save":
            target_path = payload.get("path")
            if not target_path:
                self.send_json({"success": False, "error": "Missing file path"}, status=HTTPStatus.BAD_REQUEST)
                return
            content = payload.get("content", "")
            encrypt = payload.get("encrypt", True)
            create_backup = payload.get("create_backup", True)

            try:
                saved_p, bck_p = save_thermal_file(str(target_path), content, encrypt=encrypt, create_backup=create_backup)
                self.send_json({"success": True, "path": saved_p, "backup": bck_p})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/encrypt":
            content = payload.get("content", "")
            enc_bytes = encrypt_data(content)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(enc_bytes)))
            self.end_headers()
            self.wfile.write(enc_bytes)
            return

        if path == "/api/diff":
            content_a = payload.get("content_a", "")
            name_a = payload.get("name_a", "File A")
            path_b = payload.get("path_b", "")

            if os.path.isfile(path_b):
                obj_b = load_thermal_file(path_b)
                content_b = obj_b.content
                name_b = obj_b.name
            else:
                content_b = payload.get("content_b", "")
                name_b = payload.get("name_b", "File B")

            diff_res = compute_thermal_diff(content_a, content_b, name_a=name_a, name_b=name_b)
            self.send_json({
                "summary": diff_res.summary,
                "unified_lines": diff_res.unified_diff_lines,
                "added_sections": diff_res.added_sections,
                "removed_sections": diff_res.removed_sections
            })
            return

        if path == "/api/batch-decrypt":
            src = payload.get("src")
            dst = payload.get("dst")
            if not src or not dst:
                self.send_json({"success": False, "error": "Missing src or dst directory"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                results = batch_decrypt_directory(str(src), str(dst))
                self.send_json({"success": True, "count": len(results)})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/batch-decrypt-selected":
            files = payload.get("files", [])
            dst = payload.get("dst")
            if not files or not dst:
                self.send_json({"success": False, "error": "Missing files or dst directory"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                dst_path = Path(dst)
                count = 0
                for fpath_str in files:
                    fpath = Path(fpath_str)
                    if not fpath.exists(): continue
                    try:
                        t_obj = load_thermal_file(fpath)
                        out_file = dst_path / fpath.name
                        out_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(out_file, "w", encoding="utf-8") as out_fp:
                            out_fp.write(t_obj.content)
                        count += 1
                    except Exception as e:
                        print(f"Error decrypting {fpath}: {e}")
                self.send_json({"success": True, "count": count})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/batch-encrypt":
            src = payload.get("src")
            dst = payload.get("dst")
            if not src or not dst:
                self.send_json({"success": False, "error": "Missing src or dst directory"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                results = batch_encrypt_directory(str(src), str(dst))
                self.send_json({"success": True, "count": len(results)})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/adb/inject":
            remote_path = payload.get("path")
            if not remote_path:
                self.send_json({"success": False, "error": "Missing target path on device"}, status=HTTPStatus.BAD_REQUEST)
                return
            content = payload.get("content", "")
            serial = payload.get("serial")
            enc_bytes = encrypt_data(content)
            success, msg = self.adb.inject_thermal_file(str(remote_path), enc_bytes, serial=serial)
            self.send_json({"success": success, "message": msg, "error": msg if not success else ""})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def send_json(self, data: Any, status: int = HTTPStatus.OK):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Quiet standard HTTP access logs
        return


def start_web_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    """Starts the standalone Web GUI HTTP server."""
    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, MiThermalWebHandler)
    except OSError:
        # Try fallback port if port is busy
        port = port + 1
        server_address = (host, port)
        httpd = ThreadingHTTPServer(server_address, MiThermalWebHandler)

    url = f"http://{host}:{port}"
    print(f"\n=======================================================")
    print(f"🔥 Mi Thermal Editor (Linux Web GUI) is running at:")
    print(f"   --> {url}")
    print(f"=======================================================\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mi Thermal Editor Web Server...")
        httpd.server_close()
