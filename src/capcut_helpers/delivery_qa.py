# -*- coding: utf-8 -*-
"""
交付前 QA + 圖片入片 helpers —— 教學長片 ship-QA 固化（canon M91-M95 的可執行版）。

每支影片 export 後、報告用戶前，跑 `final_delivery_qa(video, voice)`：
  - M93 頻閃：blackdetect 抓「黑↔亮」反覆 = 頻閃素材
  - M95 句間死空檔：silencedetect 抓 >1.5s 的句間停頓
  - 接觸表：人工逐格看 chrome(M91)/圖片排版(M92)/真實 artifact(M94)/字幕(M68)
還有：
  - still_blurfill()  M92 非滿版圖 → 模糊背景填滿 + 靜止（零抖動）
  - detect_long_pauses() / trim_dead_air_ranges() / remap_time()  M95 死空檔三軌同步剪
v0.7.0 新 gates：
  - check_caption_sync()       M105 — whisper 抽驗「字幕時間 = 真實語音」
  - render_fullframe_sheets()  M104 — 全片 dense 全幀掃描圖（找中央浮窗/錄影軟體 UI）
  - check_scene_pacing()       留存 gate — cut 密度分段上限（開頭最嚴）
  - check_dead_air()           留存 gate — 畫面凍結 ∩ 音訊靜音 = 真死空檔（M95 機械化）
v0.9.x 新 gates：
  - check_caption_linebreaks() M108 — 字幕斷句品質（尾懸掛/頭懸掛/腰斬/超長）
  - check_bgm_coverage()       M79  — 畫面還在播，音樂就不能停（旁白間隙+片尾抽樣量 RMS）
  - final_delivery_qa(profile=) 防假綠 — profile 一設，缺 voice/ass/sheets_dir 直接 BLOCKED
"""
import subprocess, re, os

def _run(args):
    # encoding utf-8 + errors=replace：避免 Windows cp950 對中文路徑/輸出 crash
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def _probe_dur(media):
    r = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'csv=p=0', media])
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"ffprobe 讀不到時長: {media}（檔案壞或非媒體檔）; stderr={r.stderr[-200:]}")
    return float(r.stdout.strip())

# ---------------------------------------------------------------- M92 圖片入片
def still_blurfill(img, out, dur, sigma=26, dim=0.12, fg_h=1040):
    """M92：非滿版圖/截圖 → clip。同圖放大模糊+稍暗當底，原圖置中清晰疊上。
    靜止（無 zoompan）＝零抖動。禁死黑邊。"""
    vf = (f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
          f"gblur=sigma={sigma},eq=brightness=-{dim}[bg];"
          f"[0:v]scale=1920:{fg_h}:force_original_aspect_ratio=decrease[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[o]")
    r = _run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', '30',
              '-t', dur, '-i', img, '-filter_complex', vf, '-map', '[o]', '-an',
              '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
              '-pix_fmt', 'yuv420p', '-r', '30', '-t', dur, out])
    if r.returncode:
        raise RuntimeError('still_blurfill failed: ' + r.stderr[-600:])
    return out

# ---------------------------------------------------------------- M95 死空檔
def detect_long_pauses(audio, min_sec=1.5, noise_db=-30, ignore_edge=1.2):
    """M95：silencedetect → 句間死空檔 [(start, end, dur), ...]，只回 > min_sec 的。
    對「乾淨人聲檔」跑（不要對 mix 完的，BGM 會蓋過靜音）。
    ignore_edge：忽略開頭/結尾的 lead-in / trailing 靜音（那是 intro/尾，不是句間死空檔）。"""
    total = _probe_dur(audio)
    r = _run(['ffmpeg', '-i', audio, '-af',
              f'silencedetect=noise={noise_db}dB:d=0.5', '-f', 'null', '-'])
    out, cur = [], None
    for m in re.finditer(
            r'silence_(start|end): ([\d.eE+-]+)(?: \| silence_duration: ([\d.eE+-]+))?', r.stderr):
        kind, val, dur = m.group(1), float(m.group(2)), m.group(3)
        if kind == 'start':
            cur = val
        elif kind == 'end' and cur is not None and dur and float(dur) > min_sec:
            # 跳過開頭 lead-in（start≈0）與結尾 trailing（end≈總長）
            if cur > ignore_edge and (total - val) > ignore_edge:
                out.append((cur, val, float(dur)))
            cur = None
    return out

def trim_dead_air_ranges(pauses, keep=0.5):
    """死空檔 → 要砍掉的區間 [(cut_start, cut_end), ...]（每個停頓留 keep 秒呼吸）。"""
    return [(s + keep, e) for (s, e, d) in pauses if (e - s) > keep]

def build_keep_ranges(cuts, end):
    ks, prev = [], 0.0
    for cs, ce in cuts:
        ks.append((prev, cs)); prev = ce
    ks.append((prev, end))
    return ks

def remap_time(t, cuts):
    """把原時間軸的 t 映射到「砍掉 cuts 後」的新時間（字幕/標記用同一函數平移）。"""
    nt = t
    for cs, ce in cuts:
        if t >= ce:
            nt -= (ce - cs)
        elif t > cs:
            nt -= (t - cs)
    return nt

def cut_audio_segments(audio_in, audio_out, cuts, end=None):
    """M95 鐵則：移除音訊區段用 atrim+concat（**不要 aselect**，aselect 對音訊常不真的丟 frame）。"""
    if end is None:
        end = _probe_dur(audio_in)
    keep = build_keep_ranges(cuts, end)
    fc = ''.join(f'[0:a]atrim={a}:{b},asetpts=N/SR/TB[v{i}];'
                 for i, (a, b) in enumerate(keep))
    fc += ''.join(f'[v{i}]' for i in range(len(keep))) + f'concat=n={len(keep)}:v=0:a=1[cv]'
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', audio_in,
              '-filter_complex', fc, '-map', '[cv]', audio_out])
    if r.returncode:
        raise RuntimeError('cut_audio_segments failed: ' + r.stderr[-600:])
    return audio_out

