# -*- coding: utf-8 -*-
"""Visual Master: color-space-aware, single-look, low-strength grading.

This module routes a subject to a look, inspects source metadata and representative
frames, bakes conservative 3D LUTs, and returns filters that run before captions
or motion graphics.  It never overwrites raw footage and refuses unknown Log
material instead of pretending a Rec.709 LUT is an input transform.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PROFILE_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "color_grading_profiles.json"
TREND_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "design_trend_radar.json"
LUT_ROOT = PROJECT_ROOT / "assets" / "luts" / "hao-visual-master"
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
LOG_HINTS = ("log", "s-log", "v-log", "c-log", "d-log", "logc")
# Shared HDR->SDR normaliser; must equal silent_vlog_maker.constants.HDR_TO_SDR_FILTER
# (asserted by the self-test).  npl=100 maps SDR reference white (100 cd/m2) to 1.0.
HDR_TO_SDR_FILTER = ("zscale=t=linear:npl=100,format=gbrpf32le,tonemap=hable:desat=0,"
                     "zscale=p=bt709:t=bt709:m=bt709:r=tv")
# RGB-only filters never get an implicit YUV<->RGB conversion: FFmpeg uses BT.601
# for untagged frames and RGB filters drop the matrix tag on the way back.
RGB_FILTERS = frozenset({"lut3d", "curves", "colorbalance", "colorchannelmixer", "colorlevels",
                         "lutrgb", "haldclut", "vibrance", "selectivecolor", "colortemperature"})
BT709_TAGS = "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv"
BT709_ENCODE_ARGS = ("-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709")
_SCALE_MATRIX = {"bt470bg": "bt601", "smpte170m": "bt601", "fcc": "fcc",
                 "smpte240m": "smpte240m", "bt2020nc": "bt2020", "bt2020c": "bt2020"}


def _load_config() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _norm_format(value: str) -> str:
    key = str(value or "short").lower()
    if key in {"short", "shorts", "reel", "reels"}:
        return "short"
    if key in {"long", "longform", "youtube"}:
        return "longform"
    if key in {"podcast", "vlog"}:
        return key
    return "short"


def route_profile(domain: str, format_kind: str = "short") -> str:
    cfg = _load_config()
    key = str(domain or "general").lower()
    if _norm_format(format_kind) == "podcast":
        return "podcast_skin_neutral"
    if _norm_format(format_kind) == "vlog" and key in {"general", "documentary"}:
        return "vlog_bright_clean"
    return cfg["domain_routes"].get(key, "clean_neutral")


def plan_color_system(domain: str, format_kind: str = "short",
                      profile_override: str | None = None,
                      strength_override: float | None = None) -> dict:
    cfg = _load_config()
    fmt = _norm_format(format_kind)
    profile_id = str(profile_override or route_profile(domain, fmt))
    if profile_id not in cfg["profiles"]:
        raise ValueError("unknown color profile override %r" % profile_id)
    profile = cfg["profiles"][profile_id]
    scale = float(cfg["format_strength_scale"].get(fmt, 1.0))
    base = min(float(profile["max_strength"]), float(profile["base_strength"]) * scale)
    if strength_override is not None:
        absolute = float(cfg["working_contract"]["absolute_strength_ceiling"])
        base = min(float(profile["max_strength"]), absolute, max(.12, float(strength_override)))
    return {
        "system": cfg["standard_id"],
        "version": cfg["version"],
        "profile": profile_id,
        "label_zh": profile["label_zh"],
        "description": profile["description"],
        "base_strength": round(base, 4),
        "max_strength": float(profile["max_strength"]),
        "delivery_space": cfg["working_contract"]["delivery_space"],
        "stage": "source_before_graphics",
        "one_look_only": True,
        "never_grade_graphics": True,
        "unknown_log_policy": cfg["working_contract"]["unknown_log_policy"],
        "grade_gate_profile": "shorts" if fmt == "short" else
                              (fmt if fmt in {"vlog", "podcast"} else "teaching_longform"),
    }


def plan_trend_system(domain: str, format_kind: str = "short") -> dict:
    """Route one current signal without turning the whole video into a trend skin."""
    radar = json.loads(TREND_PATH.read_text(encoding="utf-8"))
    key = str(domain or "general").lower()
    routes = {
        "food": "all_the_feels", "cafe": "all_the_feels", "product": "all_the_feels",
        "travel": "local_flavor", "city": "local_flavor", "culture": "local_flavor",
        "toy": "surreal_silliness", "game": "surreal_silliness", "comedy": "surreal_silliness",
        "interview": "connectioneering", "podcast": "connectioneering",
        "documentary": "connectioneering", "vlog": "connectioneering",
        "business": "connectioneering", "ai": "connectioneering",
    }
    signal_id = routes.get(key, "connectioneering")
    signal = radar["signals"][signal_id]
    fmt = _norm_format(format_kind)
    return {
        "radar": radar["radar_id"], "verified_at": radar["verified_at"],
        "refresh_days": radar["refresh_days"], "dominant_signal": signal_id,
        "use": signal["use"], "limit": signal["limit"],
        "application": "first_frame_or_payoff" if fmt == "short" else "chapter_punctuation_only",
        "rule": radar["hao_fusion_rules"][0],
    }


def _probe(path: str) -> dict:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=color_space,color_transfer,color_primaries,color_range,pix_fmt:format_tags",
           "-of", "json", str(path)]
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError("ffprobe failed: " + (run.stderr or "")[-400:])
    data = json.loads(run.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    tags = (data.get("format") or {}).get("tags") or {}
    return {k: stream.get(k) for k in
            ("color_space", "color_transfer", "color_primaries", "color_range", "pix_fmt")} | {"tags": tags}


def _sample_stats(path: str, count: int = 10) -> list[dict]:
    longform = ROOT / "longform_maker"
    if str(longform) not in sys.path:
        sys.path.insert(0, str(longform))
    from grade_gate import sample_video
    return sample_video(str(path), n=count)


def _fog_score(metrics: dict) -> float:
    fog = 0.0
    fog += max(0.0, min(1.0, (42.0 - metrics["contrast"]) / 24.0)) * 0.6
    fog += max(0.0, min(1.0, (0.30 - metrics["sat"]) / 0.18)) * 0.25
    fog += max(0.0, min(1.0, (metrics["luma"] - 145.0) / 70.0)) * 0.15
    return fog


def analyze_media(path: str, count: int = 10) -> dict:
    suffix = Path(path).suffix.lower()
    still = suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
    meta = {"color_space": "image", "color_transfer": "unknown",
            "color_primaries": "unknown", "color_range": "unknown",
            "pix_fmt": "rgb", "tags": {}} if still else _probe(path)
    transfer = str(meta.get("color_transfer") or "unknown").lower()
    tag_blob = " ".join(str(v) for v in (meta.get("tags") or {}).values()).lower()
    is_hdr = transfer in HDR_TRANSFERS
    unknown_log = any(hint in tag_blob for hint in LOG_HINTS) and not is_hdr
    if still:
        longform = ROOT / "longform_maker"
        if str(longform) not in sys.path:
            sys.path.insert(0, str(longform))
        from grade_gate import frame_stats
        stats = [frame_stats(path)]
    else:
        stats = _sample_stats(path, count=count)
    med = {key: statistics.median(float(row[key]) for row in stats)
           for key in ("luma", "contrast", "sat", "warm", "tint", "clip_lo", "clip_hi")}
    fog = _fog_score(med)
    return {
        "path": os.path.abspath(path), "metadata": meta, "frames": len(stats),
        "metrics": {k: round(v, 5) for k, v in med.items()},
        "fog_score": round(fog, 4), "is_hdr": is_hdr, "unknown_log": unknown_log,
        "status": "BLOCK_UNKNOWN_LOG" if unknown_log else ("NORMALIZE_HDR" if is_hdr else "READY_REC709"),
    }


def adaptive_strength(analysis: dict, color_plan: dict) -> float:
    base = float(color_plan["base_strength"])
    ceiling = float(color_plan["max_strength"])
    strength = base + float(analysis.get("fog_score", 0.0)) * 0.1
    metrics = analysis.get("metrics") or {}
    if float(metrics.get("clip_hi", 0.0)) > 0.03 or float(metrics.get("clip_lo", 0.0)) > 0.06:
        strength *= 0.78
    return round(max(0.12, min(ceiling, strength)), 4)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def _transform(rgb: tuple[float, float, float], params: dict, strength: float) -> tuple[float, float, float]:
    original = rgb
    r, g, b = rgb
    exposure = 2.0 ** float(params.get("exposure", 0.0))
    r, g, b = r * exposure, g * exposure, b * exposure
    contrast = float(params.get("contrast", 0.0))
    if contrast:
        def curve(x: float) -> float:
            smooth = x * x * (3.0 - 2.0 * x)
            return x + contrast * (smooth - x)
        r, g, b = curve(r), curve(g), curve(b)
    lift = float(params.get("lift", 0.0))
    gamma = max(0.85, min(1.15, float(params.get("gamma", 1.0))))
    r, g, b = (_clip(r + lift) ** (1.0 / gamma),
               _clip(g + lift) ** (1.0 / gamma),
               _clip(b + lift) ** (1.0 / gamma))
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Lift the middle of the tonal range without washing out blacks or clipping
    # whites.  This is the useful part of a "bright" look; a global exposure
    # increase alone only makes HDR-to-SDR footage flatter.
    midtone_brightness = float(params.get("midtone_brightness", 0.0))
    if midtone_brightness:
        mid_weight = _clip(1.0 - abs(luma - 0.5) * 2.0)
        delta = midtone_brightness * mid_weight
        r, g, b = r + delta, g + delta, b + delta
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Perceptual color boost: low-chroma colors receive more separation than
    # already-saturated colors.  Luma-vs-saturation protection keeps noisy
    # shadows and bright skies from turning neon.
    chroma = max(r, g, b) - min(r, g, b)
    vibrance = float(params.get("vibrance", 0.0))
    vibrance_gain = 1.0 + vibrance * (1.0 - _clip(chroma / 0.45))
    shadow_weight = 1.0 - _clip((luma - 0.12) / 0.34)
    highlight_weight = _clip((luma - 0.68) / 0.30)
    shadow_sat = float(params.get("shadow_saturation", 1.0))
    highlight_sat = float(params.get("highlight_saturation", 1.0))
    luma_sat = (1.0 + (shadow_sat - 1.0) * shadow_weight
               + (highlight_sat - 1.0) * highlight_weight)
    sat = float(params.get("saturation", 1.0)) * vibrance_gain * luma_sat
    r, g, b = (luma + (r - luma) * sat,
               luma + (g - luma) * sat,
               luma + (b - luma) * sat)
    warmth, tint = float(params.get("warmth", 0.0)), float(params.get("tint", 0.0))
    shadow = 1.0 - _clip(luma * 2.0)
    highlight = _clip((luma - 0.45) / 0.55)
    r += warmth + float(params.get("highlight_warm", 0.0)) * highlight
    b -= warmth * 0.7
    b += float(params.get("shadow_blue", 0.0)) * shadow
    g += tint
    compress = float(params.get("highlight_compress", 0.0))
    if compress:
        r, g, b = (x - compress * max(0.0, x - 0.72) ** 2 for x in (r, g, b))
    graded = (_clip(r), _clip(g), _clip(b))
    return tuple(_clip(a + (b_ - a) * strength) for a, b_ in zip(original, graded))


def build_lut(profile_id: str, output: str | Path, *, strength: float | None = None,
              size: int = 17) -> Path:
    cfg = _load_config()
    if profile_id not in cfg["profiles"]:
        raise KeyError("unknown color profile: " + profile_id)
    if size not in {17, 33}:
        raise ValueError("LUT size must be 17 or 33")
    profile = cfg["profiles"][profile_id]
    chosen = float(profile["base_strength"] if strength is None else strength)
    chosen = max(0.0, min(float(profile["max_strength"]), chosen,
                          float(cfg["working_contract"]["absolute_strength_ceiling"])))
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'TITLE "Visual Master {profile_id} {chosen:.3f}"',
             f"LUT_3D_SIZE {size}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    den = float(size - 1)
    for b in range(size):
        for g in range(size):
            for r in range(size):
                values = _transform((r / den, g / den, b / den), profile["params"], chosen)
                lines.append("%.7f %.7f %.7f" % values)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def build_library(size: int = 17) -> dict:
    cfg = _load_config()
    LUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile_id, profile in cfg["profiles"].items():
        path = build_lut(profile_id, LUT_ROOT / f"{profile_id}.cube", size=size)
        rows.append({"id": profile_id, "label_zh": profile["label_zh"],
                     "strength": profile["base_strength"],
                     "path": path.relative_to(PROJECT_ROOT).as_posix()})
    manifest = {"schema_version": 1, "generator": "visual_master.py", "size": size,
                "delivery_space": "Rec.709 SDR", "profiles": rows}
    (LUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def scale_matrix(color_space: str | None) -> str:
    """swscale decode matrix for a stream tag; untagged or unknown HD media is BT.709."""
    return _SCALE_MATRIX.get(str(color_space or "").lower(), "bt709")


def source_matrix(path: str | Path) -> str:
    return scale_matrix(_probe(str(path)).get("color_space"))


def to_rgb_filter(matrix: str = "bt709") -> str:
    # Range stays automatic: the frame tag is right for direct full-range input
    # and after an upstream format=yuv420p.  Point chroma upsampling pairs with the
    # area downsampling of to_yuv_filter() for a lossless 4:2:0 round trip; the
    # accurate flags keep packed RGB (bgr24 pipes) as exact as planar gbrp.
    return ("scale=in_color_matrix=%s:flags=neighbor+accurate_rnd+full_chroma_int,"
            "format=gbrp" % matrix)


def to_yuv_filter(pix_fmt: str = "yuv420p") -> str:
    return ("scale=out_color_matrix=bt709:out_range=tv:flags=area+accurate_rnd+full_chroma_inp,"
            "format=%s,%s" % (pix_fmt, BT709_TAGS))


def rgb_decode_filter(path: str | Path) -> str:
    """Filters that decode a video to true BT.709 RGB, tone-mapping HDR first."""
    meta = _probe(str(path))
    if str(meta.get("color_transfer") or "").lower() in HDR_TRANSFERS:
        return HDR_TO_SDR_FILTER + "," + to_rgb_filter("bt709")
    return to_rgb_filter(scale_matrix(meta.get("color_space")))


def split_filters(chain: str) -> list[str]:
    """Split a filter chain on top-level commas (FFmpeg quoting and escapes)."""
    parts, current, quoted, escaped = [], "", False, False
    for char in chain:
        if escaped:
            escaped = False
        elif char == "\\" and not quoted:
            escaped = True
        elif char == "'":
            quoted = not quoted
        elif char == "," and not quoted:
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def bt709_filter_chain(chain: str | list[str], *, in_matrix: str = "bt709",
                       start: str = "yuv", end: str = "yuv420p") -> str:
    """Wrap RGB-domain filters in explicit conversions; output is BT.709 limited.

    ``in_matrix`` decodes the incoming YUV frames, every later YUV stage is
    BT.709 and the result is tagged.  ``end="rgb"`` leaves gbrp frames.
    """
    items = [part for piece in ([chain] if isinstance(chain, str) else chain)
             for part in split_filters(piece)]
    rgb, out = start == "rgb", []
    for item in items:
        wants_rgb = item.split("=", 1)[0].split("@", 1)[0].strip() in RGB_FILTERS
        if wants_rgb != rgb:
            out.append(to_rgb_filter(in_matrix) if wants_rgb else to_yuv_filter("yuv444p"))
            in_matrix, rgb = "bt709", wants_rgb
        out.append(item)
    if end == "rgb":
        if not rgb:
            out.append(to_rgb_filter(in_matrix))
    else:
        if not rgb and in_matrix != "bt709":
            out.append(to_rgb_filter(in_matrix))
        out.append(to_yuv_filter(end))
    return ",".join(out)


def _lut_filter(path: Path) -> str:
    value = path.resolve().as_posix().replace(":", "\\:")
    return "lut3d=file='%s':interp=tetrahedral" % value


def lut_filter_for_plan(color_plan: dict) -> str:
    """Return the single reusable LUT filter for a non-adaptive legacy caller."""
    profile = color_plan["profile"]
    path = LUT_ROOT / (profile + ".cube")
    if not path.exists():
        build_lut(profile, path, strength=float(color_plan["base_strength"]))
    return bt709_filter_chain(_lut_filter(path))


def source_filter(path: str, color_plan: dict, cache_dir: str | Path,
                  camera_id: str | None = None) -> tuple[str, dict]:
    analysis = analyze_media(path)
    if analysis["unknown_log"]:
        raise RuntimeError("unknown Log source requires an explicit input transform: " + path)
    strength = adaptive_strength(analysis, color_plan)
    cfg = _load_config()
    profile_signature = json.dumps({
        "config_version": cfg["version"],
        "profile": color_plan["profile"],
        "params": cfg["profiles"][color_plan["profile"]]["params"],
        "strength": strength,
        "hdr_normalizer": "hable-npl100-v1",
    }, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(
        (os.path.abspath(path) + str(os.path.getmtime(path)) + profile_signature).encode("utf-8")
    ).hexdigest()[:12]
    lut = Path(cache_dir) / ("grade_%s_%s.cube" % (color_plan["profile"], fingerprint))
    if not lut.exists():
        build_lut(color_plan["profile"], lut, strength=strength)
    # Camera normalization is a separate evidence layer.  It runs only for an
    # exact verified profile; unknown cameras remain a no-op and are reported.
    from color_calibration_lab import camera_filter
    calibration_filter, calibration = camera_filter(path, camera_id)
    chain = []
    if analysis["is_hdr"]:
        chain.append(HDR_TO_SDR_FILTER)
    grade = []
    if calibration_filter:
        grade.append(calibration_filter)
    grade.append(_lut_filter(lut))
    matrix = "bt709" if analysis["is_hdr"] else scale_matrix(analysis["metadata"].get("color_space"))
    chain.append(bt709_filter_chain(grade, in_matrix=matrix))
    library_lut = LUT_ROOT / (color_plan["profile"] + ".cube")
    report = {
        "analysis": analysis,
        "profile": color_plan["profile"],
        "strength": strength,
        "adaptive_lut_id": "%s@%.4f:%s" % (color_plan["profile"], strength, fingerprint),
        "library_profile_lut": library_lut.relative_to(PROJECT_ROOT).as_posix(),
        "camera_calibration": calibration,
        "input_matrix": matrix,
        "stage": "source_before_graphics",
    }
    return ",".join(chain), report


def apply_to_video(input_path: str, output_path: str, profile: str,
                   strength: float | None = None, force: bool = False) -> dict:
    src, dst = Path(input_path), Path(output_path)
    if src.resolve() == dst.resolve():
        raise ValueError("raw/input media may not be overwritten")
    source_sidecar = src.with_suffix(src.suffix + ".grade.json")
    if source_sidecar.exists() and not force:
        raise RuntimeError("input already has a grade sidecar; refusing LUT stacking")
    plan = plan_color_system("general", "longform")
    plan["profile"] = profile
    cfg = _load_config()["profiles"][profile]
    plan["base_strength"] = float(cfg["base_strength"] if strength is None else strength)
    plan["max_strength"] = float(cfg["max_strength"])
    with tempfile.TemporaryDirectory(prefix="hao-grade-") as td:
        vf, report = source_filter(str(src), plan, td)
        dst.parent.mkdir(parents=True, exist_ok=True)
        candidate = dst.with_suffix(dst.suffix + ".candidate.mp4")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
               "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-pix_fmt", "yuv420p", *BT709_ENCODE_ARGS, "-c:a", "copy",
               "-movflags", "+faststart", str(candidate)]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if run.returncode:
            raise RuntimeError("ffmpeg grade failed: " + (run.stderr or "")[-500:])
        os.replace(candidate, dst)
    report["output"] = str(dst.resolve())
    dst.with_suffix(dst.suffix + ".grade.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _selftest() -> None:
    assert route_profile("food") == "food_warm_appetite"
    assert route_profile("interview", "podcast") == "podcast_skin_neutral"
    assert plan_trend_system("travel")["dominant_signal"] == "local_flavor"
    assert plan_trend_system("toy")["dominant_signal"] == "surreal_silliness"
    plan = plan_color_system("travel", "longform")
    assert plan["one_look_only"] and plan["never_grade_graphics"]
    assert plan["base_strength"] <= plan["max_strength"] <= 0.5
    low_chroma = (0.45, 0.40, 0.38)
    vivid = _transform(low_chroma, {
        "saturation": 1.08, "vibrance": 0.28,
        "shadow_saturation": 0.88, "highlight_saturation": 0.95,
        "midtone_brightness": 0.04,
    }, 0.42)
    assert max(vivid) - min(vivid) > max(low_chroma) - min(low_chroma)
    assert sum(vivid) / 3.0 > sum(low_chroma) / 3.0
    with tempfile.TemporaryDirectory(prefix="visual-master-test-") as td:
        lut = build_lut("clean_neutral", Path(td) / "test.cube", size=17)
        lines = [x for x in lut.read_text(encoding="utf-8").splitlines()
                 if x and not x.startswith(("TITLE", "LUT_3D_SIZE", "DOMAIN_"))]
        assert len(lines) == 17 ** 3
    for domain in _load_config()["domain_routes"]:
        routed = plan_color_system(domain, "short")
        assert routed["profile"] in _load_config()["profiles"]
    _selftest_color_contract()
    _selftest_color_roundtrip()
    print("visual_master self-test OK")


def _selftest_color_contract() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_visual_master_constants", ROOT / "silent_vlog_maker" / "constants.py")
    constants = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(constants)
    assert constants.HDR_TO_SDR_FILTER == HDR_TO_SDR_FILTER, "HDR normaliser drifted"
    assert constants.TONEMAP_FILTER == HDR_TO_SDR_FILTER + ",format=yuv420p"
    assert split_filters("lut3d=file='C\\:/a,b.cube':interp=tetrahedral, eq=gamma=1") == [
        "lut3d=file='C\\:/a,b.cube':interp=tetrahedral", "eq=gamma=1"]
    chain = bt709_filter_chain("colorchannelmixer=rr=1,eq=saturation=1,lut3d=file=x.cube",
                               in_matrix="bt601")
    assert chain.startswith(to_rgb_filter("bt601")) and chain.endswith(BT709_TAGS), chain
    assert chain.count("in_color_matrix=bt709") == 1 and chain.count("out_color_matrix=bt709") == 2
    assert bt709_filter_chain("eq=gamma=1", end="rgb").endswith("format=gbrp")
    assert scale_matrix("smpte170m") == "bt601" and scale_matrix(None) == "bt709"


def _selftest_color_roundtrip() -> None:
    """Identity LUT on SMPTE HD bars: explicit chain > 45 dB and tagged bt709 for tagged and
    untagged input; the implicit chain on untagged input (BT.601 fallback) fails."""
    import numpy as np

    def ffmpeg(*args: str) -> bytes:
        run = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True)
        if run.returncode:
            raise RuntimeError("ffmpeg failed: " + run.stderr.decode("utf-8", "replace")[-400:])
        return run.stdout

    def rgb(path: str) -> "np.ndarray":
        raw = ffmpeg("-i", path, "-frames:v", "1", "-vf", "scale=in_color_matrix=bt709:in_range=tv:"
                     "out_range=pc,format=rgb24", "-f", "rawvideo", "-")
        return np.frombuffer(raw, np.uint8).astype(np.float64)

    with tempfile.TemporaryDirectory(prefix="visual-master-color-") as td:
        cube = Path(td) / "identity.cube"
        grid = [i / 16 for i in range(17)]
        cube.write_text("LUT_3D_SIZE 17\n" + "".join("%.6f %.6f %.6f\n" % (r, g, b)
                        for b in grid for g in grid for r in grid), encoding="utf-8")
        bars, bare = str(Path(td) / "bars.mp4"), str(Path(td) / "untagged.mp4")
        ffmpeg("-f", "lavfi", "-i", "smptehdbars=size=640x360:rate=30", "-frames:v", "2",
               "-vf", to_yuv_filter(), "-c:v", "libx264", "-qp", "0", *BT709_ENCODE_ARGS, bars)
        ffmpeg("-i", bars, "-c:v", "copy", "-bsf:v", "h264_metadata=colour_primaries=2:"
               "transfer_characteristics=2:matrix_coefficients=2", bare)
        ref, results = rgb(bars), {}
        for label, source, vf in (("implicit-untagged", bare, _lut_filter(cube)),
                                  ("explicit-tagged", bars, bt709_filter_chain(_lut_filter(cube))),
                                  ("explicit-untagged", bare, bt709_filter_chain(_lut_filter(cube)))):
            out = str(Path(td) / (label + ".mp4"))
            ffmpeg("-i", source, "-vf", "format=yuv420p," + vf, "-c:v", "libx264", "-qp", "0", out)
            mse = float(((rgb(out) - ref) ** 2).mean())
            results[label] = (99.0 if mse == 0 else 10 * math.log10(255 ** 2 / mse),
                              _probe(out).get("color_space"))
        assert results["implicit-untagged"][0] < 40.0, results    # BT.601 fallback (all FFmpeg)
        for label in ("explicit-tagged", "explicit-untagged"):
            assert results[label][0] > 45.0 and results[label][1] == "bt709", results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    build = sub.add_parser("build-luts")
    build.add_argument("--size", type=int, default=17, choices=(17, 33))
    plan = sub.add_parser("plan")
    plan.add_argument("--domain", default="general")
    plan.add_argument("--format", default="short")
    inspect = sub.add_parser("analyze")
    inspect.add_argument("input")
    apply = sub.add_parser("apply")
    apply.add_argument("input"); apply.add_argument("output")
    apply.add_argument("--profile", default="clean_neutral")
    apply.add_argument("--strength", type=float)
    apply.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "selftest":
        _selftest(); return 0
    if args.cmd == "build-luts":
        print(json.dumps(build_library(args.size), ensure_ascii=False, indent=2)); return 0
    if args.cmd == "plan":
        print(json.dumps({"color_system": plan_color_system(args.domain, args.format),
                          "trend_system": plan_trend_system(args.domain, args.format)},
                         ensure_ascii=False, indent=2)); return 0
    if args.cmd == "analyze":
        print(json.dumps(analyze_media(args.input), ensure_ascii=False, indent=2)); return 0
    print(json.dumps(apply_to_video(args.input, args.output, args.profile,
                                    args.strength, args.force), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
