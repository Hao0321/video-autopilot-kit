# -*- coding: utf-8 -*-
"""Evidence-first camera calibration, shot matching and color scopes.

This layer runs before the creative LUT.  It deliberately fails closed:
unidentified cameras, unverified profiles, Log and HDR footage are reported but
never silently corrected.  A ColorChecker can enter through measured patch JSON;
automatic chart detection is intentionally out of scope until it is verified.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PROFILE_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "camera_color_profiles.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _atomic_json(path: str | Path, payload: dict) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate = target.with_suffix(target.suffix + ".candidate")
    candidate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(candidate, target)
    return target


def probe_media(path: str | Path) -> dict:
    src = Path(path)
    if src.suffix.lower() in IMAGE_EXTS:
        return {"color_space": "image", "color_transfer": "unknown", "tags": {}}
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=color_space,color_transfer,color_primaries,color_range:format_tags",
         "-of", "json", str(src)], capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError("ffprobe failed: " + (run.stderr or "")[-500:])
    data = json.loads(run.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    stream["tags"] = (data.get("format") or {}).get("tags") or {}
    return stream


def camera_identity(path: str | Path, explicit_camera_id: str | None = None) -> dict:
    meta = probe_media(path)
    tags = {str(k).lower(): str(v).strip() for k, v in (meta.get("tags") or {}).items()}
    make = tags.get("make") or tags.get("com.apple.quicktime.make") or ""
    model = tags.get("model") or tags.get("com.apple.quicktime.model") or ""
    observed = "_".join(x.lower().replace(" ", "_") for x in (make, model) if x).strip("_")
    return {
        "camera_id": explicit_camera_id or observed or "unknown",
        "source": "explicit" if explicit_camera_id else ("metadata" if observed else "unknown"),
        "make": make, "model": model,
        "color_transfer": str(meta.get("color_transfer") or "unknown").lower(),
        "color_space": str(meta.get("color_space") or "unknown").lower(),
    }


def match_profile(path: str | Path, explicit_camera_id: str | None = None) -> dict:
    identity = camera_identity(path, explicit_camera_id)
    profiles = _read_json(PROFILE_PATH).get("profiles", {})
    profile = profiles.get(identity["camera_id"])
    verified = bool(profile and profile.get("status") == "verified")
    transfer = identity["color_transfer"]
    unsafe = transfer in {"arib-std-b67", "smpte2084"} or any(x in identity["camera_id"] for x in ("log", "slog", "vlog", "clog"))
    reason = "verified_exact_match" if verified and not unsafe else (
        "hdr_or_log_requires_explicit_input_transform" if unsafe else
        "unverified_or_unknown_camera")
    return {"identity": identity, "profile": profile, "auto_apply": verified and not unsafe, "reason": reason}


def camera_filter(path: str | Path, explicit_camera_id: str | None = None) -> tuple[str, dict]:
    matched = match_profile(path, explicit_camera_id)
    if not matched["auto_apply"]:
        return "", matched
    profile = matched["profile"]
    matrix = np.asarray(profile.get("matrix", np.eye(3)), dtype=float)
    if matrix.shape != (3, 3) or np.max(np.abs(matrix - np.eye(3))) > .35:
        raise ValueError("verified camera matrix exceeds safe bound")
    names = (("rr", "rg", "rb"), ("gr", "gg", "gb"), ("br", "bg", "bb"))
    fields = [f"{names[r][c]}={matrix[r, c]:.7f}" for r in range(3) for c in range(3)]
    filters = ["colorchannelmixer=" + ":".join(fields)]
    exposure = max(-.35, min(.35, float(profile.get("exposure_ev", 0.0))))
    saturation = max(.85, min(1.15, float(profile.get("saturation", 1.0))))
    if abs(exposure) > 1e-6 or abs(saturation - 1.0) > 1e-6:
        filters.append(f"eq=brightness={exposure * .055:.6f}:saturation={saturation:.6f}")
    matched["applied_filter"] = ",".join(filters)
    return matched["applied_filter"], matched


def _sample_image(path: str | Path, at: float | None = None) -> Image.Image:
    src = Path(path)
    if src.suffix.lower() in IMAGE_EXTS:
        return Image.open(src).convert("RGB")
    with tempfile.TemporaryDirectory(prefix="hao-calibration-frame-") as td:
        frame = Path(td) / "frame.png"
        args = ["ffmpeg", "-v", "error", "-y"]
        if at is not None:
            args += ["-ss", str(max(0.0, at))]
        args += ["-i", str(src), "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", str(frame)]
        run = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if run.returncode or not frame.exists():
            raise RuntimeError("frame extraction failed: " + (run.stderr or "")[-500:])
        return Image.open(frame).convert("RGB").copy()


def frame_metrics(image: Image.Image) -> dict:
    arr = np.asarray(ImageOps.contain(image.convert("RGB"), (960, 960)), dtype=np.float32) / 255.0
    rgb = arr.reshape(-1, 3)
    luma = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    mx, mn = rgb.max(axis=1), rgb.min(axis=1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    # Broad YCbCr skin proposal. It is a diagnostic, not face recognition.
    u8 = (rgb * 255).astype(np.float32)
    cb = 128 - .168736*u8[:, 0] - .331264*u8[:, 1] + .5*u8[:, 2]
    cr = 128 + .5*u8[:, 0] - .418688*u8[:, 1] - .081312*u8[:, 2]
    skin = (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173) & (luma > .12)
    skin_rgb = rgb[skin] if np.any(skin) else np.empty((0, 3))
    means = rgb.mean(axis=0)
    return {
        "luma_mean": round(float(luma.mean()), 5),
        "luma_p05": round(float(np.quantile(luma, .05)), 5),
        "luma_p95": round(float(np.quantile(luma, .95)), 5),
        "contrast": round(float(np.std(luma)), 5),
        "saturation_mean": round(float(sat.mean()), 5),
        "clip_low_pct": round(float(np.mean(luma < .01) * 100), 4),
        "clip_high_pct": round(float(np.mean(luma > .99) * 100), 4),
        "rgb_mean": [round(float(x), 5) for x in means],
        "wb_cast": [round(float(means[0] - means[1]), 5), round(float(means[2] - means[1]), 5)],
        "skin_candidate_pct": round(float(np.mean(skin) * 100), 4),
        "skin_rgb_mean": [round(float(x), 5) for x in skin_rgb.mean(axis=0)] if len(skin_rgb) else None,
    }


def inspect_source(path: str | Path, explicit_camera_id: str | None = None) -> dict:
    matched = match_profile(path, explicit_camera_id)
    metrics = frame_metrics(_sample_image(path))
    warnings = []
    if metrics["clip_high_pct"] > 2.0: warnings.append("highlight_clipping")
    if metrics["clip_low_pct"] > 5.0: warnings.append("shadow_crush")
    if max(abs(x) for x in metrics["wb_cast"]) > .08: warnings.append("white_balance_cast")
    if metrics["skin_candidate_pct"] > .5 and metrics["skin_rgb_mean"] is None: warnings.append("skin_measurement_unavailable")
    return {"path": str(Path(path).resolve()), "camera": matched,
            "metrics": metrics, "warnings": warnings,
            "stage_order": ["verified_camera_correction", "input_transform", "creative_lut", "graphics"]}


def shot_match(paths: list[str], anchor: int = 0) -> dict:
    if not paths:
        raise ValueError("shot_match needs at least one source")
    rows = [{"path": str(Path(path).resolve()), "metrics": frame_metrics(_sample_image(path))} for path in paths]
    if not 0 <= anchor < len(rows):
        raise IndexError("anchor out of range")
    base = rows[anchor]["metrics"]
    for row in rows:
        cur = row["metrics"]
        luma_delta = base["luma_mean"] - cur["luma_mean"]
        sat_ratio = base["saturation_mean"] / max(.05, cur["saturation_mean"])
        base_rgb, cur_rgb = np.asarray(base["rgb_mean"]), np.asarray(cur["rgb_mean"])
        gains = np.clip(base_rgb / np.maximum(.05, cur_rgb), .88, 1.12)
        row["suggestion"] = {
            "exposure_ev": round(float(np.clip(luma_delta * 1.8, -.35, .35)), 4),
            "saturation": round(float(np.clip(sat_ratio, .88, 1.12)), 4),
            "channel_gains": [round(float(x), 4) for x in gains],
            "auto_apply": False,
            "reason": "bounded shot-match suggestion; reviewer approval required"
        }
    return {"schema_version": 1, "anchor": anchor, "shots": rows,
            "policy": "Match exposure/WB before creative look; never chase exact equality across intentional lighting changes."}


def render_scopes(path: str | Path, output: str | Path, at: float = 0.0) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hao-scopes-") as td:
        td = Path(td)
        original = td / "original.png"; wave = td / "wave.png"; vector = td / "vector.png"
        base = ["ffmpeg", "-v", "error", "-y", "-ss", str(max(0.0, at)), "-i", str(path), "-frames:v", "1"]
        commands = [
            base + ["-vf", "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2", str(original)],
            base + ["-vf", "waveform=mode=column:display=overlay:components=7:scale=digital,scale=960:540", str(wave)],
            base + ["-vf", "vectorscope=mode=color2,scale=960:540", str(vector)],
        ]
        for cmd in commands:
            run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if run.returncode:
                raise RuntimeError("scope render failed: " + (run.stderr or "")[-500:])
        canvas = Image.new("RGB", (1920, 1125), (9, 10, 13))
        canvas.paste(Image.open(original).convert("RGB"), (0, 45))
        canvas.paste(Image.open(wave).convert("RGB"), (960, 45))
        canvas.paste(Image.open(vector).convert("RGB"), (480, 585))
        draw = ImageDraw.Draw(canvas)
        draw.text((20, 14), "SOURCE", fill=(240, 240, 235))
        draw.text((980, 14), "WAVEFORM", fill=(240, 240, 235))
        draw.text((500, 554), "VECTORSCOPE", fill=(240, 240, 235))
        canvas.save(output, quality=94)
    return output


def _srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=float)
    rgb = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    xyz = rgb @ np.array([[.4124564, .3575761, .1804375], [.2126729, .7151522, .0721750], [.0193339, .1191920, .9503041]]).T
    xyz /= np.array([.95047, 1.0, 1.08883])
    d = 6/29
    f = np.where(xyz > d**3, np.cbrt(xyz), xyz/(3*d*d) + 4/29)
    return np.stack([116*f[:, 1]-16, 500*(f[:, 0]-f[:, 1]), 200*(f[:, 1]-f[:, 2])], axis=1)


def fit_colorchecker(measured_json: str | Path, output_profile: str | Path,
                     camera_id: str, label: str | None = None) -> dict:
    data = _read_json(measured_json)
    measured = np.asarray(data.get("measured_rgb"), dtype=float)
    reference = np.asarray(data.get("reference_rgb"), dtype=float)
    if measured.shape != reference.shape or measured.ndim != 2 or measured.shape[1] != 3 or len(measured) < 18:
        raise ValueError("ColorChecker JSON needs matching measured_rgb/reference_rgb arrays with at least 18 patches")
    if measured.max() > 1.5: measured /= 255.0
    if reference.max() > 1.5: reference /= 255.0
    matrix_t, *_ = np.linalg.lstsq(measured, reference, rcond=None)
    corrected = np.clip(measured @ matrix_t, 0, 1)
    delta_before = np.linalg.norm(_srgb_to_lab(measured) - _srgb_to_lab(reference), axis=1)
    delta_after = np.linalg.norm(_srgb_to_lab(corrected) - _srgb_to_lab(reference), axis=1)
    matrix = matrix_t.T
    status = "verified" if float(delta_after.mean()) <= float(delta_before.mean()) + 1e-6 and np.max(np.abs(matrix - np.eye(3))) <= .35 else "rejected"
    profile = {
        "label": label or camera_id, "camera_id": camera_id, "status": status,
        "input_space": data.get("input_space", "Rec.709 SDR"),
        "matrix": [[round(float(v), 8) for v in row] for row in matrix],
        "exposure_ev": 0.0, "saturation": 1.0,
        "calibration": {"method": "manual_measured_ColorChecker_patches",
                        "patch_count": len(measured),
                        "deltaE76_before_mean": round(float(delta_before.mean()), 3),
                        "deltaE76_after_mean": round(float(delta_after.mean()), 3),
                        "created_at": datetime.now(timezone.utc).isoformat()},
    }
    _atomic_json(output_profile, profile)
    return profile


def register_profile(profile_json: str | Path, registry: str | Path = PROFILE_PATH,
                     force: bool = False) -> dict:
    """Register only a verified measured profile; never infer or overwrite silently."""
    profile = _read_json(profile_json)
    camera_id = str(profile.get("camera_id") or "").strip()
    if profile.get("status") != "verified" or not camera_id:
        raise ValueError("only a verified profile with camera_id may be registered")
    target = Path(registry)
    data = _read_json(target)
    profiles = data.setdefault("profiles", {})
    if camera_id in profiles and not force:
        raise RuntimeError("camera profile already exists; use --force only after recalibration review")
    profiles[camera_id] = profile
    _atomic_json(target, data)
    return {"camera_id": camera_id, "registry": str(target.resolve()), "status": "REGISTERED_VERIFIED"}


def create_ab_review(before: str | Path, after: str | Path, output: str | Path,
                     title: str = "Color A/B review") -> Path:
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    def uri(path: str | Path) -> str:
        return Path(path).resolve().as_uri()
    doc = f"""<!doctype html><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font-family:system-ui;background:#0b0c10;color:#f5f5f0;margin:24px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}video,img{{width:100%;background:#000}}button{{padding:10px 16px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>{html.escape(title)}</h1><p>先看膚色、白平衡、明暗層次，再看風格。不得因為「比較鮮」就自動判新版較好。</p>
