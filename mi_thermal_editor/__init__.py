"""
Mi Thermal Editor - Linux Suite
Comprehensive tools for decrypting, analyzing, editing, and injecting Xiaomi/MIUI/HyperOS thermal configurations.
"""

from .core.crypto import (
    DEFAULT_KEY,
    DEFAULT_IV,
    ThermalFile,
    decrypt_data,
    encrypt_data,
    load_thermal_file,
    save_thermal_file,
    scan_thermal_files,
    batch_decrypt_directory,
    batch_encrypt_directory,
)
from .core.parser import (
    ThermalConfig,
    ThermalSection,
    ThermalTripPoint,
    parse_thermal_config,
    parse_conf,
)
from .core.analyzer import (
    XIAOMI_SCONFIG_DB,
    ThermalAnalysisReport,
    SensorAnalysis,
    DeviceMitigationAnalysis,
    analyze_thermal_config,
)
from .core.diff_engine import (
    ThermalDiffResult,
    SectionDiff,
    compute_thermal_diff,
)
from .services.adb_service import (
    ADBManager,
    ConnectedDevice,
    DeviceThermalZone,
)

__version__ = "1.0.0"
__all__ = [
    "DEFAULT_KEY",
    "DEFAULT_IV",
    "ThermalFile",
    "decrypt_data",
    "encrypt_data",
    "load_thermal_file",
    "save_thermal_file",
    "scan_thermal_files",
    "batch_decrypt_directory",
    "batch_encrypt_directory",
    "ThermalConfig",
    "ThermalSection",
    "ThermalTripPoint",
    "parse_thermal_config",
    "parse_conf",
    "XIAOMI_SCONFIG_DB",
    "ThermalAnalysisReport",
    "SensorAnalysis",
    "DeviceMitigationAnalysis",
    "analyze_thermal_config",
    "ThermalDiffResult",
    "SectionDiff",
    "compute_thermal_diff",
    "ADBManager",
    "ConnectedDevice",
    "DeviceThermalZone",
]
