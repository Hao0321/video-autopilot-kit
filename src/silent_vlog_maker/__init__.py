'Silent-vlog and vertical-video preprocessing helpers.\n\nPUBLIC_FIXTURE: public documentation contains no maintainer episode history.'

# Re-export everything for top-level convenience
from .constants import (
    SAFE_ZONE,
    TONEMAP_FILTER,
    YT_SHORTS_ENCODE_ARGS,
    ENCODE_ARGS_BY_PLATFORM, PLATFORM_DIMENSIONS, encode_args_for,
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
    LANDSCAPE_PRESETS, LAYOUT_PRESETS,
    get_preset, list_presets,
    LANDSCAPE_TITLE_Y, LANDSCAPE_DETAIL_Y,
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

# 🆕 v3 audit pipeline
from .scene_audit import (
    Scene,
    cluster_scenes,
    print_scene_timeline,
    haversine_km,
)

from .frame_audit import (
    FrameDescription,
    extract_frames_hires,
    make_audit_grid,
    audit_all_clips_frames,
    load_descriptions,
    save_descriptions,
)

from .audit_report import (
    write_markdown_report,
    write_json_report,
    run_full_audit,
)

# 🆕 v4 (2026-05-24) — content routing for mass production
from .content_routing import (
    RoutingDecision,
    detect_layout, detect_content_type, recommend_path, recommend_bgm,
    route_content, print_routing_decision,
    # 🆕 M59 (2026-05-25) — caption style decision
    should_use_flower_text, recommend_caption_style,
    # 🆕 Mode C #2 (2026-05-25) — pre-build checklists per content type (AP9 落地)
    PRE_BUILD_CHECKLIST_TEACHING_LONGFORM,
    PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING,
    PRE_BUILD_CHECKLIST_FOOD_VLOG,
    PRE_BUILD_CHECKLIST_TRAVEL_VLOG,
    PRE_BUILD_CHECKLISTS,
    get_pre_build_checklist, print_pre_build_checklist,
    validate_checklist_answers,
    # 🆕 2026-05-27 — Runtime executor for verify_steps (callable instead of string-only)
    run_verify_steps,
)

# 🆕 v4 (2026-05-24) — asset library scanner
from .asset_scanner import (
    scan_bgm, scan_fonts, scan_templates, scan_all_assets,
    print_asset_summary, INDEX_FILE as ASSETS_INDEX_FILE,
    find_assets_by_cue,  # 🆕 cue → asset matching
)

# 🆕 v4.4 (2026-05-25) — Screen rec auto-cleanup (M60+M61+M62)
from .screen_rec_cleaner import (
    DEFAULTS_OBS_CHROME_WIN11,
    clean_screen_recording,
    clean_voice_pauses,
    batch_clean_screen_recs,
    batch_clean_voice_tracks,
    # 🆕 M85 (2026-05-29) — b-roll 素材入庫 auto-normalize (strip audio + conform fps)
    normalize_broll_asset,
    batch_normalize_broll_folder,
)

# 🆕 v4.5 M64 — final build path is the universal Editkin v4 workflow.
# verify_output 移到 quality_check.py (適用任何 pipeline 出的 mp4)
from .quality_check import verify_output

# 🆕 (2026-06-01 訓練) Reels/Shorts 多彩多尺寸字幕 + 不露臉網感模板
from .shorts_captions import (
    SHORTS_CAPTION_LEVELS, style_caption, render_caption_png,
    # 2026 web 研究強化：逐塊 active 字幕 + 安全區
    SHORTS_SAFE_ZONE, safe_caption_y, chunk_caption, style_chunks_active,
)
from .shorts_template import (
    NETGAN_NICHE_PRESETS, NETGAN_SHORTS_TEMPLATE, render_hook_card,
    # 2026 web 研究強化：前 3 秒 hook formula
    HOOK_FORMULAS, suggest_hook,
)
# 🆕 M96 (2026-06-20): 美食/旅遊直式 Shorts 純 ffmpeg pipeline（多色重點字幕 + 轉正 + GPS）
from .shorts_vertical import (
    build_one_short, normalize_to_portrait, build_multicolor_ass,
    strip_emoji, extract_gps, find_music_highlight, beat_rate, pick_bgm,
    NICHE_PALETTES, NICHE_FONTS,
)
# 註：shorts_vertical 內另有同名 COLOR_VARIETY (g/o/r/w/y BGR ASS 碼)，但 package-level
# COLOR_VARIETY 保留給 constants 的 7 色命名 palette（避免 shadow）；要 ASS 碼用
# `from silent_vlog_maker.shorts_vertical import COLOR_VARIETY`。


__all__ = [
    # 🆕 M96 直式 Shorts pipeline（COLOR_VARIETY 不在此 export — 見上方註，避與 constants shadow）
    "build_one_short", "normalize_to_portrait", "build_multicolor_ass",
    "strip_emoji", "extract_gps", "find_music_highlight", "beat_rate", "pick_bgm",
    "NICHE_PALETTES", "NICHE_FONTS",
    # constants
    "SAFE_ZONE", "TONEMAP_FILTER", "YT_SHORTS_ENCODE_ARGS",
    "FONT_NOTO_BLACK", "FONT_NOTO_BOLD", "FONT_NOTO_REG", "FONT_NOTO_SERIF_BOLD",
    "FONT_BOLD", "FONT_REG",
    "CINEMATIC_CURVES",
    "COLOR_GOLD", "COLOR_WHITE", "COLOR_CREAM",
    "BOX_DARK", "BOX_SUBTLE", "BOX_CINEMATIC",
    "SUBTITLE_CENTER_Y", "SUBTITLE_DETAIL_Y",
    "COLOR_VARIETY",
    # audit
    "ClipAudit", "audit_raw_files", "print_audit_report",
    "utc_to_local", "smart_cut_offset",
    # text overlay
    "Overlay", "POSITION_PRESETS", "TV_VARIETY_PRESETS",
    # effects
    "kenburns_zoom_in", "kenburns_pan_right", "kenburns_static",
    "apply_cinematic_grade", "build_xfade_concat",
    # pipeline
    "make_keyframe_grid", "load_voice_profile", "build_filter_complex",
    "VOICE_PROFILES_PATH",
    # 🆕 v3 scene clustering
    "Scene", "cluster_scenes", "print_scene_timeline", "haversine_km",
    # 🆕 v3 frame audit
    "FrameDescription", "extract_frames_hires", "make_audit_grid",
    "audit_all_clips_frames", "load_descriptions", "save_descriptions",
    # 🆕 v3 audit report
    "write_markdown_report", "write_json_report", "run_full_audit",
    # 🆕 v4 platform-aware export + multi-layout
    "ENCODE_ARGS_BY_PLATFORM", "PLATFORM_DIMENSIONS", "encode_args_for",
    "LANDSCAPE_PRESETS", "LAYOUT_PRESETS", "get_preset", "list_presets",
    "LANDSCAPE_TITLE_Y", "LANDSCAPE_DETAIL_Y",
    # 🆕 v4 content routing
    "RoutingDecision", "detect_layout", "detect_content_type",
    "recommend_path", "recommend_bgm",
    "route_content", "print_routing_decision",
    # 🆕 Mode C #2 (2026-05-25) — pre-build checklists (AP9 落地)
    "PRE_BUILD_CHECKLIST_TEACHING_LONGFORM",
    "PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING",
    "PRE_BUILD_CHECKLIST_FOOD_VLOG",
    "PRE_BUILD_CHECKLIST_TRAVEL_VLOG",
    "PRE_BUILD_CHECKLISTS",
    "get_pre_build_checklist", "print_pre_build_checklist",
    "validate_checklist_answers",
    "run_verify_steps",  # 🆕 2026-05-27 runtime executor
    # 🆕 v4 asset scanner
    "scan_bgm", "scan_fonts", "scan_templates", "scan_all_assets",
    "print_asset_summary", "ASSETS_INDEX_FILE",
    "find_assets_by_cue",
    # 🆕 v4.4 screen rec cleaner (M60-M62)
    "DEFAULTS_OBS_CHROME_WIN11", "clean_screen_recording", "clean_voice_pauses",
    "batch_clean_screen_recs", "batch_clean_voice_tracks",
    "normalize_broll_asset", "batch_normalize_broll_folder",  # 🆕 M85 素材入庫
    # 🆕 v4.5 (M64 — Editkin v4 plan/audit/apply/render universal)
    "verify_output",
    "should_use_flower_text", "recommend_caption_style",
    # 🆕 (2026-06-01 訓練) Reels/Shorts 爆色字幕 + 不露臉網感模板
    "SHORTS_CAPTION_LEVELS", "style_caption", "render_caption_png",
    "NETGAN_NICHE_PRESETS", "NETGAN_SHORTS_TEMPLATE", "render_hook_card",
    # 2026 web 研究強化（逐塊 active 字幕 / 安全區 / hook formula）
    "SHORTS_SAFE_ZONE", "safe_caption_y", "chunk_caption", "style_chunks_active",
    "HOOK_FORMULAS", "suggest_hook",
]
