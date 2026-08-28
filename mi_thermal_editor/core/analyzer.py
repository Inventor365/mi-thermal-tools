"""
Mi Thermal Editor - Thermal Configuration Analyzer
Analyzes thermal trip points, mitigation curves, sensor thresholds, and Xiaomi SCONFIG profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .parser import ThermalConfig, ThermalSection, parse_thermal_config


# Xiaomi Peridot (POCO F6 / Redmi Turbo 3 - SM8635) SCONFIG Profiles Knowledge Base
XIAOMI_SCONFIG_DB: Dict[int, Dict[str, str]] = {
    0: {
        "name": "Default / Balanced",
        "file": "thermal-normal.conf",
        "desc": "Standard balanced profile for daily system usage. Balances CPU/GPU performance and battery temperature.",
        "category": "Daily",
        "present_on_peridot": "Yes"
    },
    1: {
        "name": "Data Migration (Huanji)",
        "file": "thermal-huanji.conf",
        "desc": "Mi Mover data transfer and heavy 5G/Wi-Fi file downloads. Prevents modem thermal throttling.",
        "category": "System",
        "present_on_peridot": "Yes"
    },
    2: {
        "name": "Abnormal Recovery",
        "file": "thermal-abnormal.conf",
        "desc": "Emergency thermal recovery profile for rapid heat dissipation.",
        "category": "Recovery",
        "present_on_peridot": "Template"
    },
    3: {
        "name": "Night Video Capture",
        "file": "thermal-nightvideo.conf",
        "desc": "Night mode video recording with computational ISP noise reduction.",
        "category": "Camera",
        "present_on_peridot": "Template"
    },
    4: {
        "name": "Dolby Vision HDR",
        "file": "thermal-dolbyvision.conf",
        "desc": "Dolby Vision HDR video playback thermal tuning.",
        "category": "Media",
        "present_on_peridot": "Template"
    },
    5: {
        "name": "In-Call / Telephony",
        "file": "thermal-phone.conf",
        "desc": "Voice and video phone calls. Keeps receiver area near ear cool during long calls.",
        "category": "Daily",
        "present_on_peridot": "Yes"
    },
    6: {
        "name": "Unconstrained Benchmark",
        "file": "thermal-nolimits.conf",
        "desc": "Triggered during AnTuTu, Geekbench, and 3DMark runs. Uncaps CPU, GPU, and RAM thermal limits.",
        "category": "Performance",
        "present_on_peridot": "Yes"
    },
    7: {
        "name": "Heavy 3D Gaming (Class 0)",
        "file": "thermal-class0.conf",
        "desc": "Heavy 3D gaming class 0 thermal profile.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    8: {
        "name": "Online Video Streaming",
        "file": "thermal-youtube.conf",
        "desc": "YouTube and web streaming video playback profile.",
        "category": "Media",
        "present_on_peridot": "Template"
    },
    9: {
        "name": "AR / VR Rendering",
        "file": "thermal-arvr.conf",
        "desc": "Augmented reality and virtual reality rendering computation.",
        "category": "Graphics",
        "present_on_peridot": "Yes"
    },
    10: {
        "name": "GPS Navigation",
        "file": "thermal-navigation.conf",
        "desc": "Google Maps & GPS navigation while in-car under sunlight.",
        "category": "Navigation",
        "present_on_peridot": "Yes"
    },
    11: {
        "name": "Video Recording",
        "file": "thermal-video.conf",
        "desc": "Standard 1080P/4K video recording thermal management.",
        "category": "Camera",
        "present_on_peridot": "Yes"
    },
    12: {
        "name": "Store Demo Mode",
        "file": "thermal-demo.conf",
        "desc": "Retail store display unit demo mode.",
        "category": "System",
        "present_on_peridot": "Template"
    },
    13: {
        "name": "Special Performance Test",
        "file": "thermal-sptm.conf",
        "desc": "Factory and lab QA thermal stress testing mode.",
        "category": "Testing",
        "present_on_peridot": "Template"
    },
    14: {
        "name": "Video Chat",
        "file": "thermal-videochat.conf",
        "desc": "WhatsApp, Zoom, Teams video calls. Manages camera ISP, modem, and CPU heat simultaneously.",
        "category": "Media",
        "present_on_peridot": "Yes"
    },
    15: {
        "name": "Camera Capture & Preview",
        "file": "thermal-camera.conf",
        "desc": "Camera viewfinder and photo capture thermal management.",
        "category": "Camera",
        "present_on_peridot": "Yes"
    },
    16: {
        "name": "4K Video Recording (Slot 1)",
        "file": "thermal-4k.conf",
        "desc": "4K 60FPS high-bitrate video recording thermal policy.",
        "category": "Camera",
        "present_on_peridot": "Yes"
    },
    17: {
        "name": "4K Video Recording (Slot 2)",
        "file": "thermal-4k.conf",
        "desc": "4K 60FPS video recording secondary slot.",
        "category": "Camera",
        "present_on_peridot": "Yes"
    },
    18: {
        "name": "Esports / MOBA Gaming",
        "file": "thermal-tgame.conf",
        "desc": "MOBA and competitive esports gaming (Honor of Kings, MLBB, Wild Rift).",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    19: {
        "name": "Heavy 3D Gaming (MGame)",
        "file": "thermal-mgame.conf",
        "desc": "Optimized for heavy 3D titles (PUBG, BGMI, Call of Duty Mobile). Maintains high GPU clocks.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    20: {
        "name": "Extreme Gaming (Yuanshen)",
        "file": "thermal-yuanshen.conf",
        "desc": "Extreme load 60FPS gaming (Genshin Impact). Prioritizes sustained FPS over skin temperature.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    25: {
        "name": "Extreme Gaming (Xingtie)",
        "file": "thermal-xingtie.conf",
        "desc": "Heavy turn-based 3D gaming (Honkai Star Rail).",
        "category": "Gaming",
        "present_on_peridot": "Template"
    },
    26: {
        "name": "High FPS Gaming (90/120Hz)",
        "file": "thermal-highfps.conf",
        "desc": "High refresh rate 90Hz / 120Hz competitive gaming thermal policy.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    27: {
        "name": "Turbo Fast Charging",
        "file": "thermal-charge.conf",
        "desc": "Turbo fast charging thermal management.",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    28: {
        "name": "Extended High-Bitrate Video",
        "file": "thermal-extravideo.conf",
        "desc": "Long duration high-bitrate video capture.",
        "category": "Camera",
        "present_on_peridot": "Template"
    },
    50: {
        "name": "HyperOS Performance Mode",
        "file": "thermal-per-normal.conf",
        "desc": "HyperOS Performance Mode in Control Center. Raises CPU throttle trigger from 37°C to 45°C.",
        "category": "Performance",
        "present_on_peridot": "Yes"
    },
    52: {
        "name": "Performance Mode (Abnormal)",
        "file": "thermal-per-abnormal.conf",
        "desc": "Performance mode abnormal recovery profile.",
        "category": "Recovery",
        "present_on_peridot": "Template"
    },
    57: {
        "name": "Performance Mode (Heavy Gaming)",
        "file": "thermal-per-class0.conf",
        "desc": "Performance Mode heavy 3D gaming thermal policy.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    58: {
        "name": "Performance Mode (Streaming)",
        "file": "thermal-per-youtube.conf",
        "desc": "Performance mode video streaming profile.",
        "category": "Media",
        "present_on_peridot": "Template"
    },
    60: {
        "name": "Performance Mode (Navigation)",
        "file": "thermal-per-navigation.conf",
        "desc": "Performance mode GPS navigation profile.",
        "category": "Navigation",
        "present_on_peridot": "Template"
    },
    61: {
        "name": "Performance Mode (Video)",
        "file": "thermal-per-video.conf",
        "desc": "Performance mode video capture profile.",
        "category": "Camera",
        "present_on_peridot": "Yes"
    },
    76: {
        "name": "Performance Mode (High FPS)",
        "file": "thermal-highfps.conf",
        "desc": "Performance mode 90/120Hz high refresh rate gaming.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    77: {
        "name": "Performance Mode (Fast Charge)",
        "file": "thermal-charge.conf",
        "desc": "Performance mode fast charging policy.",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    78: {
        "name": "Performance Mode (Extra Video)",
        "file": "thermal-extravideo.conf",
        "desc": "Performance mode extended video recording.",
        "category": "Camera",
        "present_on_peridot": "Template"
    },
    500: {
        "name": "High Power Normal (HP-Normal)",
        "file": "thermal-hp-normal.conf",
        "desc": "High-power daily profile with elevated thermal limits.",
        "category": "Performance",
        "present_on_peridot": "Yes"
    },
    501: {
        "name": "High Power Gaming (HP-MGame)",
        "file": "thermal-hp-mgame.conf",
        "desc": "High-power esports gaming profile with raised thermal trip thresholds.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    700: {
        "name": "Concurrent Gaming (CGame)",
        "file": "thermal-cgame.conf",
        "desc": "Concurrent gaming thermal management.",
        "category": "Gaming",
        "present_on_peridot": "Yes"
    },
    701: {
        "name": "Concurrent Video Capture",
        "file": "thermal-cclassvideo.conf",
        "desc": "Concurrent video capture and streaming thermal management.",
        "category": "Media",
        "present_on_peridot": "Yes"
    },
    702: {
        "name": "Thermal Computation (Comp)",
        "file": "thermal-comp.conf",
        "desc": "Heavy sustained mathematical / NPU compute workload.",
        "category": "Compute",
        "present_on_peridot": "Template"
    },
    704: {
        "name": "Wireless Charging Normal",
        "file": "thermal-wnormal.conf",
        "desc": "Wireless charging standard profile (Foldable/Flagship template).",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    705: {
        "name": "Wireless Charging Video",
        "file": "thermal-wvideo.conf",
        "desc": "Wireless charging during video playback.",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    706: {
        "name": "Wireless Charging Heavy Game",
        "file": "thermal-wclass0.conf",
        "desc": "Wireless charging during heavy gaming.",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    707: {
        "name": "Wireless Charging Gaming",
        "file": "thermal-wgame.conf",
        "desc": "Wireless charging during gaming sessions.",
        "category": "Charging",
        "present_on_peridot": "Template"
    },
    708: {
        "name": "Concurrent Video Recording",
        "file": "thermal-cvideo.conf",
        "desc": "Concurrent camera recording profile.",
        "category": "Camera",
        "present_on_peridot": "Template"
    },
    789: {
        "name": "Multi-Window Animation",
        "file": "thermal-multi-anim.conf",
        "desc": "Multi-window UI desktop animation thermal management.",
        "category": "System",
        "present_on_peridot": "Template"
    }
}


@dataclass
class SensorAnalysis:
    sensor_name: str
    is_virtual: bool
    used_in_sections: List[str] = field(default_factory=list)
    min_trigger_temp: Optional[float] = None
    max_trigger_temp: Optional[float] = None
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class DeviceMitigationAnalysis:
    device_name: str
    rule_count: int = 0
    trip_points: List[Dict[str, Any]] = field(default_factory=list)
    min_throttle_temp: Optional[float] = None
    max_throttle_temp: Optional[float] = None


@dataclass
class ThermalAnalysisReport:
    filename: str
    total_sections: int
    algorithm_types: Dict[str, int]
    sensors: List[SensorAnalysis]
    devices: List[DeviceMitigationAnalysis]
    virtual_sensors: List[str]
    lowest_throttle_temp: Optional[float] = None
    highest_throttle_temp: Optional[float] = None
    matched_sconfig: Optional[Dict[str, Any]] = None
    summary_text: str = ""


def analyze_thermal_config(
    config_or_content: ThermalConfig | str,
    filename: str = "thermal.conf"
) -> ThermalAnalysisReport:
    """
    Performs a deep structured analysis of a thermal configuration.
    """
    if isinstance(config_or_content, str):
        config = parse_thermal_config(config_or_content)
    else:
        config = config_or_content

    algo_counts: Dict[str, int] = {}
    sensor_map: Dict[str, SensorAnalysis] = {}
    device_map: Dict[str, DeviceMitigationAnalysis] = {}
    virtual_sensors: List[str] = []

    all_triggers: List[float] = []

    for sec in config.sections:
        algo = sec.algo_type or "unknown"
        algo_counts[algo] = algo_counts.get(algo, 0) + 1

        if sec.is_virtual_sensor:
            virtual_sensors.append(sec.name)

        # Track sensors
        sec_sensors = [sec.sensor] if sec.sensor else sec.sensors
        for s in sec_sensors:
            if not s:
                continue
            if s not in sensor_map:
                sensor_map[s] = SensorAnalysis(
                    sensor_name=s,
                    is_virtual=(s in virtual_sensors or "virtual" in s.lower())
                )
            sensor_map[s].used_in_sections.append(sec.name)

            for tp in sec.trip_points:
                if tp.trigger_temp is not None:
                    t_val = tp.trigger_temp
                    all_triggers.append(t_val)
                    curr_min = sensor_map[s].min_trigger_temp
                    curr_max = sensor_map[s].max_trigger_temp
                    if curr_min is None or t_val < curr_min:
                        sensor_map[s].min_trigger_temp = t_val
                    if curr_max is None or t_val > curr_max:
                        sensor_map[s].max_trigger_temp = t_val

        # Track devices
        sec_devices = [sec.device] if sec.device else sec.devices
        for d in sec_devices:
            if not d:
                continue
            if d not in device_map:
                device_map[d] = DeviceMitigationAnalysis(device_name=d)
            device_map[d].rule_count += 1

            for tp in sec.trip_points:
                if tp.trigger_temp is not None:
                    t_val = tp.trigger_temp
                    entry = {
                        "section": sec.name,
                        "trigger": t_val,
                        "clear": tp.clear_temp,
                        "action": tp.target_action
                    }
                    device_map[d].trip_points.append(entry)
                    curr_min = device_map[d].min_throttle_temp
                    curr_max = device_map[d].max_throttle_temp
                    if curr_min is None or t_val < curr_min:
                        device_map[d].min_throttle_temp = t_val
                    if curr_max is None or t_val > curr_max:
                        device_map[d].max_throttle_temp = t_val

    lowest_t = min(all_triggers) if all_triggers else None
    highest_t = max(all_triggers) if all_triggers else None

    # Match SCONFIG profile based on filename
    matched_sconfig = None
    base_name = filename.lower()
    for s_id, s_info in XIAOMI_SCONFIG_DB.items():
        if s_info["file"].lower() == base_name or f"sconfig_{s_id}" in base_name:
            matched_sconfig = {"id": s_id, **s_info}
            break

    # Build human summary
    summary_lines = [
        f"Thermal Configuration Analysis: {filename}",
        f"Total Sections: {len(config.sections)} | Format: {config.format_type.upper()}",
        f"Algorithms: " + ", ".join(f"{k}: {v}" for k, v in algo_counts.items()),
        f"Virtual Sensors: {len(virtual_sensors)} ({', '.join(virtual_sensors[:4]) if virtual_sensors else 'None'})",
        f"Controlled Devices: {len(device_map)} ({', '.join(list(device_map.keys())[:6])})",
    ]
    if lowest_t is not None and highest_t is not None:
        summary_lines.append(f"Temperature Threshold Range: {lowest_t:.1f}°C to {highest_t:.1f}°C")

    if matched_sconfig:
        summary_lines.append(
            f"Xiaomi SCONFIG Profile [{matched_sconfig['id']}]: {matched_sconfig['name']} ({matched_sconfig['category']})"
        )
        summary_lines.append(f"Profile Description: {matched_sconfig['desc']}")

    return ThermalAnalysisReport(
        filename=filename,
        total_sections=len(config.sections),
        algorithm_types=algo_counts,
        sensors=list(sensor_map.values()),
        devices=list(device_map.values()),
        virtual_sensors=virtual_sensors,
        lowest_throttle_temp=lowest_t,
        highest_throttle_temp=highest_t,
        matched_sconfig=matched_sconfig,
        summary_text="\n".join(summary_lines)
    )
