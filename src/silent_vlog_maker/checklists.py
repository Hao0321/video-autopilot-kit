"""silent_vlog_maker.checklists — PRE_BUILD_CHECKLIST_* per content type (Mode C #2, AP9 落地).

2026-06-20 從 content_routing 拆出。純資料 + get/print，無外部依賴（只 typing）。
"""
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# 🆕 Mode C #2 (2026-05-25) — PRE_BUILD_CHECKLIST per content type
# 落地 AP9：「Pipeline 第一次跑 new content type 沒 pre-flight checklist」
#
# 每個 content type 都有對應 checklist：
#   - defaults: 不問用戶直接用的 values（M-series lessons wrapped）
#   - questions_for_user: build 前必確認的 N 件事（batch 1 message 問完）
#   - wraps_lessons: 這個 checklist 落地了哪些 M-ID
#   - verify_steps: build 完 / Export 後必跑的 verify
# ─────────────────────────────────────────────────────────────────────

PRE_BUILD_CHECKLIST_TEACHING_LONGFORM = {
    # ── 不問用戶直接用 (M-series defaults wrapped) ──────────
    "defaults": {
        # Subtitle (M66 + M68 + M69)
        "subtitle_language": "繁體中文 (s2tw)",       # M66 — 永遠不簡體
        "subtitle_ai_picker": "zh-Hant",               # Editkin caption language token
        "subtitle_bilingual": True,                   # 教學長片 default 中文 + 英文
        "subtitle_style": "hao_teaching_dual_tier",   # M68 lock — apply_hao_teaching_dual_tier()
        "subtitle_corrections": True,                 # M69 — apply_subtitle_corrections() must run
        "subtitle_corrections_dict": "BRAND + CHINESE_HOMOPHONE + PHRASE (Hao default 19+ 字典)",

        # Screen recording cleanup (M60-M62) — if any OBS source
        "screen_rec_clean": True,                     # ⚠️ MANDATORY (M60 v2 2026-05-26): 任何 OBS / 螢幕錄影 import 前 MUST 跑 clean_screen_recording()。#006 v6c 沒跑 → Studio OBS 全段 Chrome + Windows taskbar 露出 → 用戶罵
        "screen_rec_top_crop_px": 200,                # M60 — Chrome tab bar
        "screen_rec_bottom_crop_px": 80,              # M60 — Win11 taskbar
        "screen_rec_trim_start_sec": 1.5,             # M61 — OBS UI flicker pre
        "screen_rec_trim_end_sec": 4.0,               # M61 — OBS stop button click post
        "voice_clean": True,                          # M62 — silence trim long pauses
        "screen_rec_auto_clean_on_import": True,      # 🚨 M60 v2: ingest 前先清掉瀏覽器 chrome / 工作列

        # Canvas / encode
        "canvas": "1920x1080 landscape",
        "fps": 30,
        "codec": "H.264",
        "audio_codec": "AAC 192k (M49 Editkin delivery default)",
        "bgm": "教學-01.mp3 (25% volume, M79 v2 loop-fill — BGM 短於 video 時 loop 填滿全片 + 1.5s crossfade 接縫，畫面還在播音樂不能停)",
        "bgm_loop_fill": True,                        # 🚨 M79 v2 (2026-06-01 修正): BGM source < video → loop 填滿到結尾 + crossfade 接縫，絕不 fade-to-silence（推翻原 bgm_no_loop）
        "assets_match_timeline_fps": True,            # 🚨 M81: ingest receipt 必證明 source 與 Editkin timeline fps 相符
        "timeline_fps": 30,                           # M81: assumed timeline fps for fps conformance check
        "trim_timeline_to_voice_end": True,           # 🚨 M82 (2026-05-27): timeline 長度由人聲真結尾決定 → 不讓 b-roll 撐到 timeline 末段純靜音 (#006 v10 45s 空白尾 bug)
        "player_safe_reencode": True,                 # 🚨 M83 (2026-05-27): final ship 用 libx264 + bf=0 + CFR + no-faststart → 避免 PotPlayer 等 player time-counter quirk (NVENC B-frame ordering)
        "broll_generic_under_main": True,             # 🚨 M86 (2026-05-30): 通用 b-roll 占比(timeline dur) MUST < 官網/產品主素材占比 + 同一 source clip 不重複 → audit_broll_main_ratio(strict=True) (#006 laptop ×3 + generic 64% bug)
        "auto_sequence_brolls": True,                 # 🚨 M75 v0.2: build 時先跑 auto_sequence_brolls() 排 b-roll（canon 早已承諾此 key — 2026-06-10 audit 補落地）

        # Build path
        "build_path": "Editkin v4 (M64 v2 universal)",
        "ffmpeg_scope": "ONLY media pre-process (M60-M62) + delivery verify; no editorial mutation",

        # Executor
        "editkin_command_receipt_required": True,
        "editkin_validation_receipt_required": True,
    },

    # ── build 前必跟用戶確認的 N 件事 (batch 1 message 問完) ──
    "questions_for_user": [
        "0. 🎥 PRODUCTION SETUP VERIFY (M78 — 不假設拍攝能力): 你能/願意錄 talking head 嗎? 露臉嗎? (Hao default = N，純 voice + screen rec)",
        "1. 影片主題 + key takeaway 一句話?",
        "2. 用戶錄的旁白 source path (D:\\...\\raw\\voice.mp3) OR AI mock 先抓節奏?",
        "3. 螢幕錄影 source paths (D:\\...\\raw\\screen-rec-*.mp4)?",
        "4. 想額外加什麼 b-roll? (filename list — 庫存 laptop/book/coffee/meeting OR 新錄)",
    ],

    # ── 這個 checklist 落地哪些 M-ID ────────────────────────
    "wraps_lessons": [
        "M20 v2 no external editor process or draft mutation",
        "M49 AAC 192k default",
        "M60 v2 OBS screen rec crop top 200 / bottom 80 — ingest Editkin 前 MUST 跑 clean_screen_recording()",
        "M79 v2 (2026-06-01 修正) BGM loop 填滿全片 — BGM source < video → loop 到結尾 + 1.5s crossfade 接縫，畫面還在播音樂不能停（推翻原 no-loop；force_mix_bgm() default loop_fill=True）",
        "M81 source asset fps 必 conform to Editkin timeline fps (default 30)；ingest receipt 不符即阻擋",
        "M61 OBS trim start 1.5s / end 4.0s",
        "M62 voice silence trim",
        "M64 v2 build path = Editkin v4 universal",
        "M66 繁體中文 mandatory",
        "M68 dual-tier subtitle style",
        "M69 subtitle corrections (19+ 字典)",
        "M70 Editkin ingest pre-flight",
        "M71 v2 structured EditGraph command only",
        "M72 Editkin export receipt + current.mp4 atomic promotion",
        "M73 helper mutate text 必同步 styles[].range (M69b fix)",
        "M74 PowerShell .ps1 + -File mode (Bash 吃 inline $_)",
        "AP15 caption-broll content matching audit (Mode C #3) — pre-Export must run",
        "M86 (2026-05-30 ENFORCED) 通用 b-roll 占比 < 官網/產品主素材占比 + 同 clip 不重複 — audit_broll_main_ratio(segments, strict=True)。修法兩槓桿：(a) Hook/Reveal 等段改秀真產品提高 main (b) 剩餘 generic 做非重複 montage (每 clip ≤1×)。#006 laptop-typing ×3 + generic 135s vs main 76s 教訓",
        "🌪️ TIM PAN INTEGRATE 不 REPLACE (M77 2026-05-26 用戶修正 + M78 retract talking head) — ✅ INTEGRATE: A節奏/B3-4視覺/C2-3-5權威/D2-4聲音/E promise / ⚙️ CALIBRATE: B1 用 Hao 彩色 / C1 軟尾語氣 / D1 LUFS -11~-12 / G 極端化只 thumbnail / ❌ REPLACE→ Hao signature: Hao0321 Studio 彩色品牌 outro 卡 (非 F1 silhouette；M78 retract — Hao 不錄 talking head 不露臉) / 軟尾字卡「我們下支見 掰掰」(非 F2 hand-on-chin) / Discord 6,940 (非 view count phone) / Hao0321 彩色 outro 永遠保留",
    ],

    # ── build 完 / Export 後必跑 verify ────────────────────
    "verify_steps": [
        "VERIFY 0 (TIM PAN INTEGRATE 必查 — M77 修正 + M78 no-face): ✅ 開頭 14 sec b-roll 一鏡 (A1，無人入鏡) / ✅ 14-22s 爆切 authority stack (A2) / ⚙️ 至少 1 個 slogan card (B1 用 Hao 彩色 OK) / ⚙️ LUFS -11~-12 (Hao 舒適區，不到 -10) / ❌ 結尾 = Hao0321 Studio 彩色品牌 outro 卡 (純圖+voice，無人入鏡) + 軟尾字卡「我們下支見 掰掰」(不用 Tim silhouette/hand-on-chin)",
        "VERIFY 0b (M81 fps conformance): Editkin ingest receipt + ffprobe 必全 = timeline fps；不符先 normalize，再重送 ingest",
        "VERIFY 0c (M82 timeline trim to voice end, 2026-05-27 NEW): silencedetect=noise=-30dB:d=5 末段 silence > 8s = FAIL (timeline 比人聲長 → b-roll 殘留空白尾)。outro card tpad 在人聲真結尾後 5-7s，不讓 b-roll 撐到 timeline 末 (#006 v10 45s 空白尾)",
        "VERIFY 0d (M83 player-safe final re-encode, 2026-05-27 NEW): ship 版必 libx264 + -bf 0 + -vsync cfr -r 30 + closed GOP + 無 faststart。確認 ffprobe pict_type 無 B-frame / avg=r_frame_rate。避免 PotPlayer time-counter quirk。BGM-loop verify 用 astats Peak=-inf 雙重確認不單靠 volumedetect mean",
        "VERIFY 1 (JSON layer): grep 简体字 count = 0 (M66 layer 1)",
        "VERIFY 2 (frame layer): ffmpeg extract t=10/mid/end → Read → confirm 繁體 + dual-tier style + 0 typo (M66 layer 3 + M68 + M69)",
        "VERIFY 3 (audio layer): ffprobe duration / codec / bitrate match defaults (M49)",
        "VERIFY 4 (subtitle integrity): Editkin caption-quality receipt has 0 typo / timing / overflow blockers (M69)",
        "VERIFY 5 (audio leak): Editkin mix validation receipt confirms B-roll source audio policy and final loudness (M55)",
        "VERIFY 5b (M60 v2 screen rec clean): ffmpeg 抽 frame at Studio/Code/Game OBS time → confirm NO Chrome tabs / NO Windows taskbar visible (#006 v6c bug — 沒跑 clean_screen_recording())",
        "VERIFY 5c (M79 v2 BGM loop-fill): astats 確認**全片都有 BGM**含 source-duration 之後的段落（post-142s 仍有音樂能量，畫面還在播音樂不能停）+ 接縫無爆音；ffprobe BGM source duration 確認需 loop 填滿到 video 結尾",
        "VERIFY 6 (caption-broll match, AP15): Editkin audit_autopilot_plan receipt high severity = 0 / match rate ≥ 90%",
        "VERIFY 6b (M86 b-roll 占比, 2026-05-30 NEW): audit_broll_main_ratio(segments, strict=True) — assert generic_s < main_s (官網/產品主素材占比 > 通用 b-roll) + repeats={} (無同一 clip 重複)。by timeline duration 不是 segment 數。違反 = 通用素材喧賓奪主 (#006 generic 64% + laptop ×3)",
        "VERIFY 7 (subtitle invariants, M73): Editkin project-schema gate validates text, timing, bounds and style token",
        "FINAL: 「已完成」definition = mp4 re-exported + 3 frame verify pass (AP10) + AP15 audit clean",
    ],
}


