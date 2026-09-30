"""Technical preflight for an Editkin voiceover-led longform timeline.

Asset counts and motion share are diagnostics, never proof of narrative fit.
This checker cannot certify meaning, smooth movement, taste or final audio.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def check(project: dict) -> dict:
    issues: list[str] = []
    warnings: list[str] = []
    assets = {asset["id"]: asset for asset in project.get("assets", [])}
    tracks = {track["id"]: track for track in project.get("tracks", [])}
    main = sorted(tracks.get("video-main", {}).get("clips", []), key=lambda clip: clip["timelineStart"])
    total = max((clip["timelineStart"] + clip["duration"] for clip in main), default=0)
    moving = [clip for clip in main if assets.get(clip["assetId"], {}).get("kind") == "video"]
    video_seconds = sum(clip["duration"] for clip in moving)
    moving_share = video_seconds / total if total else 0
    uses = Counter(clip["assetId"] for clip in moving)
    if total <= 0:
        issues.append("主畫面不存在或時長無效")
    warnings.extend(f"檢查重複來源的敘事用途：{asset_id} ×{count}" for asset_id, count in uses.items() if count > 2)
    if any(clip["duration"] > 5.1 for clip in main if assets.get(clip["assetId"], {}).get("kind") == "image"):
        warnings.append("有長時間靜態畫面；依閱讀／操作用途檢查，不能為湊動態比例換成無關 B-roll")
    for previous, current in zip(main, main[1:]):
        previous_end = previous["timelineStart"] + previous["duration"]
        if abs(current["timelineStart"] - previous_end) > .035:
            issues.append(f"主畫面斷層或重疊：{previous['id']} / {current['id']}")
        if previous["assetId"] == current["assetId"] and assets.get(current["assetId"], {}).get("kind") == "video":
            warnings.append(f"確認相鄰同來源是否維持連續操作：{current['assetId']}")
    animated = [clip["id"] for clip in main if clip.get("keyframes") or clip.get("expressions") or clip.get("floatingFrame")]
    if animated:
        warnings.append("有人工鏡頭動態；需逐段確認焦點用途及輸出抖動，專案 keyframe 合法不代表流暢")

    captions = sorted(project.get("captions", []), key=lambda caption: caption["start"])
    if not captions:
        issues.append("沒有字幕")
    for caption in captions:
        if "\n" in caption["text"] or len(caption["text"]) > 32:
            warnings.append(f"檢查字幕實際字級、行距與語意斷句：{caption['id']}")
        if caption["duration"] < .35:
            issues.append(f"字幕閃現：{caption['id']}")
    for previous, current in zip(captions, captions[1:]):
        if previous["start"] + previous["duration"] > current["start"] + .00001:
            issues.append(f"字幕重疊：{previous['id']} / {current['id']}")
    style = project.get("captionStyle", {})
    if style.get("color", "").upper() != "#FFFFFF" or not style.get("backgroundColor", "").upper().startswith("#000000"):
        issues.append("長片字幕需白字、半透明黑底")
    if style.get("outlineWidth", 0) > 4:
        warnings.append("字幕描邊偏厚；檢查是否取代半透明底或使相鄰行黏在一起")

    music = tracks.get("audio-music", {}).get("clips", [])
    if not music:
        issues.append("未配置音樂")
    for clip in music:
        asset = assets.get(clip["assetId"], {})
        if asset.get("role") != "background-music":
            issues.append(f"音樂素材角色錯誤：{clip['assetId']}")
        if clip.get("volume", 0) <= 0:
            issues.append(f"音樂軌靜音：{clip['id']}")
    if music and max(clip["timelineStart"] + clip["duration"] for clip in music) < total - .1:
        issues.append("音樂未覆蓋全片")
    return {"status": "BLOCKED" if issues else "TECHNICAL_PASS", "scope": "timeline/configuration only; semantic fit, source cadence, final loudness and aesthetics unverified", "duration": round(total, 3), "moving_share": round(moving_share, 3), "unique_broll": len(uses), "caption_count": len(captions), "animated_clips": animated, "issues": issues, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.project.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
