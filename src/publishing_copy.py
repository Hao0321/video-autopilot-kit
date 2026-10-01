# -*- coding: utf-8 -*-
"""Evidence-first publish copy and topic-research routing."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PLAYBOOK_PATH = HERE.parent / "knowledge" / "runtime" / "publishing_copy_playbooks.json"
RESEARCH_PATH = HERE.parent / "knowledge" / "runtime" / "topic_research_catalog.json"
HASHTAG_RE = re.compile(r"(?<!\w)#[^\s#]+")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _haystack(spec: dict[str, Any]) -> str:
    fields = ("name", "niche", "place", "what", "addr", "topic")
    return " ".join(str(spec.get(key, "")) for key in fields).lower()


def resolve_topic(spec: dict[str, Any], catalog: dict[str, Any] | None = None) -> str | None:
    topics = (catalog or _load(RESEARCH_PATH)).get("topics", {})
    text = _haystack(spec)
    scores = {
        key: sum(1 for alias in row.get("aliases", []) if alias.lower() in text)
        for key, row in topics.items()
    }
    winner = max(scores, key=scores.get, default=None)
    return winner if winner and scores[winner] else None


def research_status(topic: dict[str, Any] | None, *, today: date | None = None) -> str:
    if not topic:
        return "EVIDENCE_ONLY"
    checked = datetime.strptime(topic["last_verified"], "%Y-%m-%d").date()
    age = ((today or date.today()) - checked).days
    return "CURRENT" if age <= int(topic.get("refresh_days", 90)) else "RESEARCH_REQUIRED"


def _clean_hashtags(text: str, defaults: list[str], limit: int) -> list[str]:
    found = HASHTAG_RE.findall(text)
    ordered = []
    for tag in [*found, *defaults]:
        clean = tag.rstrip("，。,.!！?？;；")
        if clean and clean not in ordered:
            ordered.append(clean)
    return ordered[:limit]


def _without_hashtags(text: str) -> str:
    lines = []
    for line in text.splitlines():
        clean = HASHTAG_RE.sub("", line).strip()
        if clean:
            lines.append(clean)
    return "\n".join(lines).strip()


def _battle_mode(spec: dict[str, Any]) -> str:
    text = _haystack(spec)
    counterfeit = any(token in text for token in ("盜版", "仿製", "bootleg", "counterfeit"))
    return "official_vs_counterfeit" if counterfeit else "official_vs_official"


def _validate_beyblade(title: str, body: str, spec: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    mode = _battle_mode(spec)
    combined = title + " " + body
    if mode == "official_vs_official" and "正版" in combined:
        issues.append("正版對正版只寫陀螺名稱，不重複標示正版")
    if mode == "official_vs_counterfeit" and not any(
            token in combined for token in ("盜版", "非官方仿製品", "仿製品")):
        issues.append("正版對非官方仿製品必須揭露非官方身份")
    return issues


def build_publish_copy(spec: dict[str, Any], source_copy: dict[str, Any] | None = None,
                       *, today: date | None = None) -> dict[str, Any]:
    playbook, catalog = _load(PLAYBOOK_PATH), _load(RESEARCH_PATH)
    source_copy = source_copy or {}
    topic_key = resolve_topic(spec, catalog)
    topic = catalog.get("topics", {}).get(topic_key) if topic_key else None
    default_tags = topic.get("hashtags", []) if topic else []
    raw_body = str(source_copy.get("text") or spec.get("what") or spec.get("name") or "")
    title = str(source_copy.get("yt_title") or spec.get("what") or spec.get("name") or "").strip()
    title = title[:int(playbook["defaults"]["title_max_chars"])]
    hashtags = _clean_hashtags(raw_body, default_tags,
                               int(playbook["defaults"]["hashtags_max"]))
    body = _without_hashtags(raw_body)
    issues = _validate_beyblade(title, body, spec) if topic_key == "beyblade_x" else []
    status = research_status(topic, today=today)
    return {
        "title": title,
        "body": body,
        "hashtags": hashtags,
        "topic_key": topic_key,
        "research_status": status,
        "last_verified": topic.get("last_verified") if topic else None,
        "sources": topic.get("sources", []) if topic else [],
        "issues": issues,
        "release_ready": not issues and status != "RESEARCH_REQUIRED",
    }


def render_copy_markdown(copy: dict[str, Any]) -> str:
    tags = " ".join(copy["hashtags"])
    source_lines = [f"- [{row['title']}]({row['url']})（{row['kind']}）"
                    for row in copy.get("sources", [])]
    issue_lines = [f"- {issue}" for issue in copy.get("issues", [])] or ["- 無"]
    return "\n".join([
        "# 發布文案（可直接複製）", "",
        "## YouTube 標題", "", "```text", copy["title"], "```", "",
        "## 共用內文", "", "```text", copy["body"], "", tags, "```", "",
        "## 文案 QA", "", f"- 題材研究：`{copy['research_status']}`",
        f"- 查證日期：`{copy.get('last_verified') or '僅使用片內證據'}`",
        *issue_lines, "", "## 查證來源", "", *(source_lines or ["- 本稿未使用外部時效資訊。"]), ""
    ])


def selftest() -> None:
    official = build_publish_copy(
        {"name": "s22", "niche": "toy", "what": "三角龍對決榮耀女武神"},
        {"yt_title": "三角龍 VS 榮耀女武神", "text": "這一局誰先出界？"},
        today=date(2026, 8, 11),
    )
    assert official["topic_key"] == "beyblade_x" and not official["issues"]
    wrong = build_publish_copy(
        {"niche": "toy", "what": "正版三角龍對決正版榮耀女武神"},
        {"yt_title": "正版三角龍 VS 正版榮耀女武神", "text": "實測"},
        today=date(2026, 8, 11),
    )
    assert wrong["issues"]
    counterfeit = build_publish_copy(
        {"niche": "toy", "what": "榮耀女武神對決盜版黃金神杖"},
        {"yt_title": "榮耀女武神 VS 盜版黃金神杖", "text": "這一局實測"},
        today=date(2026, 8, 11),
    )
    assert counterfeit["release_ready"]
    print("publishing_copy self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("selftest",))
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
