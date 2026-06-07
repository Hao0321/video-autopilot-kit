"""
capcut_helpers.text_style — CapCut「基礎」tab 預設組樣式 (2026-05-24 M51 lesson).

直式 Shorts 不需要花字 effect — 基礎 tab 的「預設組樣式」(6 個 Aa preset) 反而 cleaner / 更專業。
這 module 提供 JSON pattern 套用這些 preset，不需走 Computer Use agent。

從用戶 Tamsui-Ramen-Short-v2 seg #0 手動 reverse engineer 出的 pattern：
- 字體：剪映团子 (CapCut bundled effect_id 7598225001988246801)
- 預設樣式：白底黑邊 (white fill + 0.06 black stroke + no shadow)
- 結構：清掉 extra_material_refs (花字) + 加 content.styles[].strokes
"""
import json
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────
# CapCut bundled fonts (effect_id → cache subdir → font.ttf)
# ─────────────────────────────────────────────────────────────────────

CAPCUT_FONTS = {
    "剪映团子": {
        "effect_id": "7598225001988246801",
        "cache_subdir": "1ecc73e2c3778fc5584e430e53a2560d",
        "font_filename": "font.ttf",
    },
    "capcut_systemfont": {
        # M68 (2026-05-25) — CapCut bundled SystemFont (Hao 教學 default)
        # Not in Cache/effect/ — lives in Apps/<version>/Resources/Font/SystemFont/
        # Use raw absolute path (no effect_id needed)
        "absolute_path": str(Path.home() / "AppData/Local/CapCut/Apps")  # CapCut version-specific; adjust to your install,
    },
    # Future: add more user-discovered fonts here via the same pattern
}


def get_capcut_font_path(font_name: str) -> str:
    """Resolve full font.ttf path for a CapCut bundled font."""
    from .paths import EFFECT_CACHE
    if font_name not in CAPCUT_FONTS:
        raise KeyError(f"Unknown CapCut font '{font_name}'. Known: {list(CAPCUT_FONTS.keys())}")
    f = CAPCUT_FONTS[font_name]
    # M68: support fonts that live outside effect cache (e.g. CapCut SystemFont in Apps/<version>/Resources/)
    if "absolute_path" in f:
        return f["absolute_path"]
    path = EFFECT_CACHE / f["effect_id"] / f["cache_subdir"] / f["font_filename"]
    return str(path).replace("\\", "/")


# ─────────────────────────────────────────────────────────────────────
# 預設組樣式 (basic tab presets — JSON pattern from user reverse engineer)
# ─────────────────────────────────────────────────────────────────────

PRESET_STYLES = {
    # 白底黑邊 (4th preset in panel — 用戶 2026-05-24 #004 偏好)
    "white_outline_black": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.06,
        "has_shadow": False,
        "fill_color": [1, 1, 1],  # RGB 0-1 (white)
        "stroke_color": [0, 0, 0],  # RGB 0-1 (black)
        "stroke_width": 0.06,
        "default_font": "剪映团子",
    },
    # 純白無框
    "white_plain": {
        "text_color": "#ffffff",
        "border_color": "",
        "border_width": 0,
        "has_shadow": False,
        "fill_color": [1, 1, 1],
        "stroke_color": None,
        "stroke_width": 0,
        "default_font": "剪映团子",
    },
    # 黃底黑字 (highlight 食尚玩家風)
    "yellow_highlight_black": {
        "text_color": "#000000",
        "border_color": "#FFD700",
        "border_width": 0.0,
        "has_shadow": False,
        "fill_color": [0, 0, 0],
        "stroke_color": None,
        "stroke_width": 0,
        "default_font": "剪映团子",
        "background_color": [1, 0.84, 0],  # gold highlight
    },
    # 紅字黑邊 (驚喜/強調)
    "red_outline_black": {
        "text_color": "#ff0000",
        "border_color": "#000000",
        "border_width": 0.06,
        "has_shadow": False,
        "fill_color": [1, 0, 0],
        "stroke_color": [0, 0, 0],
        "stroke_width": 0.06,
        "default_font": "剪映团子",
    },
    # ⭐ M68 (2026-05-25) — Hao 教學長片字幕 PERMANENT DEFAULT (雙 tier)
    # 用戶在 CapCut 手動 set + 2 張截圖教 + 鎖進 SKILL
    # Primary subtitle (中文 主要) — 較柔和（半透明 + 圓角 + 較高 box）
    "hao_teaching_primary": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.08,
        "has_shadow": False,
        "fill_color": [1.0, 1.0, 1.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 0.06,
        "background_color": "#000000",
        "background_alpha": 0.7,            # 不透明度 70%（CapCut 預設 3rd row 3rd Aa）
        "background_round_radius": 0.4,     # 圓角 40%
        "background_height": 0.28,          # 高度 28%
        "default_font": "capcut_systemfont",
    },
    # Secondary subtitle (英文 次要) — 較硬挺（全不透明 + 直角 + 較短 box）
    # 雙 tier 視覺區分主次 — 中文較柔和、英文較硬挺
    "hao_teaching_secondary": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.08,
        "has_shadow": False,
        "fill_color": [1.0, 1.0, 1.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 0.06,
        "background_color": "#000000",
        "background_alpha": 1.0,            # 不透明度 100% (CapCut 預設 2nd Aa)
        "background_round_radius": 0.0,     # 直角無圓角
        "background_height": 0.14,          # 高度 14% (較短 box)
        "default_font": "capcut_systemfont",
    },
}


