# -*- coding: utf-8 -*-
"""Тесты ядра панели RELOG-IC (без сети и без Minecraft).

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT))

from core import jvm, options, presets  # noqa: E402
from tools import vanilla_patch, verify_jar  # noqa: E402


class OptionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "options.txt"
        self.path.write_text(
            "version:1343\nrenderDistance:8\nfov:0.0\nlang:ru_ru\nmysteryModKey:42\n",
            encoding="utf-8",
        )

    def test_unknown_keys_survive(self) -> None:
        opts = options.OptionsFile.load(self.path)
        text, changed, _ = opts.render({"renderDistance": 12})
        self.assertIn("mysteryModKey:42", text)
        self.assertIn("lang:ru_ru", text)
        self.assertEqual(changed["renderDistance"], {"old": 8, "new": 12})

    def test_values_are_clamped(self) -> None:
        opts = options.OptionsFile.load(self.path)
        text, changed, _ = opts.render({"renderDistance": 999, "fov": -3})
        self.assertIn("renderDistance:32", text)
        self.assertIn("fov:0", text)
        self.assertEqual(changed["renderDistance"]["new"], 32)

    def test_apply_creates_backup(self) -> None:
        result = options.apply_updates(self.path, {"renderDistance": 6})
        self.assertEqual(result["count"], 1)
        self.assertTrue(Path(result["backup"]).exists())
        self.assertIn("renderDistance:6", self.path.read_text(encoding="utf-8"))

    def test_backup_folders_do_not_collide(self) -> None:
        options.apply_updates(self.path, {"renderDistance": 5})
        options.apply_updates(self.path, {"renderDistance": 4})
        backups = list((self.path.parent / ".relogic_backups").iterdir())
        self.assertEqual(len(backups), 2)

    def test_missing_file_is_created(self) -> None:
        target = Path(self.tmp.name) / "new" / "options.txt"
        result = options.apply_updates(target, {"maxFps": 144})
        self.assertTrue(target.exists())
        self.assertIsNone(result["backup"])
        self.assertIn("maxFps:144", target.read_text(encoding="utf-8"))

    def test_str_enum(self) -> None:
        self.assertEqual(options.coerce("mainHand", "left"), "left")
        self.assertEqual(options.coerce("mainHand", "nonsense"), "left")


class PresetsTest(unittest.TestCase):
    def test_every_preset_uses_known_keys(self) -> None:
        for preset in presets.PRESETS:
            unknown = set(preset["values"]) - set(options.SPEC)
            self.assertFalse(unknown, f"{preset['id']}: {unknown}")

    def test_preset_values_fit_spec(self) -> None:
        for preset in presets.PRESETS:
            for key, value in preset["values"].items():
                spec = options.SPEC[key]
                if spec["type"] == "int":
                    self.assertGreaterEqual(value, spec["min"], key)
                    self.assertLessEqual(value, spec["max"], key)

    def test_jvm_args(self) -> None:
        args = presets.jvm_args("aikar", 4096)
        self.assertIn("-Xmx4096M", args)
        self.assertIn("-Xms2048M", args)
        self.assertIn("-XX:+UseG1GC", args)
        self.assertIn("-XX:+AlwaysPreTouch", args)
        with self.assertRaises(ValueError):
            presets.jvm_args("nope", 2048)


class JvmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "launcher_profiles.json").write_text(json.dumps({
            "profiles": {
                "relogic": {"name": "RELOG-IC", "javaArgs": "-Xmx2G"},
                "other": {"name": "1.12.2", "javaArgs": ""},
            },
            "selectedProfile": "relogic",
        }), encoding="utf-8")

    def test_list(self) -> None:
        profiles = jvm.list_profiles(self.dir)
        self.assertEqual(len(profiles), 2)
        self.assertTrue(profiles[0]["selected"])

    def test_apply_by_name_and_backup(self) -> None:
        result = jvm.apply_java_args(self.dir, "RELOG-IC", "-Xmx6G")
        self.assertEqual(result["old"], "-Xmx2G")
        self.assertTrue(Path(result["backup"]).exists())
        data = json.loads((self.dir / "launcher_profiles.json").read_text(encoding="utf-8"))
        self.assertEqual(data["profiles"]["relogic"]["javaArgs"], "-Xmx6G")

    def test_unknown_profile(self) -> None:
        with self.assertRaises(KeyError):
            jvm.apply_java_args(self.dir, "missing", "-Xmx1G")


class PatcherTest(unittest.TestCase):
    """Собирает маленький фейковый jar и проверяет патч+верификацию."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "fake.jar"
        mixins = {
            "required": True,
            "package": "me/zero/clarinet/hook/mixin",
            "client": ["MixinBlock", "gui.MixinGuiMainMenu", "gui.MixinGuiIngame"],
        }
        with zipfile.ZipFile(self.src, "w") as z:
            z.writestr("mixins.impact.json", json.dumps(mixins))
            z.writestr("log4j2.xml", "<Configuration><Loggers><Root level='info'/></Loggers></Configuration>")
            z.writestr("META-INF/MANIFEST.MF",
                       "Manifest-Version: 1.0\r\nTweakClass: org.spongepowered.asm.launch.MixinTweaker\r\n"
                       "MixinConfigs: mixins.impact.json\r\n\r\n")
            for cls in ("MixinBlock", "gui/MixinGuiMainMenu", "gui/MixinGuiIngame"):
                z.writestr(f"me/zero/clarinet/hook/mixin/{cls}.class", b"\xca\xfe\xba\xbe")

    def test_patch_and_verify(self) -> None:
        out = self.dir / "out.jar"
        vanilla_patch.patch(str(self.src), str(out), verbose=False)
        with zipfile.ZipFile(out) as z:
            cfg = json.loads(z.read("mixins.impact.json"))
            self.assertEqual(cfg["client"], ["MixinBlock"])
            self.assertIn('level="off"', z.read("log4j2.xml").decode())
        code = verify_jar.main(["verify_jar.py", str(self.src), str(out)])
        self.assertEqual(code, 0)

    def test_verify_catches_broken_config(self) -> None:
        out = self.dir / "broken.jar"
        vanilla_patch.patch(str(self.src), str(out), verbose=False)
        # ломаем: добавляем миксин, класса которого нет
        with zipfile.ZipFile(out) as z:
            data = {n: z.read(n) for n in z.namelist()}
        cfg = json.loads(data["mixins.impact.json"])
        cfg["client"].append("gui.MixinNope")
        data["mixins.impact.json"] = json.dumps(cfg).encode()
        with zipfile.ZipFile(out, "w") as z:
            for name, payload in data.items():
                z.writestr(name, payload)
        self.assertEqual(verify_jar.main(["verify_jar.py", str(self.src), str(out)]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
