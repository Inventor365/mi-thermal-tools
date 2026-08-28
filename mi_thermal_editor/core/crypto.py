"""
Mi Thermal Editor - Core Cryptography Engine
Replicates and extends the AES-128-CBC encryption and decryption used by Xiaomi/MIUI/HyperOS
and Pandemonium Kernel Manager for thermal engine configuration files.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

CRYPTO_AVAILABLE = True


# Xiaomi thermal-engine standard key and IV (16 bytes = 128-bit)
DEFAULT_KEY: bytes = b"thermalopenssl.h"
DEFAULT_IV: bytes = b"thermalopenssl.h"

DEFAULT_SEARCH_PATHS = [
    "/odm/etc",
    "/vendor/etc",
    "/system/etc",
    "/system/vendor/etc",
]


@dataclass
class ThermalFile:
    name: str
    source_dir: str
    source_path: str
    content: str
    is_encrypted: bool
    file_size: int
    saved_at: float = 0.0

    @property
    def extension(self) -> str:
        return Path(self.name).suffix or ".conf"


def is_printable_text(text: str) -> bool:
    """
    Determines if text is readable configuration text vs garbage binary.
    Matches the heuristic logic from Pandemonium Kernel Manager.
    """
    if not text:
        return False
    control_count = 0
    for char in text:
        # Accept LF, CR, TAB, and standard printable chars
        code = ord(char)
        if code < 32 and char not in ("\n", "\r", "\t"):
            control_count += 1
    # Allow small tolerance of control characters
    return control_count < (len(text) // 50 + 2)


def decrypt_data(
    data: bytes,
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV
) -> Tuple[str, bool]:
    """
    Decrypts byte data using AES-128-CBC with PKCS7 padding.
    Returns:
        (text_content, was_encrypted)
    """
    if not CRYPTO_AVAILABLE:
        try:
            return data.decode("utf-8", errors="replace"), False
        except Exception:
            return str(data), False

    if len(key) != 16:
        key = key.ljust(16, b"\0")[:16]
    if len(iv) != 16:
        iv = iv.ljust(16, b"\0")[:16]

    # Try AES-128-CBC decryption
    if len(data) > 0 and len(data) % 16 == 0:
        try:
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(data) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(padded) + unpadder.finalize()
            text = decrypted.decode("utf-8", errors="replace")
            if is_printable_text(text):
                return text, True
        except Exception:
            # Not an encrypted block or invalid padding
            pass

    # Fallback to plain UTF-8 text if already unencrypted
    try:
        text = data.decode("utf-8", errors="replace")
        return text, False
    except Exception:
        return str(data), False


def encrypt_data(
    text: Union[str, bytes],
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV
) -> bytes:
    """
    Encrypts string or bytes content using AES-128-CBC with PKCS7 padding.
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("The 'cryptography' Python package is required for encryption.")

    if isinstance(text, str):
        data = text.encode("utf-8")
    else:
        data = text

    if len(key) != 16:
        key = key.ljust(16, b"\0")[:16]
    if len(iv) != 16:
        iv = iv.ljust(16, b"\0")[:16]

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded_data) + encryptor.finalize()


def load_thermal_file(
    file_path: Union[str, Path],
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV
) -> ThermalFile:
    """
    Loads and decrypts a thermal file from disk.
    """
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Thermal file not found: {file_path}")

    with open(p, "rb") as f:
        raw_bytes = f.read()

    text_content, is_enc = decrypt_data(raw_bytes, key=key, iv=iv)
    stat = p.stat()

    return ThermalFile(
        name=p.name,
        source_dir=str(p.parent),
        source_path=str(p),
        content=text_content,
        is_encrypted=is_enc,
        file_size=stat.st_size,
        saved_at=stat.st_mtime
    )


def save_thermal_file(
    file_path: Union[str, Path],
    content: str,
    encrypt: bool = True,
    create_backup: bool = True,
    backup_dir: Optional[Union[str, Path]] = None,
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV
) -> Tuple[str, Optional[str]]:
    """
    Saves a thermal configuration file to disk, optionally encrypting it and creating a backup.
    Returns:
        (saved_path, backup_path_or_none)
    """
    p = Path(file_path).resolve()
    backup_path = None

    # Handle backup creation
    if create_backup and p.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if backup_dir:
            b_dir = Path(backup_dir).resolve()
        else:
            b_dir = p.parent / "backup" / timestamp
        b_dir.mkdir(parents=True, exist_ok=True)
        backup_file = b_dir / f"{p.name}.bck"
        shutil.copy2(p, backup_file)
        backup_path = str(backup_file)

    p.parent.mkdir(parents=True, exist_ok=True)

    if encrypt:
        data_to_write = encrypt_data(content, key=key, iv=iv)
        with open(p, "wb") as f:
            f.write(data_to_write)
    else:
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    return str(p), backup_path


def scan_thermal_files(
    directory: Union[str, Path],
    filter_pattern: str = "thermal",
    recursive: bool = False
) -> List[Path]:
    """
    Scans a directory for thermal configuration files.
    """
    target = Path(directory).resolve()
    if not target.exists() or not target.is_dir():
        return []

    results: List[Path] = []
    pattern_lower = filter_pattern.lower()

    if recursive:
        candidates = target.rglob("*")
    else:
        candidates = target.iterdir()

    for item in candidates:
        if item.is_file():
            name_lower = item.name.lower()
            if pattern_lower in name_lower or item.suffix in (".conf", ".json", ".sconfig"):
                results.append(item)

    return sorted(results, key=lambda x: x.name)


def batch_decrypt_directory(
    source_dir: Union[str, Path],
    output_dir: Union[str, Path],
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV,
    recursive: bool = False
) -> List[Tuple[str, str, bool]]:
    """
    Batch decrypts all thermal files from source_dir into output_dir as plaintext.
    Returns list of (source_file, dest_file, was_encrypted).
    """
    src = Path(source_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    files = scan_thermal_files(src, recursive=recursive)
    summary = []

    for fpath in files:
        rel_path = fpath.relative_to(src) if recursive else Path(fpath.name)
        dst_path = out / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        thermal_obj = load_thermal_file(fpath, key=key, iv=iv)
        with open(dst_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(thermal_obj.content)

        summary.append((str(fpath), str(dst_path), thermal_obj.is_encrypted))

    return summary


def batch_encrypt_directory(
    source_dir: Union[str, Path],
    output_dir: Union[str, Path],
    key: bytes = DEFAULT_KEY,
    iv: bytes = DEFAULT_IV,
    recursive: bool = False
) -> List[Tuple[str, str, bool]]:
    """
    Batch encrypts all plaintext thermal files from source_dir into output_dir as encrypted AES files.
    """
    src = Path(source_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    files = scan_thermal_files(src, recursive=recursive)
    summary = []

    for fpath in files:
        rel_path = fpath.relative_to(src) if recursive else Path(fpath.name)
        dst_path = out / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            content = fp.read()

        enc_bytes = encrypt_data(content, key=key, iv=iv)
        with open(dst_path, "wb") as fp:
            fp.write(enc_bytes)

        summary.append((str(fpath), str(dst_path), True))

    return summary