PRE_BUILD_CHECKLIST_FOOD_VLOG = {
    # M57 — 食記必 batch 問用戶（不要憑視覺猜菜品 / WebSearch 抓 stale 地址）
    "defaults": {
        "canvas": "1080x1920 portrait",          # M46 auto-detect
        "fps": 30,
        "subtitle_language": "繁體中文 (s2tw)",   # M66
        "subtitle_style": "white_outline_with_box (basic preset)",  # M59 v2
        "outro_card": True,                       # M56 — 店家資訊 outro 3-5 sec
        "bgm": "旅遊-01.mp3 (25% volume)",
        "audio_strip_broll": True,                # M29 — strip B-roll audio
        "force_mix_bgm_post_export": True,        # M55 — ffmpeg force-mix mandatory
        "build_path": "Editkin v4 (M64 v2)",
    },
    "questions_for_user": [
        "1. 菜品具體名稱 (每碗 / 每盤 — 不要憑視覺猜，M44)",
        "2. 店家完整資訊 (店名 + 分店 + 完整地址 + 電話 + 營業時間 — 用戶 ground truth > WebSearch, M37)",
        "3. 哪道是 climax / 重點 emphasis?",
        "4. caption 風格 (basic preset default / 要花字 explicit 說)",
        "5. BGM 偏好 (旅遊-01 default / 02 / chill / 自備)",
    ],
    "wraps_lessons": [
        "M29 audio strip B-roll",
        "M37 user ground truth > WebSearch",
        "M44 不憑視覺猜菜品",
        "M46 auto-detect portrait canvas",
        "M49 AAC 192k default",
        "M55 ffmpeg force-mix BGM mandatory",
        "M56 outro card 店家資訊 lower-third",
        "M57 batch 5 questions",
        "M59 v2 basic preset default",
        "M64 v2 build path = Editkin v4",
        "M66 繁體中文",
        "AP15 caption-broll content matching audit (Mode C #3)",
    ],
    "verify_steps": [
        "VERIFY 1: caption text 對應用戶 ground truth 菜品 (M44)",
        "VERIFY 2: outro card 含完整店家資訊 (M56)",
        "VERIFY 3: ffprobe duration / portrait 1080×1920 (M46)",
        "VERIFY 4: audio waveform check — 無 B-roll 環境音漏出 (M55)",
        "VERIFY 5 (caption-broll match, AP15): Editkin audit_autopilot_plan receipt 證明菜名與食物特寫語意相符",
        "FINAL: mp4 frame verify + audio waveform pass + AP15 audit clean = done (AP10)",
    ],
}


