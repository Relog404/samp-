#!/usr/bin/env python3
"""Assemble the RELOG-IC client jar from the Impact jar + a compiled module jar.

The module jar is produced by CI (``ci/out/relogic-module.jar``) by compiling
``src/mod/java`` against the real 1.12.2 client, LWJGL and Impact:

    javac -cp client.jar:/tmp/mc/*:Impact-...jar -d build/classes $(find src/mod/java -name '*.java')
    (cd build/classes && jar cf relogic-module.jar .)

This script then:
  * copies every module entry into the client jar (classes + mixins.relogic.json),
  * appends ``mixins.relogic.json`` to the ``MixinConfigs`` manifest attribute
    (the jar is loaded through ``TweakClass: MixinTweaker``),
  * drops stale signature files, because the jar is modified,
  * writes ``dist/RELOG-IC-<version>.jar``.

Usage:
    python3 tools/build_client.py [--module ci/out/relogic-module.jar] [--out dist/...]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_JAR = ROOT / "Impact-4.9.1-1.12.2.jar"
DEFAULT_MODULE = ROOT / "ci" / "out" / "relogic-module.jar"
DEFAULT_OUT = ROOT / "dist" / "RELOG-IC-4.9.1-1.12.2.jar"
CONFIG = "mixins.relogic.json"


def wrap_manifest_value(name: str, value: str, limit: int = 70) -> bytes:
    """Manifest lines stay <= 72 bytes; continuation lines start with one space."""
    head = "%s: " % name
    tokens = value.split(", ")
    lines = []
    current = ""
    budget = limit - len(head)
    for index, token in enumerate(tokens):
        piece = token + (", " if index < len(tokens) - 1 else "")
        if current and len(current) + len(piece) > budget:
            lines.append(current)
            current = piece
            budget = limit - 1
        else:
            current += piece
    lines.append(current)
    data = (head + lines[0]).encode("utf-8")
    for extra in lines[1:]:
        data += b"\r\n " + extra.encode("utf-8")
    return data


def build_manifest(existing: bytes, extra_configs) -> bytes:
    text = existing.decode("utf-8", "replace")
    fields = []
    current = None
    for raw in text.replace("\r\n", "\n").split("\n"):
        if not raw:
            continue
        if raw.startswith(" ") and current is not None:
            current[1] += raw[1:]
        else:
            key, _, value = raw.partition(": ")
            current = [key, value]
            fields.append(current)

    names = {k for k, _ in fields}
    out = bytearray()
    for key, value in fields:
        if key == "MixinConfigs":
            configs = [c.strip() for c in value.split(",") if c.strip()]
            for extra in extra_configs:
                if extra not in configs:
                    configs.append(extra)
            value = ", ".join(configs)
        out += wrap_manifest_value(key, value) + b"\r\n"
    if "MixinConfigs" not in names:
        out += wrap_manifest_value("MixinConfigs", ", ".join(extra_configs)) + b"\r\n"
    out += b"\r\n"
    return bytes(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE_JAR)
    parser.add_argument("--module", type=Path, default=DEFAULT_MODULE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if not args.base.exists():
        print("missing base jar: %s" % args.base, file=sys.stderr)
        return 2
    if not args.module.exists():
        print("missing compiled module: %s" % args.module, file=sys.stderr)
        print("compile it first (see README: 'Как собрать')", file=sys.stderr)
        return 2

    with zipfile.ZipFile(args.module) as mod:
        module_entries = {
            n: mod.read(n)
            for n in mod.namelist()
            if not n.endswith("/") and n != "META-INF/MANIFEST.MF"
        }

    config_name = CONFIG
    if config_name not in module_entries:
        print("module has no %s" % config_name, file=sys.stderr)
        return 2
    config = json.loads(module_entries[config_name].decode("utf-8"))
    for name in config.get("client", []):
        cls = "%s/%s.class" % (config["package"].replace(".", "/"), name)
        if cls not in module_entries:
            print("mixin class missing from module: %s" % cls, file=sys.stderr)
            return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.base) as base:
        manifest = build_manifest(base.read("META-INF/MANIFEST.MF"), [config_name])
        entries = []
        for info in base.infolist():
            name = info.filename
            if name == "META-INF/MANIFEST.MF":
                continue
            if name.upper().startswith("META-INF/") and name.upper().endswith((".SF", ".RSA", ".DSA", ".EC")):
                continue  # jar is modified -> signature would be invalid
            entries.append((name, info, base.read(name)))

    replaced = 0
    kept = []
    for name, info, data in entries:
        if name in module_entries:
            kept.append((name, info, module_entries[name]))
            replaced += 1
        else:
            kept.append((name, info, data))

    added = 0
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as out:
        info = zipfile.ZipInfo("META-INF/MANIFEST.MF", date_time=(2020, 11, 4, 15, 18, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(info, manifest)
        for name, info, data in kept:
            out.writestr(info, data)
        for name, data in sorted(module_entries.items()):
            if any(name == existing[0] for existing in kept):
                continue
            info = zipfile.ZipInfo(name, date_time=(2020, 11, 4, 15, 18, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, data)
            added += 1

    print("base  : %s" % args.base)
    print("module: %s (%d entries)" % (args.module, len(module_entries)))
    print("out   : %s" % args.out)
    print("replaced: %d, added: %d" % (replaced, added))
    print("MixinConfigs -> %s" % build_manifest(
        zipfile.ZipFile(args.out).read("META-INF/MANIFEST.MF"), []).decode("utf-8").replace("\r\n", "\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
