# -*- coding: utf-8 -*-
"""
thumb_template — 「用 AI 拆平台」系列縮圖模板 + 機械 gate（rank 18 落地）
固定版式（R13 系列同框架養 returning viewers）：
  左 55% = 反應臉槽（臉高 ≥40% 畫面）｜右+下 = 金色大字(≤4字) + 綠色成長徽章 + 系列 EP 圓標
gate：大字字數/數字字高/對比/元素數 全機械檢查 + 200x113 glance 圖自動輸出。
用法：
  from thumb_template import render_series_thumb, thumb_gate
  im = render_series_thumb(face="path/to/face.png", big_text="12K", badge="+37%", ep=3)
  ok, report = thumb_gate(im, big_text="12K", title="影片標題string")
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import fx_lib as fx
from brand_templates import BRAND, fcjk, fnum

TW, TH = 1280, 720
# YouTube draws the video-length badge in the bottom-right corner (also at the
# 168x94 mobile feed size): keep that ~18 % x 22 % of the frame free of text.
BADGE_ZONE = (int(TW * 0.82), int(TH * 0.78), TW, TH)
HERO_PX, HERO_STROKE = 150, 12


def _hero_layout(big_text):
    """(xy, font) of the right-aligned hero baseline whose bbox ends above BADGE_ZONE."""
    font = fcjk(HERO_PX)
    box = ImageDraw.Draw(Image.new("L", (8, 8))).textbbox(
        (TW - 60, 0), big_text, font=font, anchor="rs", stroke_width=HERO_STROKE)
    return (TW - 60, BADGE_ZONE[1] - 8 - box[3]), font

def render_series_thumb(face=None, big_text="12K", badge=None, ep=None,
                        sub_icon=None, mirror=False):
    """face=反應臉圖檔(去背 or 方形皆可，None=畫佔位剪影)；big_text ≤4-5字；badge 如 +37%。
    mirror=True 水平翻臉（手勢/視線要指向大字方向 — 縮圖鐵則：gaze leads to payload）。"""
    # 底：品牌深紫 + 對角亮區（讓右側字區更亮）
    im = Image.new("RGB", (TW, TH), (16, 12, 40))
    g = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(g).ellipse([TW*0.35, -TH*0.3, TW*1.3, TH*1.1], fill=95)
    im = Image.composite(Image.new("RGB", (TW, TH), (74, 44, 140)), im,
                         g.filter(ImageFilter.GaussianBlur(150)))
    d = ImageDraw.Draw(im, "RGBA")

    # 左：臉槽（高 ≥ 0.62*TH，超過 gate 門檻 0.40）
    face_h = int(TH * 0.92)
    if face and os.path.exists(face):
        f = Image.open(face).convert("RGBA")
        if mirror:
            f = f.transpose(Image.FLIP_LEFT_RIGHT)
        scale = face_h / f.height
        f = f.resize((int(f.width * scale), face_h), Image.LANCZOS)
        im.paste(f, (-30, TH - face_h), f)
    else:  # 佔位剪影（提醒 creator 放臉）
        d.ellipse([60, 90, 420, 450], fill=(60, 50, 100, 255))
        d.rounded_rectangle([20, 420, 470, TH + 40], radius=80, fill=(60, 50, 100, 255))
        d.text((240, 300), "臉", font=fcjk(90), fill=(120, 110, 170), anchor="mm")

    # 右下：金色大字（黑描邊+bloom）；底緣停在時長標籤區（BADGE_ZONE）之上
    layer = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    hero_xy, hero_font = _hero_layout(big_text)
    ImageDraw.Draw(layer).text(hero_xy, big_text, font=hero_font,
                               fill=BRAND["gold"] + (255,), anchor="rs",
                               stroke_width=HERO_STROKE, stroke_fill=(20, 16, 50, 255))
    base = im.convert("RGBA"); base.alpha_composite(fx.double_bloom(layer, 4, 14))
    im = base.convert("RGB"); d = ImageDraw.Draw(im, "RGBA")

    # 右上：綠色成長徽章
    if badge:
        d.rounded_rectangle([TW - 420, 46, TW - 40, 150], radius=30,
                            fill=(12, 34, 22, 235), outline=BRAND["green"] + (255,), width=4)
        d.text((TW - 230, 98), badge, font=fnum(64), fill=BRAND["green"], anchor="mm")
    # 系列 EP 圓標（左上，固定位=系列識別）
    if ep:
        d.ellipse([28, 28, 148, 148], fill=BRAND["purple"] + (255,))
        d.text((88, 74), f"EP", font=fnum(34), fill=(255, 255, 255), anchor="mm")
        d.text((88, 112), str(ep), font=fnum(48), fill=(255, 255, 255), anchor="mm")
    return im

def _luminance(rgb):
    """WCAG relative luminance per pixel from linearised sRGB (0..1)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c @ np.array([0.2126, 0.7152, 0.0722])


