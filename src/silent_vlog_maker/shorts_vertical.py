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
import subprocess, os, re, shutil, json, sys, hashlib

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)

if __package__:
    from .shorts_visual_layers import (
        _PROJECT_ROOT,
        _visual_plan_card_events,
        _apply_visual_plan_cards,
        _apply_motion_asset_cues,
    )
else:
    from shorts_visual_layers import (
        _PROJECT_ROOT,
        _visual_plan_card_events,
        _apply_visual_plan_cards,
        _apply_motion_asset_cues,
    )
import art_direction as art
import editorial_templates as editorial
from storage_lifecycle import atomic_publish
from silent_vlog_maker.shorts_audio import loudnorm_two_pass as _loudnorm_two_pass


# ── encoding 顯式 utf-8（避免 Windows cp950 對中文路徑/輸出 crash；M96 bug fix）──
if __package__:
    from .shorts_music_selection import (
        _run,
        _probe_dur,
        find_music_highlight,
        beat_rate,
        _BGM_INDEX_CACHE,
        _indexed_bgm_meta,
        pick_bgm,
    )
else:
    from shorts_music_selection import (
        _run,
        _probe_dur,
        find_music_highlight,
        beat_rate,
        _BGM_INDEX_CACHE,
        _indexed_bgm_meta,
        pick_bgm,
    )


# ── M38: 去 emoji（NotoSansTC 無 emoji glyph → libass render 成豆腐框）──
if __package__:
    from .shorts_ass import (
        EMOJI_RE,
        strip_emoji,
        COLOR_VARIETY,
        COLOR_ALIAS,
        resolve_color,
        _MAIN_POS,
        _HOOK_POS,
        _SUB_POS,
        _ADDR_POS,
        _RENDER_KINDS,
        _ass_bgr,
        _header,
        _ts,
        _colored_body,
        _plain_body,
        _dialogue,
        _line_units,
        _caption_units,
        _split_caption_lines,
        _kinetic_tags,
        build_multicolor_ass,
    )
else:
    from shorts_ass import (
        EMOJI_RE,
        strip_emoji,
        COLOR_VARIETY,
        COLOR_ALIAS,
        resolve_color,
        _MAIN_POS,
        _HOOK_POS,
        _SUB_POS,
        _ADDR_POS,
        _RENDER_KINDS,
        _ass_bgr,
        _header,
        _ts,
        _colored_body,
        _plain_body,
        _dialogue,
        _line_units,
        _caption_units,
        _split_caption_lines,
        _kinetic_tags,
        build_multicolor_ass,
    )

# ── Profile-selected emphasis colors use valid ASS inline BGR tags ──

# ── Niche palette/font starter map; project profiles may override it ──
# PUBLIC_FIXTURE: use white-first captions; reserve accents for verified emphasis and key facts.
#   → palette 語意改為【候選強調色】不是【輪流全上】：每支 Short 取 palette[0] 當唯一主強調色
#     （全支同色，只給【重點】詞）、palette[1] 給【重要資訊】（數字/地名/價格），其餘一律白 'w'。
#     整行上色 / 逐重點輪播 4 色 = 🚫 禁止預設。交付前跑 shorts_captions.audit_color_ratio()
#     （有色字符 ≤35%、非白色 ≤2 色）沒過不交。
# PUBLIC_FIXTURE: aliases prevent full-name palette tokens from silently falling back; verify emitted ASS colors.
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
_CHIP_POS = r'{\an7\pos(82,420)}'     # 左上功能資訊卡；避平台頂部與右側 UI
# PUBLIC_FIXTURE: caption size is a configurable starter constrained by safe-area geometry.
# \an5+\pos(540,) 置中可用全寬 1080，最長 8 字 ×124≈1008px（±504 落在 36..1044）剛好不衝框；
# >130 的 8 字行會被裁掉。要更大就得把長句拆兩行（加 \N）。地址 58px（次要資訊不必最大）。

# font 可換（裝好/丟 assets/fonts 的繁中字體 family name；預設 Noto Sans TC）。
# ⚠️ M38：字體必須有繁中，否則中文豆腐框。niche 對應字體見 NICHE_FONTS。


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

if __package__:
    from .shorts_video_render import (
        _NORMV,
        _music_breath_filter,
        _render_short_visuals,
        _mix_short_audio,
    )
else:
    from shorts_video_render import (
        _NORMV,
        _music_breath_filter,
        _render_short_visuals,
        _mix_short_audio,
    )

# ── BGM 高光偵測：Shorts BGM 不從頭播（前奏無聊）→ 落在副歌/drop ──

# ── 音效自動篩選：量 beat 挑動感曲 + 夠長不 loop ──


# ── 最終響度歸一化：two-pass loudnorm 精準命中 target LUFS（YouTube/Shorts 標準 -14）──


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
    vis, grade_reports, color_system = _render_short_visuals(segs, visual_plan, base, work_dir, out)
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
    mux = _mix_short_audio(base, bgm, bgm_start, cap_for_mux, fade, total, visual_plan, vol)
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
    # PUBLIC_FIXTURE: synthetic caption used only for safe-area regression.
    _demo_route_lines = _split_caption_lines(
        [('示範城一天跑 4 站', 'w'), ('\n一路散步走到河畔', 'r')], 6)
    assert len(_demo_route_lines) == 2 and _caption_units(_demo_route_lines[1]) == 8.0
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
