@echo off
setlocal enabledelayedexpansion

:: Mi Thermal Editor Windows Wrapper
:: Auto-detects Python, checks dependencies, and launches the CLI/GUI

echo [INFO] Starting Mi Thermal Editor...

:: 1. Check Python installation
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Check dependencies
python -c "import cryptography; import PySide6" >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Missing required packages. Installing now...
    pip install cryptography PySide6
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies. Please run 'pip install cryptography PySide6' manually.
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully.
)

:: 3. Launch the Python module
if "%~1"=="" (
    :: No args provided, launch GUI by default
    python -m mi_thermal_editor gui
) else (
    :: Pass arguments to CLI
    python -m mi_thermal_editor %*
)
