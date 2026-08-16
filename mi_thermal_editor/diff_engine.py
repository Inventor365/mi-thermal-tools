"""
Mi Thermal Editor - Thermal Diff Engine
Semantic and line-level comparison between thermal configuration files.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .parser import ThermalConfig, ThermalSection, parse_thermal_config


@dataclass
class SectionDiff:
    section_name: str
    diff_type: str  # "added", "removed", "modified", "unchanged"
    changes: List[str] = field(default_factory=list)
    raw_diff: List[str] = field(default_factory=list)


@dataclass
class ThermalDiffResult:
    title_a: str
    title_b: str
    added_sections: List[str] = field(default_factory=list)
    removed_sections: List[str] = field(default_factory=list)
    modified_sections: List[SectionDiff] = field(default_factory=list)
    unchanged_sections: List[str] = field(default_factory=list)
    unified_diff_lines: List[str] = field(default_factory=list)
    summary: str = ""


def compute_thermal_diff(
    content_a: str,
    content_b: str,
    name_a: str = "Original",
    name_b: str = "Modified"
) -> ThermalDiffResult:
    """
    Computes both semantic section-level diff and standard unified line diff.
    """
    cfg_a = parse_thermal_config(content_a)
    cfg_b = parse_thermal_config(content_b)

    map_a = {s.name: s for s in cfg_a.sections}
    map_b = {s.name: s for s in cfg_b.sections}

    names_a = set(map_a.keys())
    names_b = set(map_b.keys())

    added = sorted(list(names_b - names_a))
    removed = sorted(list(names_a - names_b))
    common = sorted(list(names_a & names_b))

    modified: List[SectionDiff] = []
    unchanged: List[str] = []

    for name in common:
        sec_a = map_a[name]
        sec_b = map_b[name]

        changes: List[str] = []

        # Check properties
        props_a = sec_a.properties
        props_b = sec_b.properties

        all_keys = set(props_a.keys()) | set(props_b.keys())
        for k in sorted(all_keys):
            val_a = props_a.get(k)
            val_b = props_b.get(k)
            if val_a != val_b:
                changes.append(f"Property '{k}': {val_a} -> {val_b}")

        # Compute raw diff for this section
        lines_a = sec_a.raw_lines
        lines_b = sec_b.raw_lines
        raw_d = list(difflib.unified_diff(
            lines_a, lines_b,
            fromfile=f"[{name}] (old)",
            tofile=f"[{name}] (new)",
            lineterm=""
        ))

        if changes or len(lines_a) != len(lines_b):
            modified.append(SectionDiff(
                section_name=name,
                diff_type="modified",
                changes=changes,
                raw_diff=raw_d
            ))
        else:
            unchanged.append(name)

    # Full unified diff
    lines_a = content_a.splitlines(keepends=True)
    lines_b = content_b.splitlines(keepends=True)
    unified = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=name_a,
        tofile=name_b
    ))

    summary_parts = [
        f"Diff: {name_a} vs {name_b}",
        f"Sections: +{len(added)} added, -{len(removed)} removed, ~{len(modified)} modified, ={len(unchanged)} unchanged"
    ]

    return ThermalDiffResult(
        title_a=name_a,
        title_b=name_b,
        added_sections=added,
        removed_sections=removed,
        modified_sections=modified,
        unchanged_sections=unchanged,
        unified_diff_lines=unified,
        summary="\n".join(summary_parts)
    )
