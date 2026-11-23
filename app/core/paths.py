# -*- coding: utf-8 -*-
"""Поиск папки Minecraft и локальные настройки самого клиента."""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Optional

APP_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_ROOT.parent
SETTINGS_FILE = APP_ROOT / "local_settings.json"
DEMO_DIR = APP_ROOT / "demo_minecraft"


def default_minecraft_dir() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / ".minecraft"
        return home / "AppData" / "Roaming" / ".minecraft"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "minecraft"
    return home / ".minecraft"


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def minecraft_dir() -> Path:
    configured = load_settings().get("minecraftDir")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return path
    return default_minecraft_dir()


def set_minecraft_dir(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    data = load_settings()
    data["minecraftDir"] = str(path)
    save_settings(data)
    return path


DEMO_OPTIONS = """version:1343
invertYMouse:false
mouseSensitivity:0.5
fov:0.0
gamma:0.5
renderDistance:8
guiScale:0
particles:0
maxFps:120
fboEnable:true
difficulty:2
fancyGraphics:true
ao:true
renderClouds:true
resourcePacks:[]
incompatibleResourcePacks:[]
lastServer:
lang:ru_ru
chatVisibility:0
chatOpacity:1.0
snooperEnabled:true
fullscreen:false
useVbo:true
hideServerAddress:false
advancedItemTooltips:false
pauseOnLostFocus:true
touchscreen:false
overrideWidth:0
overrideHeight:0
heldItemTooltips:true
chatHeightFocused:1.0
chatHeightUnfocused:0.4375
chatScale:1.0
chatWidth:1.0
mipmapLevels:4
useNativeTransport:true
mainHand:right
attackIndicator:1
smoothCamera:false
bobView:true
enableVsync:false
anaglyph3d:false
reducedDebugInfo:false
"""

DEMO_PROFILES = {
    "profiles": {
        "1.12.2-forge": {
            "name": "1.12.2-forge",
            "lastVersionId": "1.12.2-forge1.12.2-14.23.5.2860",
            "javaArgs": "-Xmx2G -XX:+UseG1GC",
            "type": "custom",
        },
        "RELOG-IC": {
            "name": "RELOG-IC",
            "lastVersionId": "1.12.2",
            "javaArgs": "-Xmx4G -XX:+UseG1GC -XX:+ParallelRefProcEnabled",
            "type": "custom",
        },
    },
    "selectedProfile": "RELOG-IC",
    "clientToken": "demo",
    "authenticationDatabase": {},
    "launcherVersion": {"name": "2.1.1768", "format": 20},
}


def ensure_demo() -> Path:
    """Создаёт демо-папку, чтобы UI было что показывать без реального клиента."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    options = DEMO_DIR / "options.txt"
    if not options.exists():
        options.write_text(DEMO_OPTIONS, encoding="utf-8")
    profiles = DEMO_DIR / "launcher_profiles.json"
    if not profiles.exists():
        profiles.write_text(json.dumps(DEMO_PROFILES, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    return DEMO_DIR


def jar_candidates() -> list[Path]:
    """Где может лежать jar клиента — для вкладки «Мод»."""
    out: list[Path] = []
    root = PROJECT_ROOT
    for name in ("Impact-4.9.1-1.12.2.jar",):
        candidate = root / name
        if candidate.exists():
            out.append(candidate)
    out.extend(sorted((root / "dist").glob("*.jar")))
    mc = minecraft_dir()
    mods = mc / "mods"
    if mods.exists():
        out.extend(sorted(mods.glob("*.jar"))[:20])
    return out
