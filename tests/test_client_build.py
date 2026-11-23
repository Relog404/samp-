#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты сборки клиента: манифест, сборка jar, статическая проверка."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_client  # noqa: E402
import verify_client  # noqa: E402

MODULE = ROOT / "ci" / "out" / "relogic-module.jar"
DIST = ROOT / "dist" / "RELOG-IC-4.9.1-1.12.2.jar"
BASE = ROOT / "Impact-4.9.1-1.12.2.jar"


class ManifestTest(unittest.TestCase):
    def test_lines_fit_manifest_limit(self):
        value = ", ".join(["mixins.capi.json", "mixins.impact.json",
                           "mixins.baritone.json", "mixins.relogic.json"])
        data = build_client.wrap_manifest_value("MixinConfigs", value)
        for line in data.split(b"\r\n"):
            self.assertLessEqual(len(line) + 2, 72, line)

    def test_all_configs_survive_wrapping(self):
        value = ", ".join(["mixins.capi.json", "mixins.impact.json",
                           "mixins.baritone.json", "mixins.relogic.json"])
        data = build_client.wrap_manifest_value("MixinConfigs", value)
        flat = data.replace(b"\r\n ", b"").decode("utf-8")
        self.assertTrue(flat.startswith("MixinConfigs: "))
        self.assertEqual(flat.split(": ", 1)[1], value)

    def test_existing_attributes_kept(self):
        manifest = (b"Manifest-Version: 1.0\r\n"
                    b"MixinConfigs: mixins.capi.json, mixins.impact.json\r\n"
                    b"TweakClass: org.spongepowered.asm.launch.MixinTweaker\r\n\r\n")
        out = build_client.build_manifest(manifest, ["mixins.relogic.json"]).decode("utf-8")
        self.assertIn("TweakClass: org.spongepowered.asm.launch.MixinTweaker", out)
        self.assertIn("mixins.capi.json", out)
        self.assertIn("mixins.relogic.json", out)

    def test_no_duplicate_config(self):
        manifest = (b"Manifest-Version: 1.0\r\n"
                    b"MixinConfigs: mixins.relogic.json\r\n\r\n")
        out = build_client.build_manifest(manifest, ["mixins.relogic.json"]).decode("utf-8")
        self.assertEqual(out.count("mixins.relogic.json"), 1)


class ModuleTest(unittest.TestCase):
    def test_module_has_config_and_mixins(self):
        if not MODULE.exists():
            self.skipTest("module jar отсутствует (собирается в CI)")
        with zipfile.ZipFile(MODULE) as jar:
            config = json.loads(jar.read("mixins.relogic.json").decode("utf-8"))
            for name in config["client"]:
                path = "%s/%s.class" % (config["package"].replace(".", "/"), name)
                self.assertIn(path, jar.namelist())
            self.assertIn("RelogicClient.class", jar.namelist())

    def test_module_has_no_notch_references(self):
        """After the runtime crash we must never link against obfuscated names."""
        if not MODULE.exists():
            self.skipTest("module jar отсутствует (собирается в CI)")
        with zipfile.ZipFile(MODULE) as jar:
            refs = verify_client.parse_class(jar.read("RelogicClient.class"))
        notch = {"bib", "blk", "blr", "biq", "bir", "bip", "bit", "bja", "bid", "bhy"}
        self.assertFalse(notch & refs, "module still references notch classes: %s" % (notch & refs))
        self.assertIn("org/lwjgl/opengl/GL11", refs)

    def test_module_uses_srg_names(self):
        if not MODULE.exists():
            self.skipTest("module jar отсутствует (собирается в CI)")
        with zipfile.ZipFile(MODULE) as jar:
            names = verify_client.class_strings(jar.read("RelogicClient.class"))
        for name in ("net.minecraft.client.Minecraft", "func_71410_x",
                     "field_71466_p", "func_73863_a", "func_74303_b"):
            self.assertIn(name, names)
        for name in names:
            self.assertTrue(name.startswith(("net.minecraft.", "func_", "field_")), name)

    def test_mixin_targets_declared(self):
        if not MODULE.exists():
            self.skipTest("module jar отсутствует (собирается в CI)")
        with zipfile.ZipFile(MODULE) as jar:
            config = json.loads(jar.read("mixins.relogic.json").decode("utf-8"))
        for name in config["client"]:
            self.assertIn(name, verify_client.TARGETS)


class AssembledClientTest(unittest.TestCase):
    def test_dist_jar_verifies(self):
        if not DIST.exists() or not BASE.exists():
            self.skipTest("dist jar отсутствует")
        self.assertEqual(verify_client.main(["verify_client.py", str(DIST)]), 0)

    def test_dist_has_module_classes(self):
        if not DIST.exists():
            self.skipTest("dist jar отсутствует")
        with zipfile.ZipFile(DIST) as jar:
            names = jar.namelist()
            self.assertIn("RelogicClient.class", names)
            self.assertIn("mixins.relogic.json", names)
            self.assertIn("relogic/mixin/MixinGuiMainMenu.class", names)

    def test_dist_manifest_lists_module_config(self):
        if not DIST.exists():
            self.skipTest("dist jar отсутствует")
        with zipfile.ZipFile(DIST) as jar:
            manifest = jar.read("META-INF/MANIFEST.MF").decode("utf-8")
        flat = manifest.replace("\r\n ", "").replace("\r\n", "\n")
        self.assertIn("mixins.relogic.json", flat)
        self.assertIn("MixinTweaker", flat)


if __name__ == "__main__":
    unittest.main()
