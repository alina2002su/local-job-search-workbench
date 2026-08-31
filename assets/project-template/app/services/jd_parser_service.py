from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
from urllib.parse import urlsplit

from app.parsers.jd_parser import normalize_url, parse_title
from app.services.jd_cleaner_service import JDCleaner


@dataclass
class ParsedJD:
    company: str = ""
    position: str = ""
    business: str = ""
    city: list[str] = field(default_factory=list)
    external_job_id: str = ""
    source_url: str = ""
    jd_text: str = ""
    captured_at: str = ""
    capture_source: str = "browser_extension"
    page_title: str = ""
    description: str = ""

    def to_dict(self):
        return asdict(self)


class AIJDParserProvider(Protocol):
    """Future extension point. Version 1 never calls an AI provider."""

    def parse(self, payload: dict[str, Any]) -> ParsedJD: ...


class BaseJDParser(ABC):
    @abstractmethod
    def supports(self, payload: dict[str, Any]) -> bool: ...

    @abstractmethod
    def parse(self, payload: dict[str, Any]) -> ParsedJD: ...


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def find_job_posting(value: Any) -> dict[str, Any]:
    for item in _walk(value):
        kind = item.get("@type", "")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(str(entry).casefold() == "jobposting" for entry in kinds):
            return item
    return {}


def _name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "").strip()
    return str(value or "").strip()


def _cities(value: Any) -> list[str]:
    result: list[str] = []
    values = value if isinstance(value, list) else [value]
    for item in values:
        if not isinstance(item, dict):
            continue
        address = item.get("address", item)
        if not isinstance(address, dict):
            continue
        for key in ("addressLocality", "addressRegion"):
            city = str(address.get(key) or "").strip()
            if city and city not in result:
                result.append(city)
    return result


class GenericJDParser(BaseJDParser):
    ID_RE = re.compile(r"(?:职位\s*ID|职位ID|岗位\s*ID|Job\s*ID|JobID)\s*[：:#]?\s*([A-Za-z0-9_-]{3,})", re.I)
    CITY_RE = re.compile(r"(?:工作地点|工作城市|地点|城市)\s*[：:]\s*([^\n]{1,60})")

    def __init__(self, cleaner: JDCleaner | None = None):
        self.cleaner = cleaner or JDCleaner()

    def supports(self, payload: dict[str, Any]) -> bool:
        return True

    def parse(self, payload: dict[str, Any]) -> ParsedJD:
        job = find_job_posting(payload.get("structured_data"))
        page_title = str(payload.get("og_title") or payload.get("page_title") or "").strip()
        title = _name(job.get("title")) or page_title
        title_fields = parse_title(page_title or title)
        description = self.cleaner.html_to_text(str(job.get("description") or ""))
        selected = self.cleaner.clean_text(str(payload.get("selected_text") or ""))
        fragment = self.cleaner.html_to_text(str(payload.get("html_fragment") or ""))
        page_text = self.cleaner.clean_text(str(payload.get("page_text") or ""))
        if len(selected) >= 80:
            jd_text = selected
        elif description:
            jd_text = description
        elif len(fragment) >= 80:
            jd_text = fragment
        else:
            jd_text = page_text or selected or description

        identifier = job.get("identifier")
        external_id = _name(identifier)
        if not external_id and isinstance(identifier, dict):
            external_id = str(identifier.get("value") or "").strip()
        match = self.ID_RE.search("\n".join((jd_text, page_text, str(payload.get("url") or ""))))
        if not external_id and match:
            external_id = match.group(1)

        cities = _cities(job.get("jobLocation"))
        if not cities:
            city_match = self.CITY_RE.search(page_text or jd_text)
            if city_match:
                cities = [x.strip() for x in re.split(r"[、,，/|]", city_match.group(1)) if x.strip()][:8]

        company = _name(job.get("hiringOrganization")) or title_fields["company"]
        position = _name(job.get("title")) or title_fields["position"]
        return ParsedJD(
            company=company,
            position=position,
            business=title_fields["business"],
            city=cities,
            external_job_id=external_id,
            source_url=normalize_url(str(payload.get("url") or "")),
            jd_text=jd_text,
            captured_at=str(payload.get("captured_at") or ""),
            capture_source=str(payload.get("capture_source") or "browser_extension"),
            page_title=str(payload.get("page_title") or title),
            description=str(payload.get("description") or "").strip(),
        )


class SiteSpecificParser(BaseJDParser):
    """Small enhancement layer; generic parsing remains the required fallback."""

    HOSTS: tuple[str, ...] = ()

    def supports(self, payload: dict[str, Any]) -> bool:
        host = urlsplit(str(payload.get("url") or "")).netloc.casefold()
        return any(entry in host for entry in self.HOSTS)

    def parse(self, payload: dict[str, Any]) -> ParsedJD:
        return GenericJDParser().parse(payload)


class ByteDanceParser(SiteSpecificParser):
    HOSTS = ("bytedance", "douyin")


class JDParser(SiteSpecificParser):
    HOSTS = ("jd.com", "jingdong")


class MeituanParser(SiteSpecificParser):
    HOSTS = ("meituan")

    def parse(self, payload: dict[str, Any]) -> ParsedJD:
        item = GenericJDParser().parse(payload)
        item.company = item.company or "美团"
        lines = [line.strip() for line in item.jd_text.splitlines() if line.strip()]
        if not item.position or item.position in {"职位详情 | 美团招聘", "职位详情", "美团招聘"}:
            for index, line in enumerate(lines):
                if line.startswith("应届-") and index:
                    item.position = lines[index - 1]
                    break
        if not item.external_job_id:
            match = re.search(r"[?&]jobUnionId=([A-Za-z0-9_-]+)", item.source_url, re.I)
            if match:
                item.external_job_id = match.group(1)
        return item


class JDParserService:
    def __init__(self):
        self.parsers: list[BaseJDParser] = [ByteDanceParser(), JDParser(), MeituanParser(), GenericJDParser()]

    def parse(self, payload: dict[str, Any]) -> ParsedJD:
        for parser in self.parsers:
            if parser.supports(payload):
                return parser.parse(payload)
        return GenericJDParser().parse(payload)
