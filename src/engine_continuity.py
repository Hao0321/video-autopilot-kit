"""Neutral bounded compatibility declaration; never render or art certification.

Only standard-library types and canonical hashes are used. Runtime declarations
must come from the actual get_autopilot_contract response, not caller wishes.
"""
from __future__ import annotations

import copy
import hashlib
import json


class EngineContinuityError(ValueError):
    """Missing, malformed, or regressed current-engine capability."""


ENGINE_CONTINUITY_SCHEMA = "editkin.engine-continuity/v1"
ENGINE_CONTINUITY_BINDING_SCHEMA = "editkin.engine-continuity-binding/v1"
MAX_ENGINE_CONTINUITY_BYTES = 8192
_MOTION_SCHEMAS = {"hao.motion-composition/v1", "hao.motion-composition/v2", "editkin.motion-scene-2d/v1"}
_REQUIRED_MOTION_SCHEMAS = {"hao.motion-composition/v2", "editkin.motion-scene-2d/v1"}
_FIELDS = {"schema", "engineId", "commonBase", "projectSchemas", "motionSchemas", "textPreparation",
           "templateAuthoring", "floatingFrame", "planSchema", "visualReviewPolicyBound", "originalSource"}


def _object(value, fields, label):
    if type(value) is not dict or set(value) != fields:
        raise EngineContinuityError(f"{label} requires exact current-engine fields")
    return value


def _literal(value, expected, label):
    if type(value) is not type(expected) or value != expected:
        raise EngineContinuityError(f"{label} is missing or downgraded")


def parse_engine_continuity(value):
    """Validate a finite closed vocabulary and return an independent declaration."""
    value = _object(value, _FIELDS, "engineContinuity")
    for field, expected in {
        "schema": ENGINE_CONTINUITY_SCHEMA, "engineId": "editkin-motion",
        "commonBase": "editkin.scene-glyph-spring/v1", "textPreparation": "physical-glyph-binary/v1",
        "templateAuthoring": "async-generation2", "planSchema": "hao.video-autopilot.edit-plan/v4",
        "visualReviewPolicyBound": True,
    }.items():
        _literal(value[field], expected, "engineContinuity." + field)
    projects = value["projectSchemas"]
    if (type(projects) is not list or not 1 <= len(projects) <= 2
            or any(type(item) is not int or item not in {9, 10} for item in projects)
            or len(set(projects)) != len(projects) or 9 not in projects):
        raise EngineContinuityError("engineContinuity.projectSchemas requires schema9; schema10 is optional")
    motions = value["motionSchemas"]
    if (type(motions) is not list or not 2 <= len(motions) <= 3
            or any(type(item) is not str or item not in _MOTION_SCHEMAS for item in motions)
            or len(set(motions)) != len(motions) or not _REQUIRED_MOTION_SCHEMAS.issubset(motions)):
        raise EngineContinuityError("engineContinuity.motionSchemas requires current composition and scene schemas")
    floating = _object(value["floatingFrame"], {"schema", "mediaFit", "clock", "geometry"}, "engineContinuity.floatingFrame")
    for field, expected in {"schema": "editkin.floating-video-frame/v2", "mediaFit": "contain",
                            "clock": "integer_project_frames", "geometry": "upright_display_aspect_ratio"}.items():
        _literal(floating[field], expected, "engineContinuity.floatingFrame." + field)
    original = _object(value["originalSource"], {"schema", "sameProcessCommit"}, "engineContinuity.originalSource")
    _literal(original["schema"], "editkin.original-motion-source/v1", "engineContinuity.originalSource.schema")
    _literal(original["sameProcessCommit"], True, "engineContinuity.originalSource.sameProcessCommit")
    if len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) > MAX_ENGINE_CONTINUITY_BYTES:
        raise EngineContinuityError("engineContinuity exceeds its bounded declaration size")
    return copy.deepcopy(value)


def engine_continuity_sha256(value):
    normalized = parse_engine_continuity(value)
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def require_engine_continuity(runtime, floor, required_project_schema):
    """Compare actual runtime support against the bound floor and saved schema."""
    actual, minimum = parse_engine_continuity(runtime), parse_engine_continuity(floor)
    if type(required_project_schema) is not int or required_project_schema not in {9, 10}:
        raise EngineContinuityError("Saved project schema must be actual schema9 or supported schema10")
    if (required_project_schema not in actual["projectSchemas"]
            or not set(minimum["projectSchemas"]).issubset(actual["projectSchemas"])
            or not set(minimum["motionSchemas"]).issubset(actual["motionSchemas"])):
        raise EngineContinuityError("Actual runtime does not satisfy the bound current-engine floor/project schema")
    return {"floor_sha256": engine_continuity_sha256(minimum), "runtime_sha256": engine_continuity_sha256(actual),
            "required_project_schema": required_project_schema, "runtime": actual}
