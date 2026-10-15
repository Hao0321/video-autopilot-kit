"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

def _self_test_matte_delivery(_host, authored, output_dir, report, source, validate_spec):
    if not report or report.get("status") != "GREEN":
        raise AssertionError(report)
    if authored["tracked_graphics"]["mask_sheens"][0]["shape"] != "auto_sequence":
        raise AssertionError("authored plan was mutated during materialization")
    materialized = _host['json'].loads(
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
    tracking_receipt = _host['json'].loads(
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


def self_test(_host) -> None:
    """Exercise helper -> auto roto -> validator -> real render as one closure."""
    import hashlib

    import cv2

    from battle_plan_components import identity_label, subject_sheen
    from tracked_graphics import validate_spec

    with _host['tempfile'].TemporaryDirectory(prefix="shorts-delivery-tracking-") as temp:
        root = _host['Path'](temp)
        output_dir = root / "out"
        work_dir = output_dir / "_work"
        output_dir.mkdir(parents=True)
        source = output_dir / "current.mp4"
        fps, frame_count = 30, 30
        writer = cv2.VideoWriter(
            str(source), cv2.VideoWriter_fourcc(*"mp4v"), fps, (640, 360),
        )
        for frame_index in range(frame_count):
            frame = _host['np'].full((360, 640, 3), (28, 34, 43), _host['np'].uint8)
            x = round(242 + frame_index * .6)
            y = round(172 + 5 * _host['np'].sin(frame_index * .18))
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
        report = _host['apply_tracked_graphics'](
            authored, {"_dur": 1.0}, str(source), str(output_dir), str(work_dir),
        )
        _host['_self_test_matte_delivery'](authored, output_dir, report, source, validate_spec)

        before = hashlib.sha256(source.read_bytes()).hexdigest()
        broken = _host['copy'].deepcopy(authored)
        broken["tracked_graphics"]["mask_sheens"][0]["evidence"] = ""
        try:
            _host['apply_tracked_graphics'](
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
