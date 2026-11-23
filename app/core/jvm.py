# -*- coding: utf-8 -*-
"""Правка аргументов JVM в launcher_profiles.json (официальный лаунчер)."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def profiles_path(minecraft_dir: Path) -> Path:
    return Path(minecraft_dir) / "launcher_profiles.json"


def load_profiles(minecraft_dir: Path) -> Dict[str, Any]:
    path = profiles_path(minecraft_dir)
    if not path.exists():
        raise FileNotFoundError(f"не найден {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_profiles(minecraft_dir: Path) -> List[Dict[str, Any]]:
    data = load_profiles(minecraft_dir)
    selected = data.get("selectedProfile")
    result = []
    for key, profile in data.get("profiles", {}).items():
        result.append({
            "key": key,
            "name": profile.get("name", key),
            "version": profile.get("lastVersionId"),
            "javaArgs": profile.get("javaArgs", ""),
            "selected": key == selected or profile.get("name") == selected,
        })
    return sorted(result, key=lambda p: (not p["selected"], p["name"].lower()))


def apply_java_args(minecraft_dir: Path, profile_key: str, args: str) -> Dict[str, Any]:
    data = load_profiles(minecraft_dir)
    profiles = data.get("profiles", {})
    match: Optional[str] = None
    if profile_key in profiles:
        match = profile_key
    else:
        for key, profile in profiles.items():
            if profile.get("name") == profile_key:
                match = key
                break
    if match is None:
        raise KeyError(f"профиль {profile_key!r} не найден")

    path = profiles_path(minecraft_dir)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(minecraft_dir) / ".relogic_backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / path.name
    shutil.copy2(path, backup_file)

    old = profiles[match].get("javaArgs", "")
    profiles[match]["javaArgs"] = args
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "profile": profiles[match].get("name", match),
        "old": old,
        "new": args,
        "backup": str(backup_file),
    }