PRE_BUILD_CHECKLIST_TRAVEL_VLOG = {
    # 通用旅遊 vlog (#003 馬來西亞風格 — 長片或 short)
    "defaults": {
        "canvas": "auto-detect (M46)",
        "fps": 30,
        "subtitle_language": "繁體中文 (s2tw)",   # M66
        "subtitle_style": "basic preset OR favorited 花字 (M59 v2 default basic, 花字 opt-in)",
        "bgm": "旅遊-01.mp3 (25% volume)",
        "audio_strip_broll": True,                # M29
        "force_mix_bgm_post_export": True,        # M55
        "scene_cluster_run": True,                # M12 auto-cluster by time gap + GPS
        "frame_audit_hires": True,                # M9/M34 — every clip 4 frames 640x360
        "build_path": "Editkin v4 (M64 v2)",
    },
    "questions_for_user": [
        "1. 行程主題 (Day 1-2 / 全程 / 單地點) + Part N?",
        "2. 拍攝地點 (GPS 自動抓 / 手動補)?",
        "3. caption tone (M45 — 旅遊 vs 食記節奏不同；vlog default「現在時間~」軟尾)",
        "4. talking head 旁白? (Y/N — silent vlog OR voice-over)",
        "5. BGM 偏好?",
    ],
    "wraps_lessons": [
        "M9/M34 hi-res frame audit",
        "M12 scene cluster by time/GPS",
        "M29 audio strip B-roll",
        "M37 verify facts via WebSearch + user override",
        "M45 旅遊 vs 食記 tone 不同",
        "M46 auto-detect canvas",
        "M55 ffmpeg force-mix BGM",
        "M59 v2 basic preset default",
        "M64 v2 build path = Editkin v4",
        "M66 繁體中文",
        "AP15 caption-broll content matching audit (Mode C #3)",
    ],
    "verify_steps": [
        "VERIFY 1: caption 對應實拍 frame (M9 hi-res audit)",
        "VERIFY 2: scene timeline 連續 (M12 clustering)",
        "VERIFY 3: ffprobe canvas / duration",
        "VERIFY 4: audio leak check (M55)",
        "VERIFY 5 (caption-broll match, AP15): Editkin audit_autopilot_plan receipt 證明地名／景點與實拍片段相符",
        "FINAL: mp4 frame verify + 3 spot check + AP15 audit clean = done (AP10)",
    ],
}


PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING = {
    # 子集合：純 OBS 螢幕錄影 + 旁白（無 b-roll / talking head）
    # 是 TEACHING_LONGFORM 的 minimal variant
    "defaults": {
        **PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["defaults"],
        "talking_head": False,                        # 純螢幕錄影
        "broll": False,
        "subtitle_bilingual": True,                   # 教學 default 雙語
    },
    "questions_for_user": [
        "1. 教學主題 + key takeaway 一句話?",
        "2. 旁白 source path (D:\\...\\raw\\voice-*.mp3)?",
        "3. 螢幕錄影 source paths (list)?",
        "4. 章節分段 (e.g. 「Setup / Demo / Conclusion」)?",
        "5. CTA (Discord / 訂閱 / 下集預告)?",
    ],
    "wraps_lessons": PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["wraps_lessons"],
    "verify_steps": PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["verify_steps"],
}


# Lookup table — content_type → checklist
PRE_BUILD_CHECKLISTS = {
    "teaching_longform": PRE_BUILD_CHECKLIST_TEACHING_LONGFORM,
    "teaching": PRE_BUILD_CHECKLIST_TEACHING_LONGFORM,  # alias
    "screen_recording_teaching": PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING,
    "food_vlog": PRE_BUILD_CHECKLIST_FOOD_VLOG,
    "food": PRE_BUILD_CHECKLIST_FOOD_VLOG,              # alias
    "travel_vlog": PRE_BUILD_CHECKLIST_TRAVEL_VLOG,
    "vlog": PRE_BUILD_CHECKLIST_TRAVEL_VLOG,            # alias
}


