"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import re
import art_direction as art


EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "←-⇿⬀-⯿️⃣]")


def strip_emoji(s):
    return EMOJI_RE.sub("", s)


COLOR_VARIETY = {
    'w': r'{\c&H00FFFFFF&}',   # 白
    # 2026-06-24 配色 v2：硬色→可愛色（珊瑚/杏桃/薄荷）+ 新增 粉/藍/紫/奶油。
    # PUBLIC_FIXTURE: verify project-specific caption choices with creator-owned source frames.
    'r': r'{\c&H6B6BFF&}',     # 珊瑚紅 RGB FF6B6B（原硬紅 FF3B30）
    'o': r'{\c&H7AB1FF&}',     # 杏桃橘 RGB FFB17A（原硬橘 FF8C00）
    'y': r'{\c&H3FD2FF&}',     # 奶油黃 RGB FFD23F（原硬黃 FFD60A）
    'g': r'{\c&HB0C93F&}',     # 薄荷綠 RGB 3FC9B0（原硬綠 30D158）
    'b': r'{\c&HFFB05A&}',     # 天空藍 RGB 5AB0FF（新）
    'p': r'{\c&HA874FF&}',     # 泡泡粉 RGB FF74A8（新）
    'v': r'{\c&HFF6BA6&}',     # 葡萄紫 RGB A66BFF（新）
    'c': r'{\c&HE6F4FF&}',     # 奶油白 RGB FFF4E6（新，比純白暖）
}


COLOR_ALIAS = {
    "white": "w", "gold": "y", "yellow": "y", "red": "r", "coral": "r",
    "orange": "o", "apricot": "o", "green": "g", "mint": "g",
    "blue": "b", "sky": "b", "pink": "p", "purple": "v", "cream": "c",
}


def resolve_color(key):
    """顏色鍵 -> ASS 顏色標籤。**未知鍵直接 raise，不准靜默退白。**

    舊版是 `COLOR_VARIETY.get(color, COLOR_VARIETY["w"])`，任何拼錯或用全名
    都會安靜變白字。**靜默降級比大聲失敗危險**（同 M84 / M111 家族）。
    """
    k = str(key).strip().lower()
    k = COLOR_ALIAS.get(k, k)
    if k not in COLOR_VARIETY:
        raise AssertionError(
            "unknown color key %r -- valid: %s ; alias: %s"
            % (key, "/".join(sorted(COLOR_VARIETY)), "/".join(sorted(COLOR_ALIAS))))
    return COLOR_VARIETY[k]


_MAIN_POS = r'{\an5\pos(540,1180)}'


_HOOK_POS = r'{\an5\pos(540,455)}'


_SUB_POS  = r'{\an5\pos(540,1270)}'


_ADDR_POS = r'{\an5\pos(540,1390)}'


_RENDER_KINDS = {
    'main', 'hook', 'sub', 'addr', 'impact', 'impact_approved', 'ribbon',
    'float_left', 'float_right', 'chip',
}


def _ass_bgr(rgb, alpha="00"):
    r, g, b = rgb
    return f"&H{alpha}{b:02X}{g:02X}{r:02X}&"


