# -*- coding: utf-8 -*-
"""Pure Pillow renderers and declarative specs for the Hao motion pack."""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Callable

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import art_direction as art


ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SOURCE_MASTER = os.path.join(
    ROOT, "assets", "broll", "generated", "_sources", "hao_urban_collage_master_v1.png"
)
INK = (6, 7, 10)
WHITE = (244, 244, 238)
PURPLE = (102, 52, 255)
CYAN = (39, 211, 238)
YELLOW = (239, 236, 0)
RED = (255, 45, 87)


@dataclass(frozen=True)
class AssetSpec:
    id: str
    role: str
    duration: float
    energy: float
    renderer: Callable[[float, tuple[int, int], str], Image.Image]
    loop: bool = True
    blend_mode: str = "normal"
    tags: tuple[str, ...] = ()
    usage: str = ""


def _phase(progress: float) -> float:
    return 2.0 * math.pi * (float(progress) % 1.0)


def _ease01(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    im = image.convert("RGB")
    scale = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((math.ceil(im.width * scale), math.ceil(im.height * scale)), Image.LANCZOS)
    left = (im.width - size[0]) // 2
    top = (im.height - size[1]) // 2
    return im.crop((left, top, left + size[0], top + size[1]))


def _collage_canvas(size: tuple[int, int]) -> Image.Image:
    """橫版填滿；直版把母版的上下邊緣重組，中央仍留字卡安全區。"""
    if not os.path.isfile(SOURCE_MASTER):
        im = _base(size)
        draw = ImageDraw.Draw(im, "RGBA")
        w, h = size
        blocks = ((0.00,0.00,0.34,0.22,PURPLE),(0.66,0.00,1.00,0.18,CYAN),(0.00,0.74,0.28,1.00,YELLOW),(0.72,0.72,1.00,1.00,RED))
        for x0, y0, x1, y1, color in blocks:
            draw.polygon([(int(w*x0),int(h*y0)),(int(w*x1),int(h*y0)),(int(w*(x1-.06)),int(h*y1)),(int(w*x0),int(h*y1))], fill=color+(185,))
        _corner_marks(draw, size, WHITE, 150)
        return im
    src = Image.open(SOURCE_MASTER).convert("RGB")
    w, h = size
    if w >= h:
        return _cover(src, size)
    base = Image.new("RGB", size, INK)
    band_h = int(h * 0.28)
    top = _cover(src.crop((0, 0, src.width, src.height // 2)), (w, band_h))
    bot = _cover(src.crop((0, src.height // 2, src.width, src.height)), (w, band_h))
    base.paste(top, (0, 0))
    base.paste(bot, (0, h - band_h))
    return base


def _base(size: tuple[int, int]) -> Image.Image:
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im, "RGBA")
    unit = max(36, min(size) // 12)
    for x in range(0, size[0] + unit, unit):
        d.line([(x, 0), (x, size[1])], fill=WHITE + (14,), width=1)
    for y in range(0, size[1] + unit, unit):
        d.line([(0, y), (size[0], y)], fill=WHITE + (14,), width=1)
    return im


def _screen_frame(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGB", size, (0, 0, 0))


def _corner_marks(d: ImageDraw.ImageDraw, size: tuple[int, int], color, alpha=170, length=None):
    w, h = size
    m = max(18, min(size) // 22)
    ln = length or max(36, min(size) // 9)
    width = max(2, min(size) // 360)
    for x, y, sx, sy in ((m, m, 1, 1), (w-m, m, -1, 1),
                         (m, h-m, 1, -1), (w-m, h-m, -1, -1)):
        d.line([(x, y), (x + sx*ln, y)], fill=color + (alpha,), width=width)
        d.line([(x, y), (x, y + sy*ln)], fill=color + (alpha,), width=width)


def _render_urban_collage(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    # 母版本身不做 pan/zoom；只動設計圖層，符合「生成靜圖不抖動」鐵則。
    cfg = art.resolve_theme(theme)
    im = _collage_canvas(size)
    im = ImageEnhance.Brightness(im).enhance(0.78 + 0.06 * math.sin(_phase(p)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    w, h = size
    ph = _phase(p)
    scan_x = int((0.5 + 0.5 * math.sin(ph)) * w)
    d.rectangle([scan_x-2, 0, scan_x+2, h], fill=cfg["secondary"] + (90,))
    d.rectangle([scan_x-18, 0, scan_x+18, h], fill=cfg["secondary"] + (13,))
    pulse = int(70 + 45 * (0.5 + 0.5 * math.cos(ph * 2)))
    d.polygon([(0, int(h*.69)), (int(w*.28), h), (0, h)], fill=cfg["accent"] + (pulse,))
    _corner_marks(d, size, WHITE, 150)
    # 中央的訊號刻度只在邊緣，保留字卡安全區。
    for i in range(12):
        yy = int(h * (0.18 + i * 0.055))
        ln = int(w * (0.018 + 0.012 * (0.5 + 0.5 * math.sin(ph + i))))
        d.rectangle([int(w*.93)-ln, yy, int(w*.93), yy+2], fill=WHITE + (80,))
    layer = layer.filter(ImageFilter.GaussianBlur(0.35))
    out = im.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def _render_perspective_grid(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = Image.new("RGB", size, cfg["ink"])
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    vx, horizon = w * 0.5, h * (0.43 if w >= h else 0.36)
    for i in range(-10, 11):
        x = vx + i * w * 0.11
        d.line([(vx, horizon), (x, h)], fill=WHITE + (55 if i % 2 else 90,), width=1)
    offset = (p * 1.0) % 1.0
    for i in range(18):
        u = ((i / 18.0 + offset) % 1.0)
        y = horizon + (u ** 2.15) * (h - horizon)
        alpha = int(20 + 130 * u)
        d.line([(0, y), (w, y)], fill=WHITE + (alpha,), width=max(1, int(1 + u*2)))
    # 低頻跑光只佔地平線與側翼。
    glow_x = int(vx + math.sin(ph) * w * .34)
    d.ellipse([glow_x-8, horizon-8, glow_x+8, horizon+8], fill=cfg["accent"] + (230,))
    d.line([(0, horizon), (w, horizon)], fill=cfg["secondary"] + (115,), width=2)
    _corner_marks(d, size, cfg["accent"], 120)
    return im


def _render_halftone_orbit(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = _base(size)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    cx, cy = (w * .80, h * .23) if w >= h else (w * .72, h * .18)
    radius = min(size) * .16
    for ring in range(4):
        r = radius * (0.55 + ring * .22)
        box = [cx-r, cy-r, cx+r, cy+r]
        d.arc(box, int(math.degrees(ph) + ring*47), int(math.degrees(ph) + 210 + ring*47),
              fill=(cfg["accent"] if ring % 2 == 0 else WHITE) + (150-ring*20,), width=max(1, min(size)//260))
    for i in range(44):
        a = ph * (1 if i % 2 else -1) + i * math.pi * 2 / 44
        rr = radius * (1.25 + .16 * math.sin(ph*2+i))
        x, y = cx + math.cos(a)*rr, cy + math.sin(a)*rr
        r = 1 + (i % 4)
        d.ellipse([x-r, y-r, x+r, y+r], fill=cfg["secondary"] + (80 + (i%3)*35,))
    # 左下 halftone wedge，中央保持乾淨。
    step = max(12, min(size)//38)
    for yy in range(int(h*.66), h, step):
        for xx in range(0, int(w*.32), step):
            fade = max(0.0, 1.0 - xx / max(1, w*.32))
            r = max(1, int(step*.18*fade))
            d.ellipse([xx-r, yy-r, xx+r, yy+r], fill=WHITE + (int(85*fade),))
    _corner_marks(d, size, WHITE, 120)
    return im


def _render_signal_blueprint(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = art.render_background(size[0], size[1], theme, "quiet", progress=p, seed="motion-blueprint")
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    # 抽象節點圖，適合教學、AI、商業、資訊段落。
    nodes = [(0.14, .22), (.30, .36), (.18, .68), (.74, .31), (.83, .66), (.64, .76)]
    pts = []
    for i, (nx, ny) in enumerate(nodes):
        x = nx*w + math.sin(ph+i)*min(size)*.012
        y = ny*h + math.cos(ph*1.0+i*.7)*min(size)*.010
        pts.append((x, y))
    for a, b in ((0,1),(1,3),(3,4),(4,5),(5,2),(2,0)):
        d.line([pts[a], pts[b]], fill=WHITE + (55,), width=1)
    for i, (x, y) in enumerate(pts):
        r = max(5, min(size)//90)
        col = cfg["accent"] if i % 2 == 0 else cfg["secondary"]
        d.ellipse([x-r, y-r, x+r, y+r], outline=col + (180,), width=max(1, r//4))
        d.ellipse([x-2, y-2, x+2, y+2], fill=WHITE + (220,))
    _corner_marks(d, size, cfg["accent"], 110)
    return im


def _render_focus_hud(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = _screen_frame(size)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    _corner_marks(d, size, WHITE, 210, max(54, min(size)//7))
    cx, cy = w*.5, h*.5
    r = min(size) * (.16 + .012*math.sin(ph))
    d.arc([cx-r, cy-r, cx+r, cy+r], int(math.degrees(ph)), int(math.degrees(ph)+92),
          fill=cfg["accent"] + (185,), width=max(2, min(size)//260))
    d.arc([cx-r, cy-r, cx+r, cy+r], int(math.degrees(ph)+180), int(math.degrees(ph)+248),
          fill=cfg["secondary"] + (135,), width=max(1, min(size)//340))
    tick = max(6, min(size)//70)
    d.line([(cx-tick, cy), (cx+tick, cy)], fill=WHITE + (160,), width=1)
    d.line([(cx, cy-tick), (cx, cy+tick)], fill=WHITE + (160,), width=1)
    for i in range(18):
        x = int(w*.08 + i*w*.045)
        y = int(h*.91)
        height = int(min(size)*(.006 + .012*(.5+.5*math.sin(ph+i*.8))))
        d.rectangle([x, y-height, x+2, y], fill=(cfg["accent"] if i%5==0 else WHITE) + (130,))
    return im


def _render_speed_streaks(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    p = float(p) % 1.0
    cfg = art.resolve_theme(theme)
    im = _screen_frame(size)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    for i in range(24):
        base = ((i / 24.0 + p * (1 + i % 3)) % 1.0)
        y = int(base*h)
        length = int(w*(.04 + .16*((i*37)%100)/100))
        x = int((-w*.12 + base*w*1.25 + math.sin(ph+i)*w*.03) % (w+length)) - length
        col = cfg["accent"] if i % 7 == 0 else (cfg["secondary"] if i % 11 == 0 else WHITE)
        alpha = 80 + (i % 4)*35
        d.line([(x, y), (x+length, y-int(length*.18))], fill=col + (alpha,), width=1+(i%3))
    return im


def _render_scan_sweep(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = _screen_frame(size)
    layer = Image.new("RGBA", size, (0,0,0,0))
    d = ImageDraw.Draw(layer, "RGBA")
    w, h = size
    y = int((p % 1.0)*h)
    band = max(12, min(size)//36)
    for k in range(band, 0, -2):
        alpha = int(35 * (1-k/band))
        d.line([(0, y-k), (w, y-k)], fill=cfg["secondary"] + (alpha,), width=2)
    d.line([(0, y), (w, y)], fill=WHITE + (210,), width=max(1,min(size)//360))
    d.rectangle([int(w*.08), y-band, int(w*.21), y-band+3], fill=cfg["accent"] + (190,))
    for x in range(0, w, max(8, min(size)//45)):
        alpha = 16 + int(12*(.5+.5*math.sin(_phase(p)+x*.05)))
        d.line([(x,0),(x,h)], fill=WHITE+(alpha,), width=1)
    layer = layer.filter(ImageFilter.GaussianBlur(.35))
    out = im.convert("RGBA"); out.alpha_composite(layer)
    return out.convert("RGB")


def _render_kinetic_marks(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = _screen_frame(size)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    ph = _phase(p)
    pulse = .5 + .5*math.sin(ph*2)
    # 只放邊緣的節奏標記，不蓋字幕／人物中央。
    for side in (0, 1):
        x0 = int(w*(.035 if side == 0 else .965))
        direction = 1 if side == 0 else -1
        for i in range(9):
            y = int(h*(.16+i*.078))
            ln = int(min(size)*(.018 + .025*((i%3)+pulse)/3))
            d.line([(x0,y),(x0+direction*ln,y)], fill=(cfg["accent"] if i%4==0 else WHITE)+(130,), width=2)
    # 小三角、十字、條碼，都是抽象圖形，無可讀文字。
    s = max(8, min(size)//42)
    tx, ty = int(w*.84), int(h*(.18+.025*math.sin(ph)))
    d.polygon([(tx,ty-s),(tx+s,ty+s),(tx-s,ty+s)], outline=cfg["secondary"]+(190,))
    bx, by = int(w*.12), int(h*.82)
    for i in range(11):
        ww = 1 + (i%3)
        d.rectangle([bx+i*s*.42, by, bx+i*s*.42+ww, by+s*(1+.5*(i%2))], fill=WHITE+(120,))
    return im


def _render_diagonal_slash(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    x = int((-w*.55) + _ease01(min(1.0, p*1.35))*w*2.1)
    band = int(w*.18)
    d.polygon([(x-band,0),(x,0),(x-band+h*.38,h),(x-2*band+h*.38,h)], fill=WHITE+(255,))
    d.polygon([(x,0),(x+band*.56,0),(x-band*.44+h*.38,h),(x-band+h*.38,h)], fill=cfg["accent"]+(255,))
    d.line([(x+band*.7,0),(x-band*.3+h*.38,h)], fill=cfg["secondary"]+(255,), width=max(4,min(size)//70))
    return im


def _render_grid_shutter(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    cols, rows = (8, 5) if w >= h else (5, 8)
    cw, rh = math.ceil(w/cols), math.ceil(h/rows)
    open_amt = abs(2*p-1)  # 中點全閉，頭尾露黑，適合卡在剪點。
    for yy in range(rows):
        for xx in range(cols):
            delay = ((xx+yy)%4)*.04
            q = max(0.0, min(1.0, (1-open_amt-delay)/.84))
            q = _ease01(q)
            hh = int(rh*q)
            x0, y0 = xx*cw, yy*rh + (rh-hh)//2
            col = cfg["accent"] if (xx+yy)%7==0 else (WHITE if (xx+yy)%3 else cfg["secondary"])
            d.rectangle([x0, y0, min(w,x0+cw+1), y0+hh], fill=col+(245,))
    return im


def _render_signal_glitch(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = size
    # 決定性 hash，避免每次 render 不同；glitch 只是一顆 stinger，不在 loop 背景濫用。
    for i in range(18):
        raw = hashlib.sha1(f"{i}:{int(p*90)}".encode()).digest()
        y = int(raw[0]/255*h)
        hh = max(2, int((raw[1]/255)*h*.08))
        x = int((raw[2]/255-.35)*w)
        ww = int(w*(.18+raw[3]/255*.9))
        col = (cfg["accent"], cfg["secondary"], WHITE, RED)[i%4]
        alpha = int(120 + 120*math.sin(math.pi*min(1,p*1.4)))
        d.rectangle([x,y,x+ww,y+hh], fill=col+(alpha,))
    for y in range(0,h,max(3,min(size)//180)):
        d.line([(0,y),(w,y)], fill=WHITE+(22,), width=1)
    return im


def _render_paper_flash(p: float, size: tuple[int, int], theme: str) -> Image.Image:
    cfg = art.resolve_theme(theme)
    w, h = size
    im = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(im, "RGBA")
    q = math.sin(math.pi*max(0,min(1,p)))
    r = int(math.hypot(w,h)*q)
    cx, cy = w*.5, h*.5
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=WHITE+(255,))
    inner = int(r*.72)
    d.ellipse([cx-inner,cy-inner,cx+inner,cy+inner], fill=cfg["accent"]+(235,))
    inner2 = int(r*.42)
    d.ellipse([cx-inner2,cy-inner2,cx+inner2,cy+inner2], fill=INK+(255,))
    # 印刷點放在 flash 邊緣。
    if r > 8:
        for i in range(36):
            a = i*math.pi*2/36 + p
            rr = r*.86
            x, y = cx+math.cos(a)*rr, cy+math.sin(a)*rr
            dot = max(1,int(min(size)*.004))
            d.ellipse([x-dot,y-dot,x+dot,y+dot], fill=INK+(170,))
    return im


SPECS = (
    AssetSpec("urban_collage_signal", "background", 6.0, .72, _render_urban_collage,
              tags=("title_bed","editorial","grid","urban"), usage="Hook／章節字卡／沒畫面的講解段"),
    AssetSpec("perspective_grid_rush", "background", 6.0, .86, _render_perspective_grid,
              tags=("speed","payoff","grid","tech"), usage="build-up／速度感／產品或 AI payoff 前"),
    AssetSpec("halftone_orbit", "background", 6.0, .58, _render_halftone_orbit,
              tags=("breath","editorial","data","clean_center"), usage="資訊卡／數據解釋／呼吸段"),
    AssetSpec("signal_blueprint", "background", 6.0, .42, _render_signal_blueprint,
              tags=("tutorial","diagram","business","clean"), usage="AI 教學／流程／商業圖解底"),
    AssetSpec("focus_hud", "overlay", 4.0, .62, _render_focus_hud, blend_mode="screen",
              tags=("focus","proof","product","hud"), usage="強調真實畫面中的產品、數字或操作區"),
    AssetSpec("speed_streaks", "overlay", 4.0, .88, _render_speed_streaks, blend_mode="screen",
              tags=("speed","action","payoff"), usage="動作、旅遊移動、遊戲、開箱揭曉"),
    AssetSpec("scan_sweep", "overlay", 4.0, .54, _render_scan_sweep, blend_mode="screen",
              tags=("scan","analysis","tech","proof"), usage="分析畫面／規格／AI 介面掃描"),
    AssetSpec("kinetic_marks", "overlay", 4.0, .46, _render_kinetic_marks, blend_mode="screen",
              tags=("rhythm","caption","edge_safe"), usage="字幕段增加設計，但不蓋中央主體"),
    AssetSpec("diagonal_slash", "transition", .82, .92, _render_diagonal_slash, loop=False,
              tags=("chapter","slash","impact"), usage="高能章節切換；全片少量使用"),
    AssetSpec("grid_shutter", "transition", .90, .76, _render_grid_shutter, loop=False,
              tags=("grid","modular","chapter"), usage="段落／列表項目切換"),
    AssetSpec("signal_glitch", "transition", .62, .98, _render_signal_glitch, loop=False,
              tags=("glitch","error","rare"), usage="錯誤、反轉、故障；全片最多一次"),
    AssetSpec("paper_flash", "transition", .78, .70, _render_paper_flash, loop=False,
              tags=("paper","editorial","reveal"), usage="字卡揭曉／美食、旅遊、開箱的輕快切換"),
)