# ─────────────────────────────────────────────────────────────────────
# Apply preset to text segment (replaces 花字 effect approach)
# ─────────────────────────────────────────────────────────────────────

def apply_text_preset(draft: dict, segment_idx: int,
                      preset_name: str = "white_outline_black",
                      font_name: str = None,
                      font_size: int = 15,
                      clear_existing_effects: bool = True) -> dict:
    """Apply CapCut 基礎 tab 預設樣式 to a text segment.

    M51 lesson: 直式 Shorts caption 用這個取代 apply_effect_to_segment() 花字 path。

    Args:
        draft: full draft dict
        segment_idx: 0-indexed segment in first text track
        preset_name: key from PRESET_STYLES (default 'white_outline_black')
        font_name: CapCut bundled font name, defaults to preset's default_font
        font_size: CapCut UI native size (default 15 — what 預設組樣式 shows)
        clear_existing_effects: True = remove extra_material_refs entries that are 花字

    Returns: the text material dict that was modified
    Raises: KeyError if preset_name unknown
    """
    if preset_name not in PRESET_STYLES:
        raise KeyError(f"Unknown preset '{preset_name}'. Available: {list(PRESET_STYLES.keys())}")
    preset = PRESET_STYLES[preset_name]
    font = font_name or preset.get("default_font", "剪映团子")
    font_path = get_capcut_font_path(font)

    # Locate text track + segment
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]
    if not text_tracks:
        raise ValueError("No text tracks found")
    segs = text_tracks[0].get("segments", [])
    if segment_idx >= len(segs):
        raise ValueError(f"Segment idx {segment_idx} out of range")
    seg = segs[segment_idx]

    # Locate text material
    texts = draft.get("materials", {}).get("texts", [])
    mat = next((t for t in texts if t["id"] == seg.get("material_id")), None)
    if not mat:
        raise ValueError(f"No text material for segment {segment_idx}")

    # ─── Update material-level fields ───
    mat["font_path"] = font_path
    mat["text_color"] = preset["text_color"]
    mat["border_color"] = preset.get("border_color", "")
    mat["border_width"] = preset.get("border_width", 0)
    mat["has_shadow"] = preset.get("has_shadow", False)

    # ─── Update content.styles[] ───
    try:
        co = json.loads(mat.get("content", "{}"))
    except json.JSONDecodeError:
        co = {"text": "", "styles": []}

    # Ensure styles list exists
    styles = co.setdefault("styles", [])
    if not styles:
        styles.append({"range": [0, len(co.get("text", ""))]})

    for s in styles:
        # Set font
        s["font"] = {"path": font_path, "id": "", "cn_name": "", "tw_name": ""}
        # Set size (CapCut UI native — not pt)
        s["size"] = font_size
        # Clear effectStyle (花字)
        s.pop("effectStyle", None)
        # Set fill (solid color)
        s["fill"] = {
            "alpha": 1,
            "content": {
                "render_type": "solid",
                "solid": {"alpha": 1, "color": preset["fill_color"]},
            },
        }
        # Set strokes
        if preset.get("stroke_color") and preset.get("stroke_width"):
            s["strokes"] = [{
                "width": preset["stroke_width"],
                "content": {
                    "render_type": "solid",
                    "solid": {"alpha": 1, "color": preset["stroke_color"]},
                },
            }]
        else:
            s["strokes"] = []
        s["useLetterColor"] = False

    mat["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))

    # ─── Clear 花字 effect refs (extra_material_refs) ───
    if clear_existing_effects:
        # Identify which refs are 花字 effects (vs animations) by lookup in materials.effects
        effect_ids_in_materials = {
            e["id"]: e.get("category_name", "")
            for e in draft.get("materials", {}).get("effects", [])
        }
        new_refs = []
        for ref in seg.get("extra_material_refs", []):
            cat = effect_ids_in_materials.get(ref, "")
            if "text-flower" in cat or "panel-text-flower" in cat:
                # This is a 花字 effect → drop
                continue
            new_refs.append(ref)
        seg["extra_material_refs"] = new_refs

    return mat


def apply_text_preset_to_all(draft: dict, preset_name: str = "white_outline_black",
                             font_name: str = "剪映团子",
                             font_size: int = 15) -> int:
    """Bulk apply same preset to ALL text segments. Returns count modified."""
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]
    if not text_tracks:
        return 0
    n = len(text_tracks[0].get("segments", []))
    for idx in range(n):
        apply_text_preset(draft, idx, preset_name=preset_name,
                         font_name=font_name, font_size=font_size)
    return n


