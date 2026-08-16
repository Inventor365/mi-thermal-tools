# 📘 Comprehensive Guide: Xiaomi & HyperOS Thermal Subsystem

This guide provides an in-depth technical breakdown of how Xiaomi / HyperOS thermal management operates, how `mi_thermald` works, how configs are parsed and decrypted, and how to create custom thermal profiles.

---

## 1. The Xiaomi Thermal Stack Architecture

The thermal management subsystem on Qualcomm-powered Xiaomi devices is composed of three interconnected layers:

```
+-------------------------------------------------------------+
|                     Android Framework                       |
|  - PowerManager / IThermalService                           |
|  - Xiaomi Performance Mode / Game Turbo                     |
+-------------------------------------------------------------+
                              | Writes profile ID (0-19)
                              v
+-------------------------------------------------------------+
|            Sysfs Thermal Communication Node                 |
|       /sys/class/thermal/thermal_message/sconfig            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                Daemon: vendor/bin/mi_thermald               |
|  - Reads /vendor/etc/thermal-map.conf                       |
|  - Decrypts target /odm/etc/thermal-<profile>.conf (AES)    |
|  - Polls physical & virtual sensors                         |
|  - Controls hardware throttling limits via sysfs & devfreq  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                       Hardware Layer                        |
|  - CPU Clusters (Little / Mid / Prime)                      |
|  - Adreno GPU (KGSL / Devfreq)                              |
|  - Battery Charger PMIC / SMB IC (FCC mA limits)            |
|  - Display Backlight (PWM max duty limit)                   |
|  - 5G/4G Modem, Wi-Fi 6/7, Camera ISP                       |
+-------------------------------------------------------------+
```

---

## 2. Decryption & Encryption Internals

Xiaomi uses a symmetric cipher embedded in `libthermalclient.so` and `mi_thermald`:

- **Cipher**: `AES-128-CBC`
- **Key**: `74 68 65 72 6d 61 6c 6f 70 65 6e 73 73 6c 2e 68` (`thermalopenssl.h`)
- **IV**: `74 68 65 72 6d 61 6c 6f 70 65 6e 73 73 6c 2e 68` (`thermalopenssl.h`)
- **Block Size**: 16 bytes
- **Padding Mode**: PKCS#7 (PKCS#5)

### Python Decryption Implementation
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

KEY = b"thermalopenssl.h"
IV = b"thermalopenssl.h"

def decrypt_file(data: bytes) -> str:
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
```

---

## 3. Detailed Anatomy of a Thermal `.conf` File

### Virtual Sensors
Virtual sensors calculate a weighted temperature estimate to avoid relying on a single thermistor:
```ini
[VIRTUAL-SENSOR0]
algo_type       Virtual
sensors         cpu_therm  battery  charger_therm0  wifi_therm  pa_therm0  pa_therm1  quiet_therm
weight          -26        301      147             330         36         119        -2
polling         2000
weight_sum      1000
compensation    2015
```
Formula:
$$\text{Temp} = \frac{\sum (\text{sensor}_i \times \text{weight}_i)}{\text{weight\_sum}} + \text{compensation}$$

### Step Throttling (`ss`)
Step throttling reduces CPU/GPU frequency when temperatures cross `set_point`:
```ini
[SS-CPU7]
algo_type           ss
sensor              VIRTUAL-SENSOR0
device              cpu7
set_point           45000       # Trigger throttling at 45°C
set_point_clr       44000       # Clear throttling when temp drops to 44°C
time_constant       0
device_perf_floor   1094400     # Maximum allowed frequency when throttled (1.09 GHz)
action_type         1
```

### Multi-Level Matrix (`monitor`)
Used for multi-stage progressive throttling:
```ini
[MONITOR-BAT]
algo_type   monitor
sensor      battery
device      battery
polling     1000
trig        34000   35000   37500   38500   40500   45000
clr         32000   34200   36200   38000   39500   44200
target      500     900     1000    1200    1400    1500
```

---

## 4. Creating a Magisk / KernelSU Thermal Module

To create a systemless thermal module:

1. Decrypt the stock thermal files from `/odm/etc/` using `mi-thermal-editor`.
2. Edit the threshold temperatures and frequency caps.
3. Re-encrypt the files using `./mi-thermal-editor encrypt <file>`.
4. Place the encrypted `.conf` files into your Magisk module structure:
```
MyThermalModule/
├── module.prop
├── system/
│   └── odm/
│       └── etc/
│           ├── thermal-normal.conf
│           └── thermal-mgame.conf
```
5. Flash the module in Magisk / KernelSU / APatch.

---

## 5. Credits

- **[@ph12nex](https://github.com/ph12nex)** — Key discovery, reverse engineering, and implementation in Pandemonium Kernel Manager.
- **[Pandemonium Kernel Manager Updater](https://github.com/kenway214/pandemonium-kernel-manager-updater)** by **[@kenway214](https://github.com/kenway214)** — Upstream Android application.
