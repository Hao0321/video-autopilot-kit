# -*- coding: utf-8 -*-
"""Bridge to the optional Bright Editorial Motion Kit.

The separately downloadable Motion Kit is preferred when installed.  The core
ships a procedural fallback so planning and basic rendering remain operational.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from PIL import Image

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KIT_CANDIDATES = (
    os.environ.get("VIDEO_AUTOPILOT_MOTION_KIT"),
    os.path.join(PROJECT_ROOT, "community", "hao-motion-kit"),
    os.path.join(PROJECT_ROOT, "hao-motion-kit"),
)
KIT_ROOT = next((os.path.abspath(path) for path in KIT_CANDIDATES
                 if path and os.path.isfile(os.path.join(path, "template_engine.py"))), None)
if KIT_ROOT:
    sys.path.insert(0, KIT_ROOT)

try:
    if not KIT_ROOT:
        raise ImportError("optional Motion Kit is not installed")
    from template_engine import (  # type: ignore  # noqa: E402,F401
        ASPECTS, CATALOG_PATH, MANIFEST_PATH, ROLES, STYLES, TEMPLATE_ROOT,
        build_catalog, build_library, infer_topic, pick, render_background, render_template, resolve_style,
    )
    ENGINE = "motion-kit"
except (ImportError, ModuleNotFoundError):
    from editorial_template_fallback import (  # noqa: E402,F401
        ASPECTS, CATALOG_PATH, MANIFEST_PATH, ROLES, STYLES, TEMPLATE_ROOT,
        build_catalog, build_library, infer_topic, pick, render_background, render_template, resolve_style,
    )
    ENGINE = "procedural-fallback"


def self_test() -> None:
    assert resolve_style("AI 教學")["key"] == "ai_chalk_grid"
    assert resolve_style("旅遊日記")["key"] == "travel_journal"
    assert resolve_style("抹茶冰淇淋")["key"] == "matcha_fresh"
    assert resolve_style("傳統海鮮料理")["key"] == "food_heritage"
    image = render_template("hook", "公開版模板", "SHORTS", topic="AI 教學", aspect="portrait")
    assert image.size == ASPECTS["portrait"] and image.mode == "RGB"
    with tempfile.TemporaryDirectory(prefix="editorial-bridge-") as temporary:
        media_path = Path(temporary) / "face.png"
        Image.new("RGB", (320, 520), (238, 37, 122)).save(media_path)
        without_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait", seed=77)
        with_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait",
            media_paths=(media_path,), seed=77)
        assert without_media.tobytes() != with_media.tobytes()
        try:
            render_template(
                "hook", "媒體契約", aspect="portrait",
                media_paths=(Path(temporary) / "missing.png",), seed=77)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("invalid editorial media path must fail closed")
        unsupported_path = Path(temporary) / "unsupported.txt"
        unsupported_path.write_text("not an image", encoding="utf-8")
        try:
            render_template(
                "hook", "媒體契約", aspect="portrait",
                media_paths=(unsupported_path,), seed=77)
        except ValueError:
            pass
        else:
            raise AssertionError("unsupported editorial media must fail closed")
    print("editorial_templates bridge self-test OK (%s)" % ENGINE)


if __name__ == "__main__":
    self_test()
