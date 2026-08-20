# -*- coding: utf-8 -*-
"""Post-render tracking, technical QA and report writing for Shorts."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from av_util import contact_sheet, duration, grab_frame, run
from storage_lifecycle import atomic_publish


def apply_tracked_graphics(spec: dict, ready: dict, output: str,
                           output_dir: str, work_dir: str) -> dict | None:
    """Render tracking into a candidate and publish only after GREEN QA."""
    config = spec.get("tracked_graphics")
    if not config:
        return None
    from tracked_graphics import render_spec

    os.makedirs(work_dir, exist_ok=True)
    qa_dir = os.path.join(output_dir, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    render_spec_data = dict(config)
    render_spec_data["video"] = output
    render_spec_data.setdefault("start", 0.0)
    render_spec_data.setdefault("end", float(ready["_dur"]))
    spec_path = os.path.join(output_dir, "current_tracked_graphics_spec.json")
    with open(spec_path, "w", encoding="utf-8") as handle:
        json.dump(render_spec_data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    candidate = os.path.join(work_dir, "tracked_graphics_candidate.mp4")
    report = render_spec(
        render_spec_data, candidate,
        track_output=os.path.join(qa_dir, "TRACKING.json"),
        qa_sheet=os.path.join(qa_dir, "TRACKING_contact.jpg"),
    )
    if report.get("status") != "GREEN":
        raise RuntimeError("tracked graphics QA is %s (lost_ratio=%s); base cut kept" %
                           (report.get("status"), (report.get("tracking") or {}).get("lost_ratio")))
    atomic_publish(candidate, output)
    report["spec"] = spec_path
    return report


def _frame_array(video: str, timestamp: float, qa_dir: str):
    from PIL import Image
    import numpy as np

    path = os.path.join(qa_dir, "_frame.png")
    if not grab_frame(video, timestamp, path, vf="scale=90:160"):
        return None
    array = np.asarray(Image.open(path).convert("L"), dtype=float)
    os.remove(path)
    return array


def run_short_qa(video: str, ready: dict, output_dir: str, *,
                 duration_range: tuple[float, float] = (13.0, 25.5)) -> dict:
    """Check export spec, duration, A/V sync, loudness and review evidence.

    ``duration_range`` keeps the original Shorts gate as the default while
    allowing an explicitly routed vertical remix to declare its own contract.
    Callers may not silently widen the range after a failure; the routed plan
    must provide the format-specific bounds before rendering.
    """
    import numpy as np

    qa_dir = os.path.join(output_dir, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    result: dict = {}
    wh = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height,r_frame_rate",
              "-of", "csv=p=0", video]).stdout.strip()
    result["format"] = wh
    result["spec_ok"] = wh.startswith("1080,1920,30")
    measured = duration(video)
    result["dur"] = round(measured, 2)
    min_duration, max_duration = (float(duration_range[0]), float(duration_range[1]))
    if min_duration <= 0 or max_duration < min_duration:
        raise ValueError("invalid duration_range: %r" % (duration_range,))
    result["duration_range"] = [min_duration, max_duration]
    result["dur_ok"] = min_duration <= measured <= max_duration
    planned = float(ready.get("_dur", measured))
    result["planned_dur"] = round(planned, 2)
    result["duration_delta"] = round(abs(measured - planned), 2)
    result["duration_match_ok"] = result["duration_delta"] <= .15
    stream_probe = run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,duration", "-of", "json", video]).stdout
    try:
        rows = json.loads(stream_probe).get("streams") or []
        durations = {row.get("codec_type"): float(row["duration"])
                     for row in rows if row.get("duration") not in (None, "N/A")}
    except (TypeError, ValueError, KeyError):
        durations = {}
    result["av_duration_delta"] = round(abs(durations.get("video", measured) -
                                              durations.get("audio", measured)), 2)
    result["av_sync_ok"] = result["av_duration_delta"] <= .15
    loudness = run(["ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128=peak=true",
                    "-f", "null", "-"])
    matches = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", loudness.stderr)
    result["lufs"] = float(matches[-1]) if matches else None
    result["lufs_ok"] = result["lufs"] is not None and abs(result["lufs"] + 14) <= 1.5
    first = _frame_array(video, .08, qa_dir)
    last = _frame_array(video, measured - .25, qa_dir)
    result["loop_sim"] = round(float(np.corrcoef(first.ravel(), last.ravel())[0, 1]), 2) \
        if first is not None and last is not None else None
    tiles = []
    for start, end, blocks, kind in ready["caps"]:
        if kind == "addr":
            continue
        label = "".join(text for text, _color in blocks)[:10]
        path = os.path.join(qa_dir, "_caption_%.2f.jpg" % start)
        if grab_frame(video, round((start + end) / 2, 2), path, vf="scale=180:-1"):
            tiles.append((path, label))
    sheet = contact_sheet(tiles, os.path.join(qa_dir, "CAPTION_match.jpg"),
                          cols=max(1, len(tiles)), cleanup=True)
    if sheet:
        result["caption_sheet"] = sheet
    first_frame = os.path.join(qa_dir, "FIRSTFRAME.jpg")
    if grab_frame(video, 0.0, first_frame, vf="scale=540:-1"):
        result["first_frame"] = first_frame
    result["all_green"] = bool(result["spec_ok"] and result["dur_ok"] and
                               result["duration_match_ok"] and result["av_sync_ok"] and
                               result["lufs_ok"])
    print("[qa] %s dur=%.1fs drift=%.2fs av=%.2fs LUFS=%s loop=%s %s" %
          (os.path.basename(video), result["dur"], result["duration_delta"],
           result["av_duration_delta"], result["lufs"], result["loop_sim"],
           "GREEN" if result["all_green"] else "RED"))
    return result


def write_short_report(source_dir: str, spec: dict, ready: dict, qa: dict, output: str) -> None:
    lines = ["# Shorts 交付報告 — %s" % spec["name"], "",
             "- 地點／題材：**%s**／%s" % (spec.get("place", ""), spec.get("what", "")),
             "- 片長：%.1fs；段落：%d" % (ready["_dur"], len(spec["segs"])),
             "- 格式：%s；LUFS：%s；A/V 差：%.2fs；輸出差：%.2fs" %
             (qa.get("format"), qa.get("lufs"), qa.get("av_duration_delta", -1),
              qa.get("duration_delta", -1)),
             "- 技術 QA：**%s**" % ("GREEN" if qa.get("all_green") else "RED"),
             "- Quality-95：**%s / %s**" %
             ((qa.get("quality_95") or {}).get("score", "pending"),
              (qa.get("quality_95") or {}).get("status", "pending")), "",
             "## 字幕時間碼"]
    for start, end, blocks, kind in ready["caps"]:
        if kind != "addr":
            lines.append("- %.1f–%.1fs：%s" %
                         (start, end, "".join(text for text, _color in blocks)))
    lines += ["", "## 人眼證據", "- `_out/_qa/CAPTION_match.jpg`",
              "- `_out/_qa/FIRSTFRAME.jpg`", "- `_out/_review/review.html`",
              "- 成片：`%s`" % Path(output).name, ""]
    Path(source_dir, "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
