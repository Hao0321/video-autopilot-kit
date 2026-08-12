# -*- coding: utf-8 -*-
"""longform_maker/proof_stage.py — M107 機械化：真實後台截圖的 dark-stage 擺台（2026-07-23 固化）.

鐵則（M107，長片03 Hao「你自己做的誰會信」後鎖死）：
  戰績/proof 數字上鏡 = 真實後台原始截圖（保留平台 UI chrome = 不可偽造感），禁自繪動畫重建真值。
  本模組把長片03 `hero_real.py` 重複 4 次的擺台結構（深紫底→截圖 crop/scale→陰影→圓角+細白框→
  金色高亮圈→頂部 kicker）固化成一個呼叫，下支片 import 不 copy-paste（M85 第三次法則）。

用法：
  from proof_stage import stage_screenshot, assert_proof_sources
  stage_screenshot("insight.png", "out/hero.png",
                   kicker="我的真實 FB 後台・未修改原圖",
                   crop=(0, 0, 752, 418),              # 原圖座標，None=不裁
                   ring_box=(24, 70, 244, 176),        # 【crop 後】原圖座標，內部自動換算
                   ring_label="90 天・270 萬次瀏覽")    # 金字標籤（畫在圈下方）
  assert_proof_sources(plan, proof_whitelist=[...])    # build 前 gate：戰績 beat 來源必是白名單真截圖

self-test：`python proof_stage.py`（合成假截圖 → 擺台 → 尺寸/高亮圈斷言；proof gate 正反例）。
M102：stdout reconfigure utf-8。
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
from project_paths import asset_path  # noqa: E402

W, H = 1920, 1080
_FONTS = str(asset_path("fonts"))
F_DISP = _FONTS + "/_active/Huninn-Regular.ttf"      # 粉圓：全 TC 覆蓋（M-rule：SmileySans 簡體缺字）
GOLD = (255, 210, 63)
GOLD_D = (40, 26, 5)
WHITE = (255, 255, 255)
DIM = (150, 150, 180)

# 自繪真值引擎的輸出（M107 黑名單：這些檔名 pattern 當 proof 來源 = 直接 raise）
SELF_DRAWN_PATTERNS = (r"hero_climax", r"clip1_hero", r"anim\d+_", r"cover_hero", r"thumb[AB]_")


def _font(path, size):
    return ImageFont.truetype(path, size)


def bg_gradient():
    """深紫漸層 + 中央紫光暈 + 細格線（與 data_anim/demo_term 同款品牌底）。"""
    top = np.array([11, 10, 31]); bot = np.array([26, 15, 53])
    col = np.linspace(0, 1, H)[:, None]
    grad = (top[None, :] * (1 - col) + bot[None, :] * col)
    im = Image.fromarray(np.repeat(grad[:, None, :], W, axis=1).astype(np.uint8))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.25, H * 0.1, W * 0.95, H * 0.95], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(Image.new("RGB", (W, H), (70, 40, 130)), im, glow)
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(0, W, 120):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=1)
    for y in range(0, H, 120):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 10), width=1)
    return im.convert("RGB")


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def _text_outlined(d, xy, s, fnt, fill, stroke=GOLD_D, sw=5, anchor="mm"):
    d.text(xy, s, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)


def arrow_ur(d, ax, ay, color=GOLD, s=26, w=9):
    """手繪右上箭頭 ↗（Huninn 無 U+2197）。"""
    d.line([(ax - s, ay + s), (ax + s * 0.85, ay - s * 0.85)], fill=color, width=w)
    d.line([(ax + s * 0.85, ay - s * 0.85), (ax - s * 0.1, ay - s * 0.85)], fill=color, width=w)
    d.line([(ax + s * 0.85, ay - s * 0.85), (ax + s * 0.85, ay + s * 0.1)], fill=color, width=w)


def stage_screenshot(shot_png, out_png, kicker=None, ring_box=None, ring_label=None,
                     crop=None, shot_w=1360, shot_y=None, caption_safe=150,
                     kicker_size=58, label_size=54):
    """真截圖 dark-stage 擺台（M107 標準呈現）。

    shot_png   : 真實後台截圖路徑（原始檔，不改內容）
    out_png    : 輸出 1920x1080 png
    kicker     : 頂部一句白字金框（如「我的真實 FB 後台・未修改原圖」）；None=不畫
    crop       : (x0,y0,x1,y1) 原圖座標先裁（去被切半的卡/PII 區）；None=整張
    ring_box   : (x0,y0,x1,y1)【crop 後座標】金色雙層高亮圈；None=不畫
    ring_label : 圈旁金字標籤+手繪↗（畫在圈右下）；None=不畫
    shot_w     : 截圖縮放後寬度（自動限高避開 caption_safe 字幕安全區）
    shot_y     : 截圖頂端 y；None=自動（kicker 下方置中偏上）
    回 dict {'pos':(px,py),'size':(tw,th),'scale':s} 供呼叫端加自訂註記。
    """
    im = bg_gradient()
    d0 = ImageDraw.Draw(im, "RGBA")
    if kicker:
        _text_outlined(d0, (W // 2, 92), kicker, _font(F_DISP, kicker_size), WHITE, GOLD_D, 5)

    shot = Image.open(shot_png).convert("RGB")
    if crop:
        shot = shot.crop(crop)
    cw, ch = shot.size
    scale = shot_w / cw
    top = 168 if kicker else 90
    max_h = H - caption_safe - top - 20          # 底部留字幕安全區
    if ch * scale > max_h:
        scale = max_h / ch
    tw, th = int(cw * scale), int(ch * scale)
    shot = shot.resize((tw, th), Image.LANCZOS)
    px = (W - tw) // 2
    py = shot_y if shot_y is not None else max(top, top + (max_h - th) // 3)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([px + 8, py + 18, px + tw + 8, py + th + 18],
                                             radius=28, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    im = Image.alpha_composite(im.convert("RGBA"), shadow).convert("RGB")

    im.paste(shot, (px, py), _rounded_mask((tw, th), 24))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([px, py, px + tw, py + th], radius=24, outline=(255, 255, 255, 60), width=2)

    if ring_box:
        rx0 = px + int(ring_box[0] * scale); ry0 = py + int(ring_box[1] * scale)
        rx1 = px + int(ring_box[2] * scale); ry1 = py + int(ring_box[3] * scale)
        for w_, a in [(9, 255), (16, 70)]:
            d.rounded_rectangle([rx0, ry0, rx1, ry1], radius=18, outline=GOLD + (a,), width=w_)
        if ring_label:
            arrow_ur(d, rx1 + 60, ry1 + 90, GOLD, s=28, w=9)
            _text_outlined(d, (rx1 + 110, ry1 + 148), ring_label,
                           _font(F_DISP, label_size), GOLD, GOLD_D, 6, "lm")

    im.convert("RGB").save(out_png)
    return {"pos": (px, py), "size": (tw, th), "scale": scale}


def assert_proof_sources(plan, proof_whitelist, proof_beats=None):
    """M107 proof gate（build 前跑）：plan={'b01':('stillfull', src)|...}。
    proof_beats=要驗的 beat 清單（None=全部 still/stillfull/twostill 來源）。
    每個來源：① 檔案存在 ② 在 proof_whitelist（真截圖檔/其產物）內 ③ 不得 match 自繪引擎輸出 pattern。
    違規 raise AssertionError（gate 不綠不 build）。"""
    wl = [os.path.normpath(str(p)).lower() for p in proof_whitelist]

    def _check(bk, src):
        s = os.path.normpath(str(src)).lower()
        base = os.path.basename(s)
        for pat in SELF_DRAWN_PATTERNS:
            if re.search(pat, base):
                raise AssertionError(f"M107: {bk} 用自繪真值引擎輸出當 proof（{base}）— 換真截圖")
        if not os.path.exists(src):
            raise AssertionError(f"M107: {bk} proof 來源不存在：{src}")
        if not any(s == w or s.endswith(os.path.basename(w)) or os.path.basename(w) in base for w in wl):
            raise AssertionError(f"M107: {bk} 來源 {base} 不在 proof 白名單（指不回 PROOF SoT = 不可上鏡）")

    for bk, (kind, src) in sorted(plan.items()):
        if proof_beats is not None and bk not in proof_beats:
            continue
        if proof_beats is None and kind not in ("still", "stillfull", "twostill"):
            continue
        if kind == "twostill":
            _check(bk, src[0]); _check(bk, src[1])
        else:
            _check(bk, src)
    return True


# ──────────────────────────────────────────── self-test
if __name__ == "__main__":
    import tempfile, shutil
    work = tempfile.mkdtemp(prefix="proofstage_")
    try:
        # 合成一張假「後台截圖」（白底表格感）
        fake = os.path.join(work, "insight_fake.png")
        s = Image.new("RGB", (820, 418), (247, 248, 250))
        sd = ImageDraw.Draw(s)
        sd.rectangle([30, 70, 240, 175], outline=(24, 119, 242), width=3)
        sd.text((40, 100), "2,706,888", fill=(20, 20, 20))
        s.save(fake)

        out = os.path.join(work, "staged.png")
        meta = stage_screenshot(fake, out, kicker="TEST 真實後台",
                                crop=(0, 0, 752, 418), ring_box=(24, 64, 244, 180),
                                ring_label="90 天")
        img = Image.open(out)
        assert img.size == (W, H), f"輸出尺寸錯 {img.size}"
        # 高亮圈有畫到（抽 ring 邊框像素接近金色）
        rx = meta["pos"][0] + int(24 * meta["scale"])
        ry = meta["pos"][1] + int((64 + 180) / 2 * meta["scale"])
        pr = img.getpixel((max(0, rx - 4), ry))
        assert pr[0] > 180 and pr[1] > 140, f"ring 沒畫到 {pr}"

        # proof gate：正例
        plan = {"b01": ("stillfull", fake), "b05": ("clip", "concept_anim.mp4")}
        assert assert_proof_sources(plan, [fake])
        # 反例①：自繪引擎輸出
        bad = os.path.join(work, "hero_climax.png"); Image.new("RGB", (8, 8)).save(bad)
        try:
            assert_proof_sources({"b01": ("stillfull", bad)}, [bad]); raise SystemExit("gate 沒攔自繪")
        except AssertionError:
            pass
        # 反例②：不在白名單
        other = os.path.join(work, "random.png"); Image.new("RGB", (8, 8)).save(other)
        try:
            assert_proof_sources({"b02": ("still", other)}, [fake]); raise SystemExit("gate 沒攔白名單外")
        except AssertionError:
            pass
        print("[proof_stage selftest] OK — 擺台尺寸/ring/雙反例 gate 全過")
    finally:
        shutil.rmtree(work, ignore_errors=True)
