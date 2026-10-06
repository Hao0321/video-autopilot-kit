"""Short-form caption styling (public distribution).

Renders white-first readable captions with profile-selected emphasis levels and mechanical QA.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
import functools
import os
import shutil
import struct
import subprocess
import sys
from .constants import COLOR_VARIETY, SUBTITLE_CENTER_Y

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
import art_direction as art   # shared CJK font resolution (fails loudly, never tofu)
from art_direction import load_cjk_font
from caption_director import NO_LINE_START, best_break, break_points, wrap_ranges

# 字級倍率 tier 用 base_size_px 為基準
# PUBLIC_FIXTURE: starter defaults require creator-owned calibration evidence.
SHORTS_CAPTION_LEVELS = {
    1: {"name": "clean",   "base": "white", "accents": ["gold", "cyan"],
        "emph_size": 1.3, "base_size": 1.0, "rotate_all": False},
    2: {"name": "variety", "base": "white", "accents": ["gold", "magenta", "lime", "cyan", "orange"],
        "emph_size": 1.45, "base_size": 1.0, "rotate_all": False},   # 🚫 非預設（active profile opt-in）
    3: {"name": "pop",     "base": None,    "accents": ["magenta", "cyan", "gold", "lime", "orange"],
        "emph_size": 1.7, "base_size": 1.15, "rotate_all": True},    # 🚫 非預設（active profile opt-in）
}

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/NotoSansTC-Black.otf",
    "C:/Windows/Fonts/msjhbd.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]


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


def style_caption(text, level=1, emphasis=None, info=None):
    """Return tokens [(text, color_name, size_mult)] for a Shorts caption.
    🔒 white-first profile（2026-07-02）：預設 level=1 —— 底白；emphasis=【重點】→ accents[0]
    （全支同一色，不輪播）；info=【重要資訊】(數字/地名/價格) → accents[1]。
    level 2/3 only when the active profile selects it才傳入。"""
    cfg = SHORTS_CAPTION_LEVELS[level]
    info = info or []
    parts = _split_with_emphasis(text, list(emphasis or []) + list(info))
    out, ai = [], 0
    for tok, is_emph in parts:
        if cfg["rotate_all"]:
            # level 3: every token rotates color + alternates size（🚫 非預設）
            for ch in _chunk_for_pop(tok):
                color = cfg["accents"][ai % len(cfg["accents"])]; ai += 1
                size = cfg["emph_size"] if (is_emph or ai % 3 == 0) else cfg["base_size"]
                out.append((ch, color, size))
        elif is_emph:
            if level == 1:
                # white-first：重點=accents[0] 固定色；重要資訊=accents[1] 固定色。不輪播。
                color = cfg["accents"][1 % len(cfg["accents"])] if tok in info else cfg["accents"][0]
            else:
                color = cfg["accents"][ai % len(cfg["accents"])]; ai += 1
            out.append((tok, color, cfg["emph_size"]))
        else:
            out.append((tok, cfg["base"] or "white", cfg["base_size"]))
    return out


def audit_color_ratio(tokens_or_blocks, max_colored_ratio=0.35, max_accent_colors=2):
    """🔒 white-first QA gate（creator 2026-07-02）：驗「白為主、色為點綴」。
    吃 style_caption 的 tokens [(text,color,size)] 或 build_multicolor_ass 的
    blocks[(s,e,segs,kind)]（segs=[(text,color_key)]）。回 dict：
      colored_ratio  = 有色字符 / 全字符（>max_colored_ratio = FAIL）
      accent_colors  = 用到的非白色數（>max_accent_colors = FAIL，白 w/white/cream/c 不計）
    交付前跑：任一 FAIL → 減色，別交。"""
    whiteish = {"w", "white", "cream", "c", None}
    total = colored = 0
    accents = set()
    def eat(text, color):
        nonlocal total, colored
        n = len([ch for ch in str(text) if ch.strip()])
        total += n
        if color not in whiteish:
            colored += n
            accents.add(color)
    for item in tokens_or_blocks:
        if len(item) == 4 and isinstance(item[2], (list, tuple)):   # ASS block
            for seg in item[2]:
                eat(seg[0], seg[1])
        else:                                                        # token
            eat(item[0], item[1])
    ratio = (colored / total) if total else 0.0
    ok = ratio <= max_colored_ratio and len(accents) <= max_accent_colors
    return {"ok": ok, "colored_ratio": round(ratio, 3), "accent_colors": sorted(accents),
            "note": ("white-first OK" if ok else
                     f"太多色: colored {ratio:.0%}>{max_colored_ratio:.0%} 或 accent {len(accents)}>{max_accent_colors}")}


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


# ── Shorts line breaking: caption_director's shared kinsoku/word-safe breaker ──
def balanced_break(chars, width):
    """best_break() over (char, colour) pairs; colour-block edges (the author's
    semantic chunks) are preferred like spaces.  ``width(text)`` returns px."""
    text = "".join(ch for ch, _color in chars)
    edges = {i: .10 for i in range(1, len(chars)) if chars[i][1] != chars[i - 1][1]}
    return best_break(text, lambda s, e: width(text[s:e].strip()), edges)


def _cjk_chunks(text, target=4):
    """About ``target``-character chunks cut only at legal break points; clause
    punctuation is preferred and a remainder of ``target + 2`` stays whole."""
    points = break_points(text)
    chunks, start = [], 0
    while len(text) - start > target + 2:
        near = [i for i in points if start + 2 <= i <= start + target + 2]
        near = near or [i for i in sorted(points) if i >= start + 2][:1]
        if not near:
            break
        cut = min(near, key=lambda i: abs(i - start - target) - 10 * points[i])
        chunks.append(text[start:cut].strip())
        start = cut
    chunks.append(text[start:].strip())
    return [chunk for chunk in chunks if chunk]


def _font(sz):
    return load_cjk_font(sz, _FONT_CANDIDATES)


# ── libass face: one CJK face for Latin + CJK, measured with libass sizing ──
_FC_FORMAT = "%{family}|%{file}|%{index}\n"


def _fc_faces(args):
    """[(families, file, index)] from a fontconfig CLI query; [] without fontconfig."""
    if not shutil.which(args[0]):
        return []
    try:
        out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    faces = []
    for line in out.splitlines():
        names, _sep, rest = line.partition("|")
        path, _sep, index = rest.rpartition("|")
        if path and index.strip().isdigit():
            faces.append(([name.strip() for name in names.split(",")], path, int(index)))
    return faces


@functools.lru_cache(maxsize=16)
def libass_face(family, fonts_dir=None):
    """(family, file, index) a Shorts ASS should request for ``family``.

    fontconfig silently substitutes an unrelated Latin face for a missing
    family (e.g. Inter for "Noto Sans TC") and libass then mixes fonts inside
    one caption.  Keep a family the fonts dir or fontconfig really provides;
    otherwise request the CJK face platform_compat finds so one face renders
    both scripts.  Without the fontconfig CLI the configured name is kept.
    The returned file is the face used to measure caption widths.
    """
    wanted = str(family).strip().lower()
    matched = _fc_faces(["fc-match", "--format", _FC_FORMAT, "%s:bold" % family])
    scanned = _fc_faces(["fc-scan", "--format", _FC_FORMAT, fonts_dir]) \
        if fonts_dir and os.path.isdir(fonts_dir) else []
    for names, path, index in scanned + matched:
        if wanted in (name.lower() for name in names):
            return family, path, index
    path = art.find_cjk_font(["Black", "Bold"]) if art.find_cjk_font is not None else None
    faces = _fc_faces(["fc-query", "--format", _FC_FORMAT, path]) if path else []
    faces.sort(key=lambda face: not any(name.endswith(" TC") for name in face[0]))
    if faces:
        return faces[0][0][0], path, faces[0][2]
    if path or not matched:
        return family, path, 0
    return family, matched[0][1], matched[0][2]     # no CJK font: measure the substitute


def _win_height_em(path, index):
    """OS/2 (usWinAscent + usWinDescent) / unitsPerEm.  libass (like VSFilter)
    scales a face so that this height equals the ASS Fontsize."""
    with open(path, "rb") as handle:
        def read(offset, fmt):
            handle.seek(offset)
            return struct.unpack(fmt, handle.read(struct.calcsize(fmt)))
        base = read(12 + 4 * index, ">I")[0] if read(0, ">4s")[0] == b"ttcf" else 0
        tables = {}
        for i in range(read(base + 4, ">H")[0]):
            tag, _checksum, offset, _length = read(base + 12 + 16 * i, ">4sIII")
            tables[tag] = offset
        units = read(tables[b"head"] + 18, ">H")[0]
        ascent, descent = read(tables[b"OS/2"] + 74, ">hh")
    if ascent + descent <= 0 or units <= 0:
        raise ValueError("font has no usable OS/2 win metrics: %s" % path)
    return (ascent + descent) / float(units)


@functools.lru_cache(maxsize=32)
def _measure_font(path, index):
    from PIL import ImageFont
    return ImageFont.truetype(path, 100, index=index), _win_height_em(path, index)


def libass_advance(text, size, face):
    """Advance width (px) libass gives ``text`` at Fontsize ``size`` without
    \\fscx or border; None when the face cannot be measured."""
    if not face or not face[1]:
        return None
    try:
        font, height_em = _measure_font(face[1], face[2])
    except (OSError, KeyError, ValueError, struct.error):
        return None
    return font.getlength(text) / 100.0 * size / height_em


def _trim(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _caption_layout(tokens, base_size_px, gap, max_w):
    """Wrap styled tokens into trimmed (start, end) lines of a character stream.

    Token edges are preferred breaks, so words stay whole when they fit; a
    token wider than a line breaks at legal points inside it (wrap_ranges
    raises when it cannot).  ``gap`` px still separate tokens.
    Returns (chars, advances, ranges, measure)."""
    chars = []                       # (char, colour, font, gap before it)
    for text, color, mult in tokens:
        font = _font(int(base_size_px * mult))
        for pos, ch in enumerate(str(text)):
            chars.append((ch, color, font, gap if (pos == 0 and chars) else 0))
    text = "".join(c[0] for c in chars)
    advances = [font.getlength(ch) for ch, _color, font, _gap in chars]

    def measure(start, end):
        start, end = _trim(text, start, end)
        return sum(advances[i] + (chars[i][3] if i > start else 0) for i in range(start, end))

    edges = {i for i, c in enumerate(chars) if c[3]}
    ranges = [_trim(text, s, e) for s, e in wrap_ranges(text, measure, max_w, edges)]
    return chars, advances, [(s, e) for s, e in ranges if e > s], measure


def render_caption_png(tokens, out_path, width=1080, base_size_px=84,
                       stroke=4, gap=14, max_w_pad=120):
    """Render styled tokens -> transparent PNG (centered, black stroke).
    Overlay onto Shorts video at y≈SUBTITLE_CENTER_Y with ffmpeg.
    Lines wrap at kinsoku/word-safe points (also inside long tokens) and every
    line is sized from the real ascent/descent of its largest glyphs, so 1.3x
    emphasis is never clipped; text that cannot fit raises instead of being
    cropped.  Returns (out_path, height)."""
    from PIL import Image, ImageDraw
    chars, advances, ranges, measure = _caption_layout(tokens, base_size_px, gap,
                                                       width - max_w_pad)
    metrics = [[c[2].getmetrics() for c in chars[s:e]] for s, e in ranges]
    heights = [(max(a for a, _d in m), max(d for _a, d in m)) for m in metrics]
    H = sum(a + d for a, d in heights) + stroke * 2
    img = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    y = stroke
    for (start, end), (ascent, descent) in zip(ranges, heights):
        x, runs = (width - measure(start, end)) / 2.0, []   # runs: [x, text, colour, font]
        for i in range(start, end):
            ch, color, font, lead = chars[i]
            x += lead if i > start else 0
            if runs and not lead and runs[-1][2] == color and runs[-1][3] is font:
                runs[-1][1] += ch
            else:
                runs.append([x, ch, color, font])
            x += advances[i]
        for stroke_pass in (True, False):            # every stroke first, then fills
            for rx, run, color, font in runs:
                fill = (0, 0, 0, 255) if stroke_pass else _hex_rgb(COLOR_VARIETY[color]) + (255,)
                dr.text((rx, y + ascent), run, font=font, anchor="ls", fill=fill,
                        stroke_width=stroke if stroke_pass else 0, stroke_fill=fill)
        y += ascent + descent
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

# One text-safe rectangle (x0, y0, x1, y1) for every Shorts caption and overlay
# renderer: the reserved top/bottom bands above plus 10 % side margins.  The
# platform's right-side action column (like/comment/share) begins near x≈930
# in the lower half (constants.SAFE_ZONE["right"]); centred text stays clear
# of it unless a line needs the full width.
TEXT_SAFE_RECT = (108, SHORTS_SAFE_ZONE["top_reserved"], 972,
                  SHORTS_SAFE_ZONE["canvas"][1] - SHORTS_SAFE_ZONE["bottom_reserved"])


def fit_percent(width, deco, floor, what="caption"):
    """Largest scale (%) at which ``width * scale + deco`` fits the text-safe
    width; raises below ``floor`` instead of letting the frame crop the text."""
    room = TEXT_SAFE_RECT[2] - TEXT_SAFE_RECT[0]
    scale = min(100, int(100.0 * (room - deco) / max(width, 1.0)))
    if scale < floor:
        raise ValueError("%s needs %d%% (< %d%%) to fit the %d px text-safe width; "
                         "shorten it or split it into two captions" % (what, scale, floor, room))
    return scale


def fit_moving(width, xs, left, right, floor, what, pop=1.0):
    """(scale %, clamped anchor xs) keeping a centred caption ``width`` px wide
    that pops to ``pop`` x, plus ``left``/``right`` px of outline, shadow or
    tilt, inside TEXT_SAFE_RECT on its whole path; raises like fit_percent()."""
    scale = fit_percent(width * pop, left + right, floor, what)
    half = width * pop * scale / 200.0
    return scale, [int(min(max(x, TEXT_SAFE_RECT[0] + half + left),
                           TEXT_SAFE_RECT[2] - half - right)) for x in xs]


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
    回傳 [chunk_str, ...]。沒空白的純中文句 → 約 4 字一塊，只在合法斷點切
    （不拆英數字／中文數字、標點不落單、不留 1 字尾巴）。"""
    phrases = text.split()
    if len(phrases) <= 1:  # 沒有片語邊界 → 合法斷點約 4 字一塊
        return _cjk_chunks(text) or [text]
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


