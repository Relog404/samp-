#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vanilla_patch.py — пересборка Impact 4.9.1 (1.12.2) в "ванильный" вид.

Что делает:
  * выкидывает из mixins.impact.json кастомные экраны/меню/HUD клиента,
    чтобы игра рисовала обычный майнкрафтовский интерфейс;
  * вычищает брендинг из ресурсов (credits.json, changelog.md);
  * подменяет иконки окна на нейтральные;
  * отключает логи из log4j2.xml, который лежит внутри jar;
  * ставит всем записям одинаковую дату, чтобы по mtime не было видно,
    когда и из чего jar собирался;
  * пишет новый jar с нейтральным именем.

Классы/байткод НЕ трогаются: мод остаётся рабочим, меняется только
то, что видно глазами (экраны) и метаданные.

Использование:
    python3 tools/vanilla_patch.py Impact-4.9.1-1.12.2.jar dist/1.12.2.jar
    python3 tools/vanilla_patch.py in.jar out.jar --strip-all-screens
"""

from __future__ import annotations

import argparse
import io
import json
import os
import struct
import sys
import zlib
import zipfile
from datetime import datetime

# --------------------------------------------------------------------------
# что вырезаем из mixins.impact.json
# --------------------------------------------------------------------------

# Кастомное главное меню, кнопка в меню паузы, надпись версии в F3,
# и весь HUD/watermark/чат-оверлей клиента -> остаётся ванильный вид.
BRANDING_MIXINS = [
    "gui.MixinGuiMainMenu",     # своя главная менюшка с логотипом
    "gui.MixinGuiIngameMenu",   # кнопка клиента в меню паузы
    "MixinGuiOverlayDebug",     # "Impact 4.9.1" в F3
    "gui.MixinGuiIngame",       # HUD: watermark, arraylist, чат-оверлей
]

# Остальные кастомные экраны клиента (нужны, только если хочется
# полностью ванильный UI: ClickGUI, шалкеры, экран кика и т.п.).
EXTRA_SCREEN_MIXINS = [
    "gui.MixinGuiScreen",       # ClickGUI и прочие свои экраны
    "gui.MixinGuiChat",         # отрисовка своего чата
    "gui.MixinGuiChest",        # свой экран сундука (peek в шалкер)
    "gui.MixinGuiCustomizeSkin",
    "gui.MixinGuiDisconnect",   # свой экран дисконнекта
    "gui.MixinGuiGameOver",
]

FIXED_DATE = (2019, 4, 1, 0, 0, 0)  # одинаковая дата у всех записей

LOG4J_OFF = b"""<?xml version="1.0" encoding="UTF-8"?>
<!-- rewritten: no appenders, logging disabled -->
<Configuration status="OFF" packages="net.minecraft,com.mojang">
    <Loggers>
        <Root level="off"/>
    </Loggers>
</Configuration>
"""


# --------------------------------------------------------------------------
# нейтральная иконка окна (без логотипа)
# --------------------------------------------------------------------------

def _png(width: int, height: int, pixels) -> bytes:
    """Минимальный PNG-энкодер: pixels(x, y) -> (r, g, b, a)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        for x in range(width):
            raw.extend(pixels(x, y))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _icon(size: int) -> bytes:
    """Простая 'травяная' иконка, похожая на стандартную иконку Minecraft."""

    def px(x: int, y: int):
        top = size * 0.32
        if y < top:
            # зелёная "трава", чуть шумная
            n = (x * 7 + y * 13) % 11
            g = 120 + n * 4
            return (55 + n * 2, min(g, 190), 40 + n * 2, 255)
        # земля
        n = ((x * 5) ^ (y * 3)) % 13
        base = 120 + n * 3
        return (base, 88 + n * 2, 55 + n, 255)

    return _png(size, size, px)


# --------------------------------------------------------------------------
# патч
# --------------------------------------------------------------------------

def build_mixin_config(raw: bytes, remove: set[str], verbose: bool) -> bytes:
    cfg = json.loads(raw.decode("utf-8"))
    client = cfg.get("client", [])
    kept, dropped = [], []
    for entry in client:
        if entry in remove:
            dropped.append(entry)
        else:
            kept.append(entry)
    cfg["client"] = kept
    cfg["verbose"] = False
    if verbose:
        print(f"  mixin entries removed ({len(dropped)}): " + ", ".join(dropped))
    return json.dumps(cfg, indent=2).encode("utf-8")


def patch(src: str, dst: str, strip_all_screens: bool = False, verbose: bool = True) -> None:
    remove = set(BRANDING_MIXINS)
    if strip_all_screens:
        remove |= set(EXTRA_SCREEN_MIXINS)

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
        dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zout:
        for info in zin.infolist():
            name = info.filename
            data = zin.read(name)

            if name == "mixins.impact.json":
                data = build_mixin_config(data, remove, verbose)
            elif name == "log4j2.xml":
                data = LOG4J_OFF
            elif name == "assets/minecraft/impact/data/credits.json":
                data = b"{}\n"
            elif name == "assets/minecraft/impact/data/changelog.md":
                data = b""
            elif name == "welcome.md":
                data = b""
            elif name.startswith("icons/") and name.endswith(".png"):
                size = int(os.path.basename(name).split(".")[0])
                data = _icon(size)
            elif name == "META-INF/MANIFEST.MF":
                data = fix_manifest(data)
            elif name.endswith("/"):
                pass  # каталоги копируем как есть

            zi = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            # в оригинале права не заданы (external_attr == 0); zipfile сам
            # подставляет 0600, поэтому выставляем явные 0644/0755
            if name.endswith("/"):
                zi.external_attr = (0o40755 << 16) | 0x10
            else:
                zi.external_attr = 0o100644 << 16
            zout.writestr(zi, data)

    if verbose:
        print(f"  written: {dst} ({os.path.getsize(dst)/1048576:.1f} MiB)")


def fix_manifest(raw: bytes) -> bytes:
    """Убирает из MANIFEST всё, кроме необходимых атрибутов запуска."""
    wanted = ("Manifest-Version", "MixinConfigs", "TweakClass")
    lines = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        key = line.split(":", 1)[0]
        if key in wanted:
            lines.append(line)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vanilla-reskin patcher for the Impact jar")
    ap.add_argument("source", help="original Impact-4.9.1-1.12.2.jar")
    ap.add_argument("output", help="path to the patched jar")
    ap.add_argument(
        "--strip-all-screens",
        action="store_true",
        help="также отключить ClickGUI и остальные кастомные экраны клиента",
    )
    args = ap.parse_args(argv)

    for required in ("mixins.impact.json", "log4j2.xml"):
        with zipfile.ZipFile(args.source) as z:
            if required not in z.namelist():
                print(f"error: {args.source} does not look like the Impact jar "
                      f"({required} missing)", file=sys.stderr)
                return 2

    print(f"patching {args.source} -> {args.output}")
    patch(args.source, args.output, strip_all_screens=args.strip_all_screens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
