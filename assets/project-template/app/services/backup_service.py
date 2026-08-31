from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

def backup_database(database: str, directory: str, keep: int = 20, timezone: str = "Asia/Shanghai"):
    source, target_dir = Path(database), Path(directory)
    if not source.exists(): return None
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d_%H%M%S")
    target = target_dir / f"jobos_{stamp}.db"
    shutil.copy2(source, target)
    owned = sorted(target_dir.glob("jobos_????-??-??_??????.db"), key=lambda x: x.stat().st_mtime, reverse=True)
    for old in owned[keep:]: old.unlink()
    return str(target)