def cut_video_segments(video_in, video_out, cuts, end=None):
    """移除影像區段用 select+setpts（video 版可靠）。與 cut_audio_segments 用同一組 cuts → 同步。"""
    if end is None:
        end = _probe_dur(video_in)
    keep = build_keep_ranges(cuts, end)
    expr = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in keep)
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', video_in,
              '-vf', f"select='{expr}',setpts=N/FRAME_RATE/TB", '-an',
              '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
              '-pix_fmt', 'yuv420p', '-r', '30', video_out])
    if r.returncode:
        raise RuntimeError('cut_video_segments failed: ' + r.stderr[-600:])
    return video_out

# ---------------------------------------------------------------- M93 頻閃
def detect_flash(video, pic_th=0.90, d=0.05):
    """M93：blackdetect → [(start, end, dur), ...]。同區段反覆/短段 = 頻閃素材或亮度落差。"""
    r = _run(['ffmpeg', '-i', video, '-vf',
              f'blackdetect=d={d}:pic_th={pic_th}', '-an', '-f', 'null', '-'])
    return [(float(m.group(1)), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(
                r'black_start:([\d.eE+-]+) black_end:([\d.eE+-]+) black_duration:([\d.eE+-]+)', r.stderr)]


def classify_flash(flashes, cluster_gap=8.0, micro=0.12):
    """M93 v2（誤報修正）：把【真頻閃】和【刻意的 dip-to-black 轉場】分開。

    blackdetect 不知道「為什麼黑」——節奏點的 fade-to-black 轉場和真正傷眼的頻閃
    在它眼裡長得一模一樣。判斷要看【時間分布】：

    - 真頻閃 → 擋：兩段 black 的間隔 < cluster_gap（密集交替），
      或任一段 < micro 秒（單幀等級的爆閃，PSE 風險）。
    - 孤立 dip-to-black → 放行但列出：彼此間隔 >= cluster_gap 秒，
      這是剪輯者在段落邊界刻意放的 fade，屬設計不是瑕疵；仍回傳 transitions 供人眼確認。

    舊邏輯是「>=2 段 or 任一段 <1s 就 flag」——那等於【每一個 fade-to-black 轉場都判頻閃】。
    一支只有六個段落 fade（彼此隔十幾秒）的正常影片會被判 flash_flag=True
    → deliver_ok=False → 使用者永遠 BLOCKED 又看不出原因，最後學會忽略整道 gate（狼來了）。
    誤報比漏報更貴：一個永遠紅的 gate 等於沒有 gate。

    回傳 {'flag': bool, 'note': str, 'transitions': [...]}；flag=True 時 transitions 留空
    （那些不是轉場，是要修的頻閃）。"""
    flashes = sorted(flashes)
    micro_hits = [f for f in flashes if f[2] < micro]
    clustered = [(a, b) for a, b in zip(flashes, flashes[1:]) if b[0] - a[1] < cluster_gap]
    bad = bool(micro_hits or clustered)
    if bad:
        note = f"真頻閃：micro(<{micro}s)={micro_hits} clustered(<{cluster_gap}s)={clustered}"
    elif flashes:
        note = f"{len(flashes)} 個孤立 dip-to-black（節奏點 fade 轉場，間隔>={cluster_gap}s）— 可接受"
    else:
        note = "none"
    return {"flag": bad, "note": note, "transitions": [] if bad else flashes}

# ------------------------------------------------------------ M92 死黑邊（letterbox）
def _probe_wh(video):
    r = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
              'stream=width,height', '-of', 'csv=p=0:s=x', video])
    # 用 regex 抓數字（不 split('x')）：ffprobe 在 Windows 會吐尾端多餘分隔符 + CRLF
    # 例如 "1080x1920x\r" → split 會多一段空字串炸掉。findall 取前兩個數字就穩。
    nums = [int(x) for x in re.findall(r'\d+', r.stdout)]
    return nums[0], nums[1]

def detect_dead_borders(video, tol=4, frames=300):
    """M92：cropdetect 抓「非滿版留死黑邊」(letterbox/pillarbox — 非滿版圖沒做模糊填底就會這樣)。
    回 dict：{'full':(W,H), 'content':(w,h,x,y) or None, 'border_flag':bool, 'note':...}。
    border_flag=True 代表內容沒鋪滿、四周有黑邊 → 該段該用 still_blurfill 模糊填底。"""
    W, H = _probe_wh(video)
    r = _run(['ffmpeg', '-i', video, '-vf', 'cropdetect=24:2:0', '-frames:v', str(frames),
              '-an', '-f', 'null', '-'])
    crops = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', r.stderr)
    if not crops:
        return {'full': (W, H), 'content': None, 'border_flag': False, 'note': 'cropdetect 無輸出'}
    cw, ch, cx, cy = (int(v) for v in crops[-1])  # 收斂後的最終建議
    flag = (W - cw) > tol or (H - ch) > tol
    return {'full': (W, H), 'content': (cw, ch, cx, cy), 'border_flag': flag,
            'note': f'死黑邊 {W-cw}px(寬)/{H-ch}px(高) → 該段需 still_blurfill 模糊填底' if flag else '滿版無黑邊'}