def _check_text_and_font():
    # chunk_caption used to cut every 4 chars (去台北一|零一看跨) and orphan a "！"
    assert chunk_caption("去台北一零一看跨年煙火！") == ["去台北", "一零一看", "跨年煙火！"]
    for chunk in chunk_caption("今天天氣很好，我們去散步吧！真的！"):
        assert len(chunk) > 1 and chunk[0] not in NO_LINE_START, chunk
    assert _font(40).getlength("測") >= 30, "CJK glyphs must come from a real CJK font"
    face = libass_face("Noto Sans TC")
    assert face[1] is None or libass_advance("測試", 100, face) > 0, face


def _check_png(tmp):
    from PIL import Image
    path = os.path.join(tmp, "cap.png")
    _, height = render_caption_png([("這口", "white", 1.0), ("脆到會響", "gold", 1.3)],
                                   path, width=600)     # 1.3x token wraps to line 2
    box = Image.open(path).getbbox()
    assert box[1] > 0 and box[3] < height and box[0] > 0 and box[2] < 600, (box, height)
    _, height = render_caption_png([("很長很長很長很長很長的字幕", "white", 1.0)], path, width=600)
    box = Image.open(path).getbbox()
    assert height > 160 and box[0] > 0 and box[2] < 600, (box, height)   # wrapped, not cut
    try:
        render_caption_png([("Supercalifragilisticexpialidocious", "white", 1.0)], path,
                           width=600)
        raise AssertionError("an unbreakable over-wide token must raise, not be cropped")
    except ValueError:
        pass


def self_test():
    """Chunking, font resolution, PNG captions and the text-safe rect."""
    import tempfile
    assert TEXT_SAFE_RECT == (108, 384, 972, 1440)
    _check_text_and_font()
    with tempfile.TemporaryDirectory(prefix="shorts_captions_") as tmp:
        _check_png(tmp)
    print("[shorts_captions selftest] OK")


if __name__ == "__main__":   # python -m silent_vlog_maker.shorts_captions
    self_test()
