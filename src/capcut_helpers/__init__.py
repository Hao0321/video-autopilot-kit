"""
capcut_helpers — CapCut Desktop JSON manipulation helpers (2026-05-24 v1).

Generalize the ad-hoc scripts from videos/current/ into reusable module:
  - full_audit.py → audit.audit_draft()
  - apply_art_to_all.py → effects.apply_effect_to_all_captions()
  - swap_bubble_to_art.py → effects.swap_effect()
  - 4-level mute scripts → mute.mute_all_video_segments() + audit_mute_state()
  - 7-file JSON sync (M18) → draft_io.save_draft_with_sync()
  - kill CapCut process (M20) → process.kill_capcut_all()

| Module | Lines | What |
|---|---|---|
| `paths.py` | ~70 | DRAFTS_ROOT / EFFECT_CACHE / capcut-cli shim / draft_path() / discover_all_draft_jsons() |
| `process.py` | ~50 | M20 kill_capcut_all() + safe_kill_then_verify() |
| `draft_io.py` | ~90 | load_draft / save_draft_with_sync (M18 7-file sync) / verify_sync |
| `mute.py` | ~110 | M29 mute_all_video_segments (4-level) + audit_mute_state |
| `effects.py` | ~130 | apply_effect_to_all_captions / swap_effect (花字 bulk swap) / count_effects_by_id |
| `audit.py` | ~130 | audit_draft (tracks / mute / captions / effects / bgm / timing) |

Usage：

```python
from capcut_helpers import (
    draft_path, load_draft, save_draft_with_sync, verify_sync,
    kill_capcut_all, safe_kill_then_verify,
    mute_all_video_segments, audit_mute_state,
    find_effect_material, apply_effect_to_all_captions, swap_effect,
    audit_draft, print_audit_report,
)

# Typical workflow (M18 + M20 + M29 in one)
kill_capcut_all()  # M20 — kill before edit
draft = load_draft("a travel vlog")
mute_all_video_segments(draft)  # M29
save_draft_with_sync("a travel vlog", draft)  # M18 — sync 7 files
sync = verify_sync("a travel vlog")
print(f"Synced: {sync['all_synced']} ({sync['files_checked']} files)")

# Then audit
report = audit_draft(draft)
print_audit_report(report)
```

Companion to `silent_vlog_maker/` (ffmpeg-only pipeline) — same architecture pattern.
"""

from .paths import (
    CAPCUT_USER_DATA, DRAFTS_ROOT, EFFECT_CACHE,
    CAPCUT_CLI, PROJECT_ROOT, VIDEOS_DIR, ASSETS_DIR, BGM_DIR, FONTS_DIR,
    draft_path, draft_files, discover_all_draft_jsons,
)

from .process import (
    kill_capcut_all, is_capcut_running, safe_kill_then_verify,
)

from .draft_io import (
    load_draft, save_draft_with_sync, verify_sync,
    set_canvas_portrait, set_canvas_landscape, auto_set_canvas,
)

from .mute import (
    mute_all_video_segments, mute_specific_segments, audit_mute_state,
)

from .effects import (
    find_effect_material, get_effect_cache_path,
    apply_effect_to_all_captions, swap_effect, count_effects_by_id,
    apply_effect_to_segment,
)

# 🆕 M51 (2026-05-24): 直式 Shorts 預設組樣式 (非花字)
# 🆕 M68 (2026-05-25): Hao 教學長片字幕雙 tier auto-apply
from .text_style import (
    CAPCUT_FONTS, PRESET_STYLES,
    get_capcut_font_path, list_capcut_fonts, list_preset_styles,
    apply_text_preset, apply_text_preset_to_all,
    apply_hao_teaching_dual_tier,  # M68 — 教學字幕中文+英文雙 tier 一鍵套
)

# 🆕 M55+M56 (2026-05-24): ffmpeg post-process MANDATORY final phase
# 🆕 M82+M83 (2026-05-27, helper 落地 2026-05-29): ship-final 保守 re-encode + voice-end trim
#    canon 早先只有規則描述，2026-05-29 strengthening pass 補齊對應 helper + 自我兌現 M83 教訓
from .post_export import (
    force_mix_bgm,          # M55 — replace audio (4-level JSON mute 不夠)
    add_outro_card,         # M56 — 店名 + 地址 + 可選電話 lower-third
    finalize_export,        # one-shot M55 + M56
    detect_voice_end,       # M82 — silencedetect 找人聲真結尾
    trim_to_voice_end,      # M82 — trim timeline 到人聲結尾 + 可選 outro pad
    reencode_player_safe,   # M83 — libx264/-bf0/CFR/closed-GOP player-safe ship profile
)

# 🆕 v0.3.0 (2026-06-16): 交付前 QA + 圖片入片 helpers (canon M91-M95)
from .delivery_qa import (
    final_delivery_qa,      # 🚦 交付前 QA 主入口 (M93 頻閃 + M95 死空檔 + 接觸表)
    still_blurfill,         # M92 — 非滿版圖→模糊背景填滿+靜止(零抖動)
    detect_flash,           # M93 — blackdetect 抓頻閃素材/亮度落差
    detect_long_pauses,     # M95 — silencedetect 抓句間死空檔(>1.5s)
    trim_dead_air_ranges, build_keep_ranges, remap_time,  # M95 — 三軌同步剪點/平移
    cut_audio_segments,     # M95 — 移音訊段用 atrim+concat (不是 aselect!)
    cut_video_segments,     # M95 — 移影像段用 select+setpts
    contact_sheet,          # M9/M91 — 整片接觸表逐格看
)

