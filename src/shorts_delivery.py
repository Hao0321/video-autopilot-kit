# -*- coding: utf-8 -*-
"""Post-render tracking, technical QA and report writing for Shorts."""
from __future__ import annotations

import copy
import json
import math
import os
import re
import shutil
import tempfile
from fractions import Fraction
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


SHORTS_FPS = Fraction(30, 1)      # documented export spec: 1080x1920 at exactly 30/1 (CFR)
TRUE_PEAK_MAX_DBTP = -1.0         # documented delivery ceiling (-14 LUFS / -1 dBTP)
LOOP_SIM_MIN = 0.6                # first/last frame correlation floor when a loop is required


def _export_spec_ok(probe_line: str) -> bool:
    """``width,height,r_frame_rate`` probe text -> 1080x1920 at exactly 30/1 fps.

    29.97 (30000/1001) is a different rate, never "30" (the old prefix check
    accepted it, and 300/1, as a pass)."""
    lines = (probe_line or "").strip().splitlines()
    parts = [part.strip() for part in lines[0].split(",")] if lines else []
    if len(parts) < 3 or parts[:2] != ["1080", "1920"]:
        return False
    try:
        return Fraction(parts[2]) == SHORTS_FPS
    except (ValueError, ZeroDivisionError):
        return False


def _ebur128_summary(stderr: str) -> tuple[float | None, float | None]:
    """ebur128 summary -> (integrated LUFS, true peak dBTP); missing values stay None."""
    from delivery_media_ops import _parse_db

    matches = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", stderr or "")
    peak = re.search(r"True peak:\s*\n\s*Peak:\s*(\S+)\s*dB", stderr or "")
    return (float(matches[-1]) if matches else None,
            _parse_db(peak.group(1)) if peak else None)


def _stream_durations(video: str) -> dict:
    """codec_type -> finite duration of its first stream; a stream without one is absent."""
    stream_probe = run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,duration", "-of", "json", video]).stdout
    try:
        rows = json.loads(stream_probe).get("streams") or []
    except (TypeError, ValueError, AttributeError):
        return {}
    durations: dict = {}
    for row in rows:
        try:
            value = float(row.get("duration"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            durations.setdefault(row.get("codec_type"), value)
    return durations


def _short_audio_gates(result: dict, video: str) -> None:
    """A/V length, integrated loudness and true peak; a missing stream fails."""
    durations = _stream_durations(video)
    result["missing_streams"] = [kind for kind in ("video", "audio") if kind not in durations]
    result["av_duration_delta"] = None if result["missing_streams"] else \
        round(abs(durations["video"] - durations["audio"]), 2)
    result["av_sync_ok"] = result["av_duration_delta"] is not None and result["av_duration_delta"] <= .15
    loudness = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vn",
                    "-af", "ebur128=peak=true", "-f", "null", "-"])
    result["lufs"], result["true_peak"] = _ebur128_summary(loudness.stderr)
    result["lufs_ok"] = result["lufs"] is not None and abs(result["lufs"] + 14) <= 1.5
    result["true_peak_ok"] = (result["true_peak"] is not None and
                              result["true_peak"] <= TRUE_PEAK_MAX_DBTP)


def _short_visual_gates(result: dict, video: str, measured: float) -> None:
    """Reuse the long-form detectors: WCAG flash, black runs, dead borders, dead air."""
    from media_delivery_qa import (_guarded, check_black_runs, check_dead_air,
                                   detect_dead_borders, detect_photosensitive_flash)

    result["flash"] = _guarded(detect_photosensitive_flash, video, duration=measured)
    result["black_runs"] = _guarded(check_black_runs, video, duration=measured)
    result["borders"] = _guarded(detect_dead_borders, video)
    result["dead_air"] = _guarded(check_dead_air, video)
    for key in ("flash", "black_runs", "borders", "dead_air"):
        result[key + "_ok"] = result[key]["ok"] is True


