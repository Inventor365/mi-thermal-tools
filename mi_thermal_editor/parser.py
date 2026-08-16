"""
Mi Thermal Editor - Thermal Configuration Parser
Parses Qualcomm/Xiaomi thermal-engine .conf, .json, and .sconfig formats.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ThermalTripPoint:
    trigger_temp: Optional[float] = None  # in Celsius
    clear_temp: Optional[float] = None    # in Celsius
    target_action: Optional[str] = None   # frequency cap, throttle level, or cooling action
    raw_trigger: Optional[str] = None
    raw_clear: Optional[str] = None


@dataclass
class ThermalSection:
    name: str
    algo_type: str = ""
    sensor: str = ""
    sensors: List[str] = field(default_factory=list)
    device: str = ""
    devices: List[str] = field(default_factory=list)
    polling: Optional[int] = None
    sampling: Optional[int] = None
    set_point: Optional[float] = None
    set_point_clr: Optional[float] = None
    weights: List[float] = field(default_factory=list)
    weight_sum: Optional[float] = None
    compensation: Optional[float] = None
    trip_points: List[ThermalTripPoint] = field(default_factory=list)
    properties: Dict[str, Union[str, List[str]]] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)

    @property
    def is_virtual_sensor(self) -> bool:
        return self.algo_type.lower() in ("virtual", "simulated") or "virtual" in self.name.lower()

    @property
    def is_mitigation_rule(self) -> bool:
        return self.algo_type.lower() in ("ss", "monitor", "pid", "threshold", "step")


@dataclass
class ThermalConfig:
    raw_content: str
    format_type: str = "conf"  # "conf", "json", "map"
    sections: List[ThermalSection] = field(default_factory=list)
    global_comments: List[str] = field(default_factory=list)
    sconfig_mappings: Dict[int, str] = field(default_factory=dict)

    def get_section(self, name: str) -> Optional[ThermalSection]:
        for sec in self.sections:
            if sec.name == name:
                return sec
        return None

    @property
    def sensors(self) -> List[str]:
        all_sensors = set()
        for sec in self.sections:
            if sec.sensor:
                all_sensors.add(sec.sensor)
            for s in sec.sensors:
                all_sensors.add(s)
        return sorted(list(all_sensors))

    @property
    def devices(self) -> List[str]:
        all_devices = set()
        for sec in self.sections:
            if sec.device:
                all_devices.add(sec.device)
            for d in sec.devices:
                all_devices.add(d)
        return sorted(list(all_devices))


def _parse_temp(val: str) -> Optional[float]:
    """Converts millidegrees or degrees Celsius string into Celsius float."""
    try:
        num = float(val.strip())
        if abs(num) > 1000:
            return num / 1000.0
        return num
    except (ValueError, TypeError):
        return None


def parse_conf(content: str) -> ThermalConfig:
    """
    Parses Xiaomi thermal configuration .conf content.
    Handles tab/space-separated key values, multiple values, and comments.
    """
    sections: List[ThermalSection] = []
    global_comments: List[str] = []
    sconfig_maps: Dict[int, str] = []  # type: ignore
    sconfig_dict: Dict[int, str] = {}

    current_section: Optional[ThermalSection] = None
    pending_comments: List[str] = []

    lines = content.splitlines()

    # Check if this is a thermal-map file like [0:thermal-normal.conf]
    is_map_file = False
    map_pattern = re.compile(r"^\[?(\d+):([a-zA-Z0-9_\-\.]+\.conf)\]?$")

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if current_section:
                current_section.raw_lines.append(line)
            continue

        if stripped.startswith("#"):
            if current_section is None:
                global_comments.append(stripped)
            else:
                pending_comments.append(stripped)
                current_section.raw_lines.append(line)
            continue

        # Check for map line
        m = map_pattern.match(stripped)
        if m:
            is_map_file = True
            sconfig_dict[int(m.group(1))] = m.group(2)
            continue

        # Section header
        if stripped.startswith("[") and stripped.endswith("]"):
            sec_name = stripped[1:-1].strip()
            current_section = ThermalSection(
                name=sec_name,
                comments=pending_comments,
                raw_lines=[line]
            )
            sections.append(current_section)
            pending_comments = []
            continue

        if current_section is None:
            # Lines before first section header
            if ":" in stripped:
                # e.g. 8.21.0:thermal-map-india.conf
                parts = stripped.split(":", 1)
                try:
                    sconfig_dict[int(parts[0].strip())] = parts[1].strip()
                    is_map_file = True
                except ValueError:
                    global_comments.append(stripped)
            else:
                global_comments.append(stripped)
            continue

        current_section.raw_lines.append(line)

        # Parse key-value tokens (either separated by '=' or whitespace/tabs)
        if "=" in stripped and not stripped.startswith("="):
            parts = stripped.split("=", 1)
            key = parts[0].strip().lower()
            val_str = parts[1].strip()
        else:
            tokens = stripped.split()
            key = tokens[0].lower()
            val_str = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        val_tokens = val_str.split()

        current_section.properties[key] = val_str if len(val_tokens) <= 1 else val_tokens

        # Populate well-known fields
        if key == "algo_type":
            current_section.algo_type = val_str
        elif key == "sensor":
            current_section.sensor = val_str
        elif key in ("sensors", "sensor_list"):
            current_section.sensors = val_tokens
        elif key == "device":
            current_section.device = val_str
        elif key in ("devices", "device_list", "cooling_devices"):
            current_section.devices = val_tokens
        elif key == "polling":
            try:
                current_section.polling = int(val_str)
            except ValueError:
                pass
        elif key == "sampling":
            try:
                current_section.sampling = int(val_str)
            except ValueError:
                pass
        elif key == "set_point":
            current_section.set_point = _parse_temp(val_str)
        elif key == "set_point_clr":
            current_section.set_point_clr = _parse_temp(val_str)
        elif key in ("weights", "weight"):
            try:
                current_section.weights = [float(w) for w in val_tokens]
            except ValueError:
                pass
        elif key == "weight_sum":
            try:
                current_section.weight_sum = float(val_str)
            except ValueError:
                pass
        elif key == "compensation":
            current_section.compensation = _parse_temp(val_str)

    # Process multi-trip-point arrays (trig / clr / target)
    for sec in sections:
        trig_list = sec.properties.get("trig") or sec.properties.get("thresholds") or []
        clr_list = sec.properties.get("clr") or sec.properties.get("thresholds_clr") or []
        target_list = sec.properties.get("target") or sec.properties.get("actions") or []

        if isinstance(trig_list, str):
            trig_list = trig_list.split()
        if isinstance(clr_list, str):
            clr_list = clr_list.split()
        if isinstance(target_list, str):
            target_list = target_list.split()

        max_len = max(len(trig_list), len(clr_list), len(target_list))
        if max_len > 0:
            for i in range(max_len):
                trig_raw = trig_list[i] if i < len(trig_list) else None
                clr_raw = clr_list[i] if i < len(clr_list) else None
                target_raw = target_list[i] if i < len(target_list) else None

                sec.trip_points.append(ThermalTripPoint(
                    trigger_temp=_parse_temp(trig_raw) if trig_raw else None,
                    clear_temp=_parse_temp(clr_raw) if clr_raw else None,
                    target_action=target_raw,
                    raw_trigger=trig_raw,
                    raw_clear=clr_raw
                ))
        elif sec.set_point is not None:
            sec.trip_points.append(ThermalTripPoint(
                trigger_temp=sec.set_point,
                clear_temp=sec.set_point_clr,
                target_action=str(sec.properties.get("action", "")),
                raw_trigger=str(sec.properties.get("set_point", "")),
                raw_clear=str(sec.properties.get("set_point_clr", ""))
            ))

    fmt = "map" if is_map_file else "conf"
    return ThermalConfig(
        raw_content=content,
        format_type=fmt,
        sections=sections,
        global_comments=global_comments,
        sconfig_mappings=sconfig_dict
    )


def parse_thermal_config(content: str) -> ThermalConfig:
    """
    Intelligently detects whether content is JSON or .conf and parses it.
    """
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            # Create a synthetic thermal config for json
            sections: List[ThermalSection] = []
            if isinstance(data, dict):
                for k, v in data.items():
                    sec = ThermalSection(name=k, properties=v if isinstance(v, dict) else {"value": str(v)})
                    sections.append(sec)
            return ThermalConfig(raw_content=content, format_type="json", sections=sections)
        except Exception:
            pass

    return parse_conf(content)