# ---------------------------------------------------------------- 接觸表
def contact_sheet(video, out_png, every=6.0, cols=6, cell_w=440, cell_h=248):
    """整片接觸表（人工逐格看 chrome/對位/排版）。"""
    dur = _probe_dur(video)
    n = max(1, int(dur // every))
    tmp = os.path.dirname(str(out_png)) or '.'
    pngs = []
    for i in range(n):
        p = os.path.join(tmp, f'_cs_{i:03d}.png')
        _run(['ffmpeg', '-v', 'error', '-ss', i * every, '-i', video, '-frames:v', '1',
              '-vf', f'scale={cell_w}:{cell_h}:force_original_aspect_ratio=decrease,'
                     f'pad={cell_w}:{cell_h}:(ow-iw)/2:(oh-ih)/2:black', '-y', p])
        pngs.append(p)
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for p in pngs:
        cmd += ['-i', p]
    parts = ''.join(f'[{i}:v]' for i in range(len(pngs)))
    lay = '|'.join(f'{(i % cols) * cell_w}_{(i // cols) * cell_h}' for i in range(len(pngs)))
    cmd += ['-filter_complex', parts + f'xstack=inputs={len(pngs)}:layout={lay}:fill=black', out_png]
    _run(cmd)
    for p in pngs:
        try:
            os.remove(p)
        except OSError:
            pass
    return out_png

# ---------------------------------------------------------------- 🎚️ 音訊 QA gates (M103)
# 把教學長片音訊失敗模式固化成自動 gate：
#   LUFS 偏離 / outro BGM 硬切 / A/V 尾長不符(-shortest 砍音訊) / 字幕溢出片長。
def _loudnorm_measure(media):
    """loudnorm 量測模式抓 input_i(LUFS) / input_tp(dBTP)。回 (lufs, tp)，抓不到回 (None,None)。"""
    r = _run(['ffmpeg', '-hide_banner', '-i', media,
              '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'])
    mi = re.search(r'"input_i"\s*:\s*"([-\d.]+)"', r.stderr)
    mt = re.search(r'"input_tp"\s*:\s*"([-\d.]+)"', r.stderr)
    return (float(mi.group(1)) if mi else None, float(mt.group(1)) if mt else None)


def check_loudness(video, target_i=-14.0, tol=1.0, max_tp=-1.0):
    """M103 gate：成片響度落在 target±tol LUFS 且 true-peak ≤ max_tp dBTP。
    把『只 print 不 assert』升級成自動 flag → 偏離不 green 不交付。"""
    lufs, tp = _loudnorm_measure(video)
    ok = (lufs is not None and abs(lufs - target_i) <= tol
          and tp is not None and tp <= max_tp + 0.3)   # TP 留 0.3dB 量測/loudnorm 邊界誤差
    return {'lufs': lufs, 'tp': tp, 'target': target_i, 'ok': bool(ok),
            'note': f'LUFS {lufs} (要 {target_i}+-{tol}) / TP {tp} (要 <={max_tp})'}


def check_tail_silence(video, tail=0.25, max_rms_db=-40.0):
    """M103 gate：成片尾段已淡到近靜音 (各聲道 RMS < max_rms_db)。
    防 -shortest 砍 BGM 在 ~-23dB 硬切 = outro click。"""
    r = _run(['ffmpeg', '-hide_banner', '-sseof', f'-{tail}', '-i', video,
              '-af', 'astats=metadata=1:reset=1', '-f', 'null', '-'])
    rms = [float(m.group(1)) for m in re.finditer(r'RMS level dB:\s*([-\d.]+)', r.stderr)]
    tail_rms = max(rms) if rms else 0.0   # 取最大聲道 = 最保守
    return {'tail_rms_db': round(tail_rms, 1), 'max_allowed': max_rms_db, 'ok': tail_rms < max_rms_db,
            'note': f'尾 {tail}s RMS {round(tail_rms,1)}dB (要 <{max_rms_db}=已淡到靜音)'}


def _stream_dur(media, kind):
    r = _run(['ffprobe', '-v', 'error', '-select_streams', f'{kind}:0',
              '-show_entries', 'stream=duration', '-of', 'csv=p=0', media])
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return None


def check_av_sync(video, tol=0.4):
    """M103 gate：audio 與 video stream 時長一致 (|Δ|<tol)。
    防 -shortest 砍掉較長軌 = 靜默資料遺失，AP12 只驗 mux 前、碰不到成片。"""
    a, v = _stream_dur(video, 'a'), _stream_dur(video, 'v')
    diff = abs(a - v) if (a and v) else None
    return {'audio_dur': a, 'video_dur': v, 'diff': round(diff, 3) if diff is not None else None,
            'ok': diff is not None and diff < tol,
            'note': f'A {a} vs V {v} delta {round(diff,3) if diff is not None else "?"}s (要 <{tol})'}


def _ass_last_end(ass_path):
    """parse ASS Dialogue 行的 End 時間戳 (H:MM:SS.cc) → 最大 end 秒。"""
    mx = 0.0
    with open(ass_path, encoding='utf-8') as fh:
        for ln in fh:
            if not ln.startswith('Dialogue:'):
                continue
            parts = ln.split(',')
            if len(parts) >= 3:
                m = re.match(r'(\d+):(\d\d):(\d\d(?:\.\d+)?)', parts[2].strip())
                if m:
                    mx = max(mx, int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)))
    return mx


def check_captions_within_dur(ass_path, video_dur, slack=0.1):
    """M103 gate：字幕末端 end 不溢出影片長 (max_end <= video_dur+slack)。"""
    last = _ass_last_end(ass_path)
    return {'last_caption_end': round(last, 2), 'video_dur': round(video_dur, 2),
            'ok': last <= video_dur + slack,
            'note': f'末字幕 {round(last,2)}s vs 片長 {round(video_dur,2)}s (要 <=+{slack})'}


# ---------------------------------------------------------------- 🎬 留存機械 gate
# 兩條可機械驗的留存規則：cut 密度上限（開頭密、後段可放寬）+ 死空檔（畫面凍結∩音訊靜音）。
def _pick_limit(t, windows):
    """時間 t 落在哪個 window（[start,end)，end=None=到片尾）→ 回該段 gap 上限秒數。"""
    for a, b, lim in windows:
        if t >= a and (b is None or t < b):
            return lim
    return windows[-1][2]

def _pacing_violations(points, windows):
    """相鄰視覺變化點 → 超過該段上限的 gap 清單（用區間中點判落在哪段）。純函數可測。"""
    out = []
    for a, b in zip(points, points[1:]):
        gap = b - a
        lim = _pick_limit((a + b) / 2.0, windows)
        if gap > lim:
            out.append({'start': round(a, 2), 'end': round(b, 2),
                        'gap': round(gap, 2), 'limit': lim})
    return out

