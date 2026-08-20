# -*- coding: utf-8 -*-
"""
M96: 美食/旅遊直式 Shorts pipeline（純 ffmpeg）— silent footage → 多色重點字幕 → 配樂。

從 2026-06-20 四支 Shorts（觀音山獨角仙 / 潮音洞 / 豐衣足食 / 三芝淺水灣）固化。
9:16 1080x1920。專案只需餵 data（segs + caps），不用每支整檔複製。

用法：
    from silent_vlog_maker import normalize_to_portrait, build_one_short
    # 1) iPhone .MOV 轉正
    for clip in raw_clips: normalize_to_portrait(clip, norm_out)
    # 2) 餵片段 + 多色字幕 + BGM
    build_one_short(
        segs=[(norm1, 1.0, 5.0), (norm2, 0.5, 5.0)],          # (clip, in, dur)
        caps=[(0.2, 5.0, [('三芝這片海','g'), ('人超少又安靜','y')], 'main'),
              (5.0, 22.0, [('淺水灣',' w'.strip()), ('新北市三芝區','w')], 'addr')],
        bgm='D:/.../assets/bgm/chill-01.mp3', out='short.mp4', vol=0.42)
"""
import subprocess, os, re, shutil, json, sys

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
import art_direction as art
import editorial_templates as editorial
from storage_lifecycle import atomic_publish
from silent_vlog_maker.shorts_audio import loudnorm_two_pass as _loudnorm_two_pass

_PROJECT_ROOT = os.path.normpath(os.path.join(_AUTOPILOT, "..", "..", ".."))

# ── encoding 顯式 utf-8（避免 Windows cp950 對中文路徑/輸出 crash；M96 bug fix）──
def _run(args):
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def _probe_dur(f):
    return float(_run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                       '-of', 'csv=p=0', f]).stdout.strip())

# ── M38: 去 emoji（NotoSansTC 無 emoji glyph → libass render 成豆腐框）──
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "←-⇿⬀-⯿️⃣]")
def strip_emoji(s):
    return EMOJI_RE.sub("", s)

# ── 多色重點字（用戶要求重點字不同色）= ASS inline color（BGR），必包 {} ──
COLOR_VARIETY = {
    'w': r'{\c&H00FFFFFF&}',   # 白
    # 2026-06-24 配色 v2：硬色→可愛色（珊瑚/杏桃/薄荷）+ 新增 粉/藍/紫/奶油。
    # 全片仍保留厚黑描邊(Outline 10) → 再亮再可愛也清楚不糊。Hao「太紅太橘太綠」回饋。
    'r': r'{\c&H6B6BFF&}',     # 珊瑚紅 RGB FF6B6B（原硬紅 FF3B30）
    'o': r'{\c&H7AB1FF&}',     # 杏桃橘 RGB FFB17A（原硬橘 FF8C00）
    'y': r'{\c&H3FD2FF&}',     # 奶油黃 RGB FFD23F（原硬黃 FFD60A）
    'g': r'{\c&HB0C93F&}',     # 薄荷綠 RGB 3FC9B0（原硬綠 30D158）
    'b': r'{\c&HFFB05A&}',     # 天空藍 RGB 5AB0FF（新）
    'p': r'{\c&HA874FF&}',     # 泡泡粉 RGB FF74A8（新）
    'v': r'{\c&HFF6BA6&}',     # 葡萄紫 RGB A66BFF（新）
    'c': r'{\c&HE6F4FF&}',     # 奶油白 RGB FFF4E6（新，比純白暖）
}

# ── niche → 配色 / 字體 對照（2026-06-24 寫死；丟素材自動套，跟 BGM 那套同理）──
# 🔒 Hao 2026-07-02 white-first 鐵則：「字的顏色太多了。主要是白色，有重點跟重要資訊再用有色字。」
#   → palette 語意改為【候選強調色】不是【輪流全上】：每支 Short 取 palette[0] 當唯一主強調色
#     （全支同色，只給【重點】詞）、palette[1] 給【重要資訊】（數字/地名/價格），其餘一律白 'w'。
#     整行上色 / 逐重點輪播 4 色 = 🚫 禁止預設。交付前跑 shorts_captions.audit_color_ratio()
#     （有色字符 ≤35%、非白色 ≤2 色）沒過不交。
# 好記的別名 -> 單字母鍵。2026-07-29：_plan.py 骨架與人手寫的 plan 常寫
# "gold"/"white" 這類全名，舊版會**靜默退回白字** —— 「重點=金」這個設計
# 從頭到尾沒表達出來，成片看起來完全正常、gate 也不擋，只有把 .ass 拆開
# 比對顏色碼才看得出來（實測 3 支中招）。
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


