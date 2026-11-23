#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RELOG-IC Client — локальный сервер панели оптимизации.

Запуск:
    python3 app/server.py --port 8765 [--demo]

Панель открывается в браузере по адресу http://localhost:8765
Сервер ничего не отправляет в интернет: только чтение/запись файлов
Minecraft (options.txt, launcher_profiles.json) и патч jar клиента.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
STATIC_DIR = APP_ROOT / "static"
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from core import jvm, options, paths, presets  # noqa: E402

APP_NAME = "RELOG-IC"
APP_VERSION = "1.0.0"


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def minecraft_dir() -> Path:
    return paths.minecraft_dir()


def options_path(mc: Path) -> Path:
    return mc / "options.txt"


def handle_status(_payload: Dict[str, Any]) -> Dict[str, Any]:
    mc = minecraft_dir()
    jars = [str(p) for p in paths.jar_candidates()]
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "minecraftDir": str(mc),
        "exists": mc.exists(),
        "options": options_path(mc).exists(),
        "profiles": jvm.profiles_path(mc).exists(),
        "jars": jars,
        "defaultDir": str(paths.default_minecraft_dir()),
    }


def handle_set_dir(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = (payload.get("path") or "").strip()
    if not raw:
        raise ApiError("путь не указан")
    path = paths.set_minecraft_dir(raw)
    if not path.exists():
        # даём создать пустую папку, но говорим, что её не было
        return {"minecraftDir": str(path), "created": False, "warning": "папка не существует"}
    return {"minecraftDir": str(path), "created": True}


def handle_options_get(_payload: Dict[str, Any]) -> Dict[str, Any]:
    path = options_path(minecraft_dir())
    opts = options.OptionsFile.load(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "values": opts.known(),
        "spec": options.SPEC,
        "fallback": options.FALLBACK,
    }


def handle_options_apply(payload: Dict[str, Any]) -> Dict[str, Any]:
    values = payload.get("values") or {}
    if not isinstance(values, dict) or not values:
        raise ApiError("values пуст")
    unknown = [k for k in values if k not in options.SPEC]
    if unknown:
        raise ApiError("неизвестные параметры: " + ", ".join(unknown))
    return options.apply_updates(options_path(minecraft_dir()), values)


def handle_presets(_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"presets": presets.as_json()}


def handle_preset_apply(payload: Dict[str, Any]) -> Dict[str, Any]:
    preset_id = payload.get("id")
    preset = presets.BY_ID.get(preset_id)
    if preset is None:
        raise ApiError(f"неизвестный пресет: {preset_id}")
    result = options.apply_updates(options_path(minecraft_dir()), preset["values"])
    result["preset"] = {"id": preset["id"], "name": preset["name"]}
    return result


def handle_profiles(_payload: Dict[str, Any]) -> Dict[str, Any]:
    mc = minecraft_dir()
    try:
        return {"profiles": jvm.list_profiles(mc)}
    except FileNotFoundError:
        return {"profiles": [], "warning": "launcher_profiles.json не найден"}


def handle_jvm(payload: Dict[str, Any]) -> Dict[str, Any]:
    profile = payload.get("profile")
    if not profile:
        raise ApiError("профиль не выбран")
    gc = payload.get("gc", "aikar")
    try:
        max_memory = int(payload.get("maxMemoryMB", 4096))
    except (TypeError, ValueError):
        raise ApiError("maxMemoryMB должен быть числом")
    if not 512 <= max_memory <= 65536:
        raise ApiError("память должна быть в диапазоне 512..65536 МБ")
    args = presets.jvm_args(gc, max_memory, payload.get("extra", ""))
    return jvm.apply_java_args(minecraft_dir(), profile, args)


def handle_demo(_payload: Dict[str, Any]) -> Dict[str, Any]:
    demo = paths.ensure_demo()
    paths.set_minecraft_dir(str(demo))
    return {"minecraftDir": str(demo)}


def handle_jars(_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"jars": [str(p) for p in paths.jar_candidates()]}


def handle_jar_patch(payload: Dict[str, Any]) -> Dict[str, Any]:
    from tools import vanilla_patch  # локальный импорт: нужен только здесь

    source = Path((payload.get("source") or "").strip()).expanduser()
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    if not source.exists():
        raise ApiError(f"файл не найден: {source}")
    out_dir = PROJECT_ROOT / "dist"
    name = payload.get("name") or "1.12.2-relogic.jar"
    if not name.endswith(".jar"):
        name += ".jar"
    output = out_dir / name
    vanilla_patch.patch(str(source), str(output),
                        strip_all_screens=bool(payload.get("stripAllScreens")))
    return {
        "output": str(output),
        "size": output.stat().st_size,
        "stripAllScreens": bool(payload.get("stripAllScreens")),
    }


def handle_jar_verify(payload: Dict[str, Any]) -> Dict[str, Any]:
    import subprocess

    source = (payload.get("source") or "").strip()
    output = (payload.get("output") or "").strip()
    if not source or not output:
        raise ApiError("нужны source и output")
    if not Path(source).is_absolute():
        source = str(PROJECT_ROOT / source)
    if not Path(output).is_absolute():
        output = str(PROJECT_ROOT / output)
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "verify_jar.py"), source, output],
        capture_output=True, text=True, check=False,
    )
    return {"code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


ROUTES = {
    ("GET", "/api/status"): handle_status,
    ("POST", "/api/dir"): handle_set_dir,
    ("GET", "/api/options"): handle_options_get,
    ("POST", "/api/options"): handle_options_apply,
    ("GET", "/api/presets"): handle_presets,
    ("POST", "/api/preset"): handle_preset_apply,
    ("GET", "/api/profiles"): handle_profiles,
    ("POST", "/api/jvm"): handle_jvm,
    ("GET", "/api/jars"): handle_jars,
    ("POST", "/api/demo"): handle_demo,
    ("POST", "/api/jar/patch"): handle_jar_patch,
    ("POST", "/api/jar/verify"): handle_jar_verify,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "RELOG-IC/1.0"
    protocol_version = "HTTP/1.1"

    # --- утилиты ---------------------------------------------------------

    def _send(self, status: int, body: bytes, content_type: str,
              extra_headers: Dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(f"некорректный JSON: {exc}")
        if not isinstance(data, dict):
            raise ApiError("ожидался JSON-объект")
        return data

    def _static(self, path: str) -> None:
        rel = path.lstrip("/")
        if rel in ("", "/"):
            rel = "index.html"
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._json(404, {"error": "not found"})
            return
        ctype, _ = mimetypes.guess_type(str(target))
        self._send(200, target.read_bytes(), ctype or "application/octet-stream")

    # --- HTTP ------------------------------------------------------------

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        route = ROUTES.get((method, parsed.path))
        try:
            if route is None:
                if parsed.path.startswith("/api/"):
                    raise ApiError(f"нет метода {method} {parsed.path}", status=404)
                self._static(parsed.path)
                return
            payload = self._read_json() if method == "POST" else {}
            self._json(200, {"ok": True, **route(payload)})
        except ApiError as exc:
            self._json(exc.status, {"ok": False, "error": str(exc)})
        except FileNotFoundError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except KeyError as exc:
            self._json(400, {"ok": False, "error": f"не найдено: {exc}"})
        except Exception as exc:  # noqa: BLE001 - панель не должна падать
            traceback.print_exc()
            self._json(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("RELOGIC_QUIET"):
            return
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="RELOG-IC Client panel")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--demo", action="store_true",
                        help="использовать демо-папку Minecraft вместо реальной")
    args = parser.parse_args(argv)

    if args.demo:
        demo = paths.ensure_demo()
        paths.set_minecraft_dir(str(demo))

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"{APP_NAME} client panel: http://{args.host}:{args.port}")
    print(f"minecraft dir: {minecraft_dir()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
