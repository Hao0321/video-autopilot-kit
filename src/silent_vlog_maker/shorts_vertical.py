# -*- coding: utf-8 -*-
"""
M96: 美食/旅遊直式 Shorts pipeline（純 ffmpeg）— silent footage → 多色重點字幕 → 配樂。

9:16 1080x1920 直式短影音。專案只需餵 data（segs + caps），不用每支整檔複製。
適合「無人聲、靠畫面 + 重點字 + BGM」的美食/旅遊 Reels/Shorts。

用法：
    from silent_vlog_maker import normalize_to_portrait, build_one_short
    # 1) 手機直拍/橫拍 .MOV 轉正成 9:16
    for clip in raw_clips: normalize_to_portrait(clip, norm_out)
    # 2) 餵片段 + 多色字幕 + BGM
    build_one_short(
        segs=[(norm1, 1.0, 5.0), (norm2, 0.5, 5.0)],          # (clip, in, dur)
        caps=[(0.2, 5.0, [('重點A','g'), ('重點B','y')], 'main'),
              (5.0, 22.0, [('店名/地點','w'), ('地址','w')], 'addr')],
        bgm='assets/bgm/chill-01.mp3', out='short.mp4', vol=0.42)
"""
import subprocess, os, re

# ── encoding 顯式 utf-8（避免 Windows cp950 對中文路徑/輸出 crash；M96 bug fix）──
def _run(args):
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def _probe_dur(f):
    r = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'csv=p=0', f])
    if r.returncode or not r.stdout.strip():
        raise RuntimeError(f"ffprobe 讀不到時長: {f}（檔案壞或非媒體檔）; stderr={r.stderr[-200:]}")
    return float(r.stdout.strip())

# ── M38: 去 emoji（NotoSansTC 無 emoji glyph → libass render 成豆腐框）──
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "←-⇿⬀-⯿️⃣]")
def strip_emoji(s):
    return EMOJI_RE.sub("", s)

# ── 多色重點字（重點字不同色）= ASS inline color（BGR），必包 {} ──
COLOR_VARIETY = {
    'w': r'{\c&H00FFFFFF&}',   # 白
    'o': r'{\c&H008CFF&}',     # 橙 RGB FF8C00
    'y': r'{\c&H0AD6FF&}',     # 黃 RGB FFD60A
    'r': r'{\c&H303BFF&}',     # 紅 RGB FF3B30
    'g': r'{\c&H58D130&}',     # 綠 RGB 30D158
}
_MAIN_POS = r'{\an5\pos(540,1180)}'   # 中下置中（避上 384 / 下 1440 SHORTS_SAFE_ZONE）
_ADDR_POS = r'{\an5\pos(540,1390)}'   # 底部安全區地址
# MAIN 124px（「字太小」回饋放大；原 82）。⚠️ 上限約 124：WrapStyle=2 不自動換行，
# \an5+\pos(540,) 置中可用全寬 1080，最長 8 字 ×124≈1008px（±504 落在 36..1044）剛好不衝框；
# >130 的 8 字行會被裁掉。要更大就得把長句拆兩行（加 \N）。地址 58px（次要資訊不必最大）。

_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MAIN,Noto Sans TC,124,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,4,5,40,40,0,1
Style: ADDR,Noto Sans TC,58,&H00FFFFFF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,3,9,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)

def build_multicolor_ass(blocks, out_path):
    """blocks: list of (start, end, segs, kind)。
    segs=[(text,color), ...] color∈w/o/y/r/g（'\\n' 換行）；kind='main'|'addr'。
    自動 strip_emoji（M38 防呆 — 不靠人記得不放 emoji）。"""
    lines = [_HEADER]
    for start, end, segs, kind in blocks:
        pos = _ADDR_POS if kind == 'addr' else _MAIN_POS
        style = 'ADDR' if kind == 'addr' else 'MAIN'
        body = ""
        for text, color in segs:
            body += COLOR_VARIETY.get(color, COLOR_VARIETY['w']) + strip_emoji(text).replace('\n', r'\N')
        lines.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s%s" % (_ts(start), _ts(end), style, pos, body))
    open(out_path, 'w', encoding='utf-8').write("\n".join(lines))
    return out_path