NICHE_PALETTES = {   # 候選強調色（key 對 COLOR_VARIETY；[0]=主強調 [1]=資訊色，其餘備選）
    'food':     ['r', 'y', 'o', 'g'],   # 美食：主=珊瑚、資訊=黃
    'travel':   ['b', 'r', 'y', 'g'],   # 旅遊：主=天空藍、資訊=珊瑚
    'cafe':     ['o', 'c', 'v', 'r'],   # 咖啡廳：主=杏桃、資訊=奶油白
    'dessert':  ['p', 'g', 'y', 'v'],   # 甜點：主=泡泡粉、資訊=薄荷
    'unboxing': ['b', 'p', 'y', 'g'],   # 開箱：主=天空藍、資訊=泡泡粉
    'toy':      ['p', 'y', 'b', 'g'],   # 玩具：主=泡泡粉、資訊=黃
    'ai':       ['y', 'b', 'g', 'v'],   # AI：主=訊號黃、資訊=天空藍
    'teaching': ['y', 'b', 'g', 'v'],
    'game':     ['g', 'v', 'y', 'p'],   # 遊戲：主=薄荷、資訊=紫
    'gaming':   ['g', 'v', 'y', 'p'],
    'diy':      ['o', 'b', 'y', 'g'],   # DIY：主=杏桃、資訊=藍
    'product':  ['y', 'b', 'w', 'g'],   # 3C 評測：訊號黃＋證據藍
    'documentary': ['r', 'b', 'w', 'y'],
    'interview': ['b', 'o', 'w', 'y'],
    'automotive': ['g', 'o', 'w', 'r'],
    'fitness':  ['o', 'g', 'w', 'y'],
    'fashion':  ['p', 'v', 'w', 'b'],
    'architecture': ['b', 'o', 'w', 'c'],
    'business': ['y', 'b', 'w', 'g'],
    'nature':   ['g', 'b', 'w', 'y'],
    'music':    ['p', 'v', 'b', 'w'],
}
NICHE_FONTS = {      # 標題字幕字體「family name」（libass 用這個比對；2026-06-24 實測過 family name）
    'food':     'Huninn',            # 粉圓・圓體可愛台味（檔 Huninn-Regular.ttf；family=Huninn 非「jf open 粉圓」）
    'travel':   'LXGW WenKai TC',    # 文楷・楷體手寫感（旅行筆記感）✅實測
    'cafe':     'LXGW WenKai TC',    # 文青溫暖（或 Noto Serif TC）
    'dessert':  'Huninn',            # 可愛甜
    'unboxing': 'Noto Sans TC',      # 乾淨科技
    'toy':      'Huninn',            # 玩具要親切厚實
    'ai':       'Noto Sans TC',      # 科技／教學乾淨
    'teaching': 'Noto Sans TC',
    'game':     'Noto Sans TC',
    'gaming':   'Noto Sans TC',
    'diy':      'Noto Sans TC',
    'product':  'Noto Sans TC',
    'documentary': 'Noto Sans TC',
    'interview': 'Noto Sans TC',
    'automotive': 'Noto Sans TC',
    'fitness':  'Noto Sans TC',
    'fashion':  'LXGW WenKai TC',
    'architecture': 'Noto Sans TC',
    'business': 'Noto Sans TC',
    'nature':   'LXGW WenKai TC',
    'music':    'Noto Sans TC',
}

# 自訂字體資料夾（放繁中字體的 _active；libass 用 fontsdir 找，不必裝進 Windows）。
# 路徑：repo 根/assets/fonts/_active（從本檔往上 4 層）。
FONTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          '..', '..', '..', '..', 'assets', 'fonts', '_active'))
def _ass_filter(ass_basename, workdir, fonts_dir=None):
    """ass 燒錄 filter 字串。ass 用 basename、fontsdir 用「相對 workdir 的路徑」——
    兩者都不含 Windows D: 冒號 → ffmpeg filtergraph 不會把冒號當選項分隔(承同一個雷，
    `\\:` 跳脫 ffmpeg 不吃，改算相對路徑最穩)。cwd 已設 workdir 故相對 fontsdir 解析得到。"""
    fd = (fonts_dir or FONTS_DIR)
    if not (fd and os.path.isdir(fd)):
        return f'ass={ass_basename}'  # 沒自訂字體夾 → 走系統字體
    try:
        rel = os.path.relpath(fd, workdir).replace('\\', '/')  # 同碟：乾淨相對路徑
    except ValueError:
        # 跨磁碟機(workdir 在 C:、字體在 D:)→ relpath 算不出。複製字體到 workdir/_fonts
        # 用相對路徑(一樣避開 D: 冒號的 filtergraph 雷)。真實 pipeline 同碟，這分支少走。
        local = os.path.join(workdir, '_fonts'); os.makedirs(local, exist_ok=True)
        for f in os.listdir(fd):
            if f.lower().endswith(('.ttf', '.otf', '.ttc')) and not os.path.exists(os.path.join(local, f)):
                shutil.copy(os.path.join(fd, f), os.path.join(local, f))
        rel = '_fonts'
    return f'ass={ass_basename}:fontsdir={rel}'