def check_scene_pacing(video, windows=((0, 30, 7.0), (30, 180, 15.0), (180, None, 30.0)),
                       scene_th=0.2):
    """留存 gate：視覺變化(cut/鏡頭切換)間距不得超過分段上限（前 30s 最嚴 7s、
    30-180s 15s、之後 30s）。scene detect 用 ffprobe lavfi movie+select。
    回 {ok, violations, n_cuts, note}；ffprobe 不存在/失敗 → ok=None（skip 不擋）。"""
    try:
        dur = _probe_dur(video)
        # lavfi 路徑跳脫（Windows）：'\' → '/'、':' → '\\:'（graph 層 + movie 層各吃一層）
        esc = str(video).replace('\\', '/').replace(':', '\\\\:')
        r = _run(['ffprobe', '-v', 'error', '-f', 'lavfi',
                  f'movie={esc},select=gt(scene\\,{scene_th})',
                  '-show_entries', 'frame=pts_time', '-of', 'csv=p=0'])
    except Exception as e:
        return {'ok': None, 'violations': [], 'n_cuts': 0,
                'note': f'ffprobe unavailable ({e}) -> scene pacing skipped'}
    if r.returncode != 0:
        return {'ok': None, 'violations': [], 'n_cuts': 0,
                'note': 'ffprobe scene detect failed -> skipped; stderr=' + (r.stderr or '')[-200:]}
    pts = []
    for ln in (r.stdout or '').splitlines():
        ln = ln.strip().strip(',')
        if not ln:
            continue
        try:
            pts.append(float(ln))
        except ValueError:
            pass
    points = sorted(set([0.0] + pts + [dur]))
    violations = _pacing_violations(points, windows)
    ok = not violations
    return {'ok': ok, 'violations': violations, 'n_cuts': len(pts),
            'note': f'{len(pts)} cuts; ' + ('pacing ok' if ok
                    else f'{len(violations)} gap(s) over window limit')}

def _parse_freeze_silence(stderr_text, end=None):
    """ffmpeg stderr → (freezes, silences) 兩組 [(start,end)]。start/end 依序配對。
    end 給了 → 未閉合的 start 封在 end（freezedetect 凍到片尾【不會】吐 freeze_end，
    片尾凍住+靜音正是最典型死空檔）；end=None → 丟棄。純函數可測。"""
    def _pairs(prefix):
        out, cur = [], None
        for m in re.finditer(prefix + r'_(start|end): ([\d.eE+-]+)', stderr_text):
            kind, val = m.group(1), float(m.group(2))
            if kind == 'start':
                cur = val
            elif kind == 'end' and cur is not None:
                out.append((cur, val)); cur = None
        if cur is not None and end is not None and end > cur:
            out.append((cur, float(end)))
        return out
    return _pairs('freeze'), _pairs('silence')

def _intersect_ranges(a, b):
    """兩組區間的交集區間清單。純函數可測。"""
    out = []
    for s1, e1 in a:
        for s2, e2 in b:
            lo, hi = max(s1, s2), min(e1, e2)
            if hi > lo:
                out.append((lo, hi))
    return sorted(out)

def check_dead_air(video, freeze_db=-60, freeze_d=3.0, sil_db=-35, sil_d=2.0, max_total=0.5):
    """留存 gate（M95 機械化）：畫面凍結(freezedetect) ∩ 音訊靜音(silencedetect)
    = 真死空檔。交集總長 > max_total(0.5s) → ok=False 並列出區間。失敗 → ok=None。"""
    try:
        dur = _probe_dur(video)
        r = _run(['ffmpeg', '-hide_banner', '-i', video,
                  '-vf', f'freezedetect=n={freeze_db}dB:d={freeze_d}',
                  '-af', f'silencedetect=noise={sil_db}dB:d={sil_d}',
                  '-f', 'null', '-'])
    except Exception as e:
        return {'ok': None, 'dead_air': [], 'total': 0.0,
                'note': f'ffmpeg unavailable ({e}) -> dead-air skipped'}
    if r.returncode != 0:
        return {'ok': None, 'dead_air': [], 'total': 0.0,
                'note': 'ffmpeg failed -> skipped; stderr=' + (r.stderr or '')[-200:]}
    freezes, silences = _parse_freeze_silence(r.stderr or '', end=dur)
    inter = _intersect_ranges(freezes, silences)
    total = sum(e - s for s, e in inter)
    ok = total <= max_total
    return {'ok': ok, 'dead_air': [(round(s, 2), round(e, 2)) for s, e in inter],
            'total': round(total, 2), 'n_freeze': len(freezes), 'n_silence': len(silences),
            'note': f'freeze&silence overlap {round(total, 2)}s '
                    + ('(<= ' + str(max_total) + 's ok)' if ok else f'> {max_total}s = dead air')}

# ---------------------------------------------------------------- M105 字幕同步 gate
def _parse_ass_events(ass_path):
    """ASS Dialogue 行 → [(start_s, end_s, text)]（去掉 {...} override tags）。"""
    import re as _re
    evs = []
    def _sec(t):
        h, m, s = t.split(':'); return int(h) * 3600 + int(m) * 60 + float(s)
    with open(ass_path, encoding='utf-8') as fh:
        for line in fh:
            if not line.startswith('Dialogue:'):
                continue
            p = line.split(',', 9)
            if len(p) < 10:
                continue
            evs.append((_sec(p[1]), _sec(p[2]), _re.sub(r'\{[^}]*\}', '', p[9]).strip()))
    return evs


def _char_overlap(a, b):
    """CJK+英數字符集合重疊率（相對 b=字幕字符）。0-1。"""
    import re as _re
    ta = set(_re.findall(r'[一-鿿A-Za-z0-9]', a))
    tb = set(_re.findall(r'[一-鿿A-Za-z0-9]', b))
    if not tb:
        return 1.0
    return len(ta & tb) / len(tb)


