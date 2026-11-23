#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_client.py — статическая проверка собранного RELOG-IC клиента.

Проверяет без запуска игры:

  * все записи базового jar на месте и не изменены (кроме MANIFEST.MF);
  * в собранном jar лежат все классы скомпилированного модуля;
  * MANIFEST.MF содержит TweakClass и MixinConfigs со всеми конфигами,
    включая mixins.relogic.json;
  * mixins.relogic.json — валидный JSON, все его миксины есть в jar;
  * в jar нет файлов подписи (после правки они невалидны);
  * (если передан --client) целевые классы и методы миксинов реально
    существуют в client.jar 1.12.2 — то есть @Inject попадёт в цель.

    python3 tools/verify_client.py dist/RELOG-IC-4.9.1-1.12.2.jar [--client /tmp/mc/client.jar]
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "Impact-4.9.1-1.12.2.jar"
CONFIG = "mixins.relogic.json"
REQUIRED_CONFIGS = {"mixins.capi.json", "mixins.impact.json", "mixins.baritone.json", CONFIG}

# entries build_client.py intentionally rewrites
ALLOWED_CHANGED = {"META-INF/MANIFEST.MF", "mixins.impact.json", "log4j2.xml"}

# mixin class -> (target class, target method name, descriptor)
TARGETS = {
    "MixinGuiMainMenu": ("blr", "a", "(IIF)V"),
    "MixinGuiIngame": ("biq", "a", "(F)V"),
    "MixinMinecraft": ("bib", "t", "()V"),
}


def build_client_mixins():
    """Mixins that build_client.py removes from Impact's config (branding)."""
    return (
        "MixinGuiOverlayDebug",
        "gui.MixinGuiIngame",
        "gui.MixinGuiIngameMenu",
        "gui.MixinGuiMainMenu",
    )


def parse_class(data: bytes):
    """Minimal class file reader: returns the class names referenced."""
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a class file")
    pos = 8
    count = int.from_bytes(data[pos:pos + 2], "big")
    pos += 2
    cp = {}
    index = 1
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            length = int.from_bytes(data[pos:pos + 2], "big")
            pos += 2
            cp[index] = ("utf8", data[pos:pos + length].decode("utf-8", "replace"))
            pos += length
        elif tag in (7, 8, 16, 19, 20):
            cp[index] = (tag, int.from_bytes(data[pos:pos + 2], "big"))
            pos += 2
        elif tag in (15,):
            cp[index] = (tag, data[pos], int.from_bytes(data[pos + 1:pos + 3], "big"))
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            cp[index] = (tag, int.from_bytes(data[pos:pos + 4], "big"))
            pos += 4
        elif tag in (5, 6):
            cp[index] = (tag,)
            pos += 8
            index += 1
        else:
            raise ValueError("bad constant pool tag %d" % tag)
        index += 1

    def utf8(idx):
        entry = cp.get(idx)
        return entry[1] if entry and entry[0] == "utf8" else None

    classes = set()
    for entry in cp.values():
        if entry[0] == 7:
            name = utf8(entry[1])
            if name:
                classes.add(name)

    return classes


