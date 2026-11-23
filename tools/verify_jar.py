#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_jar.py — проверка результата vanilla_patch.py.

Проверяет:
  * список записей в патченном jar совпадает с оригиналом;
  * изменены только ожидаемые записи;
  * mixins.impact.json — валидный JSON, и все указанные в нём миксины
    реально лежат в jar (удалить лишнее и оставить битую ссылку нельзя);
  * log4j2.xml — валидный XML и логирование выключено.

    python3 tools/verify_jar.py Impact-4.9.1-1.12.2.jar dist/1.12.2.jar
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
import zipfile

EXPECTED_CHANGED = {
    "mixins.impact.json",
    "log4j2.xml",
    "META-INF/MANIFEST.MF",
    "assets/minecraft/impact/data/credits.json",
    "assets/minecraft/impact/data/changelog.md",
    "welcome.md",
    "icons/16.png",
    "icons/32.png",
    "icons/64.png",
    "icons/128.png",
    "icons/256.png",
    "icons/512.png",
}


def mixin_class_path(package: str, entry: str) -> str:
    return package.replace(".", "/") + "/" + entry.replace(".", "/") + ".class"


def main(argv) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    src, dst = argv[1], argv[2]
    errors: list[str] = []

    with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
        if a.namelist() != b.namelist():
            errors.append("entry list differs from the original jar")
        changed = {n for n in a.namelist() if a.read(n) != b.read(n)}
        unexpected = changed - EXPECTED_CHANGED
        if unexpected:
            errors.append("unexpected entries changed: " + ", ".join(sorted(unexpected)))
        print("entries:", len(a.namelist()), "| changed:", len(changed))

        # mixin config
        cfg = json.loads(b.read("mixins.impact.json").decode("utf-8"))
        package = cfg["package"]
        missing = [e for e in cfg["client"]
                   if mixin_class_path(package, e) not in b.namelist()]
        if missing:
            errors.append("mixin classes missing from jar: " + ", ".join(missing))
        print("mixins kept:", len(cfg["client"]), "| username/branding mixins removed:",
              sorted({"gui.MixinGuiMainMenu", "gui.MixinGuiIngameMenu",
                      "MixinGuiOverlayDebug", "gui.MixinGuiIngame"} & set(cfg["client"])))

        # logging
        root = ET.fromstring(b.read("log4j2.xml"))
        levels = [e.get("level") for e in root.iter("Root")]
        if levels != ["off"]:
            errors.append(f"log4j Root level is {levels}, expected ['off']")
        print("log4j Root level:", levels)

        # manifest
        manifest = b.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        for key in ("TweakClass", "MixinConfigs"):
            if key not in manifest:
                errors.append(f"MANIFEST is missing {key}")
        print("manifest tweak:", "org.spongepowered.asm.launch.MixinTweaker"
              in manifest)

    if errors:
        print("\nFAILED:")
        for e in errors:
            print("  -", e)
        return 1

    print("\nOK: jar пересобран корректно, лишнего не тронуто")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