def get_pre_build_checklist(content_type: str) -> Optional[dict]:
    """Get the pre-build checklist for a content_type.

    Args:
        content_type: e.g. "teaching_longform" / "food_vlog" / "travel_vlog"

    Returns:
        checklist dict with keys: defaults / questions_for_user / wraps_lessons / verify_steps
        None if content_type not registered.
    """
    return PRE_BUILD_CHECKLISTS.get(content_type)


def print_pre_build_checklist(content_type: str) -> None:
    """Print a human-readable checklist for a content_type.

    Use this at start of any new build session:
        print_pre_build_checklist("teaching_longform")
    """
    checklist = get_pre_build_checklist(content_type)
    if checklist is None:
        print(f"⚠️ No pre-build checklist for content_type: {content_type!r}")
        print(f"   Registered types: {sorted(set(PRE_BUILD_CHECKLISTS.keys()))}")
        return

    print("=" * 70)
    print(f"🎬 Pre-Build Checklist — {content_type}")
    print(f"   (Mode C #2 AP9 落地 — 「Pipeline 第一次跑 new content type 沒 pre-flight」)")
    print("=" * 70)

    print()
    print("📋 Questions for user (batch 1 message 問完, 不要 5 次來回)：")
    for q in checklist["questions_for_user"]:
        print(f"  {q}")

    print()
    print("⚙️  Defaults (不問用戶直接用)：")
    for k, v in checklist["defaults"].items():
        print(f"  • {k}: {v}")

    print()
    print("🎓 Wraps lessons（這個 checklist 自動 enforce）：")
    for lesson in checklist["wraps_lessons"]:
        print(f"  ✓ {lesson}")

    print()
    print("✅ Verify steps (build 完 + Export 後必跑)：")
    for step in checklist["verify_steps"]:
        print(f"  {step}")

    print()
    print("=" * 70)
