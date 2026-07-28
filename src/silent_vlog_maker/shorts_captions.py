"""
shorts_captions — Reels/Shorts 多彩多尺寸字幕 (2026-06-01 訓練).

用戶要「不同顏色、大小的字」（Shorts 綜藝爆色關鍵字放大）。
建在現有 COLOR_VARIETY (7 色 vibrant palette) + Shorts 1080×1920 定位之上。

3-level 強度（每段可切）：
  1 clean  — 白底 + 關鍵字單色放大（最好讀，教學型）
  2 variety— 多色輪播 + 關鍵字放大（綜藝主流，推薦預設）
  3 pop    — 每字爆色 + 大小落差（最炸，hook/高能片）

用法：
    toks = style_caption("這一招我用了三年才學會", level=2, emphasis=["三年", "才學會"])
    render_caption_png(toks, "cap.png")          # 透明 PNG
    # 再 ffmpeg overlay 到 Shorts 影片 y=SUBTITLE_CENTER_Y
"""
import os
from .constants import COLOR_VARIETY, SUBTITLE_CENTER_Y

# 字級倍率 tier 用 base_size_px 為基準
SHORTS_CAPTION_LEVELS = {
    1: {"name": "clean",   "base": "white", "accents": ["cyan"],
        "emph_size": 1.3, "base_size": 1.0, "rotate_all": False},
    2: {"name": "variety", "base": "cream", "accents": ["gold", "magenta", "lime", "cyan", "orange"],
        "emph_size": 1.45, "base_size": 1.0, "rotate_all": False},
    3: {"name": "pop",     "base": None,    "accents": ["magenta", "cyan", "gold", "lime", "orange"],
        "emph_size": 1.7, "base_size": 1.15, "rotate_all": True},
}

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/NotoSansTC-Black.otf",
    "C:/Windows/Fonts/msjhbd.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]
# 跨平台（2026-07-10）：Windows 現值排前（行為不變）；Mac/Linux 由 platform_compat
# 探測補一個候選。全 miss → _font() 既有 PIL load_default() fallback 不變。
try:
    from platform_compat import find_cjk_font as _find_cjk_font
    _p = _find_cjk_font(prefer=["Black", "bd", "Bold"])
    if _p and _p not in _FONT_CANDIDATES:
        _FONT_CANDIDATES.append(_p)
    del _p
except ImportError:
    pass


def _hex_rgb(v: str):
    """COLOR_VARIETY values like '0xFFD700' or 'white' -> (r,g,b)."""
    if v == "white":
        return (255, 255, 255)
    h = v.replace("0x", "").replace("#", "")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _split_with_emphasis(text, emphasis):
    """Split text into tokens, marking which are emphasis substrings.
    Returns [(token, is_emphasis)]."""
    if not emphasis:
        return [(text, False)]
    toks, i = [], 0
    while i < len(text):
        hit = None
        for e in emphasis:
            if e and text.startswith(e, i):
                hit = e
                break
        if hit:
            toks.append((hit, True))
            i += len(hit)
        else:
            # accumulate non-emphasis run up to next emphasis start
            j = i + 1
            while j < len(text) and not any(text.startswith(e, j) for e in emphasis if e):
                j += 1
            toks.append((text[i:j], False))
            i = j
    return toks


def style_caption(text, level=2, emphasis=None):
    """Return tokens [(text, color_name, size_mult)] for a Shorts caption."""
    cfg = SHORTS_CAPTION_LEVELS[level]
    parts = _split_with_emphasis(text, emphasis or [])
    out, ai = [], 0
    for tok, is_emph in parts:
        if cfg["rotate_all"]:
            # level 3: every token rotates color + alternates size
            for ch in _chunk_for_pop(tok):
                color = cfg["accents"][ai % len(cfg["accents"])]; ai += 1
                size = cfg["emph_size"] if (is_emph or ai % 3 == 0) else cfg["base_size"]
                out.append((ch, color, size))
        elif is_emph:
            color = cfg["accents"][ai % len(cfg["accents"])]; ai += 1
            out.append((tok, color, cfg["emph_size"]))
        else:
            out.append((tok, cfg["base"] or "white", cfg["base_size"]))
    return out


def _chunk_for_pop(tok):
    """level-3 splits a run into small chunks (per CJK char / per word) so each pops."""
    # keep ASCII words whole, split CJK per char
    chunks, buf = [], ""
    for ch in tok:
        if ch.strip() == "":
            if buf:
                chunks.append(buf); buf = ""
            continue
        if "一" <= ch <= "鿿":
            if buf:
                chunks.append(buf); buf = ""
            chunks.append(ch)
        else:
            buf += ch
    if buf:
        chunks.append(buf)
    return chunks or [tok]


