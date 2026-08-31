#!/usr/bin/env python3
"""Check portable Agent Skills structure and obvious privacy leaks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED = (
    "SKILL.md",
    "scripts/preflight.py",
    "scripts/install_workbench.py",
    "scripts/verify_workbench.py",
    "references/platform-compatibility.md",
    "adapters/prompt-only/START_HERE.md",
    "assets/project-template",
)

FORBIDDEN = (
    re.compile("/" + "Users" + "/", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\\\" + "Users" + r"\\\\", re.IGNORECASE),
    re.compile(r"['\"](?:cli_|app_|bascn|tbl|vew)[A-Za-z0-9_-]{8,}['\"]", re.IGNORECASE),
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [item for item in REQUIRED if not (root / item).exists()]
    leaks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN:
            if pattern.search(text):
                leaks.append(f"{path.relative_to(root)}: {pattern.pattern}")

    skill = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").exists() else ""
    portable_frontmatter = all(key in skill.split("---", 2)[1] for key in ("name:", "description:")) if skill.startswith("---") else False

    if missing:
        print("Missing required resources:")
        print("\n".join(f"- {item}" for item in missing))
    if leaks:
        print("Possible personal or credential data:")
        print("\n".join(f"- {item}" for item in leaks))
    if not portable_frontmatter:
        print("SKILL.md is missing portable name/description frontmatter")

    if missing or leaks or not portable_frontmatter:
        return 1
    print("Portable structure and privacy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