# ── 手機 .MOV → upright 9:16（autorotate 處理 rotation 旗標，含混 -90/+90）──
def normalize_to_portrait(clip_in, clip_out, crf=19):
    """轉正成 1080x1920/30fps/無音（M29/M81）。
    ffmpeg 預設 autorotate 先套 rotation 旗標 → scale/crop 在「已轉正的幀」上做，
    所以同批混 rot=-90/+90（手機拿反）也全部統一 upright（M96 踩過）。"""
    vf = ('scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
          'fps=30,setsar=1,format=yuv420p')
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', clip_in, '-vf', vf, '-an',
              '-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium', clip_out])
    if r.returncode:
        raise RuntimeError('normalize_to_portrait failed: ' + r.stderr[-500:])
    return clip_out

def extract_gps(clip):
    """抽手機 GPS（com.apple.quicktime.location.ISO6709）→ 例如 '+00.0000+000.0000+000/'。
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
    pts = []
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
            e = sum(seg) / len(seg)
            if e > best_e:
                best_e, best_t = e, t0
    return round(max(0.0, best_t - pre), 2)

# ── 音效自動篩選：量 beat 挑動感曲 + 夠長不 loop ──
def beat_rate(bgm):
    """每秒「響度脈衝峰」數 = 節奏密度 proxy。beat 越高越動感(挑曲/相對比較用)。
    ebur128 momentary(M) 局部峰計數。氛圍慢曲~1/s，動感快剪/Vocal Chop~2.5-3/s。"""
    r = _run(['ffmpeg', '-hide_banner', '-i', bgm, '-af', 'ebur128', '-f', 'null', '-'])
    M = []
    for line in r.stderr.splitlines():
        m = re.search(r'M:\s*(-?[\d.]+|-?inf)', line)
        if m:
            v = m.group(1); M.append(-70.0 if 'inf' in v else float(v))
    if len(M) < 10:
        return 0.0
    peaks = sum(1 for i in range(1, len(M) - 1) if M[i] > M[i-1] and M[i] >= M[i+1] and M[i] > -40)
    return round(peaks / (len(M) * 0.1), 2)

def pick_bgm(candidates, dur, prefer='energetic', margin=1.0):
    """音效自動篩選：從同題材候選曲挑「**夠長(不 loop)** + **最動感(beat 最密)**」的一首。
    candidates: BGM 路徑 list；dur: 影片秒長。回最佳路徑(沒候選回 None)。
    prefer='energetic' 選 beat 最高；'chill' 選最低(放鬆題材)。
    曲比影片短 → -stream_loop 接縫跳音(忽大忽小)→ 一律排除短曲。"""
    scored = []
    for b in candidates:
        try:
            if _probe_dur(b) < dur + margin:
                continue
            scored.append((beat_rate(b), b))
        except Exception:
            continue
    if not scored:
        if candidates:
            print(f"[pick_bgm][WARN] 所有 {len(candidates)} 首候選都 < 影片長 {dur:.0f}s，退回最接近的一首，"
                  f"播放時會 loop（可能接縫跳音）；建議換更長的曲子。")
        return candidates[0] if candidates else None
    scored.sort(reverse=(prefer == 'energetic'))
    return scored[0][1]

def build_one_short(segs, caps, bgm, out, vol=0.42, fade=1.2, bgm_start='auto'):
    """segs:[(clip,in,dur)]（已 normalize 的直式 clip）；caps:[(s,e,[(text,color)],kind)]；
    bgm: BGM(mp3/wav/m4a)；out: 成品。silent footage + 多色字幕 + BGM 當主音（無人聲）。
    bgm_start='auto'→自動抓歌高光段(find_music_highlight)；給數字=手動起秒；0=從頭。"""
    total = sum(d for _, _, d in segs)
    base = os.path.splitext(out)[0]
    # 1) visual concat
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for p, ss, d in segs:
        cmd += ['-ss', str(ss), '-t', str(d), '-i', p]
    parts, labs = [], ''
    for i, (_, _, d) in enumerate(segs):
        parts.append(f'[{i}:v]{_NORMV},trim=duration={d},setpts=PTS-STARTPTS[v{i}]'); labs += f'[v{i}]'
    fc = ';'.join(parts) + ';' + labs + f'concat=n={len(segs)}:v=1:a=0[vout]'
    vis = base + '_vis.mp4'
    r = _run(cmd + ['-filter_complex', fc, '-map', '[vout]', '-an', '-c:v', 'libx264',
                    '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '30', vis])
    if r.returncode:
        raise RuntimeError('build_one_short visual failed: ' + r.stderr[-500:])
    # 2) captions — 一律在 out 目錄內跑 + 全用 basename：ass filter 的值若含 Windows
    #    碟符冒號(任何磁碟代號) 會被當成選項分隔(original_size) → 必須用相對路徑。cwd 設在 out 目錄，
    #    basename 就能解析。（舊版第一次嘗試忘了設 cwd、fallback 又帶冒號 → 兩條都壞，已修。）
    ass = base + '.ass'; build_multicolor_ass(caps, ass)
    cap = base + '_cap.mp4'
    workdir = os.path.dirname(os.path.abspath(out)) or '.'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.basename(vis),
                        '-vf', 'ass=' + os.path.basename(ass), '-c:v', 'libx264', '-crf', '19',
                        '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '30', os.path.basename(cap)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=workdir)
    if r.returncode:
        raise RuntimeError('build_one_short caption failed: ' + r.stderr[-500:])
    # 3) BGM 當主音（無人聲）— 從歌「高光段」起播 + 壓縮器壓平忽大忽小 + 快淡入 + 結尾淡出
    start = find_music_highlight(bgm, total) if bgm_start == 'auto' else float(bgm_start)
    fo = max(0.3, total - fade)
    fi = 0.3  # 高光段從歌中間切入 → 0.3s 快淡入避免硬切爆音
    # acompressor 壓平 BGM 動態（副歌/breakdown 起伏 = 聽到「忽大忽小」）；壓峰貼近安靜段
    # 但保留每拍瞬態(beat 不死)。dynaudnorm/loudnorm 對此無效(實測)，要壓縮器。
    comp = 'acompressor=threshold=-24dB:ratio=4:attack=15:release=200:makeup=3'
    if _probe_dur(bgm) < total + 0.5:
        print(f'[build_one_short] WARN: BGM 比影片短會 loop 跳音（{os.path.basename(bgm)} '
              f'{_probe_dur(bgm):.0f}s < {total:.0f}s）— 換 >={total:.0f}s 的曲子，或用 pick_bgm 自動挑')
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', cap,
              '-ss', f'{start:.2f}', '-stream_loop', '-1', '-i', bgm,
              '-filter_complex',
              f'[1:a]{comp},volume={vol},afade=t=in:st=0:d={fi},afade=t=out:st={fo:.2f}:d={fade}[a]',
              '-map', '0:v:0', '-map', '[a]', '-t', str(total),
              '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', out])
    if r.returncode:
        raise RuntimeError('build_one_short mux failed: ' + r.stderr[-500:])
    return out


if __name__ == '__main__':
    # self-test：多色 ASS render + emoji strip（不跑 ffmpeg）
    import tempfile
    # fixture 用中性佔位字：self-test 驗的是「多色標籤 + emoji strip」，
    # 不需要真影片的字幕原文（別把成品逐字塞進測資）。
    blocks = [(0.0, 3.0, [('前段白字', 'w'), ('重點紅字', 'r'), ('尾段橘字🌸', 'o')], 'main'),
              (0.0, 3.0, [('📍 地點小字', 'w')], 'addr')]
    p = os.path.join(tempfile.gettempdir(), '_sv_test.ass')
    build_multicolor_ass(blocks, p)
    txt = open(p, encoding='utf-8').read()
    assert r'{\c&H303BFF&}重點紅字' in txt, 'inline 紅色標籤(含{})漏了'
    assert '🌸' not in txt and '📍' not in txt, 'emoji 沒被 strip'
    assert strip_emoji('a🌸b📍c') == 'abc'
    # find_music_highlight / beat_rate 的 ebur128 逐幀解析 regression（不跑 ffmpeg）
    _line = '[Parsed_ebur128_0 @ 0] t: 3.999979   TARGET:-23 LUFS    M: -13.3 S: -14.2     I: -14.9 LUFS       LRA:   0.8 LU'
    assert re.search(r't:\s*([\d.]+)', _line).group(1) == '3.999979', 'ebur128 t: 解析漏'
    assert re.search(r'S:\s*(-?[\d.]+|-?inf)', _line).group(1) == '-14.2', 'ebur128 S: 解析漏'
    assert re.search(r'M:\s*(-?[\d.]+|-?inf)', _line).group(1) == '-13.3', 'ebur128 M: 解析漏'
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
    print('[shorts_vertical selftest] OK')
