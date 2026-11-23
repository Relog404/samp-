# -*- coding: utf-8 -*-
"""Пресеты оптимизации / визуала для RELOG-IC."""

from __future__ import annotations

from typing import Any, Dict, List

AIIKAR_FLAGS = [
    "-XX:+UseG1GC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+DisableExplicitGC",
    "-XX:+AlwaysPreTouch",
    "-XX:G1NewSizePercent=30",
    "-XX:G1MaxNewSizePercent=40",
    "-XX:G1HeapRegionSize=8M",
    "-XX:G1ReservePercent=20",
    "-XX:G1HeapWastePercent=5",
    "-XX:G1MixedGCCountTarget=4",
    "-XX:InitiatingHeapOccupancyPercent=15",
    "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1RSetUpdatingPauseTimePercent=5",
    "-XX:SurvivorRatio=32",
    "-XX:+PerfDisableSharedMem",
    "-XX:MaxTenuringThreshold=1",
]

SIMPLE_G1_FLAGS = [
    "-XX:+UseG1GC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:MaxGCPauseMillis=50",
    "-XX:+DisableExplicitGC",
]

PRESETS: List[Dict[str, Any]] = [
    {
        "id": "maxfps",
        "name": "Максимальный FPS",
        "tag": "performance",
        "about": "Минимум эффектов, максимум кадров. Для слабых ПК и PvP.",
        "values": {
            "renderDistance": 4,
            "mipmapLevels": 0,
            "particles": 2,
            "renderClouds": False,
            "fancyGraphics": False,
            "ao": False,
            "useVbo": True,
            "fboEnable": True,
            "maxFps": 260,
            "guiScale": 2,
            "smoothCamera": False,
            "bobView": False,
            "gamma": 0.5,
        },
    },
    {
        "id": "balanced",
        "name": "Баланс",
        "tag": "balanced",
        "about": "Стандартный вид Minecraft при стабильных 100+ FPS.",
        "values": {
            "renderDistance": 8,
            "mipmapLevels": 2,
            "particles": 1,
            "renderClouds": True,
            "fancyGraphics": True,
            "ao": True,
            "useVbo": True,
            "maxFps": 144,
            "guiScale": 2,
        },
    },
    {
        "id": "photorealism",
        "name": "Фотореализм",
        "tag": "visual",
        "about": "Максимум детализации: mipmap 4, AO, дальность 16, все частицы.",
        "values": {
            "renderDistance": 16,
            "mipmapLevels": 4,
            "particles": 0,
            "renderClouds": True,
            "fancyGraphics": True,
            "ao": True,
            "useVbo": True,
            "maxFps": 260,
            "gamma": 0.45,
            "bobView": True,
            "anaglyph3d": False,
        },
    },
    {
        "id": "bodycam",
        "name": "Бодикам",
        "tag": "camera",
        "about": "Кинематографичная камера: плавное сглаживание, покачивание, FOV 85°.",
        "values": {
            "smoothCamera": True,
            "bobView": True,
            "fov": 0.375,
            "mouseSensitivity": 0.4,
            "fancyGraphics": True,
            "ao": True,
            "mipmapLevels": 3,
            "renderDistance": 12,
            "maxFps": 144,
        },
    },
    {
        "id": "fisheye",
        "name": "Рыбий глаз",
        "tag": "camera",
        "about": "Широкий угол обзора 110° и плавная камера.",
        "values": {
            "fov": 1.0,
            "smoothCamera": True,
            "bobView": False,
            "renderDistance": 12,
        },
    },
    {
        "id": "vanilla",
        "name": "Чистый ванилл",
        "tag": "default",
        "about": "Возвращает настройки графики к заводским значениям 1.12.2.",
        "values": {
            "renderDistance": 8,
            "mipmapLevels": 4,
            "particles": 0,
            "renderClouds": True,
            "fancyGraphics": True,
            "ao": True,
            "useVbo": True,
            "maxFps": 120,
            "gamma": 0.5,
            "fov": 0.0,
            "smoothCamera": False,
            "bobView": True,
            "mouseSensitivity": 0.5,
            "guiScale": 0,
        },
    },
]

BY_ID = {p["id"]: p for p in PRESETS}


def as_json() -> List[Dict[str, Any]]:
    return [
        {"id": p["id"], "name": p["name"], "tag": p["tag"], "about": p["about"],
         "values": p["values"]}
        for p in PRESETS
    ]


def jvm_args(gc: str, max_memory_mb: int = 4096, extra: str = "") -> str:
    """Собирает строку javaArgs для launcher_profiles.json."""
    extra = (extra or "").strip()
    parts = [f"-Xms{max_memory_mb // 2}M", f"-Xmx{max_memory_mb}M"]
    if gc == "aikar":
        parts += AIIKAR_FLAGS
    elif gc == "g1":
        parts += SIMPLE_G1_FLAGS
    elif gc == "none":
        pass
    else:
        raise ValueError(f"unknown gc mode: {gc}")
    if extra:
        parts.append(extra)
    return " ".join(parts)