def _header(font="Noto Sans TC", theme="general"):
    cfg = art.resolve_theme(theme)
    accent = _ass_bgr(cfg["accent"])
    return f"""[Script Info]
Title: creator Signal Grid / {cfg['key']}
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MAIN,{font},124,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,4,5,40,40,0,1
Style: HOOK,{font},116,&H00FFFFFF,{accent},&H5808080A,-1,0,0,0,100,100,0,0,3,6,2,5,64,64,0,1
Style: SUB,{font},112,&H00FFFFFF,&H00000000,&H30000000,-1,0,0,0,100,100,0,0,1,10,3,5,44,44,0,1
Style: ADDR,{font},58,&H00FFFFFF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,3,9,0,5,40,40,0,1
Style: IMPACT,{font},190,&H00FFFFFF,&H00000000,&H50000000,-1,0,0,0,100,100,0,0,1,12,7,5,36,36,0,1
Style: RIBBON,{font},102,&H00FFFFFF,{accent},&H90000000,-1,0,0,0,100,100,1,0,3,8,2,5,48,48,0,1
Style: FLOAT,{font},124,&H00FFFFFF,&H00000000,&H48000000,-1,0,0,0,100,100,1,0,1,10,6,5,48,48,0,1
Style: CHIP,{font},58,&H00FFFFFF,&H00000000,&HBC101217,-1,0,0,0,100,100,1,0,3,5,0,7,36,36,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def _colored_body(segs, wrap_chars=0):
    """Inline color body；impact 自動斷成兩行，避免巨字橫向裁切。"""
    chars = []
    for text, color in segs:
        clean = strip_emoji(str(text))
        for ch in clean:
            chars.append((ch, color))
    visible = [i for i, (ch, _color) in enumerate(chars) if not ch.isspace()]
    split_at = None
    if wrap_chars and len(visible) > wrap_chars and '\n' not in ''.join(ch for ch, _ in chars):
        split_at = visible[len(visible) // 2]
    out, last_color = "", None
    for index, (ch, color) in enumerate(chars):
        if split_at is not None and index == split_at:
            out += r'\N'
        if color != last_color:
            out += resolve_color(color)
            last_color = color
        out += r'\N' if ch == '\n' else ch
    return out


def _plain_body(segs, wrap_chars=0):
    return re.sub(r'\{\\c&H[0-9A-F]+&\}', '', _colored_body(segs, wrap_chars))


def _dialogue(layer, start, end, style, tags, body):
    return "Dialogue: %d,%s,%s,%s,,0,0,0,,%s%s" % (
        layer, _ts(start), _ts(end), style, tags, body)


def _line_units(text):
    """Approximate one rendered line in ems; CJK is full width."""
    units = 0.0
    for ch in text:
        if ch.isspace():
            units += .35
        elif ord(ch) < 128:
            units += .58
        else:
            units += 1.0
    return units


def _caption_units(segs, wrap_chars=0):
    """Return the widest rendered line, after the same wrapping as ASS output."""
    body = _plain_body(segs, wrap_chars)
    return max(1.0, *(_line_units(line) for line in body.split(r'\N')))


def _split_caption_lines(segs, wrap_chars=0):
    """Split caption segments into independently positioned colored lines."""
    chars = []
    for text, color in segs:
        chars.extend((ch, color) for ch in strip_emoji(str(text)))
    visible = [i for i, (ch, _color) in enumerate(chars) if not ch.isspace()]
    split_at = None
    if wrap_chars and len(visible) > wrap_chars and not any(ch == '\n' for ch, _ in chars):
        split_at = visible[len(visible) // 2]
    raw_lines, current = [], []
    for index, item in enumerate(chars):
        ch, color = item
        if (split_at is not None and index == split_at) or ch == '\n':
            if current:
                raw_lines.append(current)
                current = []
            if ch == '\n':
                continue
        current.append((ch, color))
    if current:
        raw_lines.append(current)
    output = []
    for line in raw_lines or [[('', 'w')]]:
        merged = []
        for ch, color in line:
            if merged and merged[-1][1] == color:
                merged[-1] = (merged[-1][0] + ch, color)
            else:
                merged.append((ch, color))
        output.append(merged)
    return output


def _kinetic_tags(kind, shadow=False, text_units=1.0, line_index=0, line_count=1):
    """原生 ASS pop/move/rotate；shadow layer 做假擠壓厚度，形成 2.5D 浮空感。"""
    if kind == 'impact':
        # Cross-platform portrait typography safe area: keep every visible
        # pixel (glyph + 12 px outline + 7 px shadow + 10 px depth offset) at
        # least about 10% away from both sides, including the pop overshoot.
        # 1080 * .8 = 864.  Each impact line is positioned independently so
        # horizontal fitting never collapses the vertical leading between lines.
        decorated_width = 190 * max(1.0, text_units) + 58
        peak_scale = max(44, min(100, int(86400 / decorated_width)))
        final_scale = max(40, min(94, int(peak_scale / 1.04)))
        start_scale = max(32, int(final_scale * .72))
        line_gap = 180
        y = 940 + int((line_index - (line_count - 1) / 2.0) * line_gap)
        x = 540
        if shadow:
            x += 10
            y += 14
        return (r'{\an5\pos(%d,%d)\fad(55,95)\fscx%d\fscy%d'
                r'\t(0,150,\fscx%d\fscy%d)\t(150,290,\fscx%d\fscy%d)}') % (
                    x, y, start_scale, start_scale, peak_scale, peak_scale,
                    final_scale, final_scale)
    if kind == 'ribbon':
        # RIBBON uses BorderStyle=3, so its box must stay inside the horizontal
        # safe area as well as the glyphs.  Centre the hold at x=540 and scale
        # long labels to a 72 px inset instead of entering from a negative x.
        final_scale = max(64, min(100, int(89000 / (102 * text_units + 20))))
        start_scale = max(58, int(final_scale * .88))
        return (r'{\an5\move(430,1035,540,995,0,260)\frz-4\fad(70,110)'
                r'\fscx%d\fscy%d\t(0,220,\fscx%d\fscy%d\frz-2)}') % (
                    start_scale, start_scale, final_scale, final_scale)
    if kind == 'chip':
        # Functional location / price / step label. It enters once, settles,
        # then leaves; unlike the retired decorative overlay it never spans the
        # whole frame and must carry actual editorial information.
        return (r'{\an7\move(54,420,82,420,0,180)\fad(65,100)'
                r'\fscx92\fscy92\t(0,180,\fscx100\fscy100)}')
    if kind == 'float_left':
        x1, y1, x2, y2, angle = (326, 974, 385, 914, -6)
    else:
        x1, y1, x2, y2, angle = (754, 950, 690, 890, 6)
    if shadow:
        x1 += 12; y1 += 15; x2 += 12; y2 += 15
    return (r'{\an5\move(%d,%d,%d,%d,0,420)\frz%d\fad(55,110)'
            r'\fscx72\fscy72\t(0,150,\fscx112\fscy112)'
            r'\t(150,300,\fscx100\fscy100)}') % (x1, y1, x2, y2, angle)


def build_multicolor_ass(blocks, out_path, font="Noto Sans TC", theme="general"):
    """blocks: list of (start, end, segs, kind)。
    segs=[(text,color), ...] color∈ w/r/o/y/g/b/p/v/c（白/珊瑚/杏桃/黃/薄荷/天空藍/泡泡粉/葡萄紫/奶油白；'\\n' 換行）。
    kind='main'|'hook'|'sub'|'addr'|'impact'|'ribbon'|'float_left'|'float_right'|'chip'。
    font: 標題字體 family name（預設 Noto Sans TC；niche 對應見 NICHE_FONTS，須有繁中 M38）。
    自動 strip_emoji（M38 防呆 — 不靠人記得不放 emoji）。"""
    lines = [_header(font, theme)]
    for start, end, segs, kind in blocks:
        if kind not in _RENDER_KINDS:
            raise AssertionError("unknown caption kind %r -- valid: %s"
                                 % (kind, "/".join(sorted(_RENDER_KINDS))))
        if kind == 'impact_approved':
            # A human-approved composition is evidence, not a suggestion.
            # Preserve creator's accepted v1 hero typography exactly; safety gates
            # may reject a real overflow, but must not pre-emptively redesign it.
            body = _colored_body(segs)
            plain = _plain_body(segs)
            shadow = (r'{\an5\pos(550,954)\fad(55,95)\fscx70\fscy70'
                      r'\t(0,150,\fscx112\fscy112)'
                      r'\t(150,290,\fscx100\fscy100)}'
                      r'{\c&H00111116&}')
            approved = (r'{\an5\pos(540,940)\fad(55,95)\fscx70\fscy70'
                        r'\t(0,150,\fscx112\fscy112)'
                        r'\t(150,290,\fscx100\fscy100)}')
            lines.append(_dialogue(0, start, end, 'IMPACT', shadow, plain))
            lines.append(_dialogue(2, start, end, 'IMPACT', approved, body))
            continue
        if kind == 'impact':
            caption_lines = _split_caption_lines(segs, wrap_chars=6)
            for line_index, line_segs in enumerate(caption_lines):
                body = _colored_body(line_segs)
                plain = _plain_body(line_segs)
                text_units = _caption_units(line_segs)
                tags = dict(text_units=text_units, line_index=line_index,
                            line_count=len(caption_lines))
                shadow = _kinetic_tags(kind, shadow=True, **tags) + r'{\c&H00111116&}'
                lines.append(_dialogue(0, start, end, 'IMPACT', shadow, plain))
                lines.append(_dialogue(
                    2, start, end, 'IMPACT', _kinetic_tags(kind, **tags), body))
            continue
        if kind in ('float_left', 'float_right'):
            body = _colored_body(segs)
            plain = _plain_body(segs)
            text_units = _caption_units(segs)
            style = 'FLOAT'
            # 先畫深色位移層，再畫主層；比單純 drop shadow 更像浮在畫面前。
            shadow = _kinetic_tags(kind, shadow=True, text_units=text_units) + r'{\c&H00111116&}'
            lines.append(_dialogue(0, start, end, style, shadow, plain))
            lines.append(_dialogue(
                2, start, end, style,
                _kinetic_tags(kind, text_units=text_units), body))
            continue
        if kind == 'ribbon':
            body = _colored_body(segs)
            lines.append(_dialogue(
                2, start, end, 'RIBBON',
                _kinetic_tags(kind, text_units=_caption_units(segs)), body))
            continue
        if kind == 'chip':
            body = _colored_body(segs)
            lines.append(_dialogue(
                2, start, end, 'CHIP',
                _kinetic_tags(kind, text_units=_caption_units(segs)), body))
            continue
        style = {'addr': 'ADDR', 'hook': 'HOOK', 'sub': 'SUB'}.get(kind, 'MAIN')
        pos = {'addr': _ADDR_POS, 'hook': _HOOK_POS, 'sub': _SUB_POS}.get(kind, _MAIN_POS)
        lines.append(_dialogue(0, start, end, style, pos, _colored_body(segs)))
    open(out_path, 'w', encoding='utf-8').write("\n".join(lines))
    return out_path
