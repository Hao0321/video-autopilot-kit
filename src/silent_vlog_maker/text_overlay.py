"""
silent_vlog_maker.text_overlay — R15 + R19 + R21 text overlay builder.

Overlay class + position presets for unified subtitle styling.
"""
from dataclasses import dataclass

from .constants import (
    COLOR_GOLD, COLOR_WHITE, COLOR_CREAM,
    BOX_DARK, BOX_SUBTLE, BOX_CINEMATIC,
    FONT_NOTO_BLACK, FONT_NOTO_BOLD,
    COLOR_VARIETY,
)
from .shorts_captions import TEXT_SAFE_RECT, fit_percent, load_cjk_font


# ─────────────────────────────────────────────────────────────────────
# R15 + Typography: Overlay builder
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Overlay:
    """Single drawtext overlay spec, position presets handle safe zone."""
    text: str
    position: str  # "title_hook" / "title_detail" / "tv_hook" / etc.
    t_start: float = 0.0
    t_end: float = 5.0
    fade_in: float = 0.4
    fade_out: float = 0.5

    def to_drawtext(self, text_file_path: str) -> str:
        """Convert to ffmpeg drawtext filter string (without leading comma)."""
        preset = POSITION_PRESETS[self.position]
        params = [
            f"fontfile='{preset['font']}'",
            f"textfile='{text_file_path}'",
            f"fontsize={_fit_fontsize(self.text, preset)}",
            f"fontcolor={preset['color']}",
            f"x={preset['x']}",
            f"y={preset['y']}",
        ]
        if preset.get("border_w"):
            params.append(f"borderw={preset['border_w']}")
            params.append(f"bordercolor={preset.get('border_color', 'black')}")
        if preset.get("box"):
            params.append(f"box=1")
            params.append(f"boxcolor={preset['box_color']}")
            params.append(f"boxborderw={preset['box_pad']}")

        # Build alpha curve: fade in over fade_in_s, hold, fade out at (t_end - fade_out_s)
        # drawtext 的 t 是「絕對」時間軸時間 — fade 計算必須用 (t - t_start) 相對時間，
        # 否則 t_start>0 的 overlay alpha 恆為負 → 全程隱形（2026-06-10 audit）
        rel = f"(t-{self.t_start})"
        dur = self.t_end - self.t_start
        fade_out_start = dur - self.fade_out
        alpha = (
            f"if(lt({rel},{self.fade_in}),{rel}/{self.fade_in},"
            f"if(gt({rel},{fade_out_start}),"
            f"({dur}-{rel})/{self.fade_out},1))"
        )
        params.append(f"alpha='{alpha}'")
        params.append(f"enable='between(t,{self.t_start},{self.t_end})'")
        return "drawtext=" + ":".join(params)


def _fit_fontsize(text, preset):
    """Preset size, shrunk (not below 70 %) until the widest line plus its box
    fits TEXT_SAFE_RECT's width; longer text raises instead of overflowing."""
    font = load_cjk_font(100, [str(preset["font"]).replace("\\:", ":")])
    width = max(font.getlength(line) for line in str(text).splitlines() or [""])
    deco = 2 * (preset.get("box_pad", 0) + preset.get("border_w", 0))
    return preset["fs"] * fit_percent(width * preset["fs"] / 100.0, deco, 70,
                                      "overlay %r" % text) // 100


# ─────────────────────────────────────────────────────────────────────
# R19: Unified center-bottom subtitle presets (Shorts portrait 1080×1920)
# ─────────────────────────────────────────────────────────────────────
# Every box stays inside TEXT_SAFE_RECT (x 108..972, y 384..1440): bottom
# presets are anchored with drawtext's own text height `th`, so the detail box
# ends at 1440 and the hook box ends 12 px above a one-line detail box.
_SAFE_X0, _SAFE_Y0, _SAFE_X1, _SAFE_Y1 = TEXT_SAFE_RECT

