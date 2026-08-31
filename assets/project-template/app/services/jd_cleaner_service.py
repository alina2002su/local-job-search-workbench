from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    BLOCKS = {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.ignored += 1
        elif not self.ignored and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.ignored:
            self.ignored -= 1
        elif not self.ignored and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


class JDCleaner:
    """Conservative cleaner: remove obvious chrome while preserving JD details."""

    NOISE = re.compile(
        r"^(登录|注册|首页|返回顶部|分享|收藏|扫码|二维码|在线客服|联系我们|"
        r"隐私政策|用户协议|Cookie(?:设置|政策)?|相关推荐|相似职位|其他职位|更多职位)$",
        re.I,
    )

    def html_to_text(self, value: str) -> str:
        if not value:
            return ""
        parser = _TextExtractor()
        try:
            parser.feed(value)
            return self.clean_text("".join(parser.parts))
        except Exception:
            return self.clean_text(re.sub(r"<[^>]+>", "\n", html.unescape(value)))

    def clean_text(self, value: str) -> str:
        value = html.unescape(value or "").replace("\u200b", "").replace("\xa0", " ")
        lines: list[str] = []
        previous = ""
        for raw in value.splitlines():
            line = re.sub(r"[ \t]+", " ", raw).strip()
            if not line or self.NOISE.fullmatch(line):
                continue
            if line == previous:
                continue
            lines.append(line)
            previous = line
        return "\n".join(lines).strip()

