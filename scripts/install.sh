#!/usr/bin/env bash
set -e

echo -e "\033[1;36m🔥 Installing Mi Thermal Editor...\033[0m"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m[ERROR] python3 is not installed or not in PATH.\033[0m"
    exit 1
fi

# 2. Check Git
if ! command -v git &> /dev/null; then
    echo -e "\033[1;31m[ERROR] git is not installed or not in PATH.\033[0m"
    exit 1
fi

INSTALL_DIR="$HOME/mi-thermal-tools"

# 3. Clone / Update Repository
if [ -d "$INSTALL_DIR" ]; then
    echo -e "\033[1;33m[INFO] Repository already exists at $INSTALL_DIR. Pulling latest...\033[0m"
    cd "$INSTALL_DIR"
    git pull
else
    echo -e "\033[1;33m[INFO] Cloning repository to $INSTALL_DIR...\033[0m"
    git clone https://github.com/Inventor365/mi-thermal-tools.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 4. Install Dependencies
echo -e "\033[1;33m[INFO] Checking and installing Python dependencies...\033[0m"
python3 -m pip install --upgrade pip
python3 -m pip install cryptography PySide6
python3 -m pip install -e .

# 5. Create Desktop Shortcut
echo -e "\033[1;33m[INFO] Creating Desktop Shortcut...\033[0m"
if [ "$(uname)" == "Darwin" ]; then
    # macOS Shortcut (AppleScript payload)
    DESKTOP_PATH="$HOME/Desktop/Mi Thermal Editor.app"
    mkdir -p "$DESKTOP_PATH/Contents/MacOS"
    cat <<EOF > "$DESKTOP_PATH/Contents/MacOS/app"
#!/bin/bash
cd "$INSTALL_DIR"
python3 -m mi_thermal_editor gui
EOF
    chmod +x "$DESKTOP_PATH/Contents/MacOS/app"
    echo -e "\033[1;32m✅ Installation Complete! Launch 'Mi Thermal Editor' from your Desktop.\033[0m"
else
    # Linux Desktop Entry
    DESKTOP_DIR="$HOME/Desktop"
    if [ ! -d "$DESKTOP_DIR" ]; then
        # Fallback to standard xdg
        DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
    fi
    mkdir -p "$DESKTOP_DIR"
    
    cat <<EOF > "$DESKTOP_DIR/MiThermalEditor.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Mi Thermal Editor
Comment=Xiaomi Thermal Decryptor & Analyzer
Exec=bash -c "cd '$INSTALL_DIR' && python3 -m mi_thermal_editor gui"
Icon=utilities-terminal
Terminal=false
Categories=Development;Engineering;
EOF
    chmod +x "$DESKTOP_DIR/MiThermalEditor.desktop" || true
    # Also drop in applications folder to bind it to system launcher
    mkdir -p "$HOME/.local/share/applications"
    cp "$DESKTOP_DIR/MiThermalEditor.desktop" "$HOME/.local/share/applications/"
    
    echo -e "\033[1;32m✅ Installation Complete! Launch 'Mi Thermal Editor' from your Desktop or App Launcher.\033[0m"
fi