<div class='grid'><section><h2>A / Before</h2><video controls src='{uri(before)}'></video></section>
<section><h2>B / After</h2><video controls src='{uri(after)}'></video></section></div>
<p><button onclick="document.querySelectorAll('video').forEach(v=>{{v.currentTime=0;v.play()}})">同步從頭播放</button></p>"""
    out.write_text(doc, encoding="utf-8")
    return out


def _selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="hao-calibration-test-") as td:
        td = Path(td)
        neutral = Image.new("RGB", (320, 180), (128, 128, 128)); neutral.save(td / "neutral.png")
        cast = Image.new("RGB", (320, 180), (180, 120, 90)); cast.save(td / "cast.png")
        assert max(abs(x) for x in frame_metrics(neutral)["wb_cast"]) < .01
        report = shot_match([str(td / "neutral.png"), str(td / "cast.png")])
        assert len(report["shots"]) == 2 and report["shots"][1]["suggestion"]["auto_apply"] is False
        patches = np.random.default_rng(7).uniform(.06, .94, size=(24, 3))
        payload = {"measured_rgb": patches.tolist(), "reference_rgb": patches.tolist()}
        (td / "chart.json").write_text(json.dumps(payload), encoding="utf-8")
        profile = fit_colorchecker(td / "chart.json", td / "profile.json", "unit_test_camera")
        assert profile["status"] == "verified" and profile["calibration"]["deltaE76_after_mean"] < .001
        chain, match = camera_filter(td / "neutral.png")
        assert chain == "" and match["auto_apply"] is False
    print("color_calibration_lab self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    ins = sub.add_parser("inspect"); ins.add_argument("input"); ins.add_argument("--camera-id")
    mat = sub.add_parser("shot-match"); mat.add_argument("inputs", nargs="+"); mat.add_argument("--anchor", type=int, default=0); mat.add_argument("--output")
    sco = sub.add_parser("scopes"); sco.add_argument("input"); sco.add_argument("output"); sco.add_argument("--at", type=float, default=0)
    chk = sub.add_parser("colorchecker"); chk.add_argument("measured_json"); chk.add_argument("output_profile"); chk.add_argument("--camera-id", required=True); chk.add_argument("--label")
    reg = sub.add_parser("register"); reg.add_argument("profile_json"); reg.add_argument("--registry", default=str(PROFILE_PATH)); reg.add_argument("--force", action="store_true")
    ab = sub.add_parser("ab-review"); ab.add_argument("before"); ab.add_argument("after"); ab.add_argument("output"); ab.add_argument("--title", default="Color A/B review")
    args = ap.parse_args(argv)
    if args.cmd == "selftest": _selftest(); return 0
    if args.cmd == "inspect": result = inspect_source(args.input, args.camera_id)
    elif args.cmd == "shot-match":
        result = shot_match(args.inputs, args.anchor)
        if args.output: _atomic_json(args.output, result)
    elif args.cmd == "scopes": result = {"output": str(render_scopes(args.input, args.output, args.at))}
    elif args.cmd == "colorchecker": result = fit_colorchecker(args.measured_json, args.output_profile, args.camera_id, args.label)
    elif args.cmd == "register": result = register_profile(args.profile_json, args.registry, args.force)
    else: result = {"output": str(create_ab_review(args.before, args.after, args.output, args.title))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