# 🆕 M69 (2026-05-25): AI 字幕通用校正字典 (cloud→Claude / 扣的→Code etc.)
from .subtitle_corrections import (
    BRAND_CORRECTIONS, CHINESE_HOMOPHONE_CORRECTIONS, PHRASE_CORRECTIONS,
    apply_subtitle_corrections, scan_potential_errors,
)

# 🆕 AP12 落地 (2026-05-26): helper invariants decorator pattern
# 用 @validate_invariants 包 mutation functions，自動 sync dependent metadata
from .invariants import (
    validate_invariants,
    TEXT_MATERIAL_INVARIANTS, TEXT_MATERIAL_AUTO_FIX,
)

# 🆕 AP15 落地 (2026-05-26 Mode C #3): caption ↔ b-roll content matching audit
# 解 #006 v3→v4「Studio caption 配 book b-roll」mismatch type bug
# 🆕 M75 (2026-05-26): auto-sequencer — 不只 audit，build-time 直接排好順序
from .caption_broll_matcher import (
    HAO_CAPTION_KEYWORD_MAP,
    score_broll_for_caption, match_brolls_to_captions,
    audit_caption_broll_mismatch, print_mismatch_report,
    BrollAssignment, auto_sequence_brolls, print_sequence_plan,
)
# 🆕 M86 (占比) + M87 (旁白↔畫面對位) b-roll audit — 2026-06-01 audit「拆」出獨立模組
# （caption_broll_matcher.py 逼近 1000 行）。re-export 保持外部 import 不變。
from .broll_audit import (
    classify_broll_role, audit_broll_main_ratio, print_broll_ratio_report,
    HAO_BROLL_CONTENT_KEYWORDS, narration_broll_sync_report, print_narration_sync_report,
)

from .audit import (
    audit_draft, print_audit_report,
)


__all__ = [
    # paths
    "CAPCUT_USER_DATA", "DRAFTS_ROOT", "EFFECT_CACHE",
    "CAPCUT_CLI", "PROJECT_ROOT", "VIDEOS_DIR", "ASSETS_DIR", "BGM_DIR", "FONTS_DIR",
    "draft_path", "draft_files", "discover_all_draft_jsons",
    # process
    "kill_capcut_all", "is_capcut_running", "safe_kill_then_verify",
    # draft I/O
    "load_draft", "save_draft_with_sync", "verify_sync",
    "set_canvas_portrait", "set_canvas_landscape", "auto_set_canvas",
    # mute
    "mute_all_video_segments", "mute_specific_segments", "audit_mute_state",
    # effects
    "find_effect_material", "get_effect_cache_path",
    "apply_effect_to_all_captions", "swap_effect", "count_effects_by_id",
    "apply_effect_to_segment",
    # 🆕 M51 text preset (basic tab — 非花字)
    # 🆕 M68 教學雙 tier auto-apply
    "CAPCUT_FONTS", "PRESET_STYLES",
    "get_capcut_font_path", "list_capcut_fonts", "list_preset_styles",
    "apply_text_preset", "apply_text_preset_to_all",
    "apply_hao_teaching_dual_tier",
    # 🆕 M55 + M56 mandatory post-export
    "force_mix_bgm", "add_outro_card", "finalize_export",
    # 🆕 M82 + M83 ship-final (helper 落地 2026-05-29 — 補 canon 宣稱但未實作的 helper)
    "detect_voice_end", "trim_to_voice_end", "reencode_player_safe",
    # 🆕 M69 AI 字幕校正
    "BRAND_CORRECTIONS", "CHINESE_HOMOPHONE_CORRECTIONS", "PHRASE_CORRECTIONS",
    "apply_subtitle_corrections", "scan_potential_errors",
    # 🆕 AP15 caption-broll matcher + 🆕 M75 auto-sequencer
    "HAO_CAPTION_KEYWORD_MAP",
    "score_broll_for_caption", "match_brolls_to_captions",
    "audit_caption_broll_mismatch", "print_mismatch_report",
    "BrollAssignment", "auto_sequence_brolls", "print_sequence_plan",
    # 🆕 M86 generic-vs-main b-roll 占比 enforce (2026-05-30)
    "classify_broll_role", "audit_broll_main_ratio", "print_broll_ratio_report",
    # 🆕 M87 narration↔b-roll 內容對位 (2026-05-30)
    "HAO_BROLL_CONTENT_KEYWORDS", "narration_broll_sync_report", "print_narration_sync_report",
    # 🆕 AP12 helper invariants (2026-05-26) — 漏列補上 (2026-05-29 audit)
    "validate_invariants", "TEXT_MATERIAL_INVARIANTS", "TEXT_MATERIAL_AUTO_FIX",
    # audit
    "audit_draft", "print_audit_report",
    # 🆕 v0.3.0 交付前 QA + 圖片入片 (M91-M95)
    "final_delivery_qa", "still_blurfill", "detect_flash", "detect_long_pauses",
    "trim_dead_air_ranges", "build_keep_ranges", "remap_time",
    "cut_audio_segments", "cut_video_segments", "contact_sheet",
]
