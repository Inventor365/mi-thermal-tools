"""
Mi Thermal Editor - Command Line Interface (CLI)
Provides command-line commands for decryption, encryption, batch conversion,
analysis, diffing, and ADB device operations.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from .adb import ADBManager
from .analyzer import XIAOMI_SCONFIG_DB, analyze_thermal_config
from .crypto import (
    batch_decrypt_directory,
    batch_encrypt_directory,
    decrypt_data,
    encrypt_data,
    load_thermal_file,
    save_thermal_file,
    scan_thermal_files,
)
from .diff_engine import compute_thermal_diff
from .parser import parse_thermal_config


def print_banner():
    print(r"""
  __  __ _   _____ _                               _   ______    _ _ _             
 |  \/  (_) |_   _| |                             | | |  ____|  | (_) |            
 | \  / |_    | | | |__   ___ _ __ _ __ ___   __ _| | | |__   __| |_| |_ ___  _ __ 
 | |\/| | |   | | | '_ \ / _ \ '__| '_ ` _ \ / _` | | |  __| / _` | | __/ _ \| '__|
 | |  | | |   | | | | | |  __/ |  | | | | | | (_| | | | |___| (_| | | || (_) | |   
 |_|  |_|_|   \_/ |_| |_|\___|_|  |_| |_| |_|\__,_|_| |______\__,_|_|\__\___/|_|   
                     [ Xiaomi / HyperOS Thermal Tools for Linux ]
    """)


def cli_decrypt(args):
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        print(f"[-] Error: File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    t_file = load_thermal_file(in_path)
    out_path = Path(args.output).resolve() if args.output else in_path.with_name(f"decrypted_{in_path.name}")

    with open(out_path, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(t_file.content)

    status = "AES-128-CBC Decrypted" if t_file.is_encrypted else "Plaintext (Unchanged)"
    print(f"[+] {status} -> {out_path} ({len(t_file.content)} chars)")


def cli_encrypt(args):
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        print(f"[-] Error: File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8", errors="replace") as fp:
        content = fp.read()

    enc_bytes = encrypt_data(content)
    out_path = Path(args.output).resolve() if args.output else in_path.with_name(f"encrypted_{in_path.name}")

    with open(out_path, "wb") as fp:
        fp.write(enc_bytes)

    print(f"[+] AES-128-CBC Encrypted -> {out_path} ({len(enc_bytes)} bytes)")


def cli_batch_decrypt(args):
    src_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()

    if not src_dir.is_dir():
        print(f"[-] Error: Directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Scanning and decrypting thermal files from {src_dir} to {out_dir}...")
    results = batch_decrypt_directory(src_dir, out_dir, recursive=args.recursive)

    enc_count = sum(1 for _, _, is_enc in results if is_enc)
    print(f"[+] Done! Processed {len(results)} files ({enc_count} AES encrypted decrypted) into {out_dir}")


def cli_batch_encrypt(args):
    src_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()

    if not src_dir.is_dir():
        print(f"[-] Error: Directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Scanning and encrypting thermal files from {src_dir} to {out_dir}...")
    results = batch_encrypt_directory(src_dir, out_dir, recursive=args.recursive)
    print(f"[+] Done! Encrypted {len(results)} files into {out_dir}")


def cli_analyze(args):
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        print(f"[-] Error: File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    t_file = load_thermal_file(in_path)
    report = analyze_thermal_config(t_file.content, filename=t_file.name)

    print("=" * 70)
    print(f"🔥 THERMAL CONFIGURATION ANALYSIS: {report.filename}")
    print("=" * 70)
    print(f"Encryption Status : {'🔒 AES-128-CBC Encrypted' if t_file.is_encrypted else '📄 Plaintext'}")
    print(f"Total Sections    : {report.total_sections}")
    print(f"Algorithm Types   : " + ", ".join(f"{k} ({v})" for k, v in report.algorithm_types.items()))
    print(f"Virtual Sensors   : " + (", ".join(report.virtual_sensors) if report.virtual_sensors else "None"))
    if report.lowest_throttle_temp and report.highest_throttle_temp:
        print(f"Temperature Range : {report.lowest_throttle_temp:.1f}°C to {report.highest_throttle_temp:.1f}°C")

    if report.matched_sconfig:
        sc = report.matched_sconfig
        print(f"\n[Xiaomi SCONFIG Profile]")
        print(f"  ID       : {sc['id']}")
        print(f"  Name     : {sc['name']} ({sc['category']})")
        print(f"  Use Case : {sc['desc']}")

    print("\n[Monitored Sensors]")
    print(f"  {'Sensor Name':<24} | {'Type':<14} | {'Min Temp':<10} | {'Max Temp':<10}")
    print("  " + "-" * 66)
    for s in report.sensors:
        stype = "Virtual" if s.is_virtual else "Physical"
        min_t = f"{s.min_trigger_temp:.1f}°C" if s.min_trigger_temp is not None else "-"
        max_t = f"{s.max_trigger_temp:.1f}°C" if s.max_trigger_temp is not None else "-"
        print(f"  {s.sensor_name:<24} | {stype:<14} | {min_t:<10} | {max_t:<10}")

    print("\n[Device Throttling Mitigations]")
    print(f"  {'Device':<18} | {'Section':<22} | {'Trig':<8} | {'Clr':<8} | {'Mitigation Action'}")
    print("  " + "-" * 75)
    for d in report.devices:
        for r in d.trip_points:
            trig_str = f"{r['trigger']:.1f}°C" if r['trigger'] is not None else "-"
            clr_str = f"{r['clear']:.1f}°C" if r['clear'] is not None else "-"
            action_str = str(r['action']) if r['action'] else "-"
            print(f"  {d.device_name:<18} | {r['section']:<22} | {trig_str:<8} | {clr_str:<8} | {action_str}")
    print("=" * 70)


def cli_diff(args):
    p_a = Path(args.file_a).resolve()
    p_b = Path(args.file_b).resolve()

    if not p_a.is_file() or not p_b.is_file():
        print(f"[-] Error: One or both files not found ({p_a}, {p_b})", file=sys.stderr)
        sys.exit(1)

    t_a = load_thermal_file(p_a)
    t_b = load_thermal_file(p_b)

    diff_res = compute_thermal_diff(t_a.content, t_b.content, name_a=t_a.name, name_b=t_b.name)
    print("=" * 70)
    print(diff_res.summary)
    print("=" * 70)

    if diff_res.added_sections:
        print(f"\n[+] Added Sections in {t_b.name}:")
        for s in diff_res.added_sections:
            print(f"    + [{s}]")

    if diff_res.removed_sections:
        print(f"\n[-] Removed Sections from {t_b.name}:")
        for s in diff_res.removed_sections:
            print(f"    - [{s}]")

    if diff_res.modified_sections:
        print(f"\n[~] Modified Sections:")
        for s_diff in diff_res.modified_sections:
            print(f"  [{s_diff.section_name}]:")
            for ch in s_diff.changes:
                print(f"    * {ch}")

    if args.unified:
        print("\n--- Unified Diff ---")
        for l in diff_res.unified_diff_lines:
            print(l, end="")
    print("=" * 70)


def cli_sconfig_list(args):
    print("=" * 80)
    print("XIAOMI / HYPEROS SCONFIG THERMAL PROFILES KNOWLEDGE BASE")
    print("=" * 80)
    print(f"{'ID':<4} | {'Profile Name':<24} | {'Config File':<22} | {'Category':<10}")
    print("-" * 80)
    for s_id, info in sorted(XIAOMI_SCONFIG_DB.items(), key=lambda x: x[0]):
        print(f"{s_id:<4} | {info['name']:<24} | {info['file']:<22} | {info['category']:<10}")
        print(f"     Description: {info['desc']}")
        print("-" * 80)


def cli_adb_scan(args):
    adb = ADBManager()
    devices = adb.list_devices()
    if not devices:
        print("[-] No connected ADB devices found.", file=sys.stderr)
        return

    serial = args.serial or devices[0].serial
    print(f"[*] Scanning thermal files on device {serial}...")
    files_map = adb.scan_device_thermal_files(serial=serial)
    for sdir, flist in files_map.items():
        print(f"\n📁 Directory: {sdir}")
        for f in flist:
            print(f"   - {f}")


def cli_adb_pull(args):
    adb = ADBManager()
    remote_path = args.remote_path
    serial = args.serial

    success, data, err = adb.pull_thermal_file(remote_path, serial=serial)
    if not success:
        print(f"[-] ADB Pull failed: {err}", file=sys.stderr)
        sys.exit(1)

    text_content, is_enc = decrypt_data(data)
    fname = Path(remote_path).name
    out_path = Path(args.output).resolve() if args.output else Path(f"./{fname}")

    if args.save_plain:
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(text_content)
    else:
        with open(out_path, "wb") as fp:
            fp.write(data)

    status = "AES-128-CBC Encrypted" if is_enc else "Plaintext"
    print(f"[+] Pulled {remote_path} ({status}) -> {out_path}")


def cli_adb_inject(args):
    adb = ADBManager()
    remote_path = args.remote_path
    local_path = Path(args.local_file).resolve()
    serial = args.serial

    if not local_path.is_file():
        print(f"[-] Error: Local file not found: {local_path}", file=sys.stderr)
        sys.exit(1)

    with open(local_path, "r", encoding="utf-8", errors="replace") as fp:
        content = fp.read()

    enc_bytes = encrypt_data(content)
    success, msg = adb.inject_thermal_file(remote_path, enc_bytes, serial=serial)
    if success:
        print(f"[+] {msg}")
    else:
        print(f"[-] Injection failed: {msg}", file=sys.stderr)
        sys.exit(1)


def cli_launch_gui(args):
    initial_dir = args.dir

    # If display is available, launch Tkinter GUI; otherwise launch Web GUI
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if display and not args.force_web:
        try:
            from .gui_tk import launch_gui
            launch_gui(initial_dir=initial_dir)
            return
        except Exception as e:
            print(f"[!] Native GUI launch failed ({e}), falling back to Web GUI...")

    from .gui_web import start_web_gui
    start_web_gui(host=args.host, port=args.port, open_browser=not args.no_browser)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mi-thermal-editor",
        description="Mi Thermal Editor for Linux - Xiaomi / HyperOS Thermal Decryptor & Analysis Suite"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # GUI command
    p_gui = subparsers.add_parser("gui", help="Launch Graphical User Interface")
    p_gui.add_argument("-d", "--dir", help="Initial thermal source directory")
    p_gui.add_argument("--force-web", action="store_true", help="Force Web GUI instead of Native Tkinter GUI")
    p_gui.add_argument("--host", default="127.0.0.1", help="Web GUI host (default: 127.0.0.1)")
    p_gui.add_argument("--port", type=int, default=8080, help="Web GUI port (default: 8080)")
    p_gui.add_argument("--no-browser", action="store_true", help="Don't auto-open browser for Web GUI")

    # Web GUI command
    p_web = subparsers.add_parser("web", help="Launch Web GUI server")
    p_web.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    p_web.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    p_web.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

    # Decrypt command
    p_dec = subparsers.add_parser("decrypt", help="Decrypt a single thermal configuration file")
    p_dec.add_argument("input", help="Input encrypted thermal file")
    p_dec.add_argument("-o", "--output", help="Output decrypted plaintext file")

    # Encrypt command
    p_enc = subparsers.add_parser("encrypt", help="Encrypt a plaintext thermal configuration file")
    p_enc.add_argument("input", help="Input plaintext thermal file")
    p_enc.add_argument("-o", "--output", help="Output encrypted binary file")

    # Batch Decrypt
    p_bdec = subparsers.add_parser("batch-decrypt", help="Batch decrypt all thermal files in directory")
    p_bdec.add_argument("input_dir", help="Source directory containing encrypted thermal files")
    p_bdec.add_argument("-o", "--output-dir", required=True, help="Destination directory for decrypted files")
    p_bdec.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories recursively")

    # Batch Encrypt
    p_benc = subparsers.add_parser("batch-encrypt", help="Batch encrypt all plaintext thermal files in directory")
    p_benc.add_argument("input_dir", help="Source directory containing plaintext thermal files")
    p_benc.add_argument("-o", "--output-dir", required=True, help="Destination directory for encrypted files")
    p_benc.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories recursively")

    # Analyze command
    p_ana = subparsers.add_parser("analyze", help="Analyze thermal trip points, mitigation curves, and sensors")
    p_ana.add_argument("input", help="Thermal config file to analyze")

    # Diff command
    p_diff = subparsers.add_parser("diff", help="Compare two thermal configuration files")
    p_diff.add_argument("file_a", help="First thermal file (original)")
    p_diff.add_argument("file_b", help="Second thermal file (modified)")
    p_diff.add_argument("-u", "--unified", action="store_true", help="Include full unified diff output")

    # SCONFIG list
    subparsers.add_parser("sconfig-list", help="List Xiaomi SCONFIG profile mapping knowledge base")

    # ADB commands
    p_adb_scan = subparsers.add_parser("adb-scan", help="Scan thermal files on connected ADB device")
    p_adb_scan.add_argument("-s", "--serial", help="Device serial number")

    p_adb_pull = subparsers.add_parser("adb-pull", help="Pull and decrypt thermal file from connected ADB device")
    p_adb_pull.add_argument("remote_path", help="Path on device (e.g. /odm/etc/thermal-normal.conf)")
    p_adb_pull.add_argument("-o", "--output", help="Local destination file path")
    p_adb_pull.add_argument("-s", "--serial", help="Device serial number")
    p_adb_pull.add_argument("--save-plain", action="store_true", default=True, help="Save as decrypted plaintext")

    p_adb_inject = subparsers.add_parser("adb-inject", help="Inject encrypted thermal file into device with root")
    p_adb_inject.add_argument("remote_path", help="Path on device (e.g. /odm/etc/thermal-normal.conf)")
    p_adb_inject.add_argument("local_file", help="Local thermal file to inject")
    p_adb_inject.add_argument("-s", "--serial", help="Device serial number")

    return parser


def main():
    parser = build_arg_parser()
    if len(sys.argv) == 1:
        # Default to launching GUI when called with no arguments
        args = parser.parse_args(["gui"])
    else:
        args = parser.parse_args()

    handlers = {
        "gui": cli_launch_gui,
        "web": lambda a: cli_launch_gui(argparse.Namespace(dir=None, force_web=True, host=a.host, port=a.port, no_browser=a.no_browser)),
        "decrypt": cli_decrypt,
        "encrypt": cli_encrypt,
        "batch-decrypt": cli_batch_decrypt,
        "batch-encrypt": cli_batch_encrypt,
        "analyze": cli_analyze,
        "diff": cli_diff,
        "sconfig-list": cli_sconfig_list,
        "adb-scan": cli_adb_scan,
        "adb-pull": cli_adb_pull,
        "adb-inject": cli_adb_inject,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
