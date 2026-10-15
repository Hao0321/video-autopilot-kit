"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations
from pathlib import Path
import cv2
import numpy as np
from tracked_graphics import _keyframed_bbox
from roto_mask_geometry import _round_product_mask, _skin_occlusion


class MatteFrameCollector:
    def __init__(self, spec, start, output_dir, fps, width, height, expected):
        self.spec, self.start, self.output_dir = spec, start, output_dir
        self.fps, self.width, self.height, self.expected = fps, width, height, expected
        self.rows, self.raw_masks, self.skin_masks = [], [], []
        self.debug_frames = {}
        self.sample_every = max(1, expected // 8)
        self.use_tracker = (str(spec.get("subject_class", "")) == "battle_top" and
                            str(spec.get("bbox_tracking", "csrt_radial")) == "csrt_radial")
        self.tracker = None
        self.tracker_updates = 0
        self.radial_hint = None

    def clip_box(self, box):
        bx, by, bw, bh = [float(value) for value in box]
        bx = max(0.0, min(max(0.0, self.width - 4.0), bx))
        by = max(0.0, min(max(0.0, self.height - 4.0), by))
        bw, bh = max(4.0, min(self.width - bx, bw)), max(4.0, min(self.height - by, bh))
        return bx, by, bw, bh

    def crop_and_mask(self, frame, box):
        bx, by, bw, bh = self.clip_box(box)
        cix, ciy = round(bx), round(by)
        crw = max(4, min(self.width - cix, round(bw)))
        crh = max(4, min(self.height - ciy, round(bh)))
        shot = frame[ciy:ciy + crh, cix:cix + crw]
        matte, frame_metrics = _round_product_mask(shot, self.spec, self.radial_hint)
        if float(frame_metrics.get("radial_prior_used", 0)) > 0:
            self.radial_hint = (
                float(frame_metrics["radial_prior_center_x"]),
                float(frame_metrics["radial_prior_center_y"]),
                float(frame_metrics["radial_prior_radius_ratio"]),
            )
        return cix, ciy, crw, crh, shot, matte, frame_metrics

    def collect_frame(self, frame_index, frame):
        source_time = self.start + frame_index / self.fps
        authored = _keyframed_bbox(self.spec, source_time, self.width, self.height)
        tracking_status = "authored"
        tracked = None
        if self.tracker is not None:
            tracked_ok, raw_tracked = self.tracker.update(frame)
            if tracked_ok:
                tx, ty, tw, th = self.clip_box(raw_tracked)
                if tw >= 28 and th >= 28:
                    tracked = (tx, ty, tw, th)
                    tracking_status = "csrt"
                    self.tracker_updates += 1
        ix, iy, rw, rh, crop, local_alpha, metrics = self.crop_and_mask(
            frame, tracked or authored)

        # The first authored box is a search window, not the delivered
        # track.  Refine it to the segmented/radial product before CSRT is
        # initialised so the tracker follows the top rather than the hand.
        if frame_index == 0 and self.use_tracker:
            ys, xs = np.where(local_alpha >= 48)
            if xs.size and ys.size:
                left, right = int(xs.min()), int(xs.max()) + 1
                top, bottom = int(ys.min()), int(ys.max()) + 1
                local_w, local_h = right - left, bottom - top
                padding = float(self.spec.get("tracker_padding", .10))
                px, py = local_w * padding, local_h * padding
                refined = self.clip_box((ix + left - px, iy + top - py,
                                    local_w + px * 2, local_h + py * 2))
                # Preserve the detected disc in full-frame coordinates
                # while changing from the large authored search window to
                # the tight tracker box. Later frames keep this stable
                # normalised disc prior inside the moving CSRT track.
                if self.radial_hint is not None:
                    full_cx = ix + self.radial_hint[0] * max(1, rw - 1)
                    full_cy = iy + self.radial_hint[1] * max(1, rh - 1)
                    full_radius = self.radial_hint[2] * min(rw, rh)
                    rbx, rby, rbw, rbh = refined
                    self.radial_hint = (
                        (full_cx - rbx) / max(1.0, rbw - 1),
                        (full_cy - rby) / max(1.0, rbh - 1),
                        full_radius / max(1.0, min(rbw, rbh)),
                    )
                ix, iy, rw, rh, crop, local_alpha, metrics = self.crop_and_mask(frame, refined)
                self.tracker = cv2.TrackerCSRT_create()
                self.tracker.init(frame, tuple(int(round(value)) for value in refined))
                tracking_status = "csrt_seed"
        self.raw_masks.append(cv2.resize(local_alpha, (256, 256), interpolation=cv2.INTER_AREA))
        skin = (_skin_occlusion(crop, self.spec) if self.spec.get("exclude_skin_occlusion") is True
                else np.zeros(crop.shape[:2], np.uint8))
        self.skin_masks.append(cv2.resize(skin, (256, 256), interpolation=cv2.INTER_AREA))
        if frame_index % self.sample_every == 0 or frame_index == self.expected - 1:
            self.debug_frames[frame_index] = frame.copy()
        self.rows.append({
            "frame": frame_index, "source_time": round(source_time, 5),
            "bbox": [ix, iy, rw, rh],
            "bbox_tracking_status": tracking_status,
            "matte": str(self.output_dir / f"frame_{frame_index:06d}.png"), **metrics,
        })

    def collect(self, cap):
        for frame_index in range(self.expected):
            ok, frame = cap.read()
            if not ok:
                break
            self.collect_frame(frame_index, frame)

    def result(self):
        if len(self.rows) != self.expected:
            raise RuntimeError(f"matte sequence incomplete: expected {self.expected}, rendered {len(self.rows)}")
        # Remove single-frame tracker noise without causal lag.  Masks are
        # normalised to 256px, so resizing them into these centred-median boxes
        # preserves the photographed motion while stabilising the composite.
        if self.use_tracker and len(self.rows) >= 3:
            boxes = np.asarray([row["bbox"] for row in self.rows], dtype=np.float64)
            smooth = boxes.copy()
            for index in range(len(boxes)):
                left, right = max(0, index - 1), min(len(boxes), index + 2)
                smooth[index] = np.median(boxes[left:right], axis=0)
            for row, box in zip(self.rows, smooth):
                row["bbox"] = [round(float(value), 3) for value in self.clip_box(box)]
        return {
            "fps": self.fps, "width": self.width, "height": self.height,
            "rows": self.rows, "raw_masks": self.raw_masks, "skin_masks": self.skin_masks,
            "debug_frames": self.debug_frames,
            "bbox_tracking_enabled": self.use_tracker,
            "bbox_tracking_update_ratio": round(self.tracker_updates / max(1, self.expected - 1), 5),
        }
