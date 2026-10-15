"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import art_direction as art
from project_paths import asset_path


W, H = 1920, 1080


BRAND = {
    "fonts_dir": str(asset_path("fonts")),
    "font_cjk": str(asset_path("fonts", "_active", "Huninn-Regular.ttf")),
    "font_num": str(asset_path("fonts", "Anton", "Anton-Regular.ttf")),
    "bg_top": (11, 10, 31), "bg_bot": (26, 15, 53),
    "gold": (255, 210, 63), "gold_dark": (40, 26, 5),
    "purple": (138, 92, 255), "cyan": (69, 212, 255),
    "green": (43, 214, 123), "dim": (150, 150, 180), "white": (255, 255, 255),
}


def _font(path, size): return ImageFont.truetype(path, size)


def fcjk(s): return _font(BRAND["font_cjk"], s)


def canvas(glow_center=True, theme="ai", variant="signal_grid", progress=0.0):
    """creator Signal Grid 黑底白格背景。

    `glow_center` 保留舊 API 相容；新背景本身已內建克制聚光。theme 可用
    ai/food/travel/toy/game/diy/cafe/general，讓同一版式隨題材換氣質。
    """
    im = art.render_background(W, H, theme=theme, variant=variant, progress=progress)
    if glow_center:
        cfg = art.resolve_theme(theme)
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).ellipse([W*.24, H*.12, W*.92, H*.92], fill=34)
        im = Image.composite(Image.new("RGB", (W, H), cfg["accent"]),
                             im, g.filter(ImageFilter.GaussianBlur(260)))
    return im


_MONO_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",                       # Consolas (Windows)
    "/System/Library/Fonts/Menlo.ttc",                    # Menlo (Mac)
    "C:/Windows/Fonts/cour.ttf",                          # Courier New fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def fmono(size):
    for p in _MONO_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


class _CodeText:
    """Shared ASCII/CJK measurement, truncation and drawing contract."""
    def __init__(self, draw_context, mono, cjk, max_width):
        self.draw_context, self.mono, self.cjk = draw_context, mono, cjk
        self.max_width = max_width

    def runs(self, s):
        """切成 (text, is_ascii) 連續段：ASCII 走 mono、其餘走 CJK 字型。"""
        out = []
        for ch in s:
            asc = ord(ch) < 128
            if out and out[-1][1] == asc:
                out[-1][0] += ch
            else:
                out.append([ch, asc])
        return out

    def width(self, s):
        return sum(self.draw_context.textlength(t, font=(self.mono if a else self.cjk)) for t, a in self.runs(s))

    def fit(self, s):
        if self.width(s) <= self.max_width:
            return s
        while s and self.width(s + "...") > self.max_width:
            s = s[:-1]
        return s + "..."

    def draw(self, x, y, s, fill):
        for t, a in self.runs(s):
            f = self.mono if a else self.cjk
            self.draw_context.text((x, y), t, font=f, fill=fill, anchor="la")
            x += self.draw_context.textlength(t, font=f)


def code_card(code, lang_label="PROMPT", highlights=None, theme="ai"):
    """深色圓角視窗 + 紅黃綠 titlebar + 行號 + 等寬字。
    highlights = 1-based 行號 list，該行金色底微光。長行自動截斷加 ...；最多 14 行。"""
    im = canvas(theme=theme)
    highlights = set(highlights or [])
    lines = code.rstrip("\n").split("\n")[:14]
    wx0, wy0, wx1, wy1 = 220, 130, W - 220, H - 130
    tb_h = 84
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 視窗投影
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([wx0 + 8, wy0 + 20, wx1 + 8, wy1 + 20],
                                         radius=30, fill=(0, 0, 0, 140))
    overlay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([wx0, wy0, wx1, wy1], radius=30,
                         fill=(16, 14, 28, 247), outline=(255, 255, 255, 30), width=2)
    # titlebar（上圓下平）
    od.rounded_rectangle([wx0, wy0, wx1, wy0 + tb_h], radius=30, fill=(29, 26, 48, 255))
    od.rectangle([wx0, wy0 + tb_h // 2, wx1, wy0 + tb_h], fill=(29, 26, 48, 255))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = wx0 + 48 + i * 46
        od.ellipse([cx - 13, wy0 + tb_h // 2 - 13, cx + 13, wy0 + tb_h // 2 + 13],
                   fill=c + (255,))
    od.line([(wx0, wy0 + tb_h), (wx1, wy0 + tb_h)], fill=(255, 255, 255, 22), width=2)
    od.text((wx1 - 42, wy0 + tb_h // 2), lang_label, font=fmono(30),
            fill=BRAND["gold"] + (235,), anchor="rm")
    # code 區排版
    n = len(lines)
    fs = 38 if n <= 8 else (32 if n <= 11 else 27)
    fc = fmono(fs)
    fk = fcjk(fs)          # CJK fallback（Consolas 沒中文字形 → tofu）
    lh = int(fs * 1.55)
    x_num, x_code = wx0 + 60, wx0 + 156
    max_w = wx1 - 56 - x_code
    y0 = wy0 + tb_h + max(28, ((wy1 - wy0 - tb_h) - n * lh) // 2)


    # highlights 金色底微光（先畫底、後畫字）
    if highlights:
        hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        for ln in highlights:
            if 1 <= ln <= n:
                y = y0 + (ln - 1) * lh
                hd.rounded_rectangle([x_num - 22, y - 4, wx1 - 36, y + lh - 8],
                                     radius=12, fill=BRAND["gold"] + (46,))
        overlay.alpha_composite(hl.filter(ImageFilter.GaussianBlur(10)))
        overlay.alpha_composite(hl)
    od = ImageDraw.Draw(overlay)
    text_layout = _CodeText(od, fc, fk, max_w)
    for i, ln_text in enumerate(lines):
        y = y0 + i * lh
        num_col = BRAND["gold"] + (220,) if (i + 1) in highlights else (110, 106, 150, 255)
        od.text((x_num, y), f"{i + 1:>2}", font=fc, fill=num_col, anchor="la")
        text_layout.draw(x_code, y, text_layout.fit(ln_text), BRAND["white"] + (255,))
    base = im.convert("RGBA")
    base.alpha_composite(overlay)
    return base.convert("RGB")