def _font(sz):
    from PIL import ImageFont
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def render_caption_png(tokens, out_path, width=1080, base_size_px=84,
                       stroke=4, gap=14, max_w_pad=120):
    """Render styled tokens -> transparent PNG (centered, black stroke).
    Overlay onto Shorts video at y≈SUBTITLE_CENTER_Y with ffmpeg.
    Returns (out_path, height)."""
    from PIL import Image, ImageDraw
    # measure on a scratch canvas
    scratch = Image.new("RGBA", (width, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(scratch)
    sized = [(t, c, int(base_size_px * m)) for t, c, m in tokens]
    lines, cur = [[]], 0
    for t, c, s in sized:
        w = d.textbbox((0, 0), t, font=_font(s))[2]
        if cur + w > width - max_w_pad and lines[-1]:
            lines.append([]); cur = 0
        lines[-1].append((t, c, s, w)); cur += w + gap
    lh = int(base_size_px * 1.4)
    H = lh * len(lines) + stroke * 2
    img = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    y = stroke
    for ln in lines:
        lw = sum(w for *_, w in ln) + gap * (len(ln) - 1)
        x = (width - lw) // 2
        maxs = max(s for _, _, s, _ in ln)
        for t, c, s, w in ln:
            f = _font(s)
            yy = y + (maxs - s)
            for dx in range(-stroke, stroke + 1, 2):
                for dy in range(-stroke, stroke + 1, 2):
                    dr.text((x + dx, yy + dy), t, font=f, fill=(0, 0, 0, 255))
            dr.text((x, yy), t, font=f, fill=_hex_rgb(COLOR_VARIETY[c]) + (255,))
            x += w + gap
        y += lh
    img.save(out_path)
    return out_path, H


DEFAULT_OVERLAY_Y = SUBTITLE_CENTER_Y  # 1280 for 1080×1920


# ════════════════════════════════════════════════════════════════════════════
# 2026 研究強化（web 學習 2026-06-01）— data-backed Shorts/Reels caption rules
# 來源綜整：OpusClip / Kreatli safe-zone / TikTok caption studies
# ════════════════════════════════════════════════════════════════════════════

# 安全區：避開上 20%(標題/頻道) + 下 25%(讚/留言/分享鍵)。出界 → 觀看時數 -22%。
SHORTS_SAFE_ZONE = {
    "canvas": (1080, 1920),
    "top_reserved": 384,       # 上 20% — 標題/頻道名
    "bottom_reserved": 480,    # 下 25% — 讚/留言/分享/訂閱
    "caption_y": 1180,         # 字幕安全中下帶（拉離按鈕區；研究：lower-middle third）
    "hook_y": 600,             # hook headline 上中（central 60%）
    "min_font_px": 60,         # ≈24-32pt mobile 下限（1080 canvas）— 寧大勿小
}


def safe_caption_y(caption_height, kind="caption"):
    """回傳安全的 overlay y（top-left），保證字幕不壓到平台 UI 按鈕區。"""
    z = SHORTS_SAFE_ZONE
    center = z["caption_y"] if kind == "caption" else z["hook_y"]
    y = center - caption_height // 2
    H = z["canvas"][1]
    y = max(z["top_reserved"], min(y, H - z["bottom_reserved"] - caption_height))
    return int(y)


def chunk_caption(text, phrases_per_chunk=2):
    """2026 研究：一次顯示 2-3 詞 → 動態感 + 完讀率↑（78.6% 爆款用動畫字幕）。
    **尊重詞/片語邊界**（照輸入的空白切，絕不把一個詞切兩半）→ 每塊 ~2-3 片語。
    回傳 [chunk_str, ...]。沒空白的純中文句 → 退回每 ~4 字一塊。"""
    phrases = text.split()
    if len(phrases) <= 1:  # 沒有片語邊界 → CJK 每 4 字
        return [text[i:i + 4] for i in range(0, len(text), 4)] or [text]
    n = max(1, phrases_per_chunk)
    return [" ".join(phrases[i:i + n]) for i in range(0, len(phrases), n)]


def style_chunks_active(chunks, level=2, active_color="gold", active_size=1.5,
                        karaoke=True):
    """active word highlight (變色放大) — 2026 最高影響力 caption 特徵。
    回傳 [(active_chunk_text, tokens)] 每個時間點一張：
      karaoke=True（預設）：整句可見，當前塊 active 色+放大、其餘塊 base 色
      karaoke=False：只顯示當前塊（逐塊 reveal）
    用法：逐項各 render_caption_png 一張，照旁白 timing 切。
    （2026-06-10 audit fix：之前 base 算了沒用、docstring 承諾的『其餘塊用 base』沒實作）"""
    base = SHORTS_CAPTION_LEVELS[level]["base"] or "white"
    out = []
    for i, ch in enumerate(chunks):
        if karaoke:
            tokens = [(c, active_color if j == i else base,
                       active_size if j == i else 1.0)
                      for j, c in enumerate(chunks)]
        else:
            tokens = [(ch, active_color, active_size)]
        out.append((ch, tokens))
    return out
