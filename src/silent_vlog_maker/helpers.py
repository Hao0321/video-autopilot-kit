"""
silent_vlog_maker.helpers — BACKWARD COMPAT SHIM (2026-05-23).

⚠️ DEPRECATED entry point — use `from silent_vlog_maker import X` instead.

This module previously contained ALL helpers (730 lines monolith).
2026-05-23 Bundle C 拆檔：split into 5 sub-modules for maintainability.

Old code that did:
    from silent_vlog_maker.helpers import audit_raw_files, Overlay, ...
still works — this module re-exports everything from the new sub-modules.

New code should prefer:
    from silent_vlog_maker import audit_raw_files, Overlay, ...
(via __init__.py — cleaner and faster import).

See `__init__.py` for the module map and the Editkin v4 execution boundary.
"""

# Re-export from new modules (same surface as old monolith)
from .constants import (
    SAFE_ZONE,
    TONEMAP_FILTER,
    YT_SHORTS_ENCODE_ARGS,
    FONT_NOTO_BLACK, FONT_NOTO_BOLD, FONT_NOTO_REG, FONT_NOTO_SERIF_BOLD,
    FONT_BOLD, FONT_REG,
    CINEMATIC_CURVES,
    COLOR_GOLD, COLOR_WHITE, COLOR_CREAM,
    BOX_DARK, BOX_SUBTLE, BOX_CINEMATIC,
    SUBTITLE_CENTER_Y, SUBTITLE_DETAIL_Y,
    COLOR_VARIETY,
)

from .audit import (
    ClipAudit,
    audit_raw_files,
    print_audit_report,
    utc_to_local,
    smart_cut_offset,
)

from .text_overlay import (
    Overlay,
    POSITION_PRESETS,
    TV_VARIETY_PRESETS,
)

from .effects import (
    kenburns_zoom_in,
    kenburns_pan_right,
    kenburns_static,
    apply_cinematic_grade,
    build_xfade_concat,
)

from .pipeline import (
    make_keyframe_grid,
    load_voice_profile,
    build_filter_complex,
    VOICE_PROFILES_PATH,
)

# 🆕 v3 (2026-05-24) audit pipeline
from .scene_audit import (
    Scene, cluster_scenes, print_scene_timeline, haversine_km,
)
from .frame_audit import (
    FrameDescription, extract_frames_hires, make_audit_grid,
    audit_all_clips_frames, load_descriptions, save_descriptions,
)
from .audit_report import (
    write_markdown_report, write_json_report, run_full_audit,
)
