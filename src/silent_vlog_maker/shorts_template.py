"""Reusable no-face vertical template (public distribution).

The template preserves structural energy while sourcing face policy, palette,
voice, outro and CTA from the active creator profile.  It ships no maintainer
brand phrase, community count or private sign-off.

PUBLIC_FIXTURE: profile-specific outro and community defaults are excluded.
"""
import os
import sys
from .constants import COLOR_VARIETY
from .shorts_captions import style_caption, render_caption_png, _font, _hex_rgb

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
import art_direction as art

# niche 換皮：徽章文字 + 配色 bias（從 COLOR_VARIETY 挑）
NETGAN_NICHE_PRESETS = {
    "teaching": {"badge": "AI 創作小教室", "badge_color": "cyan", "theme": "ai",
                 "accents": ["cyan", "gold", "lime"], "default_level": 1},
    "ai":       {"badge": "AI 創作小教室", "badge_color": "cyan", "theme": "ai",
                 "accents": ["cyan", "gold", "lime"], "default_level": 1},
    "travel":   {"badge": "旅遊筆記",     "badge_color": "orange",
                 "theme": "travel", "accents": ["orange", "gold", "cream"], "default_level": 1},
    "food":     {"badge": "美食筆記",     "badge_color": "gold",
                 "theme": "food", "accents": ["gold", "orange", "magenta"], "default_level": 1},
    "unboxing": {"badge": "玩具開箱",     "badge_color": "magenta",
                 "theme": "toy", "accents": ["magenta", "gold", "cyan"], "default_level": 1},
    "toy":      {"badge": "玩具開箱",     "badge_color": "magenta",
                 "theme": "toy", "accents": ["magenta", "gold", "cyan"], "default_level": 1},
    "game":     {"badge": "遊戲實驗室",   "badge_color": "lime",
                 "theme": "game", "accents": ["lime", "magenta", "gold"], "default_level": 1},
    "diy":      {"badge": "動手做",       "badge_color": "orange",
                 "theme": "diy", "accents": ["orange", "cyan", "gold"], "default_level": 1},
    "cafe":     {"badge": "咖啡散步",     "badge_color": "cream",
                 "theme": "cafe", "accents": ["cream", "orange", "magenta"], "default_level": 1},
}


def render_hook_card(title, niche="teaching", emphasis=None, out_path="hook.png",
                     bg_path=None, W=1080, H=1920, base_size_px=104):
    """Render the HOOK title card (no face): niche badge + bold爆色 hook, over b-roll/gradient.
    bg_path: your b-roll frame (else a niche-tinted gradient placeholder).
    Returns out_path."""
    from PIL import Image, ImageDraw
    cfg = NETGAN_NICHE_PRESETS.get(niche, NETGAN_NICHE_PRESETS["teaching"])
    theme = cfg.get("theme", niche)

    # ── background ──
    if bg_path and os.path.exists(bg_path):
        raw = Image.open(bg_path).convert("RGB")
        scale = max(W / raw.width, H / raw.height)
        raw = raw.resize((int(raw.width * scale), int(raw.height * scale)), Image.LANCZOS)
        bg = raw.crop(((raw.width-W)//2, (raw.height-H)//2,
                       (raw.width+W)//2, (raw.height+H)//2))
        # darken for text legibility
        ov = Image.new("RGB", (W, H), (0, 0, 0))
        bg = Image.blend(bg, ov, 0.42)
        bg = art.decorate_frame(bg, theme, art.resolve_theme(theme)["label"], "01", .8).convert("RGB")
    else:
        bg = art.render_background(W, H, theme, "signal_grid", seed=title)
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)

    # 黑紙卡提供清楚層級；白線框＋題材色底線是全頻道共同 identity。
    panel = [48, 470, W - 48, 1070]
    accent = art.resolve_theme(theme)["accent"]
    d.rounded_rectangle(panel, radius=24, fill=(7, 8, 10, 218),
                        outline=(255, 255, 255, 205), width=3)
    d.rectangle([panel[0], panel[3]-18, panel[2], panel[3]], fill=accent + (255,))

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
    img.alpha_composite(capimg, ((W - capimg.width) // 2, 570))
    try:
        os.remove(out_path + ".tmp.png")
    except OSError:
        pass

    img.convert("RGB").save(out_path)
    return out_path


def compile_hook_plan(title, niche="teaching", *, energy=.88,
                      subject="real_footage", seed=0, recent_signatures=()):
    """Compile a Shorts overlay plan before deciding whether a hook card is needed.

    Real footage remains the default.  ``render_hook_card`` is a fallback for
    scenes without readable evidence, not a mandatory opener.
    """
    from template_compiler import compile_template_plan
    return compile_template_plan(
        niche, "shorts", "first_frame", title=title, energy=energy,
        subject=subject, seed=seed, recent_signatures=recent_signatures,
    )


# ════════════════════════════════════════════════════════════════════════════
# 2026 研究：前 3 秒 = 80% 完讀率變異。3 個跨 niche 最穩的 viral hook formula。
# (web 學習 2026-06-01：OpusClip / Terra Market hook studies)
# ════════════════════════════════════════════════════════════════════════════
HOOK_FORMULAS = {
    "contrarian": {
        "name": "反差宣稱 Contrarian Claim",
        "pattern": "大家都說 {common}，但其實 {truth}",
        "examples": {
            "teaching": "大家都說寫程式很難，但我 0 基礎用 AI 90 天做出 14 款遊戲",
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
        {"seg": "hook", "t": "0-3s", "visual": "先用真結果／衝突／主體；依 compile_hook_plan() 決定 overlay", "overlay": "可讀性不足才用 render_hook_card()，不是固定開場"},
        {"seg": "body", "t": "3s-末", "visual": "三段 b-roll/螢幕錄影/產品", "overlay": "shorts_captions 跟旁白走"},
        {"seg": "outro", "t": "末段", "visual": "creator-configured outro card", "overlay": "creator-configured CTA"},
    ],
    "niches": list(NETGAN_NICHE_PRESETS.keys()),
    "caption_helper": "shorts_captions.style_caption",
    "hook_helper": "shorts_template.render_hook_card",
    "hook_plan_helper": "shorts_template.compile_hook_plan",
}
