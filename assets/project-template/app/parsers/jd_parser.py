from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import yaml

TRACKING = {"spread","utm_source","utm_medium","utm_campaign","utm_term","utm_content","from","ref","source"}

def normalize_url(url: str) -> str:
    if not url: return ""
    try:
        p = urlsplit(url.strip())
        query = urlencode([(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING])
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), query, ""))
    except Exception: return url.strip().rstrip("/")

def parse_title(title: str):
    parts = [x.strip() for x in re.split(r"\s+-\s+|\s+–\s+|\s+—\s+", title or "") if x.strip()]
    if len(parts) >= 3:
        return {"position": parts[0], "business": " - ".join(parts[1:-1]), "company": parts[-1]}
    if len(parts) == 2: return {"position": parts[0], "business": "", "company": parts[1]}
    return {"position": title.strip(), "business": "", "company": ""}

def parse_jd_file(path: str):
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    metadata, body = {}, raw
    if raw.startswith("---"):
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
        if match:
            try: metadata = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError: metadata = {}
            body = match.group(2)
    title = str(metadata.get("title") or metadata.get("position") or p.stem)
    parsed = parse_title(title)
    source_url = str(metadata.get("source_url") or metadata.get("source") or "")
    lines=[line.strip() for line in body.splitlines() if line.strip()]
    if "京东校园招聘" in title and lines:
        parsed["position"]=lines[0]
        parsed["business"]=lines[1] if len(lines)>1 else ""
        parsed["company"]=next((line for line in lines[2:12] if line in {"京东零售","京东健康","京东工业","京东物流","京东集团"}),"京东集团")
    id_match = re.search(r"(?:职位\s*ID|职位ID|Job\s*ID)\s*[：:]\s*([A-Za-z0-9_-]+)", body, re.I)
    metadata_job_id = str(metadata.get("job_id") or metadata.get("external_job_id") or "")
    if not id_match: id_match=re.search(r"(?:[?&#](?:id|jobUnionId|jobId|positionId)=)([A-Za-z0-9_-]+)",source_url,re.I)
    city_match = re.search(r"^([^\n]{1,90}?)(?:正式|实习)?(?:销售|产品|运营|技术|研发|市场).*?(?:职位\s*ID|职位ID)", body, re.M)
    created = metadata.get("captured_at") or metadata.get("created") or metadata.get("clipped_date") or date.fromtimestamp(p.stat().st_mtime).isoformat()
    if hasattr(created, "isoformat"): created = created.isoformat()
    company = str(metadata.get("company") or parsed["company"])
    position = str(metadata.get("position") or parsed["position"])
    business = str(metadata.get("business") or parsed["business"])
    city = metadata.get("city") or (city_match.group(1).strip(" 、，,") if city_match else "")
    if isinstance(city, list): city = "、".join(str(x).strip() for x in city if str(x).strip())
    if "meituan.com" in source_url.casefold():
        company = company or "美团"
        if not position or position in {"职位详情 | 美团招聘", "职位详情", "美团招聘"}:
            body_lines=[line.strip() for line in body.splitlines() if line.strip()]
            for index,line in enumerate(body_lines):
                if line.startswith("应届-") and index:
                    position=body_lines[index-1]; break
            if not position or position in {"职位详情 | 美团招聘", "职位详情", "美团招聘"}:
                for index,line in enumerate(body_lines):
                    if line.startswith("工作地点") and index:
                        position=body_lines[index-1]; break
    return {
        **parsed,
        "company": company,
        "position": position,
        "business": business,
        "raw_title": title, "source_url": source_url,
        "external_job_id": metadata_job_id or (id_match.group(1) if id_match else ""),
        "city": city,
        "clipped_date": str(created)[:10], "jd_content": body.strip(), "jd_content_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "jd_file_path": str(p.resolve()), "last_modified": p.stat().st_mtime,
    }