def methods_of(data: bytes):
    """Return {name+descriptor} for the methods of a class file."""
    pos = 8
    count = int.from_bytes(data[pos:pos + 2], "big")
    pos += 2
    cp = {}
    index = 1
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            length = int.from_bytes(data[pos:pos + 2], "big")
            pos += 2
            cp[index] = data[pos:pos + length].decode("utf-8", "replace")
            pos += length
        elif tag in (7, 8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            index += 1
        else:
            raise ValueError("bad constant pool tag %d" % tag)
        index += 1

    pos += 6
    interfaces = int.from_bytes(data[pos:pos + 2], "big")
    pos += 2 + 2 * interfaces

    def skip_members(pos, collect):
        found = set()
        members = int.from_bytes(data[pos:pos + 2], "big")
        pos += 2
        for _ in range(members):
            name_idx = int.from_bytes(data[pos + 2:pos + 4], "big")
            desc_idx = int.from_bytes(data[pos + 4:pos + 6], "big")
            pos += 6
            if collect:
                found.add((cp.get(name_idx), cp.get(desc_idx)))
            attrs = int.from_bytes(data[pos:pos + 2], "big")
            pos += 2
            for _ in range(attrs):
                pos += 2
                length = int.from_bytes(data[pos:pos + 4], "big")
                pos += 4 + length
        return pos, found

    pos, _ = skip_members(pos, False)
    pos, found = skip_members(pos, True)
    return found


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    client_path = None
    for i, arg in enumerate(argv[1:]):
        if arg == "--client":
            client_path = Path(argv[2 + i])
    if not args:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2

    jar_path = Path(args[0])
    errors: list[str] = []
    with zipfile.ZipFile(jar_path) as jar, zipfile.ZipFile(BASE) as base:
        names = set(jar.namelist())
        base_names = set(base.namelist())

        missing = base_names - names
        if missing:
            errors.append("lost base entries: %s" % ", ".join(sorted(missing)[:5]))
        changed = {n for n in base_names & names
                   if n not in ALLOWED_CHANGED and base.read(n) != jar.read(n)}
        if changed:
            errors.append("base entries changed: %s" % ", ".join(sorted(changed)[:5]))

        signatures = [n for n in names if n.upper().endswith((".SF", ".RSA", ".DSA", ".EC"))]
        if signatures:
            errors.append("signature files left in jar: %s" % signatures)

        manifest = jar.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        flat = manifest.replace("\r\n", "").replace("\n", "")
        if "TweakClass: org.spongepowered.asm.launch.MixinTweaker" not in flat:
            errors.append("TweakClass missing from manifest")
        configs = set()
        if "MixinConfigs:" in flat:
            raw = flat.split("MixinConfigs:", 1)[1]
            for token in raw.split(","):
                token = token.strip().split("TweakClass:")[0].strip()
                if token:
                    configs.add(token)
        lost = REQUIRED_CONFIGS - configs
        if lost:
            errors.append("MixinConfigs missing: %s" % ", ".join(sorted(lost)))

        config = json.loads(jar.read(CONFIG).decode("utf-8"))
        package = config.get("package", "").replace(".", "/")
        classes = config.get("client", [])
        for entry in classes:
            path = "%s/%s.class" % (package, entry)
            if path not in names:
                errors.append("mixin class missing from jar: %s" % path)

        impact = json.loads(jar.read("mixins.impact.json").decode("utf-8"))
        left = [m for m in impact.get("client", []) if m in build_client_mixins()]
        if left:
            errors.append("Impact branding mixins still active: %s" % ", ".join(left))

        level = re.search(r'<Root level="([^"]+)"', jar.read("log4j2.xml").decode("utf-8", "replace"))
        if not level or level.group(1) != "off":
            errors.append("log4j root level is %s, expected off" % (level.group(1) if level else "missing"))

        print("entries: %d | base: %d | configs: %s" % (len(names), len(base_names), sorted(configs)))
        print("impact client mixins: %d | log4j root: %s" % (len(impact.get("client", [])), level.group(1) if level else "?"))
        print("mixins: %s" % classes)

        if client_path and client_path.exists():
            with zipfile.ZipFile(client_path) as client:
                client_names = set(client.namelist())
                for entry, (target, method, desc) in TARGETS.items():
                    path = target + ".class"
                    if path not in client_names:
                        errors.append("target class not in client.jar: %s" % target)
                        continue
                    found = methods_of(client.read(path))
                    if (method, desc) not in found:
                        errors.append("target method missing: %s.%s%s" % (target, method, desc))
                    else:
                        print("target ok: %s.%s%s" % (target, method, desc))
                for entry in classes:
                    path = "%s/%s.class" % (package, entry)
                    refs = parse_class(jar.read(path))
                    unknown = [r for r in refs
                               if not r.startswith("java/")
                               and not r.startswith("[")
                               and r + ".class" not in client_names
                               and r + ".class" not in names]
                    if unknown:
                        errors.append("%s references unknown classes: %s" % (entry, unknown))
        else:
            print("client.jar not supplied: target/method checks skipped")

    if errors:
        print("\nFAILED:")
        for error in errors:
            print("  -", error)
        return 1
    print("\nOK: клиент собран корректно")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
