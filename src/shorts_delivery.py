# -*- coding: utf-8 -*-
"""Post-render tracking, technical QA and report writing for Shorts."""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from pathlib import Path

from av_util import contact_sheet, duration, grab_frame, run
from storage_lifecycle import atomic_publish


def _effect_output_name(effect: dict, index: int) -> str:
    """Return a deterministic, path-safe directory name for one matte job."""
    raw = str(effect.get("id", "subject-%d" % index)).strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-")[:48]
    return "ROTO_SEQUENCE_%02d_%s" % (index, safe or "subject")


def _require_green_roto_report(report: dict, sequence_dir: Path, *, effect_id: str) -> None:
    """Verify the matte builder receipt before a renderer can consume it.

    ``GREEN`` here is deliberately only the machine boundary.  The builder's
    ``AUTO_WITH_REVIEW`` capability and Hao approval blocker are retained in
    the materialized effect and in the final tracking report.
    """
    if report.get("status") != "GREEN":
        raise RuntimeError(
            "roto matte %s is %s; base cut kept for review" %
            (effect_id, report.get("status", "UNKNOWN"))
        )
    if report.get("capability") != "AUTO_WITH_REVIEW":
        raise RuntimeError("roto matte %s has an unexpected capability receipt" % effect_id)
    blockers = set(report.get("promotion_blocked_until") or [])
    if "Hao_approval" not in blockers:
        raise RuntimeError("roto matte %s lost the required Hao approval boundary" % effect_id)
    frame_count = int(report.get("frames", 0))
    fps = float(report.get("fps", 0))
    if frame_count <= 0 or fps <= 0:
        raise RuntimeError("roto matte %s has an incomplete frame/fps receipt" % effect_id)
    missing = [sequence_dir / ("frame_%06d.png" % index)
               for index in range(frame_count)
               if not (sequence_dir / ("frame_%06d.png" % index)).is_file()]
    if missing:
        raise RuntimeError("roto matte %s is missing required frame %s" %
                           (effect_id, missing[0]))
    report_path = Path(str(report.get("report_path", "")))
    contact_path = Path(str(report.get("contact_sheet", "")))
    if not report_path.is_file() or not contact_path.is_file():
        raise RuntimeError("roto matte %s lacks report/contact-sheet evidence" % effect_id)


def _materialize_auto_matte_sequences(render_spec: dict, qa_dir: str) -> list[dict]:
    """Build every ``auto_sequence`` into a verified per-frame alpha sequence.

    The pre-render plan is allowed to request automatic matte generation, but
    :mod:`tracked_graphics` only accepts concrete ``sequence`` inputs.  This
    transaction bridges those two stages without mutating the authored plan.
    Any failed or incomplete sequence aborts before the output video is
    replaced, so the caller retains its previous/base cut.
    """
    from roto_matte import build_sequence

    receipts: list[dict] = []
    effects = list(render_spec.get("mask_sheens") or [])
    for index, effect in enumerate(effects):
        if str(effect.get("shape", "ellipse")) != "auto_sequence":
            continue
        effect_id = str(effect.get("id", "subject-%d" % index))
        effect_start = float(effect.get("start", render_spec.get("start", 0)))
        effect_end = float(effect.get("end", render_spec.get("end", effect_start)))
        render_start = float(render_spec.get("start", 0))
        render_end = float(render_spec.get("end", render_start))
        if effect_start < render_start or effect_end > render_end or effect_end <= effect_start:
            raise RuntimeError("auto matte %s lies outside the tracked render range" % effect_id)

        sequence_dir = Path(qa_dir, _effect_output_name(effect, index)).resolve()
        roto_spec = copy.deepcopy(effect)
        roto_spec.update({
            "video": str(Path(str(render_spec["video"])).resolve()),
            "start": effect_start,
            "end": effect_end,
            "profile": str(effect.get("matte_profile", "round_product_grabcut")),
            "target_kind": "subject_object",
        })
        report = build_sequence(roto_spec, sequence_dir)
        _require_green_roto_report(report, sequence_dir, effect_id=effect_id)

        materialized = copy.deepcopy(effect)
        materialized.update({
            "shape": "sequence",
            "matte_sequence_dir": str(sequence_dir),
            "matte_sequence_fps": float(report["fps"]),
            "matte_sequence_start": float(report["sequence_start"]),
            "matte_sequence_frames": int(report["frames"]),
            "matte_sequence_prefix": "frame_",
            "matte_sequence_digits": 6,
            "matte_sequence_extension": ".png",
            "matte_sequence_report": str(report["report_path"]),
            "matte_sequence_contact_sheet": str(report["contact_sheet"]),
            "matte_quality_status": "GREEN",
            "matte_capability": "AUTO_WITH_REVIEW",
            "matte_human_review_status": "PENDING",
            "matte_promotion_blocked_until": list(report["promotion_blocked_until"]),
        })
        effects[index] = materialized
        receipts.append({
            "effect_id": effect_id,
            "status": "GREEN",
            "capability": "AUTO_WITH_REVIEW",
            "human_review_status": "PENDING",
            "frames": int(report["frames"]),
            "fps": float(report["fps"]),
            "sequence_dir": str(sequence_dir),
            "report": str(report["report_path"]),
            "contact_sheet": str(report["contact_sheet"]),
            "promotion_blocked_until": list(report["promotion_blocked_until"]),
        })
    render_spec["mask_sheens"] = effects
    return receipts


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
    # The source plan remains immutable evidence.  Materialized file paths and
    # builder receipts belong to the post-render tracking spec only.
    render_spec_data = copy.deepcopy(config)
    render_spec_data["video"] = output
    render_spec_data.setdefault("start", 0.0)
    render_spec_data.setdefault("end", float(ready["_dur"]))
    roto_receipts = _materialize_auto_matte_sequences(render_spec_data, qa_dir)
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
    report["roto_sequences"] = roto_receipts
    report["human_review"] = {
        "required": bool(roto_receipts),
        "status": "PENDING" if roto_receipts else "NOT_APPLICABLE",
        "boundary": (
            "machine GREEN permits a review candidate only; Hao approval is still required "
            "before Quality-95 certification"
        ),
    }
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