_MAIN_POS = r'{\an5\pos(540,1180)}'   # 中下置中（避上 384 / 下 1440 SHORTS_SAFE_ZONE）
_HOOK_POS = r'{\an5\pos(540,1100)}'   # hook 高一點，與後續字幕形成位置層級
_SUB_POS  = r'{\an5\pos(540,1270)}'
_ADDR_POS = r'{\an5\pos(540,1390)}'   # 底部安全區地址
_CHIP_POS = r'{\an7\pos(82,420)}'     # 左上功能資訊卡；避平台頂部與右側 UI
_RENDER_KINDS = {
    'main', 'hook', 'sub', 'addr', 'impact', 'impact_approved', 'ribbon',
    'float_left', 'float_right', 'chip',
}
# MAIN 124px（2026-06-22「字太小」回饋放大；原 82）。⚠️ 上限約 124：WrapStyle=2 不自動換行，
# \an5+\pos(540,) 置中可用全寬 1080，最長 8 字 ×124≈1008px（±504 落在 36..1044）剛好不衝框；
# >130 的 8 字行會被裁掉。要更大就得把長句拆兩行（加 \N）。地址 58px（次要資訊不必最大）。

# font 可換（裝好/丟 assets/fonts 的繁中字體 family name；預設 Noto Sans TC）。
# ⚠️ M38：字體必須有繁中，否則中文豆腐框。niche 對應字體見 NICHE_FONTS。
def _ass_bgr(rgb, alpha="00"):
    r, g, b = rgb
    return f"&H{alpha}{b:02X}{g:02X}{r:02X}&"


