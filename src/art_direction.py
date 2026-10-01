# -*- coding: utf-8 -*-
"""Hao Signal Grid — 跨片型美術導演核心。

這不是任何遊戲 UI 的複製品。它抽取「高對比黑白骨架、城市標示、斜切構圖、
編號／微標籤、少量題材色」等通用設計原理，建立 Hao 自己可長期累積的視覺語言。

Public API:
    resolve_theme(name) -> dict
    infer_theme(text, hint=None) -> str
    render_background(width, height, theme="ai", variant="signal_grid", progress=0) -> PIL.Image
    decorate_frame(image, theme="ai", label=None, index=None, intensity=1) -> PIL.Image
    render_title_card(title, subtitle="", theme="ai", size=(1920,1080), ...) -> PIL.Image
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
from typing import Dict, Iterable, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from domain_taxonomy import (
    DOMAIN_ALIASES as ALIASES,
    DOMAIN_KEYWORDS as KEYWORDS,
    infer_domain as infer_taxonomy_domain,
    normalize_domain,
)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONT_DIR = os.path.join(ROOT, "assets", "fonts", "_active")

RGB = Tuple[int, int, int]


THEMES: Dict[str, dict] = {
    "ai": {
        "label": "AI / TECH", "accent": (246, 220, 58), "secondary": (79, 220, 255),
        "ink": (7, 8, 10), "paper": (246, 246, 240), "title_font": "sans", "energy": 0.78,
    },
    "food": {
        "label": "FOOD / TASTE", "accent": (255, 91, 76), "secondary": (255, 211, 86),
        "ink": (11, 8, 7), "paper": (255, 246, 222), "title_font": "round", "energy": 0.82,
    },
    "travel": {
        "label": "TRAVEL / FIELD", "accent": (72, 204, 255), "secondary": (255, 135, 72),
        "ink": (6, 10, 13), "paper": (239, 248, 245), "title_font": "hand", "energy": 0.62,
    },
    "toy": {
        "label": "TOY / UNBOX", "accent": (255, 103, 166), "secondary": (255, 222, 68),
        "ink": (10, 7, 13), "paper": (253, 244, 255), "title_font": "round", "energy": 0.90,
    },
    "game": {
        "label": "GAME / PLAY", "accent": (175, 255, 67), "secondary": (169, 104, 255),
        "ink": (7, 9, 8), "paper": (241, 246, 236), "title_font": "sans", "energy": 0.95,
    },
    "diy": {
        "label": "DIY / BUILD", "accent": (255, 151, 62), "secondary": (75, 164, 255),
        "ink": (11, 9, 7), "paper": (249, 244, 232), "title_font": "sans", "energy": 0.72,
    },
    "cafe": {
        "label": "CAFE / SLOW", "accent": (232, 188, 126), "secondary": (171, 126, 190),
        "ink": (12, 9, 9), "paper": (253, 244, 230), "title_font": "hand", "energy": 0.42,
    },
    "documentary": {
        "label": "DOC / FIELD", "accent": (255, 82, 72), "secondary": (82, 205, 230),
        "ink": (8, 9, 10), "paper": (240, 240, 234), "title_font": "sans", "energy": 0.56,
    },
    "interview": {
        "label": "VOICE / PROOF", "accent": (39, 93, 255), "secondary": (185, 255, 69),
        "ink": (7, 10, 12), "paper": (244, 244, 238), "title_font": "sans", "energy": 0.50,
    },
    "automotive": {
        "label": "MOTION / DRIVE", "accent": (185, 255, 60), "secondary": (255, 112, 52),
        "ink": (6, 8, 8), "paper": (239, 244, 235), "title_font": "sans", "energy": 0.90,
    },
    "fitness": {
        "label": "TRAIN / POWER", "accent": (255, 113, 51), "secondary": (185, 255, 65),
        "ink": (9, 8, 7), "paper": (246, 242, 235), "title_font": "sans", "energy": 0.86,
    },
    "fashion": {
        "label": "STYLE / FORM", "accent": (255, 100, 176), "secondary": (196, 205, 218),
        "ink": (10, 7, 11), "paper": (249, 243, 247), "title_font": "hand", "energy": 0.66,
    },
    "architecture": {
        "label": "SPACE / STRUCTURE", "accent": (87, 205, 232), "secondary": (255, 174, 83),
        "ink": (7, 10, 11), "paper": (241, 244, 241), "title_font": "sans", "energy": 0.46,
    },
    "business": {
        "label": "BUSINESS / SIGNAL", "accent": (248, 218, 61), "secondary": (74, 196, 229),
        "ink": (7, 8, 10), "paper": (244, 244, 237), "title_font": "sans", "energy": 0.64,
    },
    "nature": {
        "label": "NATURE / WILD", "accent": (109, 212, 112), "secondary": (81, 190, 231),
        "ink": (7, 10, 8), "paper": (239, 246, 237), "title_font": "hand", "energy": 0.52,
    },
    "music": {
        "label": "MUSIC / PULSE", "accent": (244, 77, 181), "secondary": (106, 125, 255),
        "ink": (9, 6, 12), "paper": (246, 239, 248), "title_font": "sans", "energy": 0.86,
    },
    "product": {
        "label": "PRODUCT / PROOF", "accent": (247, 220, 59), "secondary": (69, 211, 232),
        "ink": (7, 8, 10), "paper": (244, 244, 238), "title_font": "sans", "energy": 0.74,
    },
    "general": {
        "label": "HAO / SIGNAL", "accent": (246, 220, 58), "secondary": (255, 255, 255),
        "ink": (8, 8, 10), "paper": (246, 246, 240), "title_font": "sans", "energy": 0.65,
    },
}

def resolve_theme(name: str | None) -> dict:
    key = normalize_domain(name, THEMES)
    return {"key": key, **THEMES[key]}


def infer_theme(text: str = "", hint: str | None = None) -> str:
    """由明確 hint 優先，否則對題目／BGM 資料夾／字幕做可解釋的 keyword score。"""
    return infer_taxonomy_domain(text, hint, THEMES)


def _font_candidates(kind: str) -> Iterable[str]:
    files = {
        "sans": ["C:/Windows/Fonts/msjhbd.ttc", os.path.join(FONT_DIR, "NotoSerifTC-Black.ttf")],
        "round": [os.path.join(FONT_DIR, "Huninn-Regular.ttf"), "C:/Windows/Fonts/msjhbd.ttc"],
        "hand": [os.path.join(FONT_DIR, "LXGWWenKaiTC-Bold.ttf"), "C:/Windows/Fonts/msjhbd.ttc"],
        "num": [os.path.join(ROOT, "assets", "fonts", "Anton", "Anton-Regular.ttf"),
                "C:/Windows/Fonts/arialbd.ttf"],
    }
    return files.get(kind, files["sans"])


def load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in _font_candidates(kind):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _seed_value(seed: object) -> int:
    return int(hashlib.sha1(str(seed).encode("utf-8")).hexdigest()[:8], 16)


def render_background(width: int, height: int, theme: str = "ai", variant: str = "signal_grid",
                      progress: float = 0.0, seed: object = 0) -> Image.Image:
    """產生可做字卡底／B-roll 的原創黑底白線條背景。

    progress=0..1；所有週期運動用 sin/cos，0 與 1 可無縫接回。
    variant: signal_grid / editorial / halftone / quiet。
    """
    cfg = resolve_theme(theme)
    ink, accent, secondary = cfg["ink"], cfg["accent"], cfg["secondary"]
    im = Image.new("RGB", (width, height), ink)
    d = ImageDraw.Draw(im, "RGBA")
    p = float(progress) % 1.0
    phase = 2 * math.pi * p
    unit = max(36, min(width, height) // 12)

    # 黑底白格：低對比骨架，不跟主字搶。
    off_x = int((math.sin(phase) * 0.5 + 0.5) * unit)
    off_y = int((math.cos(phase) * 0.5 + 0.5) * unit)
    grid_a = 30 if variant != "quiet" else 18
    for x in range(-unit + off_x, width + unit, unit):
        d.line([(x, 0), (x, height)], fill=(255, 255, 255, grid_a), width=1)
    for y in range(-unit + off_y, height + unit, unit):
        d.line([(0, y), (width, y)], fill=(255, 255, 255, grid_a), width=1)

    # 視覺主軸：斜切色帶 + 白線。只佔邊角，中央保留給字幕／產品。
    band = max(16, unit // 3)
    slide = int(math.sin(phase) * unit * 0.7)
    d.polygon([(0, height - unit * 2 + slide), (width * 0.48, height),
               (width * 0.48 + band * 2, height), (0, height - unit * 2 + band * 2 + slide)],
              fill=accent + ((85 if variant == "editorial" else 48),))
    d.line([(0, height - unit * 2 - band + slide), (width * 0.44, height - band)],
           fill=(255, 255, 255, 130), width=max(1, band // 8))

    # Halftone／城市印刷顆粒（規律排布，不用隨機逐幀，確保 loop）。
    if variant in ("signal_grid", "halftone", "editorial"):
        dot_step = max(18, unit // 2)
        r0 = max(1, dot_step // 9)
        for yy in range(unit // 2, int(height * 0.34), dot_step):
            for xx in range(int(width * 0.68), width, dot_step):
                wave = 0.5 + 0.5 * math.sin(phase + xx * 0.015 + yy * 0.01)
                r = r0 + int(wave * r0)
                d.ellipse([xx-r, yy-r, xx+r, yy+r], fill=secondary + (38,))

    # 邊界索引／十字準星，提供「系統感」而不是亂塞裝飾。
    margin = max(18, unit // 2)
    line = max(2, width // 960)
    c = (255, 255, 255, 115)
    for x, y, sx, sy in ((margin, margin, 1, 1), (width-margin, margin, -1, 1),
                         (margin, height-margin, 1, -1), (width-margin, height-margin, -1, -1)):
        d.line([(x, y), (x + sx*unit, y)], fill=c, width=line)
        d.line([(x, y), (x, y + sy*unit)], fill=c, width=line)

    # 輕微暗角，讓中央資訊聚焦。
    mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-width * .12, -height * .25, width * 1.12, height * 1.25], fill=120)
    glow = Image.new("RGB", (width, height), _mix(ink, accent, 0.15))
    im = Image.composite(glow, im, mask.filter(ImageFilter.GaussianBlur(max(32, unit))))
    return im


def decorate_frame(image: Image.Image, theme: str = "ai", label: str | None = None,
                   index: int | str | None = None, intensity: float = 1.0) -> Image.Image:
    """在真實畫面外加可辨識但克制的「Signal Grid」圖層，不蓋中央主體。"""
    cfg = resolve_theme(theme)
    im = image.convert("RGBA")
    w, h = im.size
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    s = max(1, round(min(w, h) / 540))
    m = max(24, min(w, h) // 18)
    alpha = max(20, min(255, int(220 * intensity)))
    # 上方訊號軌 + 左側 accent bar。
    d.line([(m, m), (w - m, m)], fill=(255, 255, 255, int(alpha * .62)), width=2*s)
    d.rectangle([m, m, m + max(8*s, w//120), m + h//9], fill=cfg["accent"] + (alpha,))
    # 右下切角編號。
    if index is not None:
        f = load_font("num", max(22, h // 28))
        text = f"{int(index):02d}" if str(index).isdigit() else str(index)
        d.text((w-m, h-m), text, font=f, fill=(255, 255, 255, alpha), anchor="rs")
    if label:
        f = load_font("num", max(16, h // 46))
        txt = re.sub(r"\s+", " ", str(label).upper())[:28]
        tw = d.textbbox((0, 0), txt, font=f)[2]
        x, y = m + max(18, w//100), m + max(16, h//100)
        font_h = getattr(f, "size", max(16, h // 46))
        d.rectangle([x-10*s, y-6*s, x+tw+10*s, y+font_h+4*s], fill=cfg["ink"] + (210,))
        d.text((x, y), txt, font=f, fill=cfg["paper"] + (alpha,), anchor="la")
    im.alpha_composite(layer)
    return im


def _wrap_text(d: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
               max_width: int, max_lines: int = 3) -> list[str]:
    chars = list(str(text).strip())
    lines, cur = [], ""
    for ch in chars:
        trial = cur + ch
        if cur and d.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(cur)
            cur = ch
            if len(lines) >= max_lines - 1:
                break
        else:
            cur = trial
    consumed = sum(len(x) for x in lines) + len(cur)
    if consumed < len(chars):
        cur = (cur[:-1] + "…") if cur else "…"
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def render_title_card(title: str, subtitle: str = "", theme: str = "ai",
                      size: Tuple[int, int] = (1920, 1080), kicker: str | None = None,
                      progress: float = 0.0, seed: object = 0,
                      background: Image.Image | None = None) -> Image.Image:
    """橫直式都可用的標題／章節／Hook 卡；中心資訊＋邊緣裝飾，有清楚層級。"""
    w, h = size
    cfg = resolve_theme(theme)
    if background is None:
        im = render_background(w, h, theme, "signal_grid", progress, seed).convert("RGBA")
    else:
        bg = background.convert("RGB")
        ratio = max(w / bg.width, h / bg.height)
        bg = bg.resize((math.ceil(bg.width * ratio), math.ceil(bg.height * ratio)), Image.LANCZOS)
        bg = bg.crop(((bg.width-w)//2, (bg.height-h)//2, (bg.width+w)//2, (bg.height+h)//2))
        im = Image.blend(bg, Image.new("RGB", size, cfg["ink"]), 0.48).convert("RGBA")
        im = decorate_frame(im, theme, cfg["label"], None, .75)

    d = ImageDraw.Draw(im, "RGBA")
    portrait = h > w
    mx = int(w * (0.075 if portrait else 0.10))
    panel_y0 = int(h * (0.30 if portrait else 0.24))
    panel_y1 = int(h * (0.72 if portrait else 0.76))
    # 黑紙卡 + 白線條 + 題材色底邊。
    d.rounded_rectangle([mx, panel_y0, w-mx, panel_y1], radius=max(12, w//90),
                        fill=cfg["ink"] + (235,), outline=(255,255,255,190), width=max(2,w//640))
    d.rectangle([mx, panel_y1-max(12,h//75), w-mx, panel_y1], fill=cfg["accent"] + (255,))
    d.polygon([(w-mx-int(w*.12), panel_y0), (w-mx, panel_y0),
               (w-mx, panel_y0+int(h*.08))], fill=cfg["secondary"] + (210,))

    kicker = kicker or cfg["label"]
    kf = load_font("num", max(20, int(h * .030)))
    d.text((mx + int(w*.03), panel_y0 + int(h*.055)), kicker.upper(), font=kf,
           fill=cfg["accent"] + (255,), anchor="lm")

    title_size = int(h * (0.095 if portrait else 0.115))
    tf = load_font(cfg["title_font"], max(42, title_size))
    lines = _wrap_text(d, title, tf, int(w * (0.72 if portrait else 0.68)), max_lines=3)
    line_h = int(title_size * 1.25)
    y = panel_y0 + int(h * .13)
    for line_text in lines:
        # 極小的 offset shadow，不做廉價大 glow。
        d.text((mx + int(w*.03)+4, y+5), line_text, font=tf, fill=(0,0,0,210), anchor="la")
        d.text((mx + int(w*.03), y), line_text, font=tf, fill=cfg["paper"] + (255,), anchor="la")
        y += line_h
    if subtitle:
        sf = load_font("sans", max(24, int(h * .042)))
        d.text((mx + int(w*.03), min(y + int(h*.025), panel_y1-int(h*.07))), subtitle,
               font=sf, fill=(220, 220, 218, 220), anchor="la")

    im = decorate_frame(im, theme, cfg["label"], _seed_value(seed) % 99, .92)
    return im.convert("RGB")


def build_contact_sheet(out_path: str) -> str:
    titles = {
        "ai": "AI 教學，不再像簡報", "food": "這口脆到會響", "travel": "城市裡的隱藏路線",
        "toy": "盒子打開的那一刻", "game": "最炸的一擊先上", "diy": "廢料變成成品",
        "cafe": "慢一點，味道才出來", "documentary": "先看見真實的人",
        "interview": "不看臉，直接看方法", "automotive": "速度之前，先聽見引擎",
        "fitness": "最後一組，才是故事", "fashion": "輪廓先說話",
        "architecture": "空間如何改變生活", "business": "數字背後的決策",
        "nature": "等待牠做出選擇", "music": "副歌落下的那一刻",
        "product": "規格之外，直接實測", "general": "Hao Signal Grid",
    }
    cards = [render_title_card(titles[k], THEMES[k]["label"], k, (960, 540), seed=k)
             for k in THEMES]
    tw, th = 480, 270
    cols = 3
    rows = math.ceil(len(cards) / cols)
    sheet = Image.new("RGB", (tw*cols, th*rows), (12,12,14))
    for i, card in enumerate(cards):
        sheet.paste(card.resize((tw, th), Image.LANCZOS), ((i%cols)*tw, (i//cols)*th))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path)
    return out_path


def _self_test() -> None:
    assert infer_theme("拉麵價格與夜市小吃") == "food"
    assert infer_theme("Claude AI 教學") == "ai"
    assert infer_theme("anything", "玩具") == "toy"
    a = render_background(320, 180, "game", progress=0)
    b = render_background(320, 180, "game", progress=1)
    # loop 首尾不能逐像素保證 JPEG/rounding，但平均差應接近零。
    assert a.tobytes() == b.tobytes(), "signal grid is not loopable"
    c = render_title_card("測試標題", "黑底白格＋題材色", "travel", (640, 360))
    assert c.size == (640, 360) and c.mode == "RGB"
    print("art_direction self-test OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()
    _self_test()
    if args.sheet:
        print("contact sheet ->", build_contact_sheet(args.sheet))