def self_test() -> None:
    """Exercise helper -> auto roto -> validator -> real render as one closure."""
    import hashlib

    import cv2
    import numpy as np

    from battle_plan_components import identity_label, subject_sheen
    from tracked_graphics import validate_spec

    with tempfile.TemporaryDirectory(prefix="shorts-delivery-tracking-") as temp:
        root = Path(temp)
        output_dir = root / "out"
        work_dir = output_dir / "_work"
        output_dir.mkdir(parents=True)
        source = output_dir / "current.mp4"
        fps, frame_count = 30, 30
        writer = cv2.VideoWriter(
            str(source), cv2.VideoWriter_fourcc(*"mp4v"), fps, (640, 360),
        )
        for frame_index in range(frame_count):
            frame = np.full((360, 640, 3), (28, 34, 43), np.uint8)
            x = round(242 + frame_index * .6)
            y = round(172 + 5 * np.sin(frame_index * .18))
            cv2.circle(frame, (x + 54, y + 54), 49, (218, 225, 235), -1, cv2.LINE_AA)
            cv2.circle(frame, (x + 54, y + 54), 24, (35, 145, 238), -1, cv2.LINE_AA)
            cv2.line(frame, (x + 22, y + 36), (x + 86, y + 72), (255, 255, 255), 4)
            writer.write(frame)
        writer.release()
        if not source.is_file() or source.stat().st_size < 1000:
            raise AssertionError("synthetic tracking source was not written")

        label_boxes = [(.10, [244, 169, 108, 108]), (.80, [257, 166, 108, 108])]
        sheen_boxes = [(.20, [246, 168, 108, 108]), (.70, [255, 166, 108, 108])]
        label = identity_label(
            ident="demo-top-label", text="三角龍", bbox=label_boxes[0][1],
            keyframes=label_boxes, start=.10, end=.80,
            evidence="editor-verified synthetic identity and boxes",
            tracking_source="verified_keyframes",
        )
        sheen = subject_sheen(
            ident="demo-top-sheen", bbox=sheen_boxes[0][1], keyframes=sheen_boxes,
            start=.20, end=.70,
            evidence="editor-verified synthetic silhouette and boxes",
        )
        authored = {
            "tracked_graphics": {
                "tracked_labels": [label],
                "mask_sheens": [sheen],
            },
        }
        report = apply_tracked_graphics(
            authored, {"_dur": 1.0}, str(source), str(output_dir), str(work_dir),
        )
        if not report or report.get("status") != "GREEN":
            raise AssertionError(report)
        if authored["tracked_graphics"]["mask_sheens"][0]["shape"] != "auto_sequence":
            raise AssertionError("authored plan was mutated during materialization")
        materialized = json.loads(
            (output_dir / "current_tracked_graphics_spec.json").read_text(encoding="utf-8")
        )
        errors = validate_spec(materialized)
        if errors:
            raise AssertionError("materialized tracked spec is invalid: " + "; ".join(errors))
        effect = materialized["mask_sheens"][0]
        if effect.get("shape") != "sequence" or effect.get("matte_human_review_status") != "PENDING":
            raise AssertionError("auto sequence or human-review boundary was not materialized")
        if report.get("human_review", {}).get("status") != "PENDING":
            raise AssertionError("render report lost the human-review boundary")
        tracking_receipt = json.loads(
            (output_dir / "_qa" / "TRACKING.json").read_text(encoding="utf-8")
        )
        persisted_report = tracking_receipt.get("report") or {}
        if persisted_report.get("human_review", {}).get("status") != "PENDING":
            raise AssertionError("persisted tracking receipt lost the human-review boundary")
        sequence_receipts = (persisted_report.get("mask_sheens") or {}).get(
            "sequence_receipts") or []
        if len(sequence_receipts) != 1 or sequence_receipts[0].get("status") != "GREEN":
            raise AssertionError("persisted tracking receipt lost the roto sequence proof")
        if not source.is_file() or source.stat().st_size < 1000:
            raise AssertionError("tracked render was not atomically published")

        # A missing evidence receipt must fail before replacing the current cut.
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        broken = copy.deepcopy(authored)
        broken["tracked_graphics"]["mask_sheens"][0]["evidence"] = ""
        try:
            apply_tracked_graphics(
                broken, {"_dur": 1.0}, str(source), str(output_dir), str(work_dir),
            )
        except (RuntimeError, ValueError):
            pass
        else:
            raise AssertionError("auto matte without evidence did not fail closed")
        after = hashlib.sha256(source.read_bytes()).hexdigest()
        if before != after:
            raise AssertionError("failed auto matte replaced the base/current cut")
    print("shorts_delivery tracking-closure self-test GREEN")
