from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.jd_clip import JDClipRequest
from app.services.jd_clipper_service import JDClipperService


router = APIRouter(prefix="/api")
service: JDClipperService | None = None


def configure_jd_clipper(root: str, log_directory: str, timezone: str = "Asia/Shanghai") -> JDClipperService:
    global service
    service = JDClipperService(root, log_directory, timezone)
    return service


@router.get("/health")
def api_health():
    if service is None:
        raise HTTPException(503, "JD Clipper 尚未配置")
    return {"status": "ok", "save_directory": str(service.root)}


@router.post("/jd/clip")
def clip_jd(payload: JDClipRequest):
    if service is None:
        raise HTTPException(503, "JD Clipper 尚未配置")
    try:
        return service.clip(payload.model_dump())
    except Exception as exc:
        raise HTTPException(500, "保存 JD 失败，请查看本地日志") from exc
