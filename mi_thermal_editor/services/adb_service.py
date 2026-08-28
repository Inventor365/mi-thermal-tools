"""
Mi Thermal Editor - ADB Integration & Device Bridge
Provides device discovery, root access detection, live thermal reading,
and root injection matching Pandemonium Kernel Manager.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConnectedDevice:
    serial: str
    state: str
    model: str = ""
    device: str = ""
    is_root: bool = False


@dataclass
class DeviceThermalZone:
    zone_id: int
    zone_type: str
    temp_celsius: float


class ADBManager:
    """
    Manages ADB interactions with connected Xiaomi/Android devices.
    """

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or shutil.which("adb") or "adb"

    def is_adb_available(self) -> bool:
        try:
            res = subprocess.run([self.adb_path, "version"], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def list_devices(self) -> List[ConnectedDevice]:
        """Lists connected ADB devices with root status detection."""
        if not self.is_adb_available():
            return []

        try:
            res = subprocess.run([self.adb_path, "devices", "-l"], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return []

            devices: List[ConnectedDevice] = []
            for line in res.stdout.splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    model = ""
                    device_name = ""
                    for p in parts[2:]:
                        if p.startswith("model:"):
                            model = p.split(":", 1)[1]
                        elif p.startswith("device:"):
                            device_name = p.split(":", 1)[1]

                    is_root = False
                    if state == "device":
                        is_root = self.check_root(serial)

                    devices.append(ConnectedDevice(
                        serial=serial,
                        state=state,
                        model=model,
                        device=device_name,
                        is_root=is_root
                    ))
            return devices
        except Exception:
            return []

    def check_root(self, serial: Optional[str] = None) -> bool:
        """Checks if adb root or su is available."""
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["shell", "su -c id || id"])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = res.stdout.lower()
            return "uid=0(root)" in output or "gid=0(root)" in output
        except Exception:
            return False

    def run_root_shell(self, command: str, serial: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Executes a shell command on device as root.
        """
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])

        # Try su first, then plain shell if already adb root
        full_sh = f"su -c '{command}' 2>/dev/null || ({command})"
        cmd.extend(["shell", full_sh])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return res.returncode == 0, res.stdout, res.stderr
        except Exception as e:
            return False, "", str(e)

    def scan_device_thermal_files(
        self,
        serial: Optional[str] = None,
        search_dirs: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Scans /odm/etc, /vendor/etc, /system/etc on device for thermal config files.
        """
        if search_dirs is None:
            search_dirs = ["/odm/etc", "/vendor/etc", "/system/etc"]

        results: Dict[str, List[str]] = {}

        for sdir in search_dirs:
            escaped_dir = sdir.replace("'", "'\\''")
            cmd = f"ls -1 '{escaped_dir}' 2>/dev/null"
            success, stdout, _ = self.run_root_shell(cmd, serial=serial)
            if success and stdout:
                lines = [l.strip() for l in stdout.splitlines() if l.strip()]
                thermal_files = [f for f in lines if "thermal" in f.lower() or f.endswith(".conf")]
                if thermal_files:
                    results[sdir] = sorted(thermal_files)

        return results

    def pull_thermal_file(
        self,
        remote_path: str,
        serial: Optional[str] = None
    ) -> Tuple[bool, bytes, str]:
        """
        Pulls a thermal file directly from device via base64.
        """
        escaped_path = remote_path.replace("'", "'\\''")
        cmd = f"base64 '{escaped_path}' 2>/dev/null || true"
        success, stdout, stderr = self.run_root_shell(cmd, serial=serial)

        if not success or not stdout.strip():
            # Fallback to direct cat if base64 not available
            cmd = f"cat '{escaped_path}' 2>/dev/null || true"
            success, stdout, stderr = self.run_root_shell(cmd, serial=serial)
            if not success or not stdout:
                return False, b"", f"Failed to read {remote_path}: {stderr}"
            return True, stdout.encode("utf-8"), ""

        try:
            raw_b64 = "".join(stdout.split())
            decoded = base64.b64decode(raw_b64)
            return True, decoded, ""
        except Exception as e:
            return False, b"", f"Base64 decode error: {e}"

    def inject_thermal_file(
        self,
        remote_path: str,
        content_bytes: bytes,
        serial: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Injects a thermal file directly into /odm, /vendor, or /system with root remount and backup.
        Replicates exact injection shell workflow from Pandemonium Kernel Manager.
        """
        escaped_path = remote_path.replace("'", "'\\''")
        backup_path = f"{remote_path}.bak".replace("'", "'\\''")
        b64_str = base64.b64encode(content_bytes).decode("ascii")

        tmp_path = f"/data/local/tmp/pkm_thermal_{int(time.time() * 1000)}.bin"

        remount_cmd = ""
        if remote_path.startswith("/odm/"):
            remount_cmd = "mount -o rw,remount /odm 2>/dev/null || true; "
        elif remote_path.startswith("/vendor/"):
            remount_cmd = "mount -o rw,remount /vendor 2>/dev/null || true; "
        elif remote_path.startswith("/system/"):
            remount_cmd = "mount -o rw,remount /system 2>/dev/null || true; "

        shell_script = (
            f"set -e; "
            f"rm -f {tmp_path}; "
            f"echo '{b64_str}' | base64 -d > {tmp_path}; "
            f"{remount_cmd}"
            f"cp -f '{escaped_path}' '{backup_path}' 2>/dev/null || true; "
            f"cp -f {tmp_path} '{escaped_path}'; "
            f"chown root:root '{escaped_path}' 2>/dev/null || true; "
            f"chmod 0644 '{escaped_path}' 2>/dev/null || true; "
            f"restorecon '{escaped_path}' >/dev/null 2>&1 || true; "
            f"sync; "
            f"rm -f {tmp_path}"
        )

        success, stdout, stderr = self.run_root_shell(shell_script, serial=serial)
        if not success:
            err_msg = stderr.strip() or stdout.strip() or "Failed to write thermal file"
            return False, err_msg

        return True, f"Thermal injected successfully to {remote_path} (backup created: {remote_path}.bak)"

    def get_active_sconfig(self, serial: Optional[str] = None) -> Optional[int]:
        """Reads the currently active /sys/class/thermal/thermal_message/sconfig profile ID."""
        cmd = "cat /sys/class/thermal/thermal_message/sconfig 2>/dev/null"
        success, stdout, _ = self.run_root_shell(cmd, serial=serial)
        if success and stdout.strip().isdigit():
            return int(stdout.strip())
        return None

    def set_active_sconfig(self, sconfig_val: int, serial: Optional[str] = None) -> bool:
        """Sets the active thermal profile by writing to sconfig node."""
        cmd = f"echo {sconfig_val} > /sys/class/thermal/thermal_message/sconfig 2>/dev/null"
        success, _, _ = self.run_root_shell(cmd, serial=serial)
        return success

    def read_thermal_zones(self, serial: Optional[str] = None) -> List[DeviceThermalZone]:
        """Reads live temperatures from /sys/class/thermal/thermal_zone*."""
        cmd = (
            "for z in /sys/class/thermal/thermal_zone*; do "
            "  if [ -d \"$z\" ]; then "
            "    type=$(cat \"$z/type\" 2>/dev/null); "
            "    temp=$(cat \"$z/temp\" 2>/dev/null); "
            "    echo \"$z:$type:$temp\"; "
            "  fi; "
            "done 2>/dev/null"
        )
        success, stdout, _ = self.run_root_shell(cmd, serial=serial)
        if not success or not stdout:
            return []

        zones: List[DeviceThermalZone] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                z_path, z_type, z_temp = parts[0], parts[1], parts[2]
                try:
                    z_id = int(z_path.split("thermal_zone")[-1])
                    temp_val = float(z_temp)
                    if abs(temp_val) > 1000:
                        temp_val /= 1000.0
                    zones.append(DeviceThermalZone(zone_id=z_id, zone_type=z_type, temp_celsius=temp_val))
                except (ValueError, IndexError):
                    continue

        return sorted(zones, key=lambda z: z.zone_id)