POSITION_PRESETS = {
    # v7 NEW — unified center-bottom subtitle position (R19)
    "title_hook": {  # 主 hook / 賣點（金黃強調）
        "fs": 80, "x": "(w-tw)/2", "y": "%d-th" % (_SAFE_Y1 - 2 * 22 - 68 - 12 - 28),
        "color": COLOR_GOLD, "font": FONT_NOTO_BLACK,
        "box": True, "box_color": BOX_DARK, "box_pad": 28,
    },
    "title_detail": {  # 副標 / 資訊細節（白色 + 在 hook 下方）
        "fs": 56, "x": "(w-tw)/2", "y": "%d-th" % (_SAFE_Y1 - 22),
        "color": COLOR_CREAM, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": BOX_DARK, "box_pad": 22,
    },

    # Legacy presets (kept for backward compat — DO NOT use in v7+)
    "main_title": {
        "fs": 120, "x": "(w-tw)/2", "y": "720",
        "color": COLOR_GOLD, "font": FONT_NOTO_BLACK,
        "box": True, "box_color": BOX_DARK, "box_pad": 32,
    },
    "subtitle": {
        "fs": 58, "x": "(w-tw)/2", "y": "880",
        "color": COLOR_CREAM, "font": FONT_NOTO_BOLD,
        "border_w": 3, "border_color": "black@0.85",
    },
    "lower_third": {
        "fs": 50, "x": str(_SAFE_X0 + 20), "y": str(_SAFE_Y0 + 20),
        "color": COLOR_WHITE, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": BOX_SUBTLE, "box_pad": 20,
    },
    "time_jump": {
        "fs": 88, "x": "(w-tw)/2", "y": "850",
        "color": COLOR_GOLD, "font": FONT_NOTO_BLACK,
        "box": True, "box_color": BOX_CINEMATIC, "box_pad": 28,
    },
    "evaluation_center": {
        "fs": 66, "x": "(w-tw)/2", "y": "1180",
        "color": COLOR_CREAM, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": BOX_DARK, "box_pad": 26,
    },
    "signature_bottom": {
        "fs": 74, "x": "(w-tw)/2", "y": "%d-th" % (_SAFE_Y1 - 30),
        "color": COLOR_GOLD, "font": FONT_NOTO_BLACK,
        "box": True, "box_color": BOX_DARK, "box_pad": 30,
    },
}


# ─────────────────────────────────────────────────────────────────────
# M13: Landscape long-form unified subtitle position (2026-05-24 v2 — mass production)
# ─────────────────────────────────────────────────────────────────────
# 長片 1920×1080 不能套 Shorts y=1280-1400（會跑出畫面）。獨立 PRESETS。

LANDSCAPE_TITLE_Y = 820       # 長片主標位置（中下偏下）
LANDSCAPE_DETAIL_Y = 930      # 長片副標位置

LANDSCAPE_PRESETS = {
    # NEW v2 — informational caption (unified landscape position)
    "title_hook": {  # 主 hook（金黃強調）
        "fs": 64, "x": "(w-tw)/2", "y": str(LANDSCAPE_TITLE_Y),
        "color": COLOR_GOLD, "font": FONT_NOTO_BLACK,
        "box": True, "box_color": BOX_DARK, "box_pad": 24,
    },
    "title_detail": {  # 副標
        "fs": 44, "x": "(w-tw)/2", "y": str(LANDSCAPE_DETAIL_Y),
        "color": COLOR_CREAM, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": BOX_DARK, "box_pad": 18,
    },
    "timestamp_corner": {  # 時間戳左上角
        "fs": 32, "x": "60", "y": "60",
        "color": COLOR_GOLD, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": "black@0.6", "box_pad": 12,
    },
    "day_marker_corner": {  # Day 標記角落小型（vs day_marker 全屏大字）
        "fs": 40, "x": "60", "y": "60",
        "color": COLOR_VARIETY["gold"], "font": FONT_NOTO_BLACK,
        "box": True, "box_color": "black@0.7", "box_pad": 14,
    },
    "location_lower_third": {  # 地點 lower-third
        "fs": 36, "x": "60", "y": str(LANDSCAPE_DETAIL_Y - 30),
        "color": COLOR_WHITE, "font": FONT_NOTO_BOLD,
        "box": True, "box_color": "black@0.55", "box_pad": 14,
    },
}


# ─────────────────────────────────────────────────────────────────────
# R21 + M15: 綜藝字卡 presets (landscape long-form 1920×1080)
# ─────────────────────────────────────────────────────────────────────
# 比 informational subtitle 更 vibrant — cyan + magenta + gold mix