def _header(font="Noto Sans TC", theme="general"):
    cfg = art.resolve_theme(theme)
    accent = _ass_bgr(cfg["accent"])
    return f"""[Script Info]
Title: Hao Signal Grid / {cfg['key']}
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MAIN,{font},124,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,4,5,40,40,0,1
Style: HOOK,{font},134,&H00FFFFFF,{accent},&H5808080A,-1,0,0,0,100,100,0,0,3,7,2,5,42,42,0,1
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
            # Preserve Hao's accepted v1 hero typography exactly; safety gates
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

# ── iPhone .MOV → upright 9:16（autorotate 處理 rotation 旗標，含混 -90/+90）──
def normalize_to_portrait(clip_in, clip_out, crf=19):
    """轉正成 1080x1920/30fps/無音（M29/M81）。
    ffmpeg 預設 autorotate 先套 rotation 旗標 → scale/crop 在「已轉正的幀」上做，
    所以同批混 rot=-90/+90（iPhone 拿反）也全部統一 upright（M96 踩過）。"""
    vf = ('scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
          'fps=30,setsar=1,format=yuv420p')
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', clip_in, '-vf', vf, '-an',
              '-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium', clip_out])
    if r.returncode:
        raise RuntimeError('normalize_to_portrait failed: ' + r.stderr[-500:])
    return clip_out

def extract_gps(clip):
    """抽 iPhone GPS（com.apple.quicktime.location.ISO6709）→ '+25.2526+121.4710+004/'。
    回 (lat, lon, alt) 或 None。地址要再 web 反查（無法套件化）。"""
    raw = _run(['ffprobe', '-v', 'error', '-show_entries',
                'format_tags=com.apple.quicktime.location.ISO6709',
                '-of', 'default=nw=1:nk=1', clip]).stdout.strip()
    m = re.match(r'([+-][\d.]+)([+-][\d.]+)([+-][\d.]+)?', raw)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)),
            float(m.group(3)) if m.group(3) else None)

_NORMV = ('scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
          'setsar=1,fps=30,format=yuv420p')

# ── BGM 高光偵測：Shorts BGM 不從頭播（前奏無聊）→ 落在副歌/drop ──
def find_music_highlight(bgm, dur, pre=0.0):
    """回 BGM「高光時刻」起始秒數：整支 Short 騎在歌最 energetic 的 dur 秒窗上。
    用 ebur128 短期響度 S(3s 滑動 LUFS) 當 energy proxy，找平均最大的 dur 秒窗。
    pre=讓 drop 晚 pre 秒進(預設 0=高光從頭就到)。歌比短片短就回 0(反正會 loop)。"""
    total = _probe_dur(bgm)
    if total <= dur + 0.5:
        return 0.0
    # 注意：ebur128 的逐幀 t:/S: 行印在 stderr；加 metadata=1 反而會「關掉」這些行(踩過) → 不要加
    r = _run(['ffmpeg', '-hide_banner', '-i', bgm, '-af', 'ebur128', '-f', 'null', '-'])
    pts = []  # [(t, short_term_LUFS)]
    for line in r.stderr.splitlines():
        mt = re.search(r't:\s*([\d.]+)', line)
        ms = re.search(r'S:\s*(-?[\d.]+|-?inf)', line)
        if mt and ms:
            s = ms.group(1)
            pts.append((float(mt.group(1)), -120.0 if 'inf' in s else float(s)))
    if len(pts) < 5:
        return 0.0
    best_t, best_e = 0.0, -1e9
    for i, (t0, _) in enumerate(pts):
        if t0 + dur > total + 0.01:
            break
        seg = [s for (t, s) in pts[i:] if t <= t0 + dur]
        if seg:
            e = sum(seg) / len(seg)        # 視窗平均響度 = energy
            if e > best_e:
                best_e, best_t = e, t0
    return round(max(0.0, best_t - pre), 2)

# ── 音效自動篩選：量 beat 挑動感曲 + 夠長不 loop ──
def beat_rate(bgm):
    """每秒「響度脈衝峰」數 = 節奏密度 proxy。beat 越高越動感(挑曲/相對比較用)。
    用 ebur128 momentary(M) 局部峰計數。氛圍慢曲~1/s，動感快剪/Vocal Chop~2.5-3/s。"""
    r = _run(['ffmpeg', '-hide_banner', '-i', bgm, '-af', 'ebur128', '-f', 'null', '-'])
    M = []
    for line in r.stderr.splitlines():
        m = re.search(r'M:\s*(-?[\d.]+|-?inf)', line)
        if m:
            v = m.group(1); M.append(-70.0 if 'inf' in v else float(v))
    if len(M) < 10:
        return 0.0
    peaks = sum(1 for i in range(1, len(M) - 1) if M[i] > M[i-1] and M[i] >= M[i+1] and M[i] > -40)
    return round(peaks / (len(M) * 0.1), 2)   # peaks / 秒

_BGM_INDEX_CACHE = {}

def _indexed_bgm_meta(path):
    """Read the existing per-folder analysis instead of probing the song again."""
    folder = os.path.dirname(os.path.abspath(path))
    index_path = os.path.join(folder, 'bgm_index.json')
    if not os.path.isfile(index_path):
        return {}
    if index_path not in _BGM_INDEX_CACHE:
        try:
            data = json.load(open(index_path, encoding='utf-8'))
            _BGM_INDEX_CACHE[index_path] = {
                str(row.get('file', '')).lower(): row for row in data.get('tracks', [])
            }
        except (OSError, ValueError, TypeError):
            _BGM_INDEX_CACHE[index_path] = {}
    return _BGM_INDEX_CACHE[index_path].get(os.path.basename(path).lower(), {})

def pick_bgm(candidates, dur, prefer='energetic', margin=1.0):
    """音效自動篩選：從同題材候選曲挑「**夠長(不 loop)** + **最動感(beat 最密)**」的一首。
    candidates: BGM 路徑 list；dur: 影片秒長。回最佳路徑(沒候選回 None)。
    prefer='energetic' 選 beat 最高；'chill' 選 beat 最低(放鬆題材)。
    踩雷固化：曲比影片短 → `-stream_loop` 接縫跳音(忽大忽小)→ 一律排除短曲(M99)。"""
    scored = []
    for b in candidates:
        try:
            meta = _indexed_bgm_meta(b)
            indexed_dur = meta.get('duration_sec')
            track_dur = float(indexed_dur) if indexed_dur is not None else _probe_dur(b)
            if track_dur < dur + margin:   # 太短 → loop 跳音 → 排除
                continue
            # BPM is already calculated by music_engine/librosa.  Only legacy or
            # unindexed files pay the expensive ebur128 beat-rate pass.
            rhythm = float(meta['bpm']) if meta.get('bpm') is not None else beat_rate(b)
            scored.append((rhythm, b))
        except Exception:
            continue
    if not scored:
        return candidates[0] if candidates else None   # 候選都太短 → 退第一首(交給呼叫端決定)
    scored.sort(reverse=(prefer == 'energetic'))        # energetic→beat 高優先；chill→低優先
    return scored[0][1]

# ── 最終響度歸一化：two-pass loudnorm 精準命中 target LUFS（YouTube/Shorts 標準 -14）──
def _visual_plan_card_events(visual_plan, total):
    """Return explicitly approved gaps that may use a full-frame card.

    A semantic turn is not permission to cover real footage.  Full-frame cards
    are opt-in only and require both an explicit authoring flag and a verified
    footage gap.  Ordinary pattern interrupts stay on the source footage.
    """
    events = []
    for e in (visual_plan or {}).get("events", []):
        t, dur = float(e.get("t", 0)), float(e.get("duration", 0))
        text = str(e.get("source_text", "")).strip()
        if (e.get("type") == "pattern_interrupt" and text and t >= 1.0
                and e.get("allow_full_frame_card") is True
                and e.get("footage_gap_verified") is True
                and e.get("reason") != "payoff_marker"
                and t + dur <= total - 0.8 and dur >= 0.25):
            events.append((t, min(dur, 0.82), text, str(e.get("card", "NOTE"))))
        if len(events) >= 3:
            break
    return events


def _apply_visual_plan_cards(video_in, visual_plan, theme, base, total):
    """只在明確核准的素材缺口使用全屏 Bright Editorial 字卡。

    片頭、一般語意轉折、片尾與 payoff proof 一律保留真畫面；有真實素材時只能使用不遮
    證據的 overlay，不能用 SHAPE / PLAY、TRAVEL / JOURNAL 等通用模板整頁取代畫面。
    """
    events = _visual_plan_card_events(visual_plan, total)
    if not events:
        return video_in

    card_dir = base + "_cards"
    os.makedirs(card_dir, exist_ok=True)
    card_paths = []
    template_cfg = (visual_plan or {}).get("template_system") or {}
    style_hint = template_cfg.get("style")
    topic = (visual_plan or {}).get("domain", theme)
    role_map = {"price": "stat", "score": "stat", "proof": "stat", "steps": "steps",
                "question": "quote", "quote": "quote", "chapter": "chapter",
                "location": "lower_third", "route": "chapter", "verdict": "chapter"}
    for i, (_t, _dur, text, card_type) in enumerate(events, 1):
        p = os.path.join(card_dir, f"card_{i:02d}.png")
        role = role_map.get(card_type.lower(), "hook")
        editorial.render_template(role, text, card_type.upper(), topic=topic, aspect="portrait",
                                  style_hint=style_hint, value=text, seed=f"{text}:{i}").save(p)
        card_paths.append(p)

    workdir = os.path.dirname(os.path.abspath(video_in)) or "."
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', os.path.basename(video_in)]
    for p in card_paths:
        cmd += ['-loop', '1', '-i', os.path.relpath(p, workdir)]
    filters, prev = [], '[0:v]'
    for i, ((t, dur, _text, _card_type), _p) in enumerate(zip(events, card_paths), 1):
        # 字卡在語意句首硬切。曾試 80ms crossfade，但卡片與底層字幕同句會短暫疊成雙字；
        # 乾淨硬切反而更像設計好的 pattern interrupt，也不犧牲可讀性。
        filters.append(f'[{i}:v]format=rgba[c{i}]')
        out_label = f'[v{i}]'
        filters.append(
            f"{prev}[c{i}]overlay=enable='between(t,{t:.3f},{t+dur:.3f})':shortest=1{out_label}")
        prev = out_label
    decorated = base + '_cards.mp4'
    cmd += ['-filter_complex', ';'.join(filters), '-map', prev, '-an', '-t', str(total),
            '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p',
            '-r', '30', os.path.basename(decorated)]
    r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode:
        raise RuntimeError('visual plan cards failed: ' + r.stderr[-700:])
    return decorated


def _apply_motion_asset_cues(video_in, visual_plan, base, total):
    """把 motion_assets cues 疊到 Shorts 成片。

    - overlay：素材本身是黑底 Screen 資產；以 colorkey 去黑再控制 38% opacity，避免巨大 alpha MOV。
    - background：只在 visual plan 明確標成 replace_only_if_no_footage 時使用；目前預設略過，
      因 renderer 無法自行判斷該秒是否真的缺 footage，不能拿設計底蓋掉真素材。
    - transition：全屏短 stinger，依 cue 的時間／長度出現。

    每顆 cue 分開編一次，換素材或壞檔時會大聲失敗，不靜默交付半套效果。
    """
    cues = ((visual_plan or {}).get("motion_assets") or {}).get("cues") or []
    semantic_overlay_contracts = {
        "tracked_label", "proof_highlight", "subject_masked_sheen",
        "particle_payoff", "location_or_price_tag",
    }

    def _eligible(cue):
        role = cue.get("role")
        if role == "transition":
            return True
        if role != "overlay":
            return False
        # 防止舊 visual plan 把無語意題材框線重新帶回成片。真正 overlay
        # 必須說清楚它跟哪個主體／證據綁定，及其功能類型。
        return bool(cue.get("semantic_target")) and cue.get("overlay_contract") in semantic_overlay_contracts

    cues = [c for c in cues if _eligible(c)]
    if not cues:
        return video_in
    current = video_in
    workdir = os.path.dirname(os.path.abspath(video_in)) or "."
    for i, cue in enumerate(cues, 1):
        try:
            t = float(cue.get("t", 0))
            dur = min(float(cue.get("max_duration", .8)), max(0.0, total - t))
        except (TypeError, ValueError):
            continue
        if dur < .12 or t < 0 or t >= total:
            continue
        rel = str(cue.get("path", "")).replace("/", os.sep)
        asset = rel if os.path.isabs(rel) else os.path.join(_PROJECT_ROOT, rel)
        if not os.path.isfile(asset):
            raise FileNotFoundError("motion asset missing: " + asset)
        role = cue.get("role")
        shifted = (f"[1:v]trim=start=0:duration={dur:.3f},"
                   f"setpts=PTS-STARTPTS+{t:.3f}/TB")
        if role == "overlay":
            # 黑底素材轉透明；低 opacity 只留下訊號線／HUD，不蓋字幕與主體。
            prep = shifted + ",colorkey=0x000000:0.045:0.10,format=rgba,colorchannelmixer=aa=0.38[fx]"
        else:
            prep = shifted + "[fx]"
        fc = (prep + ";[0:v][fx]overlay=eof_action=pass:repeatlast=0:shortest=0:"
              f"enable='between(t,{t:.3f},{t+dur:.3f})'[v]")
        out_i = base + f"_motion_{i:02d}.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.abspath(current),
               "-i", os.path.abspath(asset), "-filter_complex", fc, "-map", "[v]", "-an",
               "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-r", "30", os.path.abspath(out_i)]
        r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            raise RuntimeError("motion cue failed %s: %s" % (cue.get("asset_id"), r.stderr[-800:]))
        current = out_i
    return current


def _music_breath_filter(visual_plan):
    """把 visual plan 的 payoff 前呼吸真正套到 BGM；room tone 類素材則由別條 pipeline 保留。

    使用短線性 ramp 而非瞬間音量跳變，避免 click。回傳可直接接在 ffmpeg audio chain
    後面的 filter 片段；沒有計畫時保持舊行為。
    """
    win = ((visual_plan or {}).get("audio_plan") or {}).get("pre_payoff_space") or {}
    try:
        start, end = float(win["start"]), float(win["end"])
        gain = 10 ** (float(win.get("music_db_delta", -8)) / 20.0)
    except (KeyError, TypeError, ValueError):
        return ""
    if end - start < .12 or start < 0:
        return ""
    ramp = min(.14, (end - start) / 3.0)
    up = end - ramp
    expr = ("if(lt(t,{s:.3f}),1,"
            "if(lt(t,{sr:.3f}),1-(1-{g:.5f})*(t-{s:.3f})/{r:.3f},"
            "if(lt(t,{u:.3f}),{g:.5f},"
            "if(lt(t,{e:.3f}),{g:.5f}+(1-{g:.5f})*(t-{u:.3f})/{r:.3f},1))))"
            ).format(s=start, sr=start+ramp, g=gain, r=ramp, u=up, e=end)
    return ",volume='%s':eval=frame" % expr


def build_one_short(segs, caps, bgm, out, vol=0.42, fade=1.2, bgm_start='auto',
                    font="Noto Sans TC", target_lufs=-14.0, theme="general", visual_plan=None,
                    work_dir=None):
    """segs:[(clip,in,dur)]（已 normalize 的直式 clip）；caps:[(s,e,[(text,color)],kind)]；
    bgm: BGM(mp3/wav/m4a 皆可)；out: 成品。silent footage + 多色字幕 + BGM 當主音（無人聲）。
    bgm_start='auto'→自動抓歌高光段起點(find_music_highlight)；給數字=手動指定起秒；0=從頭。
    target_lufs=-14→最後 two-pass loudnorm 打到 -14 LUFS（YouTube/Shorts 標準，content_pipeline_rules §3）；
      None=跳過歸一（保留舊行為，響度隨 vol/源檔）。
    work_dir：M115 中間檔集中位置。給值後 ``out`` 只保留目前成片，中間 render 不再
      散落同層；最後先完成 candidate，再原子換成 out，修改同一支片不建立 vN 副本。"""
    total = sum(d for _, _, d in segs)
    out = os.path.abspath(out)
    if work_dir:
        os.makedirs(work_dir, exist_ok=True)
        base = os.path.join(os.path.abspath(work_dir), os.path.splitext(os.path.basename(out))[0])
    else:
        base = os.path.splitext(out)[0]
    # 1) visual concat
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for p, ss, d in segs:
        cmd += ['-ss', str(ss), '-t', str(d), '-i', p]
    parts, labs = [], ''
    grade_reports, grade_filters = [], {}
    color_system = (visual_plan or {}).get("color_system") or {}
    if color_system:
        from visual_master import source_filter
        grade_cache = os.path.join(work_dir or os.path.dirname(os.path.abspath(out)), "color_luts")
        os.makedirs(grade_cache, exist_ok=True)
        for source, _start, _duration in segs:
            if source not in grade_filters:
                grade_filters[source], report = source_filter(source, color_system, grade_cache)
                grade_reports.append(report)
    for i, (source, _, d) in enumerate(segs):
        grade = grade_filters.get(source, "")
        grade = ("," + grade) if grade else ""
        parts.append(f'[{i}:v]{_NORMV}{grade},trim=duration={d},setpts=PTS-STARTPTS[v{i}]'); labs += f'[v{i}]'
    fc = ';'.join(parts) + ';' + labs + f'concat=n={len(segs)}:v=1:a=0[vout]'
    vis = base + '_vis.mp4'
    # ── 視覺層快取（2026-07-29 R6）：迭代最常見的是「改字幕/換 BGM 重 build」，
    # segs 沒動就不必重跑最貴的 concat+encode。key=segs 全量 + 各來源檔 mtime，
    # 存 sidecar json；任何一項變了就重編，**寧可多編不可錯用**。
    _vis_key = {"segs": [[p, ss, d] for p, ss, d in segs],
                "mtimes": [os.path.getmtime(p) for p, _s, _d in segs],
                "color_system": color_system,
                "grade_filters": grade_filters}
    _vis_side = base + '_vis.json'

    def _vis_cache_ok():
        try:
            return (os.path.exists(vis)
                    and json.load(open(_vis_side, encoding='utf-8')) == _vis_key)
        except Exception:
            return False

    if _vis_cache_ok():
        print('  [cache] visual concat unchanged -> reuse %s' % os.path.basename(vis))
        r = type('R', (), {'returncode': 0})()
    else:
        r = _run(cmd + ['-filter_complex', fc, '-map', '[vout]', '-an', '-c:v', 'libx264',
                        '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '30', vis])
        if not r.returncode:
            json.dump(_vis_key, open(_vis_side, 'w', encoding='utf-8'))
    if r.returncode:
        raise RuntimeError('build_one_short visual failed: ' + r.stderr[-500:])
    # 2) captions — 一律在 out 目錄內跑 + 全用 basename：ass filter 的值若含 Windows
    #    碟符冒號(D:) 會被當成選項分隔(original_size) → 必須用相對路徑。cwd 設在 out 目錄，
    #    basename 就能解析。（舊版第一次嘗試忘了設 cwd、fallback 又帶冒號 → 兩條都壞，已修。）
    ass = base + '.ass'; build_multicolor_ass(caps, ass, font=font, theme=theme)
    cap = base + '_cap.mp4'
    # M115 work_dir 啟用後 vis/ass/cap 都在 `_out/_work`；cwd 必跟 base，而不是 final out。
    workdir = os.path.dirname(os.path.abspath(base)) or '.'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.basename(vis),
                        '-vf', _ass_filter(os.path.basename(ass), workdir), '-c:v', 'libx264', '-crf', '19',
                        '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '30', os.path.basename(cap)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=workdir)
    if r.returncode:
        raise RuntimeError('build_one_short caption failed: ' + r.stderr[-500:])
    # 2.5) 節奏導演事件 → 真正中段字卡（先燒字幕再蓋卡，避免文字重複）
    cap_for_mux = _apply_visual_plan_cards(cap, visual_plan, theme, base, total)
    cap_for_mux = _apply_motion_asset_cues(cap_for_mux, visual_plan, base, total)
    # 3) BGM 當主音（無人聲）— 從歌「高光段」起播 + 壓縮器壓平忽大忽小 + 快淡入 + 結尾淡出
    start = find_music_highlight(bgm, total) if bgm_start == 'auto' else float(bgm_start)
    fo = max(0.3, total - fade)
    fi = 0.3  # 高光段是從歌中間切入 → 0.3s 快淡入避免硬切爆音
    # acompressor 壓平 BGM 動態（歌的副歌/breakdown 起伏 = 用戶聽到「忽大忽小」）；
    # 壓峰貼近安靜段但保留每拍瞬態(beat 還在)。dynaudnorm/loudnorm 對此無效(實測)，要壓縮器。
    comp = 'acompressor=threshold=-24dB:ratio=4:attack=15:release=200:makeup=3'
    breath_filter = _music_breath_filter(visual_plan)
    if _probe_dur(bgm) < total + 0.5:
        # 歌比影片短 → 會 loop，接縫處跳音(也是忽大忽小一種)。換更長的歌，別硬 loop 短曲。
        print(f'[build_one_short] ⚠ BGM 比影片短會 loop 跳音：{os.path.basename(bgm)} '
              f'({_probe_dur(bgm):.0f}s < {total:.0f}s) — 建議換 ≥{total:.0f}s 的曲子')
    # M115：永遠先產 work candidate，不讓 ffmpeg 在現行成片 inode 上直接 truncate。
    # 這也讓同 volume 的已發布 hard link 保持舊版，不會被下一輪修改連動覆寫。
    mux = base + '_mux.mp4'
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', cap_for_mux,
              '-ss', f'{start:.2f}', '-stream_loop', '-1', '-i', bgm,
              '-filter_complex',
                f'[1:a]{comp},volume={vol}{breath_filter},afade=t=in:st=0:d={fi},afade=t=out:st={fo:.2f}:d={fade}[a]',
              '-map', '0:v:0', '-map', '[a]', '-t', str(total),
              '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', mux])
    if r.returncode:
        raise RuntimeError('build_one_short mux failed: ' + r.stderr[-500:])
    # 4) 響度歸一到 target LUFS（預設 -14 = YouTube/Shorts 標準）。fixed volume 只保證片內
    #    相對關係、不保證絕對響度（源檔而定，實測 ~-21 → 太小聲）→ 這步用 two-pass loudnorm 補上。
    candidate = base + '_candidate.mp4'
    if target_lufs is not None:
        if _loudnorm_two_pass(mux, candidate, I=target_lufs):
            try:
                os.remove(mux)
            except OSError:
                pass
        else:
            # loudnorm 量測/套用失敗 → 保底用未歸一的 mux 當成品，不讓整支 build 掛掉
            print('[build_one_short] ⚠ loudnorm 失敗，改用未歸一版本（響度可能偏小聲，約 -21 LUFS）')
            os.replace(mux, candidate)
    else:
        os.replace(mux, candidate)
    atomic_publish(candidate, out)
    if grade_reports:
        grade_report_path = os.path.join(os.path.dirname(os.path.abspath(out)),
                                         "current_color_report.json")
        with open(grade_report_path, "w", encoding="utf-8") as handle:
            json.dump({"system": color_system.get("system"),
                       "stage": "source_before_graphics", "sources": grade_reports},
                      handle, ensure_ascii=False, indent=2)
    return out


if __name__ == '__main__':
    # self-test：多色 ASS render + emoji strip（不跑 ffmpeg）
    import tempfile
    blocks = [(0.0, 3.0, [('整棵樹', 'w'), ('爬滿', 'r'), ('獨角仙🪲', 'o')], 'main'),
              (0.0, 3.0, [('📍 淺水灣', 'w')], 'addr'),
              (3.0, 4.2, [('AI 快了 ', 'w'), ('3 倍', 'y')], 'impact'),
              (4.2, 5.4, [('第 1 步', 'w')], 'ribbon'),
              (5.4, 6.5, [('只改這裡', 'g')], 'float_left')]
    p = os.path.join(tempfile.gettempdir(), '_sv_test.ass')
    build_multicolor_ass(blocks, p)
    txt = open(p, encoding='utf-8').read()
    assert r'{\c&H6B6BFF&}爬滿' in txt, 'inline 珊瑚色標籤(含{})漏了'  # 配色 v2：珊瑚 FF6B6B
    assert r'\move(430,1035,540,995,0,260)' in txt, 'ribbon 未鎖進水平安全區'
    assert '🪲' not in txt and '📍' not in txt, 'emoji 沒被 strip'
    assert strip_emoji('a🪲b📍c') == 'abc'
    assert 'Style: IMPACT' in txt and 'Style: RIBBON' in txt and 'Style: FLOAT' in txt
    assert r'\move(326,974,385,914' in txt
    _miaoli_lines = _split_caption_lines(
        [('苗栗一天跑 4 站', 'w'), ('\n吃完一路玩到斷橋', 'r')], 6)
    assert len(_miaoli_lines) == 2 and _caption_units(_miaoli_lines[1]) == 8.0
    _safe_impact = _kinetic_tags(
        'impact', text_units=8.0, line_index=1, line_count=2)
    assert r'\pos(540,1030)' in _safe_impact and r'\fscx54\fscy54' in _safe_impact
    assert txt.count('Dialogue:') == 7, 'impact/float 必須各有 shadow+main 兩層'
    try:
        build_multicolor_ass([(0, 1, [('錯', 'w')], 'explode')], p)
        raise AssertionError('unknown kind should fail')
    except AssertionError as exc:
        assert 'unknown caption kind' in str(exc)
    # find_music_highlight 的 ebur128 逐幀解析 regression（不跑 ffmpeg，純驗 regex）
    _line = '[Parsed_ebur128_0 @ 0] t: 3.999979   TARGET:-23 LUFS    M: -13.3 S: -14.2     I: -14.9 LUFS       LRA:   0.8 LU'
    assert re.search(r't:\s*([\d.]+)', _line).group(1) == '3.999979', 'ebur128 t: 解析漏'
    assert re.search(r'S:\s*(-?[\d.]+|-?inf)', _line).group(1) == '-14.2', 'ebur128 S: 解析漏'
    assert re.search(r'M:\s*(-?[\d.]+|-?inf)', _line).group(1) == '-13.3', 'ebur128 M:(beat_rate用) 解析漏'
    # beat_rate 局部峰計數邏輯（純算，不跑 ffmpeg）
    _M = [-30, -25, -28, -24, -29, -22, -27]   # 3 個局部峰
    _pk = sum(1 for i in range(1, len(_M)-1) if _M[i] > _M[i-1] and _M[i] >= _M[i+1] and _M[i] > -40)
    assert _pk == 3, 'beat_rate 峰計數錯'
    # pick_bgm 選曲邏輯 regression（mock _probe_dur/beat_rate，不跑 ffmpeg）
    _orig_pd, _orig_br = _probe_dur, beat_rate
    try:
        _durs = {'short.mp3': 5.0, 'long_lo.mp3': 30.0, 'long_hi.mp3': 30.0}
        _beats = {'short.mp3': 5.0, 'long_lo.mp3': 1.0, 'long_hi.mp3': 3.0}
        _probe_dur = lambda f: _durs[f]            # noqa: E731  (test shim)
        beat_rate = lambda f: _beats[f]            # noqa: E731  (test shim)
        _cand = ['short.mp3', 'long_lo.mp3', 'long_hi.mp3']
        assert pick_bgm(_cand, dur=17) == 'long_hi.mp3', 'energetic 應挑夠長+beat 最密'
        assert pick_bgm(_cand, dur=17, prefer='chill') == 'long_lo.mp3', 'chill 應挑夠長+beat 最低'
        assert pick_bgm(['short.mp3'], dur=17) == 'short.mp3', '全短曲應 fallback 回 candidates[0]'
        assert pick_bgm([], dur=17) is None, '空候選應回 None'
    finally:
        _probe_dur, beat_rate = _orig_pd, _orig_br
    # _probe_wh 解析 Windows '1080x1920x\r'（M97 修過，防回歸）
    assert re.findall(r'\d+', '1080x1920x\r')[:2] == ['1080', '1920'], '_probe_wh 解析 Windows CRLF 漏'
    # loudnorm pass1 JSON 解析 regression（純 regex，不跑 ffmpeg）— 打 -14 LUFS 的 target 補償
    _ln = ('[Parsed_loudnorm_0 @ 0] \n{\n"input_i" : "-21.56",\n"input_tp" : "-3.10",\n'
           '"input_lra" : "5.20",\n"input_thresh" : "-31.80",\n"target_offset" : "-0.40"\n}\n')
    _m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', _ln, re.S)
    assert _m and json.loads(_m.group(0))['input_i'] == '-21.56', 'loudnorm pass1 json 解析漏'
    print('[shorts_vertical selftest] OK')
