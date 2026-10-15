"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import re


_BEAT_RE = re.compile(
    r"^\*\*\[(\d{1,2}):(\d{2})\s*[-–~]\s*(\d{1,2}):(\d{2})\s+([^\]]+)\]\*\*\s*$",
    re.MULTILINE,
)


_MD_HEAD_RE = re.compile(r"^#{1,4}\s+(.+?)\s*$", re.MULTILINE)


def _strip_markup(s: str) -> str:
    """去 markdown 記號，留純旁白字。

    blockquote 行（> 開頭）＝檔頭註記/M10 對帳注釋，不是旁白 → 整行剔除
    （否則 gate 會把註記裡的 fork/M79/BGM 當旁白掃，時長也灌水）。"""
    s = re.sub(r"(?m)^\s*>.*$", "", s)
    s = _BEAT_RE.sub("", s)
    s = _MD_HEAD_RE.sub("", s)
    s = re.sub(r"[*_`>#\[\]|]+", "", s)
    return s


def _count_chars(s: str) -> int:
    """可念字數：只算 CJK + 英數（去標點/空白）。"""
    return len(re.findall(r"[一-鿿A-Za-z0-9]", _strip_markup(s)))


def parse_beats(text: str) -> list:
    """切 beats。優先 **[mm:ss-mm:ss 標題]**，退 markdown header，再退整篇一章。

    回傳 [{title, t_start, t_end, body}]（t_* 秒；無標時 None）。
    """
    beats = []
    matches = list(_BEAT_RE.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            start = int(m.group(1)) * 60 + int(m.group(2))
            end = int(m.group(3)) * 60 + int(m.group(4))
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            beats.append({
                "title": m.group(5).strip(),
                "t_start": start,
                "t_end": end,
                "body": text[body_start:body_end].strip(),
            })
        return beats

    md = list(_MD_HEAD_RE.finditer(text))
    if md:
        for i, m in enumerate(md):
            body_start = m.end()
            body_end = md[i + 1].start() if i + 1 < len(md) else len(text)
            beats.append({
                "title": m.group(1).strip(),
                "t_start": None,
                "t_end": None,
                "body": text[body_start:body_end].strip(),
            })
        return beats

    return [{"title": "(all)", "t_start": None, "t_end": None, "body": text.strip()}]
