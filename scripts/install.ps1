# Mi Thermal Editor Windows Automated Installer

Write-Host "🔥 Installing Mi Thermal Editor..." -ForegroundColor Cyan

# 1. Check Python
$python_exe = "python"
if (-Not (Get-Command $python_exe -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.8+ (ensure 'Add to PATH' is checked) and run this again." -ForegroundColor Yellow
    Exit 1
}

# 2. Check Git (optional for zip flow, but requested)
if (-Not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Git is not installed or not in PATH." -ForegroundColor Red
    Exit 1
}

$InstallDir = "$env:USERPROFILE\mi-thermal-tools"

# 3. Clone / Update Repository
if (Test-Path $InstallDir) {
    Write-Host "[INFO] Repository already exists at $InstallDir. Pulling latest..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull
} else {
    Write-Host "[INFO] Cloning repository to $InstallDir..." -ForegroundColor Yellow
    git clone https://github.com/Inventor365/mi-thermal-tools.git $InstallDir
    Set-Location $InstallDir
}

# 4. Install Dependencies
Write-Host "[INFO] Checking and installing dependencies (cryptography, PySide6)..." -ForegroundColor Yellow
& $python_exe -m pip install setuptools wheel
& $python_exe -m pip install cryptography PySide6
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
    Exit 1
}
& $python_exe -m pip install -e .

# 5. Create Desktop Shortcut
Write-Host "[INFO] Creating Desktop Shortcut..." -ForegroundColor Yellow
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Mi Thermal Editor.lnk")
$Shortcut.TargetPath = "$InstallDir\mi-thermal-editor.bat"
$Shortcut.Arguments = "gui"
$Shortcut.WorkingDirectory = "$InstallDir"
$Shortcut.Save()

Write-Host "✅ Installation Complete! You can now launch 'Mi Thermal Editor' from your Desktop." -ForegroundColor Green