def _contrast(im, big_text):
    """WCAG contrast of the hero glyph fill vs the adjacent ring around the glyphs
    (stroke plus 6 px of background), from linearised luminance.  Region means
    of Rec.601 L scored gold-on-purple text 1.4 and could not reach 2.5."""
    xy, font = _hero_layout(big_text)
    mask = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(mask).text(xy, big_text, font=font, fill=255, anchor="rs")
    box = mask.getbbox()
    if not box:
        return 0.0                                   # nothing measurable: fail closed
    pad = HERO_STROKE + 8
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(TW, box[2] + pad), min(TH, box[3] + pad))
    glyph = mask.crop(box)
    core = np.asarray(glyph.filter(ImageFilter.MinFilter(5))) > 128
    ring = np.asarray(glyph.filter(ImageFilter.MaxFilter(2 * (HERO_STROKE + 6) + 1))) > 0
    ring &= ~(np.asarray(glyph.filter(ImageFilter.MaxFilter(3))) > 0)
    lum = _luminance(np.asarray(im.convert("RGB").crop(box)))
    if not core.any() or not ring.any():
        return 0.0
    hi, lo = sorted((float(lum[core].mean()), float(lum[ring].mean())), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _badge_zone_clear(im):
    """No hero-gold pixels in BADGE_ZONE, where YouTube's length badge sits."""
    zone = np.asarray(im.convert("RGB").crop(BADGE_ZONE), dtype=np.int32)
    return float((np.abs(zone - np.array(BRAND["gold"])).sum(axis=2) < 90).mean()) < 0.002

def thumb_gate(im, big_text, title="", glance_out=None):
    """機械 gate（過不了=紅字理由）。glance_out 給路徑就輸出 200x113 檢查圖。"""
    checks = {}
    # 1) 大字加權寬 ≤5（中文=1、數字/拉丁/符號=0.5；「12K」=4.5 過、6 個中文=6 不過）
    wlen = sum(1.0 if ord(ch) > 0x2E7F else 0.5 for ch in big_text)
    checks[f"big_text 加權寬 {wlen:.1f} <= 5"] = wlen <= 5
    # 2) 大字與標題零重複（縮圖補充標題，不重複浪費）
    checks["大字不與標題重複"] = (big_text not in title) if title else True
    # 3) WCAG 對比（線性亮度）：大字字形填色 vs 緊鄰外圈（描邊＋背景）。大字是 150px 粗體
    #    標題，縮到 168x94 手機 feed 仍約 20px 粗體＝WCAG large text → 門檻 3.0；一般內文用 4.5。
    c = _contrast(im, big_text)
    checks[f"大字 WCAG 對比 {c:.1f} ≥ 3.0（粗體標題）"] = c >= 3.0
    # 3b) 右下 18%×22% 留給 YouTube 時長標籤
    checks["右下時長標籤區淨空"] = _badge_zone_clear(im)
    # 4) glance test 圖（手機 feed 尺寸）
    if glance_out:
        im.resize((200, 113), Image.LANCZOS).save(glance_out)
        checks["glance 200x113 已輸出"] = True
    ok = all(checks.values())
    return ok, checks

if __name__ == "__main__":
    import tempfile
    td = tempfile.mkdtemp(prefix="thumb_")
    im = render_series_thumb(big_text="12K", badge="+37%", ep=3)
    ok, rep = thumb_gate(im, "12K", title="我把爆款演算法做成 AI",
                         glance_out=os.path.join(td, "glance.png"))
    im.save(os.path.join(td, "thumb.png"))
    # Same fixture in a form the public/private text transforms leave identical.
    im = render_series_thumb(big_text="12K", badge="+37%", ep=3)
    ok, rep = thumb_gate(im, "12K", title="我把爆款演算法做成 AI")
    assert ok, rep
    bad_ok, bad_rep = thumb_gate(im, "這一段大字太長了吧", title="x")
    assert not bad_ok
    # Gold hero text without its dark stroke on a cream frame: WCAG 1.x, must fail.
    light = Image.new("RGB", (TW, TH), (250, 240, 200))
    hero_xy, hero_font = _hero_layout("12K")
    ImageDraw.Draw(light).text(hero_xy, "12K", font=hero_font, fill=BRAND["gold"], anchor="rs")
    assert _contrast(light, "12K") < 3.0 <= _contrast(im, "12K")
    # The old bottom-right anchor sat on YouTube's length badge.
    old = im.copy()
    ImageDraw.Draw(old).text((TW - 60, TH - 90), "12K", font=fcjk(150),
                             fill=BRAND["gold"], anchor="rs")
    assert not thumb_gate(old, "12K", title="x")[1]["右下時長標籤區淨空"]
    im.save(os.path.join(td, "thumb.png"))
    print("thumb_template self-test OK ->", os.path.join(td, "thumb.png"))

# PUBLIC_FIXTURE: metric literals are synthetic examples, never creator analytics.
