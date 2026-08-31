from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.parsers.jd_parser import normalize_url, parse_jd_file
from app.services.jd_cleaner_service import JDCleaner


def content_hash(value: str) -> str:
    normalized = "\n".join(line.strip() for line in (value or "").splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class DedupMatch:
    path: Path
    same_content: bool
    reason: str


class JDDeduplicator:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.cleaner = JDCleaner()

    def find(self, item: dict) -> DedupMatch | None:
        wanted_url = normalize_url(item.get("source_url", ""))
        wanted_id = str(item.get("external_job_id") or "").strip().casefold()
        wanted_pair = (str(item.get("company") or "").strip().casefold(), str(item.get("position") or "").strip().casefold())
        wanted_hash = content_hash(item.get("jd_text", ""))
        hash_match: DedupMatch | None = None
        for path in sorted(self.root.rglob("*.md")) if self.root.exists() else []:
            try:
                existing = parse_jd_file(str(path))
                raw = path.read_text(encoding="utf-8")
                metadata = {}
                if raw.startswith("---"):
                    parts = raw.split("---", 2)
                    if len(parts) == 3:
                        metadata = yaml.safe_load(parts[1]) or {}
                existing_hash = str(metadata.get("content_hash") or content_hash(self.cleaner.clean_text(existing.get("jd_content", ""))))
                same = existing_hash == wanted_hash
                if wanted_url and normalize_url(existing.get("source_url", "")) == wanted_url:
                    return DedupMatch(path, same, "source_url")
                existing_id = str(existing.get("external_job_id") or metadata.get("job_id") or "").strip().casefold()
                if wanted_id and existing_id == wanted_id:
                    return DedupMatch(path, same, "external_job_id")
                pair = (str(existing.get("company") or "").strip().casefold(), str(existing.get("position") or "").strip().casefold())
                if all(wanted_pair) and pair == wanted_pair:
                    return DedupMatch(path, same, "company_position")
                if same:
                    hash_match = DedupMatch(path, True, "content_hash")
            except Exception:
                continue
        return hash_match
