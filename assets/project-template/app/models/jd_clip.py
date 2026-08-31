from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JDClipRequest(BaseModel):
    capture_source: str = "browser_extension"
    url: str = ""
    page_title: str = ""
    selected_text: str = ""
    page_text: str = ""
    html_fragment: str = ""
    meta_description: str = ""
    og_title: str = ""
    og_description: str = ""
    description: str = ""
    structured_data: Any = Field(default_factory=dict)
    captured_at: str = ""
    browser_info: str = ""
