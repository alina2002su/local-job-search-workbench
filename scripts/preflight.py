#!/usr/bin/env python3
"""Check whether the local machine is ready for the workbench."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path.home() / "LocalJobWorkbench"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    target = Path(args.project_root).expanduser()
    port_free = False
    sock = socket.socket()
    try:
        sock.bind((args.host, args.port))
        port_free = True
    except OSError:
        pass
    finally:
        sock.close()

    report = {
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 9),
        "project_parent_exists": target.parent.exists(),
        "project_target_empty": not target.exists() or not any(target.iterdir()),
        "port_free": port_free,
        "chrome_detected": bool(shutil.which("google-chrome") or shutil.which("chromium") or Path("/Applications/Google Chrome.app").exists()),
        "lark_cli": shutil.which("lark-cli") or "",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["python_supported"] and report["project_parent_exists"] and report["project_target_empty"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
