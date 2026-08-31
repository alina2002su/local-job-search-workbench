#!/usr/bin/env python3
"""Verify generated files and optionally the running local service."""

from __future__ import annotations

import argparse
import ast
import json
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--check-running", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    settings_path = root / "config" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    required = [
        root / "app/main.py",
        root / "browser-extension/manifest.json",
        root / "requirements.txt",
        root / "Start_Workbench.command",
        root / "Stop_Workbench.command",
        Path(settings["jd_directory"]),
        Path(settings["resume_directory"]),
    ]
    missing = [str(path) for path in required if not path.exists()]
    compile_errors = []
    for path in (root / "app").rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            compile_errors.append(f"{path}: {exc}")

    health = None
    if args.check_running:
        url = f'http://{settings["server_host"]}:{settings["server_port"]}/api/health'
        with urllib.request.urlopen(url, timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))

    report = {"missing": missing, "compile_errors": compile_errors, "health": health}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing and not compile_errors and (not args.check_running or health and health.get("status") == "ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
