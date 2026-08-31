from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.jd_dedup_service import JDDeduplicator
from app.services.jd_markdown_service import JDMarkdownWriter
from app.services.jd_parser_service import JDParserService


class JDClipperService:
    def __init__(self, root: str, log_directory: str, timezone: str = "Asia/Shanghai"):
        self.root = Path(root)
        self.timezone = timezone
        self.parser = JDParserService()
        self.deduplicator = JDDeduplicator(self.root)
        self.writer = JDMarkdownWriter(self.root)
        log_root = Path(log_directory)
        log_root.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"jd_clipper.{self.root}")
        if not self.logger.handlers:
            handler = logging.FileHandler(log_root / "jd_clipper.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

    def clip(self, payload: dict) -> dict:
        url = str(payload.get("url") or "")
        self.logger.info("clip_started url=%s", url)
        try:
            parsed = self.parser.parse(payload).to_dict()
            if not parsed["captured_at"]:
                parsed["captured_at"] = datetime.now(ZoneInfo(self.timezone)).isoformat(timespec="seconds")
            match = self.deduplicator.find(parsed)
            if match and match.same_content:
                self.logger.info("clip_duplicate url=%s reason=%s file=%s", url, match.reason, match.path.name)
                return {"status": "already_saved", "message": "该岗位已经保存", "filename": match.path.name, "path": str(match.path), **self._summary(parsed)}
            path = self.writer.write(parsed, versioned=bool(match))
            status = "version_saved" if match else "saved"
            self.logger.info("clip_saved url=%s status=%s file=%s", url, status, path.name)
            return {"status": status, "message": "JD 已保存", "filename": path.name, "path": str(path), **self._summary(parsed)}
        except Exception as exc:
            self.logger.exception("clip_failed url=%s error=%s", url, type(exc).__name__)
            raise

    @staticmethod
    def _summary(item: dict) -> dict:
        return {key: item.get(key) for key in ("company", "position", "business", "city", "external_job_id", "source_url")}