TV_VARIETY_PRESETS = {
    "day_marker": {  # 「Day 1 啟程」大字卡（landscape 1920×1080，全屏中央）
        "fs": 110, "x": "(w-tw)/2", "y": "(h-th)/2",
        "color": COLOR_VARIETY["gold"], "font": FONT_NOTO_BLACK,
        "box": True, "box_color": "black@0.8", "box_pad": 50,
    },
    "tv_hook": {  # 綜藝感主標題 (cyan) — landscape 中下
        "fs": 72, "x": "(w-tw)/2", "y": "820",
        "color": COLOR_VARIETY["cyan"], "font": FONT_NOTO_BLACK,
        "box": True, "box_color": "black@0.65", "box_pad": 26,
    },
    "tv_emoji_caption": {  # 行動描述 + emoji — landscape 中下偏下
        "fs": 54, "x": "(w-tw)/2", "y": "930",
        "color": COLOR_VARIETY["white"], "font": FONT_NOTO_BOLD,
        "box": True, "box_color": "black@0.55", "box_pad": 20,
    },
    "tv_emphasis": {  # 強調點 (magenta)
        "fs": 80, "x": "(w-tw)/2", "y": "880",
        "color": COLOR_VARIETY["magenta"], "font": FONT_NOTO_BLACK,
        "box": True, "box_color": "black@0.7", "box_pad": 24,
    },
    "tv_timestamp": {  # 時間軸（左上小字）
        "fs": 40, "x": "40", "y": "40",
        "color": COLOR_VARIETY["gold"], "font": FONT_NOTO_BOLD,
        "box": True, "box_color": "black@0.6", "box_pad": 14,
    },
}


# ─────────────────────────────────────────────────────────────────────
# Layout dispatcher (2026-05-24 v2 — mass production unified API)
# ─────────────────────────────────────────────────────────────────────

LAYOUT_PRESETS = {
    "portrait": POSITION_PRESETS,         # Shorts 1080×1920
    "landscape": LANDSCAPE_PRESETS,       # 長片 1920×1080 informational
    "landscape_variety": TV_VARIETY_PRESETS,  # 長片 1920×1080 綜藝感
}


def get_preset(name: str, layout: str = "portrait") -> dict:
    """Get preset by name with layout dispatch.

    Usage:
        from silent_vlog_maker import Overlay, get_preset
        # Same Overlay class works for both layouts — preset dict drives positioning
        ov = Overlay(text="DAY 1 出發拉", position="title_hook", t_start=0, t_end=3)
        # to_drawtext() reads POSITION_PRESETS["title_hook"] by default (portrait)
        # For landscape, swap preset family:
        # POSITION_PRESETS = LAYOUT_PRESETS["landscape"]  # not recommended — module mut
        # Better: pass preset directly via custom Overlay subclass or layout-aware factory.

    Returns: preset dict from the requested layout family.
    Raises: KeyError if name not in layout family.
    """
    if layout not in LAYOUT_PRESETS:
        raise KeyError(f"Unknown layout '{layout}'. Available: {list(LAYOUT_PRESETS.keys())}")
    family = LAYOUT_PRESETS[layout]
    if name not in family:
        raise KeyError(f"Preset '{name}' not in layout '{layout}'. Available: {list(family.keys())}")
    return family[name]


def list_presets(layout: str = None) -> dict:
    """List all preset names per layout family. If layout=None, return all."""
    if layout:
        return {layout: list(LAYOUT_PRESETS[layout].keys())}
    return {l: list(presets.keys()) for l, presets in LAYOUT_PRESETS.items()}


def self_test() -> None:
    """Portrait preset boxes stay in TEXT_SAFE_RECT; long overlays shrink or fail."""
    for name, preset in POSITION_PRESETS.items():
        th, pad = 1.2 * preset["fs"], preset.get("box_pad", 0)   # one line, generous
        y = preset["y"]
        top = int(y[:-3]) - th if y.endswith("-th") else int(y)
        assert top - pad >= _SAFE_Y0 and top + th + pad <= _SAFE_Y1, name   # was 1490 / 1680
        assert not preset["x"].isdigit() or int(preset["x"]) - pad >= _SAFE_X0, name
    assert "fontsize=80:" in Overlay("短標題", "title_hook").to_drawtext("t.txt")
    long_title = Overlay("這是一個非常非常長的標題", "title_hook").to_drawtext("t.txt")
    assert 56 <= int(long_title.split("fontsize=")[1].split(":")[0]) < 80, long_title
    try:
        Overlay("這是一個長到怎麼縮小都放不進安全區的超級標題文字", "title_hook").to_drawtext("t")
        raise AssertionError("an overlay needing < 70% must fail instead of overflowing")
    except ValueError:
        pass
    print("[text_overlay selftest] OK")


if __name__ == "__main__":   # python -m silent_vlog_maker.text_overlay
    self_test()
