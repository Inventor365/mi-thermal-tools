# ðŸ”¥ Mi Thermal Editor (Cross-Platform Edition)

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blueviolet.svg)]()
[![Target: Xiaomi Peridot (SM8635)](https://img.shields.io/badge/Target-Xiaomi%20Peridot%20(SM8635)-green.svg)]()
[![Cipher: AES--128--CBC](https://img.shields.io/badge/Cipher-AES--128--CBC-red.svg)]()

> A Standalone Windows / Linux GUI and CLI tool suite to **decrypt**, **analyze**, **edit**, **diff**, and **inject** Xiaomi / MIUI / HyperOS thermal configuration files across `/odm/etc`, `/vendor/etc`, and `/system/etc`.
>
> **Note:** The specific thermal profiles, sconfig values, and engineering data documented in this repository are based on deep-dive reverse-engineering of **Xiaomi Peridot (POCO F6 / Redmi Turbo 3 - Qualcomm Snapdragon 8s Gen 3 / SM8635)**.

---

## ðŸ“– Table of Contents

- [Overview](#overview)
- [How Xiaomi Thermal Encryption Works](#how-xiaomi-thermal-encryption-works)
- [Xiaomi Peridot (SM8635) Thermal Architecture & Mapping](#xiaomi-peridot-sm8635-thermal-architecture--mapping)
  - [SCONFIG Mapping Matrix & ODM Presence Breakdown](#sconfig-mapping-matrix--odm-presence-breakdown)
  - [India Regional Variant (thermal-region-map.conf)](#india-regional-variant-thermal-region-mapconf)
- [Features](#features)
- [Installation & Requirements](#installation--requirements)
- [Graphical User Interface (GUI)](#graphical-user-interface-gui)
  - [1. Native Desktop GUI (Tkinter)](#1-native-desktop-gui-tkinter)
  - [2. Embedded Web GUI (Local / Remote / Headless)](#2-embedded-web-gui-local--remote--headless)
- [Command-Line Interface (CLI) Guide](#command-line-interface-cli-guide)
- [Deep-Dive Thermal Configuration Anatomy](#deep-dive-thermal-configuration-anatomy)
- [Step-by-Step Customization Guide](#step-by-step-customization-guide)
- [Project Architecture](#project-architecture)
- [Credits & Acknowledgments](#credits--acknowledgments)

---

## ðŸŽ¯ Overview

On Xiaomi, Redmi, and POCO devices running MIUI or HyperOS, thermal throttling policies (controlling CPU frequency caps, GPU throttling, charging current stepdowns, brightness dimming, and modem fallback) are defined in configuration files located in:
- `/odm/etc/thermal*.conf`
- `/vendor/etc/thermal*.conf`
- `/system/etc/thermal*.conf`

By default, Xiaomi encrypts these files using proprietary AES-128-CBC encryption to prevent users and kernel developers from modifying thermal throttling curves.

**Mi Thermal Editor (Cross-Platform Edition)** is a Linux desktop application, web application, and command-line suite that reproduces the thermal decryption, editing, analysis, and injection capabilities found in the **Tools > Mi Thermal Editor** module of the **Pandemonium Kernel Manager (PKM)** Android app.

---

## ðŸ” How Xiaomi Thermal Encryption Works

### 1. Cryptographic Specifications

Through reverse-engineering of `mi_thermald` and the Pandemonium Kernel Manager APK (`app-arm64-v8a-release-20260222-2007.apk`):

| Parameter | Specification | Details |
|---|---|---|
| **Algorithm** | `AES-128-CBC` | Advanced Encryption Standard in Cipher Block Chaining mode |
| **Padding** | `PKCS#7` (`PKCS#5`) | Standard 16-byte block padding |
| **Secret Key** | `b"thermalopenssl.h"` | 16-byte ASCII / UTF-8 string (128-bit key) |
| **Initialization Vector (IV)** | `b"thermalopenssl.h"` | 16-byte ASCII / UTF-8 string (128-bit IV) |

### 2. Encryption Detection Heuristic

Not all files matching `thermal*.conf` are encrypted (some ROMs or files like `thermal-chg-only.conf` may be stored in plaintext).

The decryption engine checks:
1. If the input data is a multiple of 16 bytes and non-empty.
2. Performs AES-128-CBC decryption with key/IV `thermalopenssl.h` and removes PKCS#7 padding.
3. Tests decrypted string with `isPrintableText`: verifies that non-standard ISO control characters (excluding `\n`, `\r`, `\t`) account for fewer than `(len(text) // 50 + 2)` characters.
4. If decryption succeeds and the output passes validation, the file is loaded as decrypted plaintext; otherwise, it is treated as already unencrypted text.

### 3. Built-In Plaintext Bypass Flag

In `mi_thermald` on Xiaomi devices:
```c
if (access("/vendor/etc/thermal-decrypt", F_OK) == 0) {
    // Plaintext bypass active: loads .conf files directly without AES decryption
}
```
Placing an empty file named `thermal-decrypt` in `/vendor/etc/` instructs the `mi_thermald` daemon to bypass AES decryption completely, allowing plaintext `.conf` files to be loaded directly on custom ROMs.

---

## ðŸ“± Xiaomi Peridot (SM8635) Thermal Architecture & Mapping

> **Target Device Focus**: This section contains the exact reverse-engineered profiles for **Xiaomi Peridot** (POCO F6 / Redmi Turbo 3 - Qualcomm Snapdragon 8s Gen 3 / SM8635).

### SCONFIG Mapping Matrix & ODM Presence Breakdown

Xiaomi's `/vendor/etc/thermal-map.conf` contains master lookup entries for all potential form-factors (candybar, foldables `-unfold`, wireless charging `-w`, and lab certification `-iec-`). 

Because **Peridot** is a single-screen phone with wired fast charging (90W) and no foldable display, only the active device-specific profiles are present in `/odm/etc/`. The table below aligns the master `sconfig` values with their presence on Peridot:

| SCONFIG ID | Target Thermal Config File | Present on Peridot `/odm/etc`? | Category | Profile Purpose & Throttling Characteristics |
|:---|:---|:---:|:---|:---|
| **0** | `thermal-normal.conf` | **âœ… Yes** | Daily | **Default Balanced Profile**: CPU3/7 throttle starts at 37Â°C; battery charging stepdown from 15.6A to 0.3A. |
| **1** | `thermal-huanji.conf` | **âœ… Yes** | System | **Data Migration (Mi Mover)**: Disables modem/Wi-Fi throttling for high-speed file transfer. |
| **2** | `thermal-abnormal.conf` | âŒ Template | Recovery | Emergency thermal recovery mode for rapid heat dissipation. |
| **3** | `thermal-nightvideo.conf` | âŒ Template | Camera | Night mode video capture with computational ISP noise reduction. |
| **4** | `thermal-dolbyvision.conf` | âŒ Template | Media | Dolby Vision HDR video playback thermal tuning. |
| **5** | `thermal-phone.conf` | **âœ… Yes** | Daily | **Telephony / In-Call**: Lowers receiver ear-piece surface temperature during voice calls. |
| **6** | `thermal-nolimits.conf` | **âœ… Yes** | Performance | **Benchmark / Unconstrained**: GPU throttle trigger raised to 51Â°C; uncapped CPU clocks for AnTuTu/Geekbench. |
| **7** | `thermal-class0.conf` | **âœ… Yes** | Gaming | **Heavy 3D Gaming Class 0**: Mild power saving during background 3D tasks. |
| **8** | `thermal-youtube.conf` | âŒ Template | Media | YouTube and web streaming video playback profile. |
| **9** | `thermal-arvr.conf` | **âœ… Yes** | Graphics | **AR / VR Rendering**: Augmented reality rendering thermal profile. |
| **10** | `thermal-navigation.conf` | **âœ… Yes** | Navigation | **GPS Navigation**: Prevents brightness dimming and modem disconnects under direct sunlight in-car. |
| **11** | `thermal-video.conf` | **âœ… Yes** | Camera | **Standard 1080P/4K Video Recording**: Limits CPU spikes to prevent camera ISP overheating. |
| **12** | `thermal-demo.conf` | âŒ Template | System | Store demo unit display mode. |
| **13** | `thermal-sptm.conf` | âŒ Template | Testing | Factory QA / Special Performance Test Mode. |
| **14** | `thermal-videochat.conf` | **âœ… Yes** | Media | **Video Calling**: Tuned for WhatsApp/Teams/Zoom; manages camera ISP, modem, and CPU heat concurrently. |
| **15** | `thermal-camera.conf` | **âœ… Yes** | Camera | **Camera Viewfinder & Photo Capture**: Strictly manages sensor thermals. |
| **16** | `thermal-4k.conf` | **âœ… Yes** | Camera | **4K 60FPS Video Recording (Slot 1)**: Sustained 4K video recording policy. |
| **17** | `thermal-4k.conf` | **âœ… Yes** | Camera | **4K 60FPS Video Recording (Slot 2)**: Secondary slot mapping. |
| **18** | `thermal-tgame.conf` | **âœ… Yes** | Gaming | **Esports / MOBA Gaming**: Tuned for Honor of Kings, MLBB, Wild Rift. |
| **19** | `thermal-mgame.conf` | **âœ… Yes** | Gaming | **Heavy 3D Gaming (MGame)**: PUBG Mobile, BGMI, CoD Mobile; maintains sustained GPU clock ceiling. |
| **20** | `thermal-yuanshen.conf` | **âœ… Yes** | Gaming | **Extreme Gaming (Genshin Impact)**: High 60FPS priority; raises throttle trigger to 48Â°C. |
| **25** | `thermal-xingtie.conf` | âŒ Template | Gaming | Honkai Star Rail heavy turn-based 3D gaming. |
| **26** | `thermal-highfps.conf` | **âœ… Yes** | Gaming | **High Refresh Rate Gaming (90/120Hz)**: 90/120 FPS high-refresh competitive gaming profile. |
| **27** | `thermal-charge.conf` | âŒ Template | Charging | Fast charging thermal management. |
| **28** | `thermal-extravideo.conf` | âŒ Template | Camera | High-bitrate extended video recording. |
| **50** | `thermal-per-normal.conf` | **âœ… Yes** | Performance | **HyperOS Performance Mode**: Triggered via Control Center toggle. CPU throttle trigger shifted from 37Â°C to 45Â°C. |
| **52** | `thermal-per-abnormal.conf` | âŒ Template | Recovery | Performance mode abnormal recovery. |
| **57** | `thermal-per-class0.conf` | **âœ… Yes** | Gaming | **Performance Mode Heavy Gaming**: Raised thermal trip thresholds for games. |
| **58** | `thermal-per-youtube.conf`| âŒ Template | Media | Performance mode streaming video. |
| **60** | `thermal-per-navigation.conf`| âŒ Template | Navigation | Performance mode GPS navigation. |
| **61** | `thermal-per-video.conf` | **âœ… Yes** | Camera | **Performance Mode Video Capture**: Sustained high-resolution video recording. |
| **76** | `thermal-highfps.conf` | **âœ… Yes** | Gaming | Performance mode 90/120Hz gaming slot. |
| **77** | `thermal-charge.conf` | âŒ Template | Charging | Performance mode fast charge. |
| **78** | `thermal-extravideo.conf` | âŒ Template | Camera | Performance mode extra video. |
| **100-161** | `thermal-*-unfold.conf` | âŒ Template | Foldable | Foldable form-factor template profiles (MIX Fold series). |
| **200-361** | `thermal-iec-*.conf` | âŒ Template | Testing | IEC lab certification testing profiles. |
| **500** | `thermal-hp-normal.conf` | **âœ… Yes** | Performance | **High Power Normal (HP-Normal)**: Raised thermal trip points for heavy multitasking. |
| **501** | `thermal-hp-mgame.conf` | **âœ… Yes** | Gaming | **High Power Gaming (HP-MGame)**: Raised gaming thermal threshold. |
| **700** | `thermal-cgame.conf` | **âœ… Yes** | Gaming | **Concurrent Gaming (CGame)**: Concurrent gaming and background task management. |
| **701** | `thermal-cclassvideo.conf` | **âœ… Yes** | Media | **Concurrent Video**: Video capture during active background data operations. |
| **704-707** | `thermal-w*.conf` | âŒ Template | Wireless | Wireless charging thermal profiles (Peridot uses 90W wired only). |
| **N/A** | `thermal-boost.conf` | **âœ… Yes** | Performance | **Superfast 90W Charging & Uncapped Boost**: Unlocks full 16A fast charging. |
| **N/A** | `thermal-chg-only.conf` | **âœ… Yes** | Charging | **Screen-Off Fast Charge**: Plaintext profile used when booted in off-mode charging. |

---

### India Regional Variant (`thermal-region-map.conf`)

For the Indian SKU (`8.21.0`), `/odm/etc/thermal-region-map.conf` routes `mi_thermald` to use `/odm/etc/thermal-map-india.conf`, which references the regional Indian profile set:

```ini
8.21.0:thermal-map-india.conf
```

The India-specific configuration files (`thermal-india-*.conf`) are tuned for higher ambient temperatures:
- `thermal-india-normal.conf` (SCONFIG 0)
- `thermal-india-huanji.conf` (SCONFIG 1)
- `thermal-india-phone.conf` (SCONFIG 5)
- `thermal-india-nolimits.conf` (SCONFIG 6)
- `thermal-india-class0.conf` (SCONFIG 7)
- `thermal-india-arvr.conf` (SCONFIG 9)
- `thermal-india-navigation.conf` (SCONFIG 10)
- `thermal-india-video.conf` (SCONFIG 11)
- `thermal-india-videochat.conf` (SCONFIG 14)
- `thermal-india-camera.conf` (SCONFIG 15)
- `thermal-india-4k.conf` (SCONFIG 16 & 17)
- `thermal-india-tgame.conf` (SCONFIG 18)
- `thermal-india-mgame.conf` (SCONFIG 19)
- `thermal-india-yuanshen.conf` (SCONFIG 20)
- `thermal-india-highfps.conf` (SCONFIG 26 / 76)
- `thermal-india-per-normal.conf` (SCONFIG 50)
- `thermal-india-per-class0.conf` (SCONFIG 57)
- `thermal-india-per-video.conf` (SCONFIG 61)
- `thermal-india-hp-normal.conf` (SCONFIG 500)
- `thermal-india-hp-mgame.conf` (SCONFIG 501)
- `thermal-india-cgame.conf` (SCONFIG 700)
- `thermal-india-cclassvideo.conf` (SCONFIG 701)

---

## âš¡ Features

- **Dual Graphical User Interface**:
  - **Native Desktop GUI**: Dark Material design, syntax highlighting, diff viewer, visual threshold tables, and ADB sync.
  - **Embedded Web GUI**: Runs on local web server with zero external dependencies; ideal for SSH port forwarding, remote Linux servers, or containers.
- **One-Click Decrypt & Encrypt**: Decrypt proprietary Xiaomi thermal binaries to readable `.conf` / `.json` or re-encrypt for flashing/injection.
- **Thermal Policy & Mitigation Analyzer**:
  - Automatically identifies virtual and physical thermal sensors.
  - Decodes CPU/GPU frequency stepdowns at each trigger temperature (Â°C).
  - Inspects battery charging rate stepdowns (`thermal_fcc_override`).
  - Matches profiles against the Xiaomi SCONFIG database.
- **Semantic & Line Diff Viewer**: Compare stock vs modified thermal configs, or compare balanced vs gaming profiles side-by-side.
- **Batch Processing**: Decrypt or encrypt entire directories of extracted ROM partitions in seconds.
- **ADB Root Device Bridge**: Pull thermal configs directly from connected USB devices, or inject modified configs with automated root remount, `.bak` backups, and SELinux context restoration.

---

## ðŸ’» Installation & Requirements

### Requirements
- **OS**: Linux (Ubuntu, Debian, Fedora, Arch, etc.)
- **Python**: Version 3.8 or newer
- **Dependencies**: `cryptography`
- *(Optional)*: `adb` (Android Debug Bridge for USB device communication)

### Quick Setup (Windows)

1. **Install Python**: Download [Python 3.8+](https://www.python.org/downloads/windows/) and ensure **"Add Python to PATH"** is checked during installation.
2. Clone the repository or download the ZIP:
``cmd
git clone https://github.com/Inventor365/mi-thermal-tools.git
cd mi-thermal-tools
``
3. Run the tool. The included batch script (mi-thermal-editor.bat) automatically detects missing dependencies and installs them:
``cmd
mi-thermal-editor.bat gui
``

### Quick Setup (Linux)

``bash
# Clone the repository
git clone https://github.com/Inventor365/mi-thermal-tools.git
cd mi-thermal-tools

# Install dependencies
pip3 install cryptography

# Run the GUI
./mi-thermal-editor gui
``
# (Optional) Install as local package
pip3 install -e .
```

---

## ðŸ–¥ï¸ Graphical User Interface (GUI)

### 1. Native Desktop GUI (Tkinter)

Launch the native desktop interface:
```bash
./mi-thermal-editor gui
# or specify a starting directory:
./mi-thermal-editor gui -d /path/to/extracted/odm/etc
```

Features included in the Desktop GUI:
- **File Explorer Sidebar**: One-click presets for `/odm/etc`, `/vendor/etc`, `/system/etc`, live search filter, and encryption status badges (`ðŸ”’ Encrypted` / `ðŸ“„ Plaintext`).
- **Code Editor**: Real-time syntax highlighting for thermal configuration syntax, undo/redo, and save options.
- **Visual Analyzer Tab**: Tabulated sensor threshold curves and device throttling action lists.
- **Diff & Compare Tab**: Visual side-by-side section and unified line diff.
- **ADB Sync Dialog**: Discover connected devices, check root access, and pull files directly.

### 2. Embedded Web GUI (Local / Remote / Headless)

If you are working over SSH or in a headless environment without an active `$DISPLAY`:
```bash
./mi-thermal-editor web --port 8080
```
Open `http://localhost:8080` in your web browser.

---

## âŒ¨ï¸ Command-Line Interface (CLI) Guide

### 1. Decrypt a Thermal File
```bash
# Decrypt encrypted binary to plaintext .conf
./mi-thermal-editor decrypt /odm/etc/thermal-normal.conf -o ./decrypted-normal.conf
```

### 2. Encrypt a Thermal File
```bash
# Encrypt modified plaintext .conf to Xiaomi AES-128-CBC binary
./mi-thermal-editor encrypt ./modified-normal.conf -o /odm/etc/thermal-normal.conf
```

### 3. Batch Decrypt an Entire Directory (e.g., Extracted ROM Dump)
```bash
./mi-thermal-editor batch-decrypt /path/to/rom/odm/etc -o ./decrypted_odm_thermal/
```

### 4. Batch Encrypt an Entire Directory
```bash
./mi-thermal-editor batch-encrypt ./modified_configs/ -o ./encrypted_configs/
```

### 5. Analyze Thermal Policies & Trip Points
```bash
./mi-thermal-editor analyze /odm/etc/thermal-mgame.conf
```
*Output preview on Xiaomi Peridot:*
```text
======================================================================
ðŸ”¥ THERMAL CONFIGURATION ANALYSIS: thermal-mgame.conf
======================================================================
Encryption Status : ðŸ”’ AES-128-CBC Encrypted
Total Sections    : 14
Algorithm Types   : ss (4), sic (1), monitor (9)
Temperature Range : 1.0Â°C to 65.0Â°C

[Xiaomi SCONFIG Profile]
  ID       : 19
  Name     : Heavy 3D Gaming (MGame) (Gaming)
  Use Case : Optimized for heavy 3D titles (PUBG, BGMI, Call of Duty Mobile). Maintains high GPU clocks.

[Device Throttling Mitigations]
  Device             | Section                | Trig     | Clr      | Mitigation Action
  ---------------------------------------------------------------------------
  cpu0               | MGAME-SS-CPU0          | 46.0Â°C   | 44.0Â°C   | 902400
  cpu0               | MGAME-SS-CPU0          | 48.0Â°C   | 46.0Â°C   | 787200
  cpu3               | MGAME-SS-CPU3          | 46.0Â°C   | 45.0Â°C   | 1056000
  cpu3               | MGAME-SS-CPU3          | 48.0Â°C   | 46.0Â°C   | 787200
  cpu7               | MGAME-SS-CPU7          | 46.0Â°C   | 45.0Â°C   | 1094400
  cpu7               | MGAME-SS-CPU7          | 48.0Â°C   | 46.0Â°C   | 787200
  thermal_fcc_override | MGAME-SIC-BAT        | 32.0Â°C   | 31.0Â°C   | 32000
  thermal_fcc_override | MGAME-SIC-BAT        | 36.0Â°C   | 34.0Â°C   | 36000
  thermal_fcc_override | MGAME-SIC-BAT        | 42.5Â°C   | 42.0Â°C   | 43500
```

### 6. Compare Two Thermal Files (Diff)
```bash
./mi-thermal-editor diff thermal-normal.conf thermal-mgame.conf --unified
```

### 7. View SCONFIG Knowledge Base
```bash
./mi-thermal-editor sconfig-list
```

### 8. ADB Device Commands
```bash
# Scan thermal files on connected device
./mi-thermal-editor adb-scan

# Pull and auto-decrypt a file from device
./mi-thermal-editor adb-pull /odm/etc/thermal-normal.conf -o ./stock-normal.conf

# Inject modified file to device with root
./mi-thermal-editor adb-inject /odm/etc/thermal-normal.conf ./tuned-normal.conf
```

---

## ðŸ› ï¸ Deep-Dive Thermal Configuration Anatomy

Xiaomi thermal configurations use the Qualcomm / Xiaomi `thermal-engine` format with specialized algorithm blocks:

### 1. Virtual Sensor Matrix (`algo_type Virtual`)
Combines readings from 7 physical thermistors across the PCB using a weighted formula to calculate the composite skin temperature:
```ini
[VIRTUAL-SENSOR0]
algo_type       Virtual
sensors         cpu_therm   battery   charger_therm0   wifi_therm   pa_therm0   pa_therm1   quiet_therm
weight          -26         301       147              330          36          119         -2
polling         2000
weight_sum      1000
compensation    2015
```

### 2. Step-Wise Throttling (`algo_type ss`)
Controls frequency ceilings on CPU clusters (Little: `cpu0`, Gold: `cpu3`, Prime Cortex-X4: `cpu7`) with hysteresis:
```ini
[SS-CPU3]
algo_type       ss
sensor          VIRTUAL-SENSOR0
device          cpu3
polling         2000
trig            25000    37000    39000    41000    43000    44000    45000    46000    47000    48000
clr             23000    35000    37000    39000    41000    43000    44000    45000    46000    47000
target          2572800  2188800  1920000  1593600  1401600  1401600  1056000  940800   787200   633600
```

### 3. Closed-Loop Fast Charge Current (`algo_type sic`)
Controls `thermal_fcc_override` (Fast Charge Current) in mA with PID coefficients:
```ini
[SIC-BAT]
algo_type       sic
sensor          VIRTUAL-SENSOR0
device          thermal_fcc_override
polling         2000
proportion      0
trig            15000    35000    35200    38500    41300    44500    45000    46000
clr             14000    34000    34500    37700    39000    44000    44500    45500
target          0        35000    37200    39500    43500    44500    45000    46000
ks              0        0        6500000  6300000  6000000  6000000  6000000  6000000
ki              0        0        100000   100000   100000   100000   100000   100000
max             15600    15600    13500    8000     4500     1000     500      300
min             15600    15600    4600     4500     2500     1000     500      300
```

---

## ðŸ“ Step-by-Step Customization Guide

### Example: Relaxing CPU Throttling for Sustained Performance

1. **Extract or Pull the Thermal Config**:
   ```bash
   ./mi-thermal-editor decrypt /odm/etc/thermal-normal.conf -o ./my-thermal.conf
   ```

2. **Open in the Editor or GUI**:
   ```bash
   ./mi-thermal-editor gui
   ```

3. **Locate Throttling Trip Points**:
   In `my-thermal.conf`, locate the CPU cluster throttling rules (e.g. `[SS-CPU3]` or `[SS-CPU7]`):
   ```ini
   [SS-CPU3]
   # Raise trigger point from 37.0Â°C to 45.0Â°C (like Performance Mode)
   trig   25000  45000  47000  49000  51000
   clr    23000  43000  45000  47000  49000
   ```

4. **Adjust Charging Limits**:
   In `[SIC-BAT]`, raise the charging current limits under moderate load.

5. **Re-Encrypt or Inject**:
   ```bash
   # Option A: Save encrypted for Magisk/KernelSU module
   ./mi-thermal-editor encrypt ./my-thermal.conf -o ./thermal-normal.conf

   # Option B: Inject directly to rooted device
   ./mi-thermal-editor adb-inject /odm/etc/thermal-normal.conf ./my-thermal.conf
   ```

---

## ðŸ“‚ Project Architecture

```
mi-thermal-editor/
â”œâ”€â”€ mi-thermal-editor             # Executable CLI/GUI launcher
â”œâ”€â”€ setup.py                      # Package installation script
â”œâ”€â”€ pyproject.toml                # Project configuration metadata
â”œâ”€â”€ LICENSE                       # MIT License
â”œâ”€â”€ README.md                     # Documentation and guide
â”œâ”€â”€ GUIDE.md                      # Developer architecture guide
â”œâ”€â”€ mi_thermal_editor/
â”‚   â”œâ”€â”€ __init__.py               # Package exports
â”‚   â”œâ”€â”€ crypto.py                 # AES-128-CBC engine & validation heuristics
â”‚   â”œâ”€â”€ parser.py                 # .conf and .json AST parser
â”‚   â”œâ”€â”€ analyzer.py               # Thermal curves & threshold analyzer
â”‚   â”œâ”€â”€ diff_engine.py            # Section-aware diff engine
â”‚   â”œâ”€â”€ adb.py                    # ADB device bridge & root injector
â”‚   â”œâ”€â”€ gui_tk.py                 # Native desktop Tkinter GUI
â”‚   â”œâ”€â”€ gui_web.py                # Standalone embedded Web GUI
â”‚   â””â”€â”€ cli.py                    # Command-line interface subcommands
â””â”€â”€ tests/
    â””â”€â”€ test_all.py               # Unit and integration test suite
```

---

## ðŸ¤ Credits & Acknowledgments

- **[@ph12nex](https://github.com/ph12nex)** â€” For reverse-engineering the Xiaomi thermal AES-128-CBC encryption key (`thermalopenssl.h`), decryption heuristics, and original implementation in the Pandemonium Kernel Manager Android application.
- **[Pandemonium Kernel Manager Updater](https://github.com/kenway214/pandemonium-kernel-manager-updater)** by **[@kenway214](https://github.com/kenway214)** â€” For the upstream Android application and tools ecosystem.
