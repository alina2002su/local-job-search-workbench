#!/usr/bin/env python3
"""Create a private local job-search workbench from the bundled template."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path.home() / "LocalJobWorkbench"))
    parser.add_argument("--product-name", default="我的求职工作台")
    parser.add_argument("--season-label", default="求职管理")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--feishu-base-token", default="")
    parser.add_argument("--feishu-table-id", default="")
    parser.add_argument("--feishu-view-id", default="")
    parser.add_argument("--lark-cli", default="")
    parser.add_argument("--install-deps", action="store_true")
    return parser.parse_args()


def write_start_scripts(root: Path, host: str, port: int) -> None:
    start = f'''#!/bin/sh
set -eu
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$PROJECT_DIR"
command -v python3 >/dev/null 2>&1 || {{ echo "Python 3 is required"; exit 1; }}
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
if [ -f data/server.pid ] && kill -0 "$(cat data/server.pid)" 2>/dev/null; then
  URL="http://{host}:{port}"
else
  nohup .venv/bin/python -m uvicorn app.main:app --host {host} --port {port} > data/logs/server.log 2>&1 &
  echo $! > data/server.pid
  sleep 2
  URL="http://{host}:{port}"
fi
if command -v open >/dev/null 2>&1; then open "$URL"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; else echo "$URL"; fi
'''
    stop = '''#!/bin/sh
set -eu
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/data/server.pid"
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then kill "$PID"; fi
  rm -f "$PID_FILE"
fi
'''
    for name, content in (("Start_Workbench.command", start), ("Stop_Workbench.command", stop)):
        path = root / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty directory: {root}")

    template = Path(__file__).resolve().parents[1] / "assets" / "project-template"
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, root, dirs_exist_ok=True)
    for relative in ("JD库", "简历库", "data/backups", "data/logs", "config"):
        (root / relative).mkdir(parents=True, exist_ok=True)

    settings = {
        "product_name": args.product_name,
        "season_label": args.season_label,
        "project_root": str(root),
        "jd_directory": str(root / "JD库"),
        "jd_clipper_directory": str(root / "JD库"),
        "resume_directory": str(root / "简历库"),
        "database": str(root / "data" / "workbench.db"),
        "backup_directory": str(root / "data" / "backups"),
        "log_directory": str(root / "data" / "logs"),
        "timezone": args.timezone,
        "server_host": args.host,
        "server_port": args.port,
        "feishu": {
            "base_name": "岗位池",
            "base_token": args.feishu_base_token,
            "table_name": "岗位池",
            "table_id": args.feishu_table_id,
            "view_name": "全部岗位",
            "view_id": args.feishu_view_id,
            "cli_path": args.lark_cli,
        },
    }
    (root / "config" / "settings.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    manifest_path = root / "browser-extension" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["host_permissions"] = [f"http://{args.host}:{args.port}/*"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    utils_path = root / "browser-extension" / "utils.js"
    utils_path.write_text(
        utils_path.read_text(encoding="utf-8").replace("http://127.0.0.1:8765", f"http://{args.host}:{args.port}"),
        encoding="utf-8",
    )
    write_start_scripts(root, args.host, args.port)

    if args.install_deps:
        subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], check=True)
        python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(root / "requirements.txt")], check=True)

    print(json.dumps({
        "project_root": str(root),
        "workbench_url": f"http://{args.host}:{args.port}",
        "extension_directory": str(root / "browser-extension"),
        "jd_directory": str(root / "JD库"),
        "resume_directory": str(root / "简历库"),
        "settings": str(root / "config" / "settings.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
