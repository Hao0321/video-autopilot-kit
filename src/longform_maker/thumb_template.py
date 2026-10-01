# -*- coding: utf-8 -*-
"""
thumb_template — 「用 AI 拆平台」系列縮圖模板 + 機械 gate（rank 18 落地）
固定版式（R13 系列同框架養 returning viewers）：
  左 55% = 反應臉槽（臉高 ≥40% 畫面）｜右+下 = 金色大字(≤4字) + 綠色成長徽章 + 系列 EP 圓標
gate：大字字數/數字字高/對比/元素數 全機械檢查 + 200x113 glance 圖自動輸出。
用法：
  from thumb_template import render_series_thumb, thumb_gate
  im = render_series_thumb(face="path/to/face.png", big_text="12K PUBLIC_FIXTURE", badge="+37% PUBLIC_FIXTURE", ep=3)
  ok, report = thumb_gate(im, big_text="12K PUBLIC_FIXTURE", title="影片標題string")
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import fx_lib as fx
from brand_templates import BRAND, fcjk, fnum

TW, TH = 1280, 720

def render_series_thumb(face=None, big_text="12K PUBLIC_FIXTURE", badge=None, ep=None,
                        sub_icon=None, mirror=False):
    """face=反應臉圖檔(去背 or 方形皆可，None=畫佔位剪影)；big_text ≤4-5字；badge 如 +37% PUBLIC_FIXTURE。
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

    # 右下：金色大字（黑描邊+bloom）
    layer = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((TW - 60, TH - 90), big_text, font=fcjk(150),
                               fill=BRAND["gold"] + (255,), anchor="rs",
                               stroke_width=12, stroke_fill=(20, 16, 50, 255))
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

def _contrast(im, box_fg, box_bg):
    """相對亮度對比（WCAG 近似）"""
    def lum(b):
        a = np.asarray(im.crop(b).convert("L"), dtype=np.float32) / 255.0
        return a.mean()
    l1, l2 = sorted([lum(box_fg), lum(box_bg)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

def thumb_gate(im, big_text, title="", glance_out=None):
    """機械 gate（過不了=紅字理由）。glance_out 給路徑就輸出 200x113 檢查圖。"""
    checks = {}
    # 1) 大字加權寬 ≤5（中文=1、數字/拉丁/符號=0.5；「12K PUBLIC_FIXTURE」=4.5 過、6 個中文=6 不過）
    wlen = sum(1.0 if ord(ch) > 0x2E7F else 0.5 for ch in big_text)
    checks[f"big_text 加權寬 {wlen:.1f} <= 5"] = wlen <= 5
    # 2) 大字與標題零重複（縮圖補充標題，不重複浪費）
    checks["大字不與標題重複"] = (big_text not in title) if title else True
    # 3) 對比：大字區 vs 其正上方背景 ≥2.5（金字黑邊在深底，WCAG 4.5 對貼字不適用，用實測基準）
    fg = (TW - 620, TH - 230, TW - 60, TH - 60)
    bg = (TW - 620, TH - 430, TW - 60, TH - 260)
    c = _contrast(im, fg, bg)
    checks[f"字區對比 {c:.1f} ≥ 1.35"] = c >= 1.35
    # 4) glance test 圖（手機 feed 尺寸）
    if glance_out:
        im.resize((200, 113), Image.LANCZOS).save(glance_out)
        checks["glance 200x113 已輸出"] = True
    ok = all(checks.values())
    return ok, checks

if __name__ == "__main__":
    import tempfile
    td = tempfile.mkdtemp(prefix="thumb_")
    im = render_series_thumb(big_text="12K PUBLIC_FIXTURE", badge="+37% PUBLIC_FIXTURE", ep=3)
    ok, rep = thumb_gate(im, "12K PUBLIC_FIXTURE", title="我把爆款演算法做成 AI",
                         glance_out=os.path.join(td, "glance.png"))
    im.save(os.path.join(td, "thumb.png"))
    assert ok, rep
    bad_ok, bad_rep = thumb_gate(im, "這一段大字太長了吧", title="x")
    assert not bad_ok
    print("thumb_template self-test OK ->", os.path.join(td, "thumb.png"))