def _is_chinese_text(text: str) -> bool:
    """Detect if text contains Chinese characters (CJK Unified Ideographs)."""
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in text)


def apply_hao_teaching_dual_tier(draft: dict) -> dict:
    """⭐ M68 — Hao 教學長片字幕 PERMANENT WORKFLOW (2026-05-25 用戶 lock)

    自動偵測每個 text material 語言 → apply 對應 preset：
    - 中文 (CJK chars) → hao_teaching_primary (alpha 0.7 / radius 0.4 / height 0.28 — 柔和)
    - 英文 (no CJK) → hao_teaching_secondary (alpha 1.0 / radius 0.0 / height 0.14 — 硬挺)

    Modifies text materials at the JSON FIELD level (NOT via apply_text_preset because
    M68 uses background_alpha/radius/height field — different from base content.styles).

    Returns: {'zh_count': N, 'en_count': N, 'total': N}

    Usage (after CapCut AI 字幕 + 翻譯 done, but before Export):
        kill_capcut_all()           # M20
        draft = load_draft(name)
        stats = apply_hao_teaching_dual_tier(draft)
        save_draft_with_sync(name, draft)
        # User reopens CapCut → verify → Export
    """
    import json
    primary = PRESET_STYLES["hao_teaching_primary"]
    secondary = PRESET_STYLES["hao_teaching_secondary"]
    font_path = get_capcut_font_path(primary["default_font"])  # capcut_systemfont

    texts = draft.get("materials", {}).get("texts", [])
    zh_count = 0
    en_count = 0

    for t in texts:
        try:
            co = json.loads(t.get("content", "{}"))
        except json.JSONDecodeError:
            continue
        text = co.get("text", "")
        if not text:
            continue

        preset = primary if _is_chinese_text(text) else secondary
        if preset is primary:
            zh_count += 1
        else:
            en_count += 1

        # Apply M68 background fields (these live on material itself, NOT content.styles)
        t["text_color"] = preset["text_color"]
        t["border_color"] = preset["border_color"]
        t["border_width"] = preset["border_width"]
        t["has_shadow"] = preset["has_shadow"]
        t["background_color"] = preset["background_color"]
        t["background_alpha"] = preset["background_alpha"]
        t["background_round_radius"] = preset["background_round_radius"]
        t["background_height"] = preset["background_height"]
        t["font_path"] = font_path

        # Also sync content.styles[] fill + stroke + font
        for s in co.get("styles", []):
            s["font"] = {"path": font_path, "id": "", "cn_name": "", "tw_name": ""}
            s["fill"] = {
                "alpha": 1.0,
                "content": {"render_type": "solid",
                            "solid": {"alpha": 1.0, "color": preset["fill_color"]}},
            }
            s["strokes"] = [{
                "width": preset["stroke_width"],
                "alpha": 1.0,
                "content": {"render_type": "solid",
                            "solid": {"alpha": 1.0, "color": preset["stroke_color"]}},
            }]

        t["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))

    return {"zh_count": zh_count, "en_count": en_count, "total": zh_count + en_count}


def list_capcut_fonts() -> list[str]:
    """List known CapCut bundled fonts."""
    return list(CAPCUT_FONTS.keys())


def list_preset_styles() -> list[str]:
    """List available preset styles."""
    return list(PRESET_STYLES.keys())