def check_caption_sync(video, ass_path, n=8, model_size='base', min_overlap=0.50, pad=0.25):
    """M105 gate — 抽 n 行字幕，各抽該時間窗音訊 → whisper 轉錄 → 字符重疊率驗「字幕時間=真實語音」。
    回 {ok, checked, fails:[{start,caption,heard,overlap}], note}。
    faster_whisper 不可用 → ok=None（視為需人工驗，不默默放行）。"""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return {'ok': None, 'checked': 0, 'fails': [],
                'note': 'faster_whisper unavailable -> caption sync needs manual check'}
    import tempfile
    evs = _parse_ass_events(ass_path)
    if not evs:
        return {'ok': False, 'checked': 0, 'fails': [], 'note': 'ASS has no events'}
    idx = sorted(set(int(i * (len(evs) - 1) / max(1, n - 1)) for i in range(n)))
    m = WhisperModel(model_size, device='cpu', compute_type='int8')
    fails, results = [], []
    with tempfile.TemporaryDirectory(prefix='capsync_') as td:
        for i in idx:
            s, e, txt = evs[i]
            wav = os.path.join(td, f'w{i}.wav')
            _run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, s - pad):.2f}',
                  '-t', f'{(e - s) + 2 * pad:.2f}', '-i', str(video),
                  '-vn', '-ar', '16000', '-ac', '1', wav])
            segs, _info = m.transcribe(wav, language='zh', vad_filter=False)
            heard = ''.join(sg.text.strip() for sg in segs)
            ov = _char_overlap(heard, txt)
            results.append((round(s, 2), txt, heard, round(ov, 2)))
            if ov < min_overlap:
                fails.append({'start': round(s, 2), 'caption': txt, 'heard': heard, 'overlap': round(ov, 2)})
    ok = not fails
    return {'ok': ok, 'checked': len(idx), 'fails': fails, 'results': results,
            'note': f'{len(idx)} lines sampled; ' + ('all passed' if ok
                    else f'{len(fails)} line(s) overlap < {min_overlap}')}


