"""
shorts_template — 不露臉版「網感模板」骨架 (2026-06-01 訓練).

用戶要做美图「网感模板」那種 talking-head 爆色字幕短片，但他 M78 不露臉。
解法：保留「網感」的**結構 + 字幕能量**，把真人換成 b-roll / 螢幕錄影 / 產品畫面。
跨 niche 可重複套（教學 / 旅遊 / 美食 …）—— 結構固定，niche 只換配色 + 徽章 + 素材。

## 固定結構（每支都一樣）
  ┌ 0–3s   HOOK 標題卡：niche 徽章 + 一句爆色 hook（疑問/數字/反差）—— 蓋在 b-roll 上
  ├ 3–Xs   BODY 三段：b-roll/螢幕錄影 + shorts_captions 爆色字幕（跟旁白走）
  └ 末段   OUTRO：(your brand) outro card + your sign-off card + SUBSCRIBE + 你的社群 CTA

字幕走 `shorts_captions.style_caption`；hook 卡走本檔 `render_hook_card`；outro 走品牌系統。
**全程不露臉**（M78）。
"""
import os
from .constants import COLOR_VARIETY
from .shorts_captions import style_caption, render_caption_png, _font, _hex_rgb

# niche 換皮：徽章文字 + 配色 bias（從 COLOR_VARIETY 挑）
NETGAN_NICHE_PRESETS = {
    "teaching": {"badge": "你的徽章文字", "badge_color": "cyan",
                 "accents": ["cyan", "gold", "lime"], "default_level": 2},
    "travel":   {"badge": "旅遊筆記",     "badge_color": "orange",
                 "accents": ["orange", "gold", "cream"], "default_level": 2},
    "food":     {"badge": "美食筆記",     "badge_color": "gold",
                 "accents": ["gold", "orange", "magenta"], "default_level": 2},
    "finance":  {"badge": "理財小教室",   "badge_color": "lime",
                 "accents": ["lime", "gold", "cyan"], "default_level": 2},
}


def render_hook_card(title, niche="teaching", emphasis=None, out_path="hook.png",
                     bg_path=None, W=1080, H=1920, base_size_px=104):
    """Render the HOOK title card (no face): niche badge + bold爆色 hook, over b-roll/gradient.
    bg_path: your b-roll frame (else a niche-tinted gradient placeholder).
    Returns out_path."""
    from PIL import Image, ImageDraw
    cfg = NETGAN_NICHE_PRESETS.get(niche, NETGAN_NICHE_PRESETS["teaching"])

    # ── background ──
    if bg_path and os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGB").resize((W, H))
        # darken for text legibility
        ov = Image.new("RGB", (W, H), (0, 0, 0))
        bg = Image.blend(bg, ov, 0.35)
    else:
        bg = Image.new("RGB", (W, H), (20, 22, 30))
        d0 = ImageDraw.Draw(bg)
        tint = _hex_rgb(COLOR_VARIETY[cfg["badge_color"]])
        for yy in range(H):
            f = yy / H
            d0.line([(0, yy), (W, yy)],
                    fill=(int(16 + tint[0] * 0.06 + yy // 110),
                          int(18 + tint[1] * 0.06 + yy // 130),
                          int(28 + tint[2] * 0.06 + yy // 90)))
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)

    # ── niche badge (top-left pill) ──
    bf = _font(46)
    btxt = cfg["badge"]
    bw = d.textbbox((0, 0), btxt, font=bf)[2]
    pad = 26
    bx, by = 60, 120
    d.rounded_rectangle([bx, by, bx + bw + pad * 2, by + 78], radius=39,
                        fill=_hex_rgb(COLOR_VARIETY[cfg["badge_color"]]) + (235,))
    d.text((bx + pad, by + 14), btxt, font=bf, fill=(0, 0, 0, 255))

    # ── hook title (爆色, upper-mid) using shorts_captions tokens ──
    toks = style_caption(title, level=cfg["default_level"], emphasis=emphasis or [])
    cap, h = render_caption_png(toks, out_path + ".tmp.png", width=W, base_size_px=base_size_px)
    capimg = Image.open(out_path + ".tmp.png")
    img.alpha_composite(capimg, ((W - capimg.width) // 2, 560))
    try:
        os.remove(out_path + ".tmp.png")
    except OSError:
        pass

    img.convert("RGB").save(out_path)
    return out_path


# ════════════════════════════════════════════════════════════════════════════
# 2026 研究：前 3 秒 = 80% 完讀率變異。3 個跨 niche 最穩的 viral hook formula。
# (web 學習 2026-06-01：OpusClip / Terra Market hook studies)
# ════════════════════════════════════════════════════════════════════════════
HOOK_FORMULAS = {
    "contrarian": {
        "name": "反差宣稱 Contrarian Claim",
        "pattern": "大家都說 {common}，但其實 {truth}",
        "examples": {
            "teaching": "大家都說寫程式很難，但我 0 基礎用 AI 做出了完整作品",
            "travel":   "大家都搶著去 {熱門景點}，但這個祕境連在地人都不知道",
            "food":     "大家都排隊那家網美店，但巷弄這碗才是真本事",
        },
    },
    "mistake_warning": {
        "name": "踩雷警告 Mistake Warning",
        "pattern": "別再 {wrong} 了，{percent}% 的人都做錯",
        "examples": {
            "teaching": "別再自己硬刻了，90% 的新手都把 AI 用錯方向",
            "travel":   "別再跟團了，這樣玩才不會踩雷",
            "food":     "別再亂點了，這家必點的是這 3 道",
        },
    },
    "list_tease": {
        "name": "清單預告 List Tease",
        "pattern": "{n} 個 {topic} 的關鍵，第 {k} 個最重要",
        "examples": {
            "teaching": "用 AI 做出產品的 3 個關鍵，第 2 個 90% 的人不知道",
            "travel":   "這趟必做的 3 件事，最後一個才是重點",
            "food":     "這家必點 3 道，第 1 道就跪了",
        },
    },
}


def suggest_hook(niche="teaching", formula="contrarian"):
    """回傳該 niche × formula 的 hook 範例（給寫腳本起手）。前 3 秒 10-14 字內最佳。"""
    f = HOOK_FORMULAS.get(formula, HOOK_FORMULAS["contrarian"])
    return {"formula": f["name"], "pattern": f["pattern"],
            "example": f["examples"].get(niche, next(iter(f["examples"].values())))}


# template spec — 串給 content_pipeline / 給 AI 助手照著搭
NETGAN_SHORTS_TEMPLATE = {
    "name": "不露臉網感模板 (no-face viral template)",
    "face": False,  # M78 — 全程不露臉
    "structure": [
        {"seg": "hook", "t": "0-3s", "visual": "b-roll/螢幕錄影", "overlay": "render_hook_card() — 徽章+爆色 hook"},
        {"seg": "body", "t": "3s-末", "visual": "三段 b-roll/螢幕錄影/產品", "overlay": "shorts_captions 跟旁白走"},
        {"seg": "outro", "t": "末段", "visual": "(your brand) outro card", "overlay": "your sign-off + SUBSCRIBE + your community CTA"},
    ],
    "niches": list(NETGAN_NICHE_PRESETS.keys()),
    "caption_helper": "shorts_captions.style_caption",
    "hook_helper": "shorts_template.render_hook_card",
}