def _short_loop_gate(result: dict, ready: dict, video: str, measured: float, qa_dir: str) -> None:
    """Gate first/last-frame similarity only when the plan requires a seamless loop.

    ``loop_policy`` is the shorts_gate S-D contract (default ``required``);
    ``forbidden`` keeps the value informational, anything else cannot be verified."""
    first = _frame_array(video, .08, qa_dir)
    last = _frame_array(video, measured - .25, qa_dir)
    similarity = None
    if first is not None and last is not None:
        with np.errstate(all="ignore"):
            value = float(np.corrcoef(first.ravel(), last.ravel())[0, 1])
        similarity = round(value, 2) if math.isfinite(value) else None
    result["loop_sim"] = similarity
    result["loop_policy"] = policy = str(ready.get("loop_policy", "required"))
    result["loop_required"] = policy != "forbidden"
    result["loop_ok"] = policy == "forbidden" or (
        policy == "required" and similarity is not None and similarity >= LOOP_SIM_MIN)


def _short_verdict(result: dict) -> None:
    gates = ["spec_ok", "dur_ok", "duration_match_ok", "av_sync_ok", "lufs_ok", "true_peak_ok",
             "flash_ok", "black_runs_ok", "borders_ok", "dead_air_ok", "loop_ok"]
    result["failed_checks"] = [gate[:-3] for gate in gates if result.get(gate) is not True]
    result["all_green"] = not result["failed_checks"]


def _seconds(value) -> str:
    return "n/a" if value is None else "%.2fs" % value


def run_short_qa(video: str, ready: dict, output_dir: str, *,
                 duration_range: tuple[float, float] = (13.0, 25.5)) -> dict:
    """Check export spec, duration, A/V sync, loudness and review evidence.

    ``duration_range`` keeps the original Shorts gate as the default while
    allowing an explicitly routed vertical remix to declare its own contract.
    Callers may not silently widen the range after a failure; the routed plan
    must provide the format-specific bounds before rendering.
    ``all_green`` additionally requires true peak <= -1 dBTP, both streams,
    the shared flash/black/border/dead-air detectors and, when the plan
    requires a loop, a matching first/last frame; ``failed_checks`` names
    every gate that is not a strict pass.
    """
    qa_dir = os.path.join(output_dir, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    result: dict = {}
    wh = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height,r_frame_rate",
              "-of", "csv=p=0", video]).stdout.strip()
    result["format"] = wh
    result["spec_ok"] = _export_spec_ok(wh)
    measured = duration(video)
    result["dur"] = round(measured, 2)
    min_duration, max_duration = (float(duration_range[0]), float(duration_range[1]))
    if min_duration <= 0 or max_duration < min_duration:
        raise ValueError("invalid duration_range: %r" % (duration_range,))
    result["duration_range"] = [min_duration, max_duration]
    result["dur_ok"] = min_duration <= measured <= max_duration
    planned = ready.get("_dur")
    result["planned_dur"] = None if planned is None else round(float(planned), 2)
    result["duration_delta"] = None if planned is None else round(abs(measured - float(planned)), 2)
    result["duration_match_ok"] = result["duration_delta"] is not None and result["duration_delta"] <= .15
    _short_audio_gates(result, video)
    _short_visual_gates(result, video, measured)
    _short_loop_gate(result, ready, video, measured, qa_dir)
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
    _short_verdict(result)
    print("[qa] %s dur=%.1fs drift=%s av=%s LUFS=%s TP=%s loop=%s %s%s" %
          (os.path.basename(video), result["dur"], _seconds(result["duration_delta"]),
           _seconds(result["av_duration_delta"]), result["lufs"], result["true_peak"],
           result["loop_sim"], "GREEN" if result["all_green"] else "RED",
           "" if result["all_green"] else " (" + ", ".join(result["failed_checks"]) + ")"))
    return result


