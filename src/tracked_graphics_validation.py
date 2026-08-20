# -*- coding: utf-8 -*-
"""Validation helpers for the tracked-graphics shot specification.

The renderer deliberately keeps validation in a separate module so adding a
new visual treatment does not make the compositing transaction harder to
audit.  Low-level regexes and registries are injected by the caller; this
module owns policy, not rendering implementation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Pattern


def _validate_time_range(spec: dict[str, Any], errors: list[str]) -> tuple[float, float]:
    start = float(spec.get("start", 0))
    end = float(spec.get("end", start))
    if end <= start:
        errors.append("end must exceed start")
    return start, end


def _validate_keyframes(label: dict[str, Any], prefix: str, errors: list[str]) -> None:
    keyframes = label.get("keyframes") or []
    if not keyframes:
        errors.append(prefix + " keyframes mode requires keyframes")
        return
    previous_time = -float("inf")
    for key_index, row in enumerate(keyframes):
        if not isinstance(row.get("bbox"), list) or len(row.get("bbox", [])) != 4:
            errors.append(prefix + ".keyframes[%d] bbox must be a four-value list" % key_index)
        current_time = float(row.get("time", -1))
        if current_time < previous_time:
            errors.append(prefix + " keyframes must be time ordered")
        previous_time = current_time


def _validate_label(
    label: dict[str, Any], index: int, start: float, end: float,
    errors: list[str], *, text_profiles: dict[str, Any],
    currency_re: Pattern[str], measured_value_re: Pattern[str],
) -> None:
    prefix = "tracked_labels[%d]" % index
    text = str(label.get("text", ""))
    if not text.strip():
        errors.append(prefix + " text is empty")
    if label.get("profile", "neon_value_green") not in text_profiles:
        errors.append(prefix + " has unknown profile")
    if not isinstance(label.get("initial_bbox"), list) or len(label.get("initial_bbox", [])) != 4:
        errors.append(prefix + " initial_bbox must be a four-value list")
    mode = str(label.get("tracking_mode", "csrt"))
    if mode not in {"csrt", "keyframes"}:
        errors.append(prefix + " tracking_mode must be csrt or keyframes")
    if mode == "keyframes":
        _validate_keyframes(label, prefix, errors)
    if float(label.get("end", end)) <= float(label.get("start", start)):
        errors.append(prefix + " end must exceed start")
    if currency_re.search(text) and not str(label.get("evidence", "")).strip():
        errors.append(prefix + " currency/value text requires evidence")
    style = str(label.get("style", "typography"))
    if style not in {"typography", "telemetry_callout"}:
        errors.append(prefix + " style must be typography or telemetry_callout")
    if style == "telemetry_callout":
        if not str(label.get("meaning", "")).strip():
            errors.append(prefix + " telemetry_callout requires meaning")
        if ((currency_re.search(text) or measured_value_re.search(text)) and
                not str(label.get("evidence", "")).strip()):
            errors.append(prefix + " measured telemetry requires evidence")


def _validate_hud(hud: dict[str, Any], errors: list[str], currency_re: Pattern[str]) -> None:
    if hud.get("mode", "current_badge") not in {"current_badge", "ladder"}:
        errors.append("hud.mode must be current_badge or ladder")
    if not hud.get("items"):
        errors.append("hud.items must not be empty")
    for index, item in enumerate(hud.get("items", [])):
        label = str(item.get("label", ""))
        if not label.strip():
            errors.append("hud.items[%d] label is empty" % index)
        if currency_re.search(label) and not str(item.get("evidence", "")).strip():
            errors.append("hud.items[%d] currency/value text requires evidence" % index)


def _validate_lock_effect(
    effect: dict[str, Any], index: int, start: float, end: float, errors: list[str],
) -> None:
    prefix = "lock_effects[%d]" % index
    effect_start = float(effect.get("start", start))
    effect_end = float(effect.get("end", end))
    if effect_end <= effect_start:
        errors.append(prefix + " end must exceed start")
    if effect_end - effect_start > .8:
        errors.append(prefix + " attention lock must not persist longer than 0.8 seconds")
    if not str(effect.get("evidence", "")).strip():
        errors.append(prefix + " requires verified target/state evidence")
    if not str(effect.get("meaning", "")).strip():
        errors.append(prefix + " requires an explicit information meaning")
    if effect.get("no_occlusion_review") is not True:
        errors.append(prefix + " requires no_occlusion_review=true")
    center = effect.get("center", [.5, .53])
    if not isinstance(center, list) or len(center) != 2:
        errors.append(prefix + " center must be a two-value list")
    if float(effect.get("radius", .16)) <= 0:
        errors.append(prefix + " radius must be positive")


def _validate_matte_source(effect: dict[str, Any], prefix: str, errors: list[str]) -> None:
    shape = effect.get("shape", "ellipse")
    if shape not in {"ellipse", "rectangle", "polygon", "alpha", "sequence"}:
        errors.append(prefix + " shape must be ellipse, rectangle, polygon, alpha or sequence")
    if shape == "polygon" and len(effect.get("polygon") or []) < 3:
        errors.append(prefix + " polygon shape requires at least three points")
    matte_path = str(effect.get("matte_path", "")).strip()
    if shape == "alpha" and not matte_path:
        errors.append(prefix + " alpha shape requires matte_path")
    if matte_path and not Path(matte_path).is_file():
        errors.append(prefix + " matte_path does not exist")
    sequence_dir = str(effect.get("matte_sequence_dir", "")).strip()
    if shape == "sequence" and not sequence_dir:
        errors.append(prefix + " sequence shape requires matte_sequence_dir")
    if sequence_dir and not Path(sequence_dir).is_dir():
        errors.append(prefix + " matte_sequence_dir does not exist")
    if shape == "sequence" and float(effect.get("matte_sequence_fps", 0)) <= 0:
        errors.append(prefix + " sequence shape requires positive matte_sequence_fps")
    if str(effect.get("subject_class", "")) in {"vehicle", "person", "irregular"} and \
            shape not in {"polygon", "alpha", "sequence"}:
        errors.append(prefix + " irregular subjects require polygon, alpha or sequence matte")


def _validate_sheen_effect(
    effect: dict[str, Any], index: int, start: float, end: float,
    errors: list[str], *, sheen_materials: dict[str, Any],
) -> None:
    prefix = "mask_sheens[%d]" % index
    if float(effect.get("end", end)) <= float(effect.get("start", start)):
        errors.append(prefix + " end must exceed start")
    if not isinstance(effect.get("initial_bbox"), list) or len(effect.get("initial_bbox", [])) != 4:
        errors.append(prefix + " initial_bbox must be a four-value list")
    _validate_matte_source(effect, prefix, errors)
    if effect.get("material_profile", "generic_product") not in sheen_materials:
        errors.append(prefix + " has unknown material_profile")
    if str(effect.get("target_kind", "subject_object")) != "subject_object":
        errors.append(prefix + " target_kind must be subject_object; typography sheen belongs to text effects")
    if str(effect.get("subject_class", "")).lower() in {
            "text", "typography", "caption", "title", "subtitle"}:
        errors.append(prefix + " must target a photographed subject object, never text")
    if float(effect.get("band_width", .16)) <= 0:
        errors.append(prefix + " band_width must be positive")
    if str(effect.get("reveal_mode", "sheen_only")) not in {"sheen_only", "black_to_color"}:
        errors.append(prefix + " reveal_mode must be sheen_only or black_to_color")
    if not 0.0 <= float(effect.get("blackout_opacity", 1.0)) <= 1.0:
        errors.append(prefix + " blackout_opacity must be between 0 and 1")
    if not 0.08 <= float(effect.get("reveal_softness", .42)) <= 1.2:
        errors.append(prefix + " reveal_softness must be between 0.08 and 1.2")
    if not 0.0 <= float(effect.get("contrast", .16)) <= .45:
        errors.append(prefix + " contrast must be between 0 and 0.45")
    if not 0.0 < float(effect.get("core", .9)) <= 1.0:
        errors.append(prefix + " core must be above 0 and at most 1")
    duration = float(effect.get("end", end)) - float(effect.get("start", start))
    if duration > .8:
        errors.append(prefix + " subject sheen must not exceed 0.8 seconds")
    if not str(effect.get("evidence", "")).strip():
        errors.append(prefix + " requires evidence for the subject matte")


def validate_spec(
    spec: dict[str, Any], *, text_profiles: dict[str, Any],
    sheen_materials: dict[str, Any], currency_re: Pattern[str],
    measured_value_re: Pattern[str],
) -> list[str]:
    """Validate one shot spec without importing renderer implementation."""
    errors: list[str] = []
    if not Path(str(spec.get("video", ""))).is_file():
        errors.append("video does not exist")
    start, end = _validate_time_range(spec, errors)
    for index, label in enumerate(spec.get("tracked_labels", [])):
        _validate_label(
            label, index, start, end, errors, text_profiles=text_profiles,
            currency_re=currency_re, measured_value_re=measured_value_re,
        )
    if spec.get("hud"):
        _validate_hud(spec["hud"], errors, currency_re)
    for index, effect in enumerate(spec.get("lock_effects", [])):
        _validate_lock_effect(effect, index, start, end, errors)
    for index, effect in enumerate(spec.get("mask_sheens", [])):
        _validate_sheen_effect(
            effect, index, start, end, errors, sheen_materials=sheen_materials,
        )
    return errors
