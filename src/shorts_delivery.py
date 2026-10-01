# -*- coding: utf-8 -*-
"""Post-render tracking, technical QA and report writing for Shorts."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np

from av_util import contact_sheet, duration, grab_frame, run
from storage_lifecycle import atomic_publish


def _require_green_roto_report(report: dict, sequence_dir: Path, *, effect_id: str) -> None:
    """Verify the matte builder receipt before a renderer can consume it."""
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


def _bbox_center(box: list[float]) -> tuple[float, float]:
    return float(box[0]) + float(box[2]) / 2, float(box[1]) + float(box[3]) / 2


def _expand_box(box: list[float], padding: float) -> list[float]:
    x, y, w, h = [float(value) for value in box]
    return [x - w * padding, y - h * padding,
            w * (1.0 + padding * 2), h * (1.0 + padding * 2)]


def _smooth_subject_keyframes(report: dict, *, padding: float = .035) -> list[dict]:
    """Turn dense matte geometry into a stable, zero-lag editorial track."""
    rows = [row for row in report.get("frames_detail", []) if row.get("subject_bbox")]
    if not rows:
        return []
    boxes = np.asarray([row["subject_bbox"] for row in rows], dtype=np.float64)
    # Centred median rejects single-frame GrabCut spikes; the following centred
    # mean removes one-pixel edge chatter without introducing causal lag.
    median = boxes.copy()
    for index in range(len(boxes)):
        left, right = max(0, index - 2), min(len(boxes), index + 3)
        median[index] = np.median(boxes[left:right], axis=0)
    smooth = median.copy()
    for index in range(len(median)):
        left, right = max(0, index - 1), min(len(median), index + 2)
        smooth[index] = np.mean(median[left:right], axis=0)
    width, height = [float(value) for value in report["resolution"]]
    keyframes = []
    for row, box in zip(rows, smooth):
        x, y, w, h = [float(value) for value in box]
        px, py = w * padding, h * padding
        x, y = max(0.0, x - px), max(0.0, y - py)
        w, h = min(width - x, w + px * 2), min(height - y, h + py * 2)
        keyframes.append({
            "time": float(row["source_time"]),
            "bbox": [round(x, 3), round(y, 3), round(w, 3), round(h, 3)],
        })
    return keyframes


def _pair_label_to_matte(label: dict, matte_rows: list[dict]) -> dict | None:
    label_start = float(label.get("start", 0))
    label_end = float(label.get("end", label_start))
    label_center = _bbox_center(label["initial_bbox"])
    best: tuple[float, dict] | None = None
    for row in matte_rows:
        effect = row["effect"]
        overlap = max(0.0, min(label_end, float(effect["end"])) -
                      max(label_start, float(effect["start"])))
        if overlap <= 0:
            continue
        target_center = _bbox_center(row["original_bbox"])
        distance = ((label_center[0] - target_center[0]) ** 2 +
                    (label_center[1] - target_center[1]) ** 2) ** .5
        score = overlap * 10000.0 - distance
        if best is None or score > best[0]:
            best = (score, row)
    return best[1] if best else None


def _materialize_subject_mattes(config: dict, video: str, work_dir: str,
                                 qa_dir: str) -> tuple[dict, list[dict]]:
    """Replace auto battle-top placeholders with fail-closed alpha sequences."""
    from roto_matte import build_sequence

    rendered = copy.deepcopy(config)
    matte_rows: list[dict] = []
    reports: list[dict] = []
    root = Path(work_dir, "subject_mattes")
    root.mkdir(parents=True, exist_ok=True)
    for index, effect in enumerate(rendered.get("mask_sheens", [])):
        if str(effect.get("shape", "")) != "auto_sequence":
            continue
        ident = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(effect.get("id", f"sheen-{index}"))).strip("-")
        matte_dir = root / (ident or f"sheen-{index}")
        if matte_dir.exists():
            shutil.rmtree(matte_dir)
        matte_spec = dict(effect)
        # The reveal may last only ~0.6s while its identity label remains for
        # 1-2s.  Build one shared track over the union so the label never
        # freezes as soon as the sheen ends.
        related_labels = []
        effect_center = _bbox_center(list(effect["initial_bbox"]))
        for label in rendered.get("tracked_labels", []):
            if str(label.get("tracking_source", "")) != "subject_matte":
                continue
            overlap = max(0.0, min(float(effect.get("end", 0)), float(label.get("end", 0))) -
                          max(float(effect.get("start", 0)), float(label.get("start", 0))))
            if overlap <= 0:
                continue
            label_center = _bbox_center(list(label["initial_bbox"]))
            distance = ((effect_center[0] - label_center[0]) ** 2 +
                        (effect_center[1] - label_center[1]) ** 2) ** .5
            related_labels.append((distance, label))
        related = min(related_labels, key=lambda row: row[0])[1] if related_labels else None
        track_start = min(float(effect["start"]), float(related.get("start", effect["start"]))) \
            if related else float(effect["start"])
        track_end = max(float(effect["end"]), float(related.get("end", effect["end"]))) \
            if related else float(effect["end"])
        matte_spec.update({
            "video": video,
            "start": track_start,
            "end": track_end,
            "profile": str(effect.get("matte_profile", "round_product_grabcut")),
            "target_kind": "subject_object",
            "output_geometry": str(effect.get("output_geometry", "segmented_silhouette")),
        })
        search_padding = max(0.0, min(.35, float(effect.get("matte_search_padding", .18))))
        matte_spec["initial_bbox"] = _expand_box(list(effect["initial_bbox"]), search_padding)
        matte_spec["keyframes"] = [
            {"time": float(row["time"]),
             "bbox": _expand_box(list(row["bbox"]), search_padding)}
            for row in effect.get("keyframes", [])
        ]
        report = build_sequence(matte_spec, matte_dir)
        if report.get("status") != "GREEN":
            raise RuntimeError(
                "subject matte %s failed closed: confidence=%s chatter=%s checks=%s" % (
                    ident, report.get("confidence_p05"),
                    report.get("aligned_silhouette_change_px_p95_at_256"),
                    report.get("quality_checks"),
                ))
        _require_green_roto_report(report, matte_dir, effect_id=ident)
        keyframes = _smooth_subject_keyframes(
            report, padding=float(effect.get("track_padding", .035)))
        if not keyframes:
            raise RuntimeError("subject matte %s produced no usable subject track" % ident)
        original_bbox = list(effect["initial_bbox"])
        effect.update({
            "shape": "sequence",
            "initial_bbox": list(keyframes[0]["bbox"]),
            "keyframes": keyframes,
            "matte_sequence_dir": str(matte_dir),
            "matte_sequence_fps": float(report["fps"]),
            "matte_sequence_start": float(report["sequence_start"]),
            "matte_sequence_frames": int(report["frames"]),
            "matte_sequence_prefix": "frame_",
            "matte_sequence_digits": 6,
            "matte_sequence_extension": ".png",
            "matte_quality_status": "GREEN",
            "matte_capability": "AUTO_WITH_REVIEW",
            "matte_sequence_report": str(report["report_path"]),
            "matte_sequence_contact_sheet": str(report["contact_sheet"]),
            "matte_human_review_status": "PENDING",
            "matte_promotion_blocked_until": list(report["promotion_blocked_until"]),
        })
        contact = Path(str(report["contact_sheet"]))
        qa_contact = Path(qa_dir, "ROTO_%s.jpg" % ident)
        if contact.is_file():
            shutil.copy2(contact, qa_contact)
        row = {"effect": effect, "original_bbox": original_bbox,
               "keyframes": keyframes, "report": report}
        matte_rows.append(row)
        reports.append({
            "id": ident, "effect_id": ident, "status": report["status"],
            "capability": "AUTO_WITH_REVIEW",
            "human_review_status": "PENDING",
            "frames": int(report["frames"]), "fps": float(report["fps"]),
            "sequence_dir": str(matte_dir),
            "confidence_p05": report["confidence_p05"],
            "edge_chatter_px_p95": report["aligned_silhouette_change_px_p95_at_256"],
            "quality_checks": report.get("quality_checks"),
            "report": str(report["report_path"]),
            "contact_sheet": str(report["contact_sheet"]),
            "qa_contact_sheet": str(qa_contact),
            "promotion_blocked_until": list(report["promotion_blocked_until"]),
        })

    for label in rendered.get("tracked_labels", []):
        if str(label.get("tracking_source", "")) != "subject_matte":
            continue
        target = _pair_label_to_matte(label, matte_rows)
        if target is None:
            raise RuntimeError("tracked identity label %s has no overlapping subject matte" %
                               label.get("id", "unknown"))
        label.update({
            "tracking_mode": "keyframes",
            "initial_bbox": list(target["keyframes"][0]["bbox"]),
            "keyframes": copy.deepcopy(target["keyframes"]),
            "track_quality_status": "GREEN",
            "track_source_id": target["effect"].get("id"),
            "lost_hold_frames": 2,
        })
    return rendered, reports


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
    render_spec_data = copy.deepcopy(config)
    render_spec_data["video"] = output
    render_spec_data.setdefault("start", 0.0)
    render_spec_data.setdefault("end", float(ready["_dur"]))
    # Segment and derive motion from the clean, colour-graded visual concat.
    # The delivery master already contains hook/subtitle typography; using it
    # as detector input lets large captions become false "objects" and is the
    # source of the cyan blocks rejected in review.  Timelines are identical,
    # so the clean matte sequence can still composite onto the final master.
    clean_visual = os.path.join(work_dir, "current_vis.mp4")
    matte_source = clean_visual if os.path.isfile(clean_visual) else output
    render_spec_data, matte_reports = _materialize_subject_mattes(
        render_spec_data, matte_source, work_dir, qa_dir)
    if matte_reports:
        Path(qa_dir, "ROTO_MATTE.json").write_text(
            json.dumps({"status": "GREEN", "mattes": matte_reports}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
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
    report["subject_mattes"] = matte_reports
    report["roto_sequences"] = matte_reports
    report["human_review"] = {
        "required": bool(matte_reports),
        "status": "PENDING" if matte_reports else "NOT_APPLICABLE",
        "boundary": (
            "machine GREEN permits a review candidate only; Hao approval is still required "
            "before Quality-95 certification"
        ),
    }
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


def self_test() -> None:
    """Exercise helper -> auto roto -> validator -> real render as one closure."""
    import hashlib

    import cv2

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
            # Leave a real background ring around the radial subject so the
            # canonical search-padding path exercises both GrabCut classes.
            cv2.circle(frame, (x + 54, y + 54), 34, (218, 225, 235), -1, cv2.LINE_AA)
            cv2.circle(frame, (x + 54, y + 54), 16, (35, 145, 238), -1, cv2.LINE_AA)
            cv2.line(frame, (x + 34, y + 43), (x + 74, y + 65), (255, 255, 255), 3)
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
        # Keep this closure fixture deterministic: CSRT/refined radial tracking
        # has its own roto_matte self-test, while this test proves the authored
        # plan -> sequence receipt -> tracked render -> atomic publish boundary.
        sheen["bbox_tracking"] = "authored"
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