def write_short_report(source_dir: str, spec: dict, ready: dict, qa: dict, output: str) -> None:
    lines = ["# Shorts 交付報告 — %s" % spec["name"], "",
             "- 地點／題材：**%s**／%s" % (spec.get("place", ""), spec.get("what", "")),
             "- 片長：%.1fs；段落：%d" % (ready["_dur"], len(spec["segs"])),
             "- 格式：%s；LUFS：%s；TP：%s dBTP；A/V 差：%s；輸出差：%s" %
             (qa.get("format"), qa.get("lufs"), qa.get("true_peak"),
              _seconds(qa.get("av_duration_delta")), _seconds(qa.get("duration_delta"))),
             "- 技術 QA：**%s**%s" % ("GREEN" if qa.get("all_green") else "RED",
                                    "" if qa.get("all_green") else
                                    "（未通過：%s）" % ", ".join(qa.get("failed_checks") or ["?"])),
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


def _qa_self_test() -> None:
    """Fail-closed technical QA regressions on tiny real lavfi fixtures (ffmpeg required)."""
    import contextlib
    import io

    from delivery_media_ops import _lavfi_clip

    assert _export_spec_ok("1080,1920,30/1\n") and _export_spec_ok("1080,1920,30/1,\r")
    assert not _export_spec_ok("1080,1920,30000/1001"), "29.97 fps is not the 30/1 spec"
    assert not _export_spec_ok("1080,1920,300/1") and not _export_spec_ok("1080,1920,0/0")
    assert not _export_spec_ok("") and not _export_spec_ok("1920,1080,30/1")
    summary = "  Integrated loudness:\n    I:         -14.9 LUFS\n  True peak:\n    Peak:        2.6 dBFS\n"
    assert _ebur128_summary(summary) == (-14.9, 2.6), _ebur128_summary(summary)
    assert _ebur128_summary(summary.replace("2.6", "-inf"))[1] == -200.0
    assert _ebur128_summary("") == (None, None)
    tone = "aevalsrc=0.21*sin(2*PI*997*t)*clip((2.55-t)/0.35\\,0\\,1):s=48000:c=stereo:d=3"
    over = "aevalsrc=0.19*sin(2*PI*997*t)+if(lt(mod(t\\,0.25)\\,0.001)\\,0.9\\,0):s=48000:c=stereo:d=3"
    small = "s=180x320:r=30"
    with tempfile.TemporaryDirectory(prefix="shorts-qa-") as temp, \
            contextlib.redirect_stdout(io.StringIO()):
        def clip(name: str, video: str, audio: str | None = None) -> str:
            return _lavfi_clip(os.path.join(temp, name + ".mp4"), video, audio)

        def qa(path: str, **ready) -> dict:
            plan = dict({"caps": [], "_dur": 3.0}, **ready)
            return run_short_qa(path, plan, temp, duration_range=(1.0, 5.0))

        good = qa(clip("good", "smptehdbars=s=1080x1920:r=30:d=3", tone))
        assert good["all_green"] and good["failed_checks"] == [], good
        bad = qa(clip("strobe_over", f"color=c=white:{small}:d=3,format=yuv420p,"
                                     "geq=lum='if(mod(N,2),16,235)':cb=128:cr=128", over))
        assert {"spec", "flash", "true_peak"} <= set(bad["failed_checks"]), bad["failed_checks"]
        assert bad["lufs_ok"] and not bad["all_green"], "true peak must gate on its own"
        silent = clip("loop_noaudio", f"smptehdbars={small}:d=1.5[a];testsrc2={small}:d=1.5[b];"
                                      "[a][b]concat=n=2:v=1:a=0")
        loop = qa(silent)
        assert loop["missing_streams"] == ["audio"] and loop["av_sync_ok"] is False, loop
        assert loop["av_duration_delta"] is None and loop["loop_ok"] is False, loop
        assert qa(silent, loop_policy="forbidden")["loop_ok"] is True
        assert "duration_match" in qa(silent, _dur=None)["failed_checks"]


def self_test() -> None:
    """Exercise helper -> auto roto -> validator -> real render as one closure."""
    import hashlib

    import cv2

    from battle_plan_components import identity_label, subject_sheen
    from tracked_graphics import validate_spec

    _qa_self_test()

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
