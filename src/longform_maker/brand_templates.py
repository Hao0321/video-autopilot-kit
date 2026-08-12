# -*- coding: utf-8 -*-
"""
brand_templates — Hao 品牌模板引擎（skill 級，支支重用）
卡片家族：章節數字卡 / 問號卡(open-loop) / 懶人包 recap / 萬用 stat 卡 / SUBSCRIBE lower-third / 進度圓點
全部吃 BRAND config，用 fx_lib 質感層。self-test 會把每種卡渲染成 PNG contact sheet。
用法：from brand_templates import *; im = chapter_card(2, "拆解演算法"); im.save(...)
"""
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import fx_lib as fx

# brand_templates 可直接從 longform_maker/ 執行；把 video-autopilot 根加進 import path。
_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
import art_direction as art
import editorial_templates as editorial
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
def fnum(s): return _font(BRAND["font_num"], s)

def canvas(glow_center=True, theme="ai", variant="signal_grid", progress=0.0):
    """Hao Signal Grid 黑底白格背景。

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


def title_card(title, subtitle="", theme="ai", kicker=None, progress=0.0):
    """Legacy compatibility card; new builds should prefer editorial_card()."""
    return art.render_title_card(title, subtitle, theme, (W, H), kicker, progress, seed=title)


def editorial_card(role, title, subtitle="", theme="ai", style_hint=None,
                   value="87%", items=(), media_paths=(), seed=0):
    """Render the shared Bright Editorial system for new long-form builds.

    Legacy Signal Grid cards remain available for old projects. New automated
    builds should use this entry point so long and short videos share one
    domain-aware design system without duplicating template files.
    """
    return editorial.render_template(
        role=role,
        title=title,
        subtitle=subtitle,
        topic=theme,
        aspect="landscape",
        style_hint=style_hint,
        value=str(value),
        items=items,
        media_paths=media_paths,
        seed=seed or (role, title, theme),
    )


def compile_editorial_plan(role, title="", theme="ai", *, energy=.65,
                           subject="real_footage", seed=0, recent_signatures=()):
    """Return the component plan used before rendering a long-form graphic."""
    from template_compiler import compile_template_plan
    return compile_template_plan(
        theme, "longform", role, title=title, energy=energy, subject=subject,
        seed=seed, recent_signatures=recent_signatures,
    )


def bright_title_card(title, subtitle="", theme="ai", style_hint=None,
                      media_paths=()):
    return editorial_card("hook", title, subtitle, theme, style_hint,
                          media_paths=media_paths)


def bright_chapter_card(title, subtitle="", theme="ai", number="01",
                        style_hint=None):
    return editorial_card("chapter", title, subtitle, theme, style_hint,
                          value=number)


def bright_quote_card(quote, author="", theme="ai", style_hint=None):
    return editorial_card("quote", quote, author, theme, style_hint)


def bright_stat_card(label, value, note="", theme="ai", style_hint=None):
    return editorial_card("stat", label, note, theme, style_hint, value=value)


def bright_compare_card(title, left, right, theme="ai", style_hint=None):
    return editorial_card("compare", title, "", theme, style_hint,
                          items=(left, right))


def bright_steps_card(title, steps, theme="ai", style_hint=None):
    return editorial_card("steps", title, "", theme, style_hint, items=steps)


def bright_end_card(title, subtitle="", theme="ai", style_hint=None):
    return editorial_card("end_card", title, subtitle, theme, style_hint)


def bright_thumbnail(title, subtitle="", theme="ai", style_hint=None,
                     media_paths=()):
    return editorial_card("thumbnail", title, subtitle, theme, style_hint,
                          media_paths=media_paths)

def _bloom_text(im, xy, text, fnt, fill, anchor="mm", stroke=None, sw=0,
                tight=4, wide=16):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=fnt, fill=fill, anchor=anchor,
                               stroke_width=sw, stroke_fill=stroke or BRAND["gold_dark"])
    base = im.convert("RGBA"); base.alpha_composite(fx.double_bloom(layer, tight, wide))
    im.paste(base.convert("RGB"), (0, 0))

# ---------------- 1) 章節數字卡 ----------------
def chapter_card(n, title, total=None, theme="ai"):
    """超大金數字 01/02/03 + 章節名。total 給了就畫進度圓點。"""
    im = canvas(theme=theme)
    _bloom_text(im, (W//2, H//2 - 90), f"{n:02d}", fnum(340), BRAND["gold"] + (255,),
                sw=10)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W//2, H//2 + 170), title, font=fcjk(76), fill=BRAND["white"], anchor="mm")
    if total:
        progress_dots(d, n, total, y=H - 110)
    return im

# ---------------- 2) 問號卡（open-loop 節拍）----------------
def question_card(text="", theme="ai"):
    """深紫底 + 巨大金問號 +（可選）問題小字。搭配旁白丟問句後 0.6-0.8s 留白。"""
    im = canvas(theme=theme)
    _bloom_text(im, (W//2, H//2 - 60), "?", fnum(430), BRAND["gold"] + (255,), sw=12)
    if text:
        d = ImageDraw.Draw(im, "RGBA")
        d.text((W//2, H - 220), text, font=fcjk(60), fill=BRAND["dim"], anchor="mm")
    return im

# ---------------- 3) 懶人包 recap 卡（可截圖分享規格）----------------
def recap_card(bullets, title="本集重點", source=None, theme="ai"):
    """金標題 + ≤3 條白 bullet（每條 ≤14 全形字），單張截圖完整可讀（Line 群傳圖文化）。"""
    im = canvas(theme=theme)
    _bloom_text(im, (W//2, 150), title, fcjk(92), BRAND["gold"] + (255,), sw=7)
    d = ImageDraw.Draw(im, "RGBA")
    y = 380
    for i, b in enumerate(bullets[:3]):
        d.rounded_rectangle([260, y - 56, W - 260, y + 56], radius=34,
                            fill=(255, 255, 255, 18))
        d.ellipse([300, y - 14, 328, y + 14],
                  fill=[BRAND["gold"], BRAND["cyan"], BRAND["green"]][i % 3])
        d.text((370, y), b, font=fcjk(56), fill=BRAND["white"], anchor="lm")
        y += 170
    if source:
        d.text((36, H - 34), source, font=fcjk(22), fill=BRAND["dim"] + (200,), anchor="lm")
    return im

# ---------------- 4) 萬用 stat 卡 ----------------
def stat_card(label, value, growth=None, note=None, vcolor=None, theme="ai"):
    """單一數據主打卡：灰標籤 + 金色大數字（固定字槽防抖）+ 綠成長 + 小註。M10：value 必須真值。"""
    im = canvas(theme=theme)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W//2, 260), label, font=fcjk(64), fill=BRAND["dim"], anchor="mm")
    # 固定字槽數字（同 M106 counter 規格，靜態版）
    fnt = fnum(230)
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    slot = max(probe.textlength(c, font=fnt) for c in "0123456789")
    widths = [slot if c.isdigit() else slot * 0.55 for c in str(value)]
    total_w = sum(widths)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x = (W - total_w) / 2
    col = (vcolor or BRAND["gold"]) + (255,)
    for c, w in zip(str(value), widths):
        ld.text((x + w/2, 380), c, font=fnt, fill=col, anchor="ma",
                stroke_width=9, stroke_fill=BRAND["gold_dark"])
        x += w
    base = im.convert("RGBA"); base.alpha_composite(fx.double_bloom(layer, 5, 18))
    im.paste(base.convert("RGB"), (0, 0))
    if growth:
        d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle([W//2 - 190, 760, W//2 + 190, 850], radius=34,
                            fill=(16, 40, 26, 230), outline=BRAND["green"] + (255,), width=3)
        d.text((W//2, 805), growth, font=fnum(52), fill=BRAND["green"], anchor="mm")
    if note:
        ImageDraw.Draw(im, "RGBA").text((W//2, 930), note, font=fcjk(44),
                                        fill=BRAND["dim"], anchor="mm")
    return im

# ---------------- 5) SUBSCRIBE lower-third ----------------
def subscribe_lower_third():
    """透明底 RGBA：黃膠囊 SUBSCRIBE 徽章（左下），成片 overlay 用（策略點閃 3-4s）。"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bx, by, bw, bh = 80, H - 200, 460, 104
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2,
                        fill=BRAND["gold"] + (255,))
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2,
                        outline=BRAND["gold_dark"] + (255,), width=4)
    d.text((bx + bw//2, by + bh//2), "SUBSCRIBE", font=fnum(50),
           fill=(20, 14, 2), anchor="mm")
    return im

# ---------------- 6) 進度圓點 ----------------
def progress_dots(d, current, total, y=H - 110, cx=None, gap=64, r=13):
    """常駐章節進度（目前章=金、其餘=暗）。d = ImageDraw。"""
    cx = cx if cx is not None else W // 2 - (total - 1) * gap // 2
    for i in range(total):
        c = BRAND["gold"] if (i + 1) == current else (90, 85, 130)
        d.ellipse([cx + i*gap - r, y - r, cx + i*gap + r, y + r], fill=c)

# ---------------- 等寬字（code_card / device_frame 用） ----------------
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

# ---------------- 7) code_card（AI 教學 prompt/code 展示） ----------------
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

    def _runs(s):
        """切成 (text, is_ascii) 連續段：ASCII 走 mono、其餘走 CJK 字型。"""
        out = []
        for ch in s:
            asc = ord(ch) < 128
            if out and out[-1][1] == asc:
                out[-1][0] += ch
            else:
                out.append([ch, asc])
        return out

    def _wlen(s):
        return sum(od.textlength(t, font=(fc if a else fk)) for t, a in _runs(s))

    def _fit(s):
        if _wlen(s) <= max_w:
            return s
        while s and _wlen(s + "...") > max_w:
            s = s[:-1]
        return s + "..."

    def _draw_mixed(x, y, s, fill):
        for t, a in _runs(s):
            f = fc if a else fk
            od.text((x, y), t, font=f, fill=fill, anchor="la")
            x += od.textlength(t, font=f)

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
    for i, ln_text in enumerate(lines):
        y = y0 + i * lh
        num_col = BRAND["gold"] + (220,) if (i + 1) in highlights else (110, 106, 150, 255)
        od.text((x_num, y), f"{i + 1:>2}", font=fc, fill=num_col, anchor="la")
        _draw_mixed(x_code, y, _fit(ln_text), BRAND["white"] + (255,))
    base = im.convert("RGBA")
    base.alpha_composite(overlay)
    return base.convert("RGB")

# ---------------- 8) vs_card（左 ✗ 右 ✓ 對比） ----------------
def _cap(d, x, y, r, color):
    d.ellipse([x - r, y - r, x + r, y + r], fill=color)

def _hand_cross(d, cx, cy, r=19, color=(255, 118, 108), w=8):
    """手繪叉：兩筆微不對稱 + 圓端點（不用字元）。"""
    c = color + (255,)
    a1, a2 = (cx - r, cy - r + 3), (cx + r - 2, cy + r)
    b1, b2 = (cx + r, cy - r), (cx - r + 3, cy + r - 2)
    d.line([a1, (cx + 1, cy), a2], fill=c, width=w, joint="curve")
    d.line([b1, (cx - 1, cy + 1), b2], fill=c, width=w, joint="curve")
    for p in (a1, a2, b1, b2):
        _cap(d, p[0], p[1], w // 2, c)

def _hand_check(d, cx, cy, r=20, color=None, w=8):
    """手繪勾：兩段折線 + 圓端點，右上筆稍長（手寫感）。"""
    c = (color or BRAND["green"]) + (255,)
    p1 = (cx - r, cy + 2)
    p2 = (cx - int(r * 0.28), cy + int(r * 0.78))
    p3 = (cx + r + 3, cy - int(r * 0.85))
    d.line([p1, p2, p3], fill=c, width=w, joint="curve")
    for p in (p1, p2, p3):
        _cap(d, p[0], p[1], w // 2, c)

def vs_card(left_title, right_title, left_items, right_items, verdict=None, theme="ai"):
    """左右對比：左暗紅調(✗) / 右亮綠調(✓) / 中央金色 VS 圓。verdict 給了畫底部金框結論。"""
    im = canvas(theme=theme)
    d = ImageDraw.Draw(im, "RGBA")
    mid = W // 2
    top = 140
    bot = H - 240 if verdict else H - 150
    red_txt = (255, 140, 132)
    # 面板
    d.rounded_rectangle([120, top, mid - 70, bot], radius=36,
                        fill=(88, 28, 40, 120), outline=(255, 110, 100, 80), width=3)
    d.rounded_rectangle([mid + 70, top, W - 120, bot], radius=36,
                        fill=(16, 66, 44, 120), outline=BRAND["green"] + (100,), width=3)
    d.text(((120 + mid - 70) // 2, top + 84), left_title,
           font=fcjk(56), fill=red_txt, anchor="mm")
    d.text(((mid + 70 + W - 120) // 2, top + 84), right_title,
           font=fcjk(56), fill=BRAND["green"], anchor="mm")
    d.line([(180, top + 160), (mid - 130, top + 160)], fill=(255, 110, 100, 60), width=2)
    d.line([(mid + 130, top + 160), (W - 180, top + 160)],
           fill=BRAND["green"] + (60,), width=2)
    # 條目（各 ≤4）
    y0, gap = top + 250, 128
    for i, it in enumerate(left_items[:4]):
        y = y0 + i * gap
        _hand_cross(d, 240, y, color=(255, 118, 108))
        d.text((310, y), it, font=fcjk(44), fill=BRAND["white"], anchor="lm")
    for i, it in enumerate(right_items[:4]):
        y = y0 + i * gap
        _hand_check(d, mid + 190, y)
        d.text((mid + 260, y), it, font=fcjk(44), fill=BRAND["white"], anchor="lm")
    # 中央金色 VS 圓（bloom）
    vs_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vs_layer)
    cy, r = (top + bot) // 2, 88
    vd.ellipse([mid - r, cy - r, mid + r, cy + r], fill=BRAND["gold"] + (255,),
               outline=BRAND["gold_dark"] + (255,), width=6)
    vd.text((mid, cy), "VS", font=fnum(76), fill=(30, 20, 4), anchor="mm")
    base = im.convert("RGBA")
    base.alpha_composite(fx.double_bloom(vs_layer, 6, 22))
    im.paste(base.convert("RGB"), (0, 0))
    if verdict:
        d = ImageDraw.Draw(im, "RGBA")
        tw = d.textlength(verdict, font=fcjk(48))
        px = int(max(300, tw / 2 + 70))
        d.rounded_rectangle([W // 2 - px, H - 190, W // 2 + px, H - 90], radius=50,
                            fill=(40, 32, 10, 220), outline=BRAND["gold"] + (255,), width=3)
        d.text((W // 2, H - 140), verdict, font=fcjk(48), fill=BRAND["gold"], anchor="mm")
    return im

# ---------------- 9) steps_card（直向 1→2→3 步驟流） ----------------
def steps_card(steps, title="", theme="ai"):
    """金色編號圓 + 連接線 + 白字步驟（≤4 步）。"""
    im = canvas(theme=theme)
    steps = list(steps)[:4]
    y_top = 190
    if title:
        _bloom_text(im, (W // 2, 130), title, fcjk(76), BRAND["gold"] + (255,), sw=5)
        y_top = 290
    n = max(1, len(steps))
    y_bot = H - 150
    gap = (y_bot - y_top) / n
    centers = [int(y_top + gap * (i + 0.5)) for i in range(n)]
    cx, r = 560, 48
    d = ImageDraw.Draw(im, "RGBA")
    if n > 1:
        d.line([(cx, centers[0]), (cx, centers[-1])],
               fill=BRAND["gold"] + (90,), width=5)
    # 編號圓走 bloom 層（premium 質感）
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i, cy in enumerate(centers):
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BRAND["gold"] + (255,),
                   outline=BRAND["gold_dark"] + (255,), width=4)
        ld.text((cx, cy), str(i + 1), font=fnum(54), fill=(30, 20, 4), anchor="mm")
    base = im.convert("RGBA")
    base.alpha_composite(fx.double_bloom(layer, 5, 18))
    im.paste(base.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for cy, s in zip(centers, steps):
        d.text((cx + 100, cy), s, font=fcjk(56), fill=BRAND["white"], anchor="lm")
    return im

# ---------------- 10) device_frame（截圖裝進手繪裝置框） ----------------
def device_frame(shot, kind="browser", url="localhost"):
    """截圖（路徑或 PIL Image）→ 質感裝置框（RGBA 含投影，直接 overlay 到 canvas 上）。
    kind="browser"：titlebar + 三圓點 + 假網址列（url 參數顯示文字）。
    kind="phone"：直式手機框（聽筒/鏡頭 + home bar）。"""
    if isinstance(shot, str):
        shot = Image.open(shot)
    shot = shot.convert("RGB")
    if kind == "phone":
        cw = 560
        ch = max(1, round(cw * shot.height / shot.width))
        content = shot.resize((cw, ch), Image.LANCZOS)
        bez, top, bot, rad = 20, 78, 78, 72
        fw, fh = cw + bez * 2, ch + top + bot
        frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([0, 0, fw - 1, fh - 1], radius=rad,
                             fill=(24, 22, 40, 255), outline=(255, 255, 255, 42), width=3)
        fd.rounded_rectangle([fw // 2 - 70, top // 2 - 7, fw // 2 + 70, top // 2 + 7],
                             radius=7, fill=(72, 68, 104, 255))
        fd.ellipse([fw // 2 + 94, top // 2 - 9, fw // 2 + 112, top // 2 + 9],
                   fill=(72, 68, 104, 255))
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, fill=255)
        frame.paste(content, (bez, top), m)
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([fw // 2 - 92, fh - bot // 2 - 6, fw // 2 + 92, fh - bot // 2 + 6],
                             radius=6, fill=(92, 88, 124, 255))
    else:  # browser
        cw = 1560
        ch = max(1, round(cw * shot.height / shot.width))
        content = shot.resize((cw, ch), Image.LANCZOS)
        tb, bez, rad = 96, 12, 26
        fw, fh = cw + bez * 2, ch + tb + bez
        frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([0, 0, fw - 1, fh - 1], radius=rad,
                             fill=(27, 24, 46, 255), outline=(255, 255, 255, 38), width=2)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = 46 + i * 44
            fd.ellipse([cx - 12, tb // 2 - 12, cx + 12, tb // 2 + 12], fill=c + (255,))
        # 假網址列
        ux0, ux1 = 190, fw - 46
        fd.rounded_rectangle([ux0, tb // 2 - 27, ux1, tb // 2 + 27], radius=27,
                             fill=(13, 11, 25, 255), outline=(255, 255, 255, 24), width=2)
        fd.ellipse([ux0 + 24, tb // 2 - 7, ux0 + 38, tb // 2 + 7],
                   fill=BRAND["green"] + (255,))  # 小綠點 = 假鎖
        fd.text((ux0 + 58, tb // 2), url, font=fmono(30),
                fill=(190, 188, 215, 255), anchor="lm")
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=16, fill=255)
        frame.paste(content, (bez, tb), m)
    # 投影 + 邊距
    mg = 90
    out = Image.new("RGBA", (fw + mg * 2, fh + mg * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([mg + 6, mg + 28, mg + fw + 6, mg + fh + 28],
                                         radius=rad, fill=(0, 0, 0, 150))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(36)))
    out.alpha_composite(frame, (mg, mg))
    return out

# ---------------- self-test ----------------
if __name__ == "__main__":
    import os, tempfile
    out = os.path.join(tempfile.mkdtemp(prefix="brandtpl_"), "sheet.png")
    cards = [
        chapter_card(2, "拆解演算法", total=4),
        question_card("為什麼讚多反而不推？"),
        recap_card(["爆款看非追蹤者觸及", "滿意度大於互動量", "內文絕不放連結"],
                   source="資料來源：平台洞察報告"),
        stat_card("累積瀏覽次數", "1,234,567", growth="↑999%", note="90 天累積"),
    ]
    tw, th = 760, 428
    sheet = Image.new("RGB", (tw*2 + 60, th*2 + 60), (18, 16, 34))
    for i, c in enumerate(cards):
        r, cc = divmod(i, 2)
        sheet.paste(c.resize((tw, th)), (20 + cc*(tw+20), 20 + r*(th+20)))
    lt = subscribe_lower_third()
    assert lt.mode == "RGBA" and lt.getpixel((90, H - 150))[3] > 0
    sheet.save(out)
    # 固定字槽驗證：兩個不同數字排版總寬一致
    a = stat_card("x", "1111111"); b = stat_card("x", "8888888")
    print("brand_templates self-test OK ->", out)

    # ---------- 新卡 self-test（code / vs / steps / device_frame） ----------
    demo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")
    os.makedirs(demo_dir, exist_ok=True)

    cc = code_card(
        "role: 資深剪輯師\n"
        "task: 幫我把 10 分鐘素材剪成 60 秒\n"
        "rules:\n"
        "  - 靜止不抖，禁 zoompan\n"
        "  - 字幕 white-first\n"
        "  - 長行自動截斷測試" + "很長" * 40 + "\n"
        "output: CapCut 草稿",
        lang_label="PROMPT", highlights=[4, 5])
    assert cc.size == (W, H) and cc.mode == "RGB"
    # >14 行輸入不炸（自動截到 14）
    assert code_card("\n".join(f"line {i}" for i in range(20))).size == (W, H)

    vs = vs_card("ffmpeg zoompan", "fx_lib Ken Burns",
                 ["整數 snap 畫面抖", "參數難調又難讀", "出錯只能重跑"],
                 ["float 亞像素零抖動", "easing 一行換", "支支重用"],
                 verdict="靜止不抖 = 永遠用右邊")
    assert vs.size == (W, H) and vs.mode == "RGB"

    st = steps_card(["把 prompt 貼進 Claude", "跑 self-test 看綠燈", "打開 _demo 收成品"],
                    title="三步上手")
    assert st.size == (W, H) and st.mode == "RGB"

    # 合成假截圖（不用真媒體）：漸層 + 假 UI 方塊
    def _fake_shot(w, h):
        import numpy as np
        col = np.linspace(40, 90, h)[:, None, None]
        arr = np.repeat(np.repeat(col, w, axis=1), 3, axis=2)
        arr[..., 2] += 60
        s = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
        sd = ImageDraw.Draw(s)
        sd.rectangle([0, 0, w, int(h * 0.12)], fill=(28, 26, 50))
        for i in range(3):
            sd.rounded_rectangle([40 + i * (w // 3), int(h * 0.2),
                                  40 + i * (w // 3) + w // 4, int(h * 0.6)],
                                 radius=18, fill=(60, 55, 100))
        return s

    df_b = device_frame(_fake_shot(1280, 800), kind="browser", url="localhost:3000")
    assert df_b.mode == "RGBA" and df_b.width > 1560 and df_b.height > 800
    assert df_b.getpixel((2, 2))[3] == 0          # 角落透明（含投影邊距）
    df_p = device_frame(_fake_shot(590, 1280), kind="phone")
    assert df_p.mode == "RGBA" and df_p.height > df_p.width
    # 路徑輸入也吃
    _shot_path = os.path.join(demo_dir, "_selftest_shot.png")
    _fake_shot(1280, 800).save(_shot_path)
    assert device_frame(_shot_path, kind="browser").mode == "RGBA"
    os.remove(_shot_path)

    # contact sheet：新卡 5 格存 _demo/new_cards.png
    def _tile(card, tw2, th2):
        t = Image.new("RGB", (tw2, th2), (18, 16, 34))
        c2 = card.copy()
        if c2.mode == "RGBA":
            bg = Image.new("RGB", c2.size, (18, 16, 34))
            bg.paste(c2, (0, 0), c2)
            c2 = bg
        c2.thumbnail((tw2, th2), Image.LANCZOS)
        t.paste(c2, ((tw2 - c2.width) // 2, (th2 - c2.height) // 2))
        return t

    tw2, th2 = 760, 428
    new_cards = [cc, vs, st, df_b, df_p]
    sheet2 = Image.new("RGB", (tw2 * 3 + 80, th2 * 2 + 60), (18, 16, 34))
    for i, c in enumerate(new_cards):
        r2, c2i = divmod(i, 3)
        sheet2.paste(_tile(c, tw2, th2), (20 + c2i * (tw2 + 20), 20 + r2 * (th2 + 20)))
    out2 = os.path.join(demo_dir, "new_cards.png")
    sheet2.save(out2)
    bright = [
        bright_title_card("AI 工作流真的更快嗎？", "三個實測結果", "ai"),
        bright_chapter_card("先看核心差異", "不是工具越多越好", "ai", "02"),
        bright_stat_card("完成時間", "-43%", "同一份素材實測", "ai"),
        bright_steps_card("三步開始", ["整理素材", "選擇節奏", "輸出檢查"], "ai"),
        bright_end_card("下一支影片見", "把流程留給系統", "ai"),
    ]
    assert all(card.size == (W, H) and card.mode == "RGB" for card in bright)
    print("new cards self-test OK ->", out2)
