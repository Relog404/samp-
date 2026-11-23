# -*- coding: utf-8 -*-
"""Работа с options.txt Minecraft 1.12.2.

Формат файла — построчный ``ключ:значение``. Парсер намеренно "мягкий":
неизвестные ключи сохраняются как есть, чтобы не ломать настройки,
добавленные модами или другим лаунчером.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

# ключи, которые клиент умеет показывать/менять, с типами и границами
SPEC: Dict[str, Dict[str, Any]] = {
    # --- графика -----------------------------------------------------------
    "renderDistance": {"type": "int", "min": 2, "max": 32, "step": 1},
    "mipmapLevels": {"type": "int", "min": 0, "max": 4, "step": 1},
    "maxFps": {"type": "int", "min": 10, "max": 260, "step": 10},
    "guiScale": {"type": "int", "min": 0, "max": 3, "step": 1},
    "particles": {"type": "enum", "choices": [0, 1, 2]},  # all / decreased / minimal
    "fancyGraphics": {"type": "bool"},
    "ao": {"type": "bool"},
    "renderClouds": {"type": "bool"},
    "fboEnable": {"type": "bool"},
    "useVbo": {"type": "bool"},
    "gamma": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "fullscreen": {"type": "bool"},
    "enableVsync": {"type": "bool"},
    "anaglyph3d": {"type": "bool"},
    # --- камера / "бодикам" ------------------------------------------------
    "fov": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "smoothCamera": {"type": "bool"},
    "bobView": {"type": "bool"},
    "mouseSensitivity": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "invertYMouse": {"type": "bool"},
    # --- прочее ------------------------------------------------------------
    "chatOpacity": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "chatScale": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "pauseOnLostFocus": {"type": "bool"},
    "touchscreen": {"type": "bool"},
    "advancedItemTooltips": {"type": "bool"},
    "reducedDebugInfo": {"type": "bool"},
    "chatVisibility": {"type": "enum", "choices": [0, 1, 2]},
    "attackIndicator": {"type": "enum", "choices": [0, 1, 2]},
    "mainHand": {"type": "str_enum", "choices": ["left", "right"]},
    "snooperEnabled": {"type": "bool"},
    "hideServerAddress": {"type": "bool"},
    "heldItemTooltips": {"type": "bool"},
    "useNativeTransport": {"type": "bool"},
}

# значения, которые 1.12.2 пишет по умолчанию (используются, если ключа нет)
FALLBACK: Dict[str, Any] = {
    "renderDistance": 8,
    "mipmapLevels": 4,
    "maxFps": 120,
    "guiScale": 0,
    "particles": 0,
    "fancyGraphics": True,
    "ao": True,
    "renderClouds": True,
    "fboEnable": True,
    "useVbo": True,
    "gamma": 0.5,
    "fullscreen": False,
    "enableVsync": False,
    "anaglyph3d": False,
    "fov": 0.0,
    "smoothCamera": False,
    "bobView": True,
    "mouseSensitivity": 0.5,
    "invertYMouse": False,
    "chatOpacity": 1.0,
    "chatScale": 1.0,
    "pauseOnLostFocus": True,
    "touchscreen": False,
    "advancedItemTooltips": False,
    "reducedDebugInfo": False,
    "chatVisibility": 0,
    "attackIndicator": 1,
    "mainHand": "right",
    "snooperEnabled": True,
    "hideServerAddress": False,
    "heldItemTooltips": True,
    "useNativeTransport": True,
}


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in ("true", "1", "yes")


def coerce(key: str, value: Any) -> Any:
    """Приводит значение к типу из SPEC и зажимает в границы."""
    spec = SPEC.get(key)
    if spec is None:
        return value
    kind = spec["type"]
    if kind == "bool":
        if isinstance(value, str):
            return parse_bool(value)
        return bool(value)
    if kind == "int":
        ival = int(round(float(value)))
        return max(spec["min"], min(spec["max"], ival))
    if kind == "float":
        fval = float(value)
        return round(max(spec["min"], min(spec["max"], fval)), 4)
    if kind == "str_enum":
        val = str(value)
        return val if val in spec["choices"] else spec["choices"][0]
    if kind == "enum":
        ival = int(value)
        return ival if ival in spec["choices"] else spec["choices"][0]
    return value


def to_text(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def from_text(key: str, raw: str) -> Any:
    spec = SPEC.get(key)
    if spec is None:
        return raw
    if spec["type"] == "bool":
        return parse_bool(raw)
    if spec["type"] == "int" or spec["type"] == "enum":
        try:
            return int(float(raw.strip()))
        except ValueError:
            return FALLBACK.get(key)
    if spec["type"] == "float":
        try:
            return float(raw.strip())
        except ValueError:
            return FALLBACK.get(key)
    if spec["type"] == "str_enum":
        val = raw.strip()
        return val if val in spec["choices"] else FALLBACK.get(key)
    return raw


@dataclass
class OptionsFile:
    path: Path
    values: Dict[str, Any] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)  # порядок и чужие ключи

    @classmethod
    def load(cls, path: Path) -> "OptionsFile":
        path = Path(path)
        values: Dict[str, Any] = {}
        lines: list[str] = []
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                lines.append(line)
                if ":" in line:
                    key, _, raw = line.partition(":")
                    values[key.strip()] = from_text(key.strip(), raw)
        return cls(path=path, values=values, raw_lines=lines)

    def known(self) -> Dict[str, Any]:
        """Только те ключи, которые клиент умеет редактировать."""
        out = {}
        for key in SPEC:
            if key in self.values:
                out[key] = self.values[key]
            elif key in FALLBACK:
                out[key] = FALLBACK[key]
        return out

    def merged(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(self.values)
        for key, value in updates.items():
            merged[key] = coerce(key, value)
        return merged

    def render(self, updates: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Возвращает (текст файла, что изменилось, что не изменилось)."""
        target = self.merged(updates or {})
        changed: Dict[str, Any] = {}
        unchanged: Dict[str, Any] = {}
        for key, new in (updates or {}).items():
            new = coerce(key, new)
            old = self.values.get(key)
            if old != new:
                changed[key] = {"old": old, "new": new}
            else:
                unchanged[key] = new

        # перестраиваем файл, сохраняя исходный порядок строк
        seen = set()
        out: list[str] = []
        for line in self.raw_lines:
            if ":" not in line:
                out.append(line)
                continue
            key, _, _raw = line.partition(":")
            key = key.strip()
            if key in target:
                out.append(f"{key}:{to_text(key, target[key])}")
                seen.add(key)
            else:
                out.append(line)
                seen.add(key)
        for key, value in target.items():
            if key not in seen:
                out.append(f"{key}:{to_text(key, value)}")

        return "\n".join(out) + "\n", changed, unchanged


def backup(path: Path, backup_root: Optional[Path] = None) -> Optional[Path]:
    """Копирует файл в резервную папку; возвращает путь копии."""
    path = Path(path)
    if not path.exists():
        return None
    root = Path(backup_root) if backup_root else path.parent / ".relogic_backups"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target_dir = root / stamp
    suffix = 1
    while target_dir.exists() and (target_dir / path.name).exists():
        target_dir = root / f"{stamp}-{suffix}"
        suffix += 1
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / path.name
    shutil.copy2(path, dst)
    return dst


def apply_updates(path: Path, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Записывает обновления в options.txt, предварительно сделав бэкап."""
    path = Path(path)
    opts = OptionsFile.load(path)
    text, changed, unchanged = opts.render(updates)
    backup_path = backup(path) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "path": str(path),
        "backup": str(backup_path) if backup_path else None,
        "changed": changed,
        "unchanged": sorted(unchanged),
        "count": len(changed),
    }