def render_fullframe_sheets(video, out_dir, step=1.5, cell_w=300, cell_h=169, cols=7, rows=5):
    """M104 gate 素材 — 全片每 step 秒抽【全幀】拼 contact sheets（不是只邊緣）。
    回 sheet 路徑 list。產出後必須逐張人工看：找中央浮窗(錄影軟體面板/通知)+邊緣 chrome
    —— 生成是機械的，看是必須的。"""
    os.makedirs(out_dir, exist_ok=True)
    dur = _probe_dur(video)
    ts = [round(i * step, 2) for i in range(int(dur / step) + 1)]
    per = cols * rows
    sheets = []
    for ci in range(0, len(ts), per):
        chunk = ts[ci:ci + per]
        frames = []
        for t in chunk:
            f = os.path.join(out_dir, f'ff_{t:07.2f}.jpg')
            _run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(video),
                  '-update', '1', '-frames:v', '1', '-vf', f'scale={cell_w}:{cell_h}', f])
            frames.append(f)
        ins = []
        for f in frames:
            ins += ['-i', f]
        lbl = ''.join(f'[{i}:v]' for i in range(len(frames)))
        r = max(1, (len(frames) + cols - 1) // cols)
        sheet = os.path.join(out_dir, f'fullframe_sheet_{ci // per}.jpg')
        _run(['ffmpeg', '-v', 'error', '-y'] + ins +
             ['-filter_complex', f'{lbl}concat=n={len(frames)}:v=1:a=0,tile={cols}x{r}',
              '-update', '1', '-frames:v', '1', sheet])
        sheets.append(sheet)
        for f in frames:
            try: os.remove(f)
            except OSError: pass
    return sheets


# ---------------------------------------------------------------- M108 斷句 gate
def _ass_texts(ass_path):
    """讀 ASS → 去 tag 的行文字（時間序）。"""
    texts = []
    with open(ass_path, encoding="utf-8") as fh:
        for l in fh:
            if l.startswith("Dialogue:"):
                parts = l.rstrip("\n").split(",", 9)
                if len(parts) > 9:
                    texts.append(re.sub(r"\{[^}]*\}", "", parts[9]).replace("\\N", " ").strip())
    return texts


def check_caption_linebreaks(ass_path):
    """M108 gate：字幕行 尾懸掛/頭懸掛/腰斬/超長 = 0 才過。
    規則本體住在 `longform_maker/word_captions.scan_line_quality`（與生成側同一組常數）
    —— 這裡只負責讀 ASS + 接線。word_captions 不在 path（單獨複製 delivery_qa 出去用的
    情況）→ 回 ok=None，視為「需人工驗」而不是默默放行。"""
    try:
        import sys
        from pathlib import Path
        lm = Path(__file__).resolve().parents[1] / "longform_maker"
        if str(lm) not in sys.path:
            sys.path.insert(0, str(lm))
        from word_captions import scan_line_quality
    except Exception as e:
        return {"ok": None, "note": f"word_captions import failed ({e}) -> M108 scan skipped"}
    r = scan_line_quality(_ass_texts(ass_path))
    r["note"] = "M108 " + r["note"]
    return r


# ---------------------------------------------------------------- M79 BGM 覆蓋 gate
def check_bgm_coverage(video, voice, gap_min=1.2, floor_db=-48.0, max_windows=8):
    """M79 gate：畫面還在播，音樂就不能停 —— 抽「旁白間隙 + 片尾」量成片音軌 RMS，
    任一窗 mean_volume < floor_db = BGM 斷了（成片該處只剩 room-tone/靜音）。
    片尾窗必抽：BGM 短於影片而沒 loop-fill 時，斷點幾乎都落在後段/尾段，
    正片播完前音樂先停是最常見、也最容易被機械項全綠蓋過去的交付失敗。
    voice = 乾淨人聲檔（用來定位旁白間隙；不要傳 mix 完的）。"""
    vdur = _probe_dur(video)
    wins = [(s, min(e, s + 4.0)) for s, e, _ in detect_long_pauses(voice, min_sec=gap_min)][:max_windows - 1]
    wins.append((max(0.5, vdur - 6.0), vdur - 1.0))          # 片尾窗必抽
    holes = []
    for s, e in wins:
        if e - s < 0.8:
            continue
        r = _run(['ffmpeg', '-hide_banner', '-nostats', '-ss', f'{s:.2f}', '-t', f'{e - s:.2f}',
                  '-i', video, '-af', 'volumedetect', '-f', 'null', '-'])
        m = re.search(r'mean_volume:\s*(-?[\d.]+)', r.stderr or '')
        if m and float(m.group(1)) < floor_db:
            holes.append((round(s, 1), round(e, 1), float(m.group(1))))
    return {"ok": not holes, "windows": len(wins),
            "note": (f"M79 BGM 覆蓋 ok（抽 {len(wins)} 窗全 >{floor_db}dB）" if not holes
                     else f"M79 BGM 斷點 {holes} < {floor_db}dB — 音樂停了")}


# ---------------------------------------------------------------- 🚦 QA 主入口
def final_delivery_qa(video, *, voice=None, contact_out=None, audio=False, ass=None,
                      caption_sync=False, sheets_dir=None, scene_pacing=False, dead_air=False,
                      profile=None):
    """🚦 交付前 QA（canon M91-M95/M103-M105/M108/M79 + QA 清單）。回 dict + 印報告。
    機械項：M93 頻閃、M95 死空檔、M103(audio=True)LUFS/尾靜音/A-V同步/字幕溢出、
    M105 字幕同步(caption_sync=True)、M108 斷句(給了 ass 就自動跑)。
    M104：sheets_dir 給了就強制產全幀掃描圖（人工逐張看 = 交付前提）。
    留存 gate：scene_pacing=True 驗 cut 密度分段上限、dead_air=True 驗
    畫面凍結∩靜音交集（兩者 ok=None=工具缺→只 warn 不擋；預設 False=舊行為不變）。

    profile='teaching_longform'（防假綠）：教學長片交付一律用這個 —
    強制開 audio/caption_sync/M108 斷句/M79 BGM 覆蓋，且 voice/ass/sheets_dir
    【缺一 = 直接 BLOCKED】。沒有這道防線時，只傳 video 也會印 DELIVER OK ——
    真正該驗的音訊/字幕/掃描圖全部沒跑，綠燈是假的。

    ⚠️ video 之後【一律關鍵字】：位置參數會靜默綁錯（ass 綁到 contact_out、
    sheets_dir 綁到 audio）→ 真參數留 None → profile 判 missing → 永遠 BLOCKED，
    而 BLOCKED 長得像「gate 正常運作」= 靜默失敗。加 `*` 後錯誤呼叫直接 TypeError。
    正確式：final_delivery_qa(video, voice=..., ass=..., sheets_dir=..., profile='teaching_longform')"""
    missing = []
    if profile == 'teaching_longform':
        audio = True; caption_sync = True
        if not voice: missing.append('voice (clean narration wav)')
        if not ass: missing.append('ass (captions.ass)')
        if not sheets_dir: missing.append('sheets_dir (M104 全幀掃描)')
    rep = {'video': str(video), 'duration': round(_probe_dur(video), 2),
           'profile': profile, 'missing_inputs': missing}
    flashes = detect_flash(video)
    rep['flash_segments'] = flashes
    fc = classify_flash(flashes)   # M93 v2：真頻閃才擋；孤立 fade 轉場放行（列出供人眼確認）
    rep['flash_flag'] = fc['flag']
    rep['flash_note'] = fc['note']
    rep['flash_transitions'] = fc['transitions']
    # M92 死黑邊（非滿版沒模糊填底 → letterbox）
    borders = detect_dead_borders(video)
    rep['dead_border'] = borders
    rep['border_flag'] = borders['border_flag']
    if voice:
        rep['long_pauses'] = detect_long_pauses(voice)
        rep['deadair_flag'] = len(rep['long_pauses']) > 0
    if audio:   # M103 音訊 gate（教學長片成片 = 跑這組；純 silent vlog 可略）
        rep['loudness'] = check_loudness(video)
        rep['tail_silence'] = check_tail_silence(video)
        rep['av_sync'] = check_av_sync(video)
        rep['audio_ok'] = rep['loudness']['ok'] and rep['tail_silence']['ok'] and rep['av_sync']['ok']
    if ass:
        rep['captions'] = check_captions_within_dur(ass, rep['duration'])
        rep['linebreaks'] = check_caption_linebreaks(ass)   # M108 斷句 gate（自動跑）
        if caption_sync:   # M105：whisper 抽驗字幕時間=真實語音
            rep['caption_sync'] = check_caption_sync(video, ass)
    if voice and (audio or profile == 'teaching_longform'):
        rep['bgm_coverage'] = check_bgm_coverage(video, voice)   # M79 音樂不能停
    if scene_pacing:   # 留存 gate：cut 密度分段上限
        rep['scene_pacing'] = check_scene_pacing(video)
    if dead_air:       # 留存 gate：畫面凍結∩靜音 = 真死空檔（M95 機械化）
        rep['dead_air'] = check_dead_air(video)
    if contact_out:
        contact_sheet(video, contact_out)
        rep['contact_sheet'] = str(contact_out)
    if sheets_dir:   # M104：全幀 dense 掃描圖（生成機械、閱讀必須）
        rep['fullframe_sheets'] = render_fullframe_sheets(video, sheets_dir)

    # cp950 console 不能印 emoji → runtime 輸出一律 ASCII marker（canon 文件才用 emoji）
    def _mk(ok): return '[OK] ' if ok else '[WARN] '
    print(f"[QA] final_delivery_qa: {rep['video']} | {rep['duration']}s")
    print('  M93 flash :', ('[WARN] ' if rep['flash_flag'] else '[OK] ') + rep['flash_note'])
    print('  M92 border:', '[WARN] ' + borders['note'] if rep['border_flag'] else '[OK] 滿版無黑邊')
    if voice:
        print('  M95 deadair(>1.5s):', '[WARN] ' + str(rep['long_pauses']) if rep['deadair_flag'] else '[OK] none')
    if audio:
        print('  M103 loudness:', _mk(rep['loudness']['ok']) + rep['loudness']['note'])
        print('  M103 tail    :', _mk(rep['tail_silence']['ok']) + rep['tail_silence']['note'])
        print('  M103 av-sync :', _mk(rep['av_sync']['ok']) + rep['av_sync']['note'])
    if ass:
        print('  M103 caption :', _mk(rep['captions']['ok']) + rep['captions']['note'])
        lb = rep['linebreaks']
        print('  M108 breaks  :', ('[??] ' if lb['ok'] is None else _mk(lb['ok'])) + lb['note'])
        if caption_sync:
            cs = rep['caption_sync']
            print('  M105 cap-sync:', ('[??] ' if cs['ok'] is None else _mk(cs['ok'])) + cs['note'])
    if 'bgm_coverage' in rep:
        bc = rep['bgm_coverage']
        print('  M79 bgm-cov  :', _mk(bc['ok']) + bc['note'])
    if missing:
        print('  [WARN] profile 必要輸入缺:', ', '.join(missing))
    if scene_pacing:
        sr = rep['scene_pacing']
        print('  pacing    :', ('[??] ' if sr['ok'] is None else _mk(sr['ok'])) + sr['note'])
    if dead_air:
        dr = rep['dead_air']
        print('  deadair   :', ('[??] ' if dr['ok'] is None else _mk(dr['ok'])) + dr['note'])
    if contact_out:
        print('  contact_sheet ->', contact_out)
    if sheets_dir:
        print(f"  M104 fullframe sheets x{len(rep['fullframe_sheets'])} -> {sheets_dir}  (必須逐張人工看：中央浮窗/錄影軟體面板)")
    # 總閘門：機械可驗項全綠才算可交付（人工項仍需看接觸表；留存 gate ok=None=工具缺不擋）
    _cs = rep.get('caption_sync', {}).get('ok')
    # profile 下 caption_sync=None（whisper 缺）也擋 — 教學長片不可跳過 M105（None=放行=假綠）
    _cs_bad = (caption_sync and ass and _cs is False) or (profile == 'teaching_longform' and _cs is not True)
    _sp_bad = scene_pacing and rep.get('scene_pacing', {}).get('ok') is False
    _da_bad = dead_air and rep.get('dead_air', {}).get('ok') is False
    _lb = rep.get('linebreaks', {}).get('ok')
    _lb_bad = (ass and _lb is False) or (profile == 'teaching_longform' and _lb is not True)
    _bgm_bad = 'bgm_coverage' in rep and not rep['bgm_coverage']['ok']
    rep['deliver_ok'] = not (rep['flash_flag'] or rep['border_flag']
                             or rep.get('deadair_flag', False)
                             or (audio and not rep.get('audio_ok', False))
                             or (ass and not rep['captions']['ok'])
                             or _cs_bad or _sp_bad or _da_bad
                             or _lb_bad or _bgm_bad or bool(missing))
    print('  [GATE]', 'DELIVER OK (機械項全綠)' if rep['deliver_ok'] else 'BLOCKED — 修正上面 [WARN] 再交付')
    print('  Note: 人工項 — M91/M104 全幀掃描圖逐張看(中央浮窗+邊緣chrome) / M92 圖片排版 / M94 真實 artifact / M68 字幕樣式 / M107 上鏡數據對真截圖')
    return rep


# ── self-test (regression guard，rank5 強化) — `python delivery_qa.py` ──
if __name__ == "__main__":
    cuts = [(10.0, 15.0), (30.0, 33.0)]
    assert build_keep_ranges(cuts, 40) == [(0, 10.0), (15.0, 30.0), (33.0, 40)]
    assert remap_time(5, cuts) == 5            # 在第一個 cut 之前 → 不動
    assert remap_time(20, cuts) == 15          # 過第一 cut → -5
    assert remap_time(35, cuts) == 27          # 過兩 cut → -8
    assert trim_dead_air_ranges([(22.5, 26.3, 3.8)], keep=0.5) == [(23.0, 26.3)]
    import re as _re
    fp = _re.compile(r"black_start:([\d.eE+-]+) black_end:([\d.eE+-]+) black_duration:([\d.eE+-]+)")
    assert fp.search("black_start:1.2e-05 black_end:0.4 black_duration:0.39"), "科學記號 black ts 漏判"
    assert fp.search("black_start:68 black_end:74 black_duration:6"), "整數 ts 漏判"
    # ── M93 v2 classify_flash（誤報回歸測，純資料不跑 ffmpeg）──
    # 1) 孤立的 dip-to-black = 段落邊界 fade 轉場 → 放行，且要列出供人眼確認
    _iso = [(12.0, 12.40, 0.40), (31.0, 31.40, 0.40), (58.2, 58.70, 0.50)]
    _c_iso = classify_flash(_iso)
    assert _c_iso['flag'] is False, f"孤立 fade 轉場不該擋: {_c_iso}"
    assert _c_iso['transitions'] == sorted(_iso), "放行時必須把轉場列出（人眼確認用）"
    assert classify_flash([(20.0, 20.6, 0.6)])['flag'] is False, "單次 fade-to-black 不該擋"
    _c_none = classify_flash([])
    assert _c_none['flag'] is False and _c_none['note'] == 'none', "0 段 = 乾淨"
    # 2) 連續多次短閃（彼此間隔 < cluster_gap）= 真頻閃 → 擋，且不得當成轉場列出
    _burst = [(5.0, 5.2, 0.2), (5.5, 5.7, 0.2), (6.1, 6.3, 0.2), (6.8, 7.0, 0.2)]
    _c_burst = classify_flash(_burst)
    assert _c_burst['flag'] is True, f"連續短閃該擋: {_c_burst}"
    assert _c_burst['transitions'] == [], "擋下時不該把頻閃當轉場列出"
    # 3) 單幀等級爆閃（<micro）即使孤立也擋（PSE 風險）
    assert classify_flash([(9.0, 9.05, 0.05), (40.0, 40.4, 0.4)])['flag'] is True, "單幀爆閃(<0.12s)該擋"
    # 4) 邊界：間隔剛好 == cluster_gap → 放行（判準是 <，不是 <=）
    assert classify_flash([(0.0, 1.0, 1.0), (9.0, 10.0, 1.0)])['flag'] is False, "間隔==cluster_gap 該放行"
    assert classify_flash([(0.0, 1.0, 1.0), (8.9, 9.9, 1.0)])['flag'] is True, "間隔<cluster_gap 該擋"
    # 5) 未排序輸入不能影響判定（內部 sorted）
    assert classify_flash(list(reversed(_burst)))['flag'] is True, "亂序輸入該得到同樣結論"
    # 6) 舊邏輯回歸守門：舊式「>=2 段 or 任一段 <1s」會把 _iso 全誤報 → 永遠 BLOCKED
    assert (len(_iso) >= 2 or any(f[2] < 1.0 for f in _iso)), "舊邏輯確實會誤報（本案例存在的理由）"
    assert not classify_flash(_iso)['flag'], "新邏輯必須修掉舊誤報，否則 deliver_ok 永遠 False"
    sp = _re.compile(r"silence_(start|end): ([\d.eE+-]+)(?: \| silence_duration: ([\d.eE+-]+))?")
    assert sp.search("silence_end: 26.28 | silence_duration: 3.75"), "silence parse 漏判"
    # M92 死黑邊 cropdetect 解析 + flag 邏輯（不跑 ffmpeg，純驗 parse + threshold）
    cp = _re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", "x crop=1920:1036:0:22 y crop=1920:1036:0:22")
    assert cp and cp[-1] == ('1920', '1036', '0', '22'), "cropdetect 解析漏判"
    _cw, _ch = 1920, 1036
    assert (1920 - _cw) <= 4 and (1080 - _ch) > 4, "死黑邊 threshold 邏輯錯（高度該判有黑邊）"
    # _probe_wh 解析：對 ffprobe csv 尾端多餘分隔符 + CRLF 免疫（不 split('x')）
    assert [int(x) for x in _re.findall(r'\d+', "1080x1920x\r")][:2] == [1080, 1920], "_probe_wh 尾端分隔解析漏判"
    # ── M103 音訊 gate parser regression（純字串，真 ffmpeg 跑在 final_delivery_qa(audio=True)）──
    li = _re.search(r'"input_i"\s*:\s*"([-\d.]+)"', 'x "input_i" : "-14.07",\n "input_tp" : "-1.33"')
    lt = _re.search(r'"input_tp"\s*:\s*"([-\d.]+)"', '"input_tp" : "-1.33"')
    assert li and float(li.group(1)) == -14.07 and lt and float(lt.group(1)) == -1.33, "loudnorm json parse 漏判"
    rms = [float(m.group(1)) for m in _re.finditer(r'RMS level dB:\s*([-\d.]+)', "RMS level dB: -49.66\nRMS level dB: -49.70")]
    assert rms == [-49.66, -49.70] and max(rms) < -40, "astats RMS parse / tail gate 邏輯漏判"
    assert abs(-14.07 - (-14.0)) <= 1.0 and (-1.33) <= (-1.0) + 0.3, "loudness gate 該 PASS(-14.07/-1.33)"
    assert not (abs(-11.5 - (-14.0)) <= 1.0), "loudness gate 該 BLOCK(-11.5 偏離 -14)"
    _m = _re.match(r'(\d+):(\d\d):(\d\d(?:\.\d+)?)', "0:01:23.45")
    assert _m and int(_m.group(1)) * 3600 + int(_m.group(2)) * 60 + float(_m.group(3)) == 83.45, "ASS 末時間戳解析漏判"
    assert 83.45 <= 83.60 + 0.1, "caption-within-dur gate 該 PASS(末字幕<=片長+slack)"
    # ── M108 斷句 gate 接線（_ass_texts 解析 + scan_line_quality 真跑）──
    import tempfile as _tf
    with _tf.NamedTemporaryFile('w', suffix='.ass', delete=False, encoding='utf-8') as _f:
        _f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                 "Dialogue: 0,0:00:01.00,0:00:03.50,Cap,,0,0,0,,{\\fad(90,60)}這是一句正常的字幕\n"
                 "Dialogue: 0,0:00:03.60,0:00:06.00,Cap,,0,0,0,,第二句也很正常\n")
        _assp = _f.name
    assert _ass_texts(_assp) == ["這是一句正常的字幕", "第二句也很正常"], "_ass_texts 去 tag / 解析錯"
    _lbr = check_caption_linebreaks(_assp)
    assert _lbr['ok'] is not False, f"乾淨字幕不該被 M108 擋: {_lbr}"
    os.remove(_assp)
    with _tf.NamedTemporaryFile('w', suffix='.ass', delete=False, encoding='utf-8') as _f:
        _f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                 "Dialogue: 0,0:00:01.00,0:00:03.50,Cap,,0,0,0,,這一段先講到這裡所以\n"
                 "Dialogue: 0,0:00:03.60,0:00:06.00,Cap,,0,0,0,,我們繼續往下看\n")
        _assp2 = _f.name
    _lbr2 = check_caption_linebreaks(_assp2)
    assert _lbr2['ok'] in (False, None), f"尾懸掛該被 M108 抓: {_lbr2}"
    os.remove(_assp2)
    # ── profile 防假綠：缺 voice/ass/sheets_dir 必列 missing，且 missing 非空 = 不可交付 ──
    def _missing_for(profile, voice=None, ass=None, sheets_dir=None):
        mi = []
        if profile == 'teaching_longform':
            if not voice: mi.append('voice')
            if not ass: mi.append('ass')
            if not sheets_dir: mi.append('sheets_dir')
        return mi
    assert len(_missing_for('teaching_longform')) == 3, "profile 只傳 video 該列 3 項 missing"
    assert _missing_for('teaching_longform', 'v.wav', 'c.ass', 'sheets/') == [], "三件齊全不該列 missing"
    assert _missing_for(None) == [], "沒給 profile 不該強制 missing（舊行為不變）"
    assert not (not bool(_missing_for('teaching_longform'))), "missing 非空必須讓 deliver_ok=False"
    # profile 下 caption_sync/linebreaks 的 None（工具缺）也要擋，不能當放行
    for _v in (None, False):
        assert (_v is not True), "profile 下 ok=None/False 都必須擋（None=放行=假綠）"
    print("[delivery_qa selftest] OK")
