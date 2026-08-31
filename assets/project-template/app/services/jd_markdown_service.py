from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

from app.services.jd_dedup_service import content_hash


class JDMarkdownWriter:
    ILLEGAL = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def filename(self, item: dict) -> str:
        company = item.get("company", "").strip()
        position = item.get("position", "").strip()
        job_id = item.get("external_job_id", "").strip()
        if company and position:
            stem = "_".join(x for x in (company, position, job_id) if x)
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            stem = f"{item.get('page_title') or position or '未识别岗位'}_{stamp}"
        stem = self.ILLEGAL.sub("_", stem)
        stem = re.sub(r"\s+", " ", stem).strip(" ._")[:150]
        return f"{stem or '未识别岗位'}.md"

    def render(self, item: dict) -> str:
        frontmatter = {
            "company": item.get("company", ""),
            "position": item.get("position", ""),
            "business": item.get("business", ""),
            "city": item.get("city", []),
            "job_id": item.get("external_job_id", ""),
            "source_url": item.get("source_url", ""),
            "captured_at": item.get("captured_at", ""),
            "capture_source": item.get("capture_source", "browser_extension"),
            "description": item.get("description", ""),
            "content_hash": content_hash(item.get("jd_text", "")),
        }
        title = item.get("position") or item.get("page_title") or "未识别岗位"
        company = item.get("company") or "未识别"
        business = item.get("business") or "未识别"
        body = item.get("jd_text") or "未能提取正文，请通过原岗位链接查看。"
        header = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{header}\n---\n\n# {title}\n\n## 公司\n\n{company}\n\n## 业务线\n\n{business}\n\n## JD原文\n\n{body.strip()}\n"

    def write(self, item: dict, versioned: bool = False) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        base = self.root / self.filename(item)
        candidate = base
        version = 2
        if versioned:
            candidate = base.with_name(f"{base.stem}_v{version}{base.suffix}")
            version += 1
        if candidate.exists():
            while candidate.exists():
                candidate = base.with_name(f"{base.stem}_v{version}{base.suffix}")
                version += 1
        with candidate.open("x", encoding="utf-8") as handle:
            handle.write(self.render(item))
        return candidate
