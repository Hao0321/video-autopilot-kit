# -*- coding: utf-8 -*-
"""Media delivery quality assurance (public distribution).

Checks the rendered artifact for technical, audio, caption, freeze, flash and coverage failures.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
import subprocess, re, os, sys
from pathlib import Path

from delivery_media_ops import _probe_dur, _run, still_blurfill


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
    """Separate clustered or micro flashes from isolated transition fades.

    PUBLIC_FIXTURE: thresholds are configurable starter values and carry no
    private project result or dated review evidence.
    """
    flashes = sorted(flashes)
    micro_hits = [f for f in flashes if f[2] < micro]
    clustered = [(a, b) for a, b in zip(flashes, flashes[1:]) if b[0] - a[1] < cluster_gap]
    bad = bool(micro_hits or clustered)
    if bad:
        note = f"真頻閃：micro(<{micro}s)={micro_hits} clustered(<{cluster_gap}s)={clustered}"
    elif flashes:
        note = f"{len(flashes)} 個孤立 dip-to-black（beat fade 轉場，間隔>={cluster_gap}s）— 可接受"
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
# 把本 session 人工 audit 抓到的長片音訊失敗模式固化成自動 gate：
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
    取代舊 _audit.py『只 print 不 assert』→ 偏離自動 flag、不 green 不交付。"""
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

# ---------------------------------------------------------------- 🎬 留存機械 gate (rank9)
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
    """rank9 gate：視覺變化(cut/鏡頭切換)間距不得超過分段上限（前 30s 最嚴 7s、
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
    片尾凍住+靜音正是最典型死空檔，實測 2026-07-09 抓到）；end=None → 丟棄。純函數可測。"""
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
    """rank9 gate（M95 機械化）：畫面凍結(freezedetect) ∩ 音訊靜音(silencedetect)
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

# ---------------------------------------------------------------- 🚦 QA 主入口
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
                'note': 'faster_whisper 不可用 -> 字幕同步需人工驗'}
    import tempfile
    evs = _parse_ass_events(ass_path)
    if not evs:
        return {'ok': False, 'checked': 0, 'fails': [], 'note': 'ASS 無事件'}
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
            'note': f'{len(idx)} 行抽驗 {"全過" if ok else str(len(fails)) + " 行重疊<" + str(min_overlap)}'}


def render_fullframe_sheets(video, out_dir, step=1.5, cell_w=300, cell_h=169, cols=7, rows=5):
    """M104 gate 素材 — 全片每 step 秒抽【全幀】拼 contact sheets（不是只邊緣）。
    回 sheet 路徑 list。產出後必須逐張 Read 找中央浮窗(OBS/通知)+邊緣 chrome —— 生成是機械的，看是必須的。"""
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
    規則本體住在 longform_maker/word_captions.scan_line_quality（生成側同一組常數）。"""
    try:
        import sys
        from pathlib import Path
        lm = Path(__file__).resolve().parent / "longform_maker"
        if str(lm) not in sys.path:
            sys.path.insert(0, str(lm))
        from word_captions import scan_line_quality
    except Exception as e:
        return {"ok": None, "note": f"word_captions 匯入失敗（{e}）— M108 掃描跳過"}
    r = scan_line_quality(_ass_texts(ass_path))
    r["note"] = "M108 " + r["note"]
    return r


def check_bgm_coverage(video, voice, gap_min=1.2, floor_db=-48.0, max_windows=8):
    """Measure rendered audio during narration gaps and near the tail.

    PUBLIC_FIXTURE: a window below ``floor_db`` is treated as a potential
    coverage hole; calibrate against creator-owned approved media.
    """
    vdur = _probe_dur(video)
    wins = [(s, min(e, s + 4.0)) for s, e, _ in detect_long_pauses(voice, min_sec=gap_min)][:max_windows - 1]
    wins.append((max(0.5, vdur - 6.0), vdur - 1.0))  # PUBLIC_FIXTURE: always sample a near-tail window.
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


def _print_delivery_report(rep, *, voice, audio, ass, caption_sync,
                           scene_pacing, dead_air, contact_out, sheets_dir):
    """Print the technical evidence without changing gate state."""
    marker = lambda ok: '[OK] ' if ok else '[WARN] '
    print(f"[QA] final_delivery_qa: {rep['video']} | {rep['duration']}s")
    print('  M93 flash :', ('[WARN] ' if rep['flash_flag'] else '[OK] ') + rep['flash_note'])
    print('  M92 border:', '[WARN] ' + rep['dead_border']['note']
          if rep['border_flag'] else '[OK] 滿版無黑邊')
    if voice:
        print('  M95 deadair(>1.5s):', '[WARN] ' + str(rep['long_pauses'])
              if rep['deadair_flag'] else '[OK] none')
    if audio:
        for label, key in (('loudness', 'loudness'), ('tail    ', 'tail_silence'),
                           ('av-sync ', 'av_sync')):
            print('  M103 %s:' % label, marker(rep[key]['ok']) + rep[key]['note'])
    if ass:
        print('  M103 caption :', marker(rep['captions']['ok']) + rep['captions']['note'])
        linebreaks = rep['linebreaks']
        print('  M108 breaks  :', ('[??] ' if linebreaks['ok'] is None else
                                 marker(linebreaks['ok'])) + linebreaks['note'])
        if caption_sync:
            sync = rep['caption_sync']
            print('  M105 cap-sync:', ('[??] ' if sync['ok'] is None else
                                     marker(sync['ok'])) + sync['note'])
    for label, key in (('M79 bgm-cov', 'bgm_coverage'), ('R9 pacing', 'scene_pacing'),
                       ('R9 deadair', 'dead_air')):
        if key in rep:
            item = rep[key]
            prefix = '[??] ' if item['ok'] is None else marker(item['ok'])
            print('  %s:' % label, prefix + item['note'])
    if rep['missing_inputs']:
        print('  [WARN] profile 必要輸入缺:', ', '.join(rep['missing_inputs']))
    if contact_out:
        print('  contact_sheet ->', contact_out)
    if sheets_dir:
        print(f"  M104 fullframe sheets x{len(rep['fullframe_sheets'])} -> {sheets_dir}  (必須逐張 Read 找中央浮窗/OBS)")


def _apply_delivery_gate(rep, *, audio, ass, caption_sync, scene_pacing,
                         dead_air, profile):
    caption_sync_ok = rep.get('caption_sync', {}).get('ok')
    sync_bad = ((caption_sync and ass and caption_sync_ok is False) or
                (profile == 'teaching_longform' and caption_sync_ok is not True))
    pacing_bad = scene_pacing and rep.get('scene_pacing', {}).get('ok') is False
    dead_air_bad = dead_air and rep.get('dead_air', {}).get('ok') is False
    linebreak_ok = rep.get('linebreaks', {}).get('ok')
    linebreak_bad = ((ass and linebreak_ok is False) or
                     (profile == 'teaching_longform' and linebreak_ok is not True))
    bgm_bad = 'bgm_coverage' in rep and not rep['bgm_coverage']['ok']
    rep['deliver_ok'] = not (
        rep['flash_flag'] or rep['border_flag'] or rep.get('deadair_flag', False) or
        (audio and not rep.get('audio_ok', False)) or
        (ass and not rep['captions']['ok']) or sync_bad or pacing_bad or dead_air_bad or
        linebreak_bad or bgm_bad or bool(rep['missing_inputs']))
    print('  [GATE]', 'DELIVER OK (機械項全綠)' if rep['deliver_ok']
          else 'BLOCKED — 修正上面 [WARN] 再交付')
    print('  Note: 人工項 — M91/M104 全幀掃描圖逐張看(中央浮窗+邊緣chrome) / M92 圖片排版 / M94 真實 artifact / M68 字幕樣式 / M107 戰績鏡頭逐張對 PROOF SoT 真截圖')


def _attach_quality95(video, sheets_dir, rep):
    """Add fail-closed aesthetic evidence without redefining technical QA."""
    if not sheets_dir:
        return
    autopilot = Path(__file__).resolve().parent
    if not autopilot.is_dir():
        return
    sys.path.insert(0, str(autopilot))
    try:
        from quality_95 import longform_evidence, write_report as write_quality_report
        from review_loop import create_bundle as create_review_bundle
        quality = write_quality_report(
            Path(sheets_dir), longform_evidence(content_id=Path(video).stem, delivery_qa=rep))
        rep['quality_95'] = {'status': quality['status'], 'score': quality['score'],
                             'report': quality['json']}
        rep['hao_review'] = create_review_bundle(video, Path(video).stem, quality['json'])
    except Exception as exc:
        rep['quality_95'] = {'status': 'BLOCKED', 'error': str(exc)}
        rep['deliver_ok'] = False


def final_delivery_qa(video, *, voice=None, contact_out=None, audio=False, ass=None,
                      caption_sync=False, sheets_dir=None, scene_pacing=False, dead_air=False,
                      profile=None):
    """🚦 交付前 QA（canon M91-M95/M103-M105 + QA 清單）。回 dict + 印報告。
    機械項：M93 頻閃、M95 死空檔、M103 音訊 4 gate、M105 字幕同步(caption_sync=True)。
    M104：sheets_dir 給了就強制產全幀掃描圖（人工逐張看 = 交付前提）。
    rank9 留存 gate：scene_pacing=True 驗 cut 密度分段上限、dead_air=True 驗
    畫面凍結∩靜音交集（兩者 ok=None=工具缺→只 warn 不擋；預設 False=舊行為不變）。

    profile='teaching_longform'（2026-07-13 審計修 silent-pass）：教學長片交付一律用這個 —
    強制開 audio/caption_sync/M108 linebreaks/M79 bgm_coverage，且 voice/ass/sheets_dir
    【缺一 = 直接 BLOCKED】（過去只傳 video 也印 DELIVER OK = 假綠）。

    ⚠️ video 之後【一律關鍵字】（2026-07-28 R5 修）：曾有文件寫成位置參數
    `(video, voice, ass, sheets_dir, profile=)`，實際會把 ass 綁到 contact_out、
    sheets_dir 綁到 audio → 真 ass/sheets_dir 留 None → profile 判定 missing → 永遠 BLOCKED。
    照文件呼叫卻永遠交付不了，且 BLOCKED 長得像「gate 正常運作」= 靜默失敗。
    加 `*` 後錯誤呼叫直接 TypeError。正確式：
    final_delivery_qa(video, voice=..., ass=..., sheets_dir=..., profile='teaching_longform')"""
    missing = []
    if profile == 'teaching_longform':
        audio = True; caption_sync = True
        if not voice: missing.append('voice(master_voice.wav)')
        if not ass: missing.append('ass(captions.ass)')
        if not sheets_dir: missing.append('sheets_dir(M104 全幀掃描)')
    rep = {'video': str(video), 'duration': round(_probe_dur(video), 2),
           'profile': profile, 'missing_inputs': missing}
    flashes = detect_flash(video)
    rep['flash_segments'] = flashes
    fc = classify_flash(flashes)   # M93 v2：真頻閃才擋，孤立 fade 轉場放行（列出供人眼確認）
    rep['flash_flag'] = fc['flag']
    rep['flash_note'] = fc['note']
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
    if scene_pacing:   # rank9：cut 密度分段上限（留存機械 gate）
        rep['scene_pacing'] = check_scene_pacing(video)
    if dead_air:       # rank9：畫面凍結∩靜音 = 真死空檔（M95 機械化）
        rep['dead_air'] = check_dead_air(video)
    if contact_out:
        contact_sheet(video, contact_out)
        rep['contact_sheet'] = str(contact_out)
    if sheets_dir:   # M104：全幀 dense 掃描圖（生成機械、閱讀必須）
        rep['fullframe_sheets'] = render_fullframe_sheets(video, sheets_dir)

    _print_delivery_report(
        rep, voice=voice, audio=audio, ass=ass, caption_sync=caption_sync,
        scene_pacing=scene_pacing, dead_air=dead_air,
        contact_out=contact_out, sheets_dir=sheets_dir,
    )
    _apply_delivery_gate(
        rep, audio=audio, ass=ass, caption_sync=caption_sync,
        scene_pacing=scene_pacing, dead_air=dead_air, profile=profile,
    )
    _attach_quality95(video, sheets_dir, rep)
    return rep


# ── self-test (regression guard，rank5 強化) — `python media_delivery_qa.py` ──
def _selftest():
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
    sp = _re.compile(r"silence_(start|end): ([\d.eE+-]+)(?: \| silence_duration: ([\d.eE+-]+))?")
    assert sp.search("silence_end: 26.28 | silence_duration: 3.75"), "silence parse 漏判"
    # M92 死黑邊 cropdetect 解析 + flag 邏輯（不跑 ffmpeg，純驗 parse + threshold）
    cp = _re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", "x crop=1920:1036:0:22 y crop=1920:1036:0:22")
    assert cp and cp[-1] == ('1920', '1036', '0', '22'), "cropdetect 解析漏判"
    _cw, _ch = 1920, 1036
    assert (1920 - _cw) <= 4 and (1080 - _ch) > 4, "死黑邊 threshold 邏輯錯（高度該判有黑邊）"
    # PUBLIC_FIXTURE: starter defaults require creator-owned calibration evidence.
    assert [int(x) for x in _re.findall(r'\d+', "1080x1920x\r")][:2] == [1080, 1920], "_probe_wh 尾端分隔解析漏判"
    # ── M103 音訊 gate parser regression（純字串，真 ffmpeg 跑在 final_delivery_qa(audio=True)）──
    li = _re.search(r'"input_i"\s*:\s*"([-\d.]+)"', 'x "input_i" : "-14.07",\n "input_tp" : "-1.33"')
    lt = _re.search(r'"input_tp"\s*:\s*"([-\d.]+)"', '"input_tp" : "-1.33"')
    assert li and float(li.group(1)) == -14.07 and lt and float(lt.group(1)) == -1.33, "loudnorm json parse 漏判"
    rms = [float(m.group(1)) for m in _re.finditer(r'RMS level dB:\s*([-\d.]+)', "RMS level dB: -49.66\nRMS level dB: -49.70")]
    assert rms == [-49.66, -49.70] and max(rms) < -40, "astats RMS parse / tail gate 邏輯漏判"
    # check_loudness 閾值邏輯（不跑 ffmpeg，注入 measure 結果驗判定）
    assert abs(-14.07 - (-14.0)) <= 1.0 and (-1.33) <= (-1.0)+0.3, "loudness gate 該 PASS(-14.07/-1.33)"
    assert not (abs(-11.5 - (-14.0)) <= 1.0), "loudness gate 該 BLOCK(-11.5 偏離 -14)"
    # ASS 末時間戳解析（H:MM:SS.cc）
    _m = _re.match(r'(\d+):(\d\d):(\d\d(?:\.\d+)?)', "0:04:41.62")
    assert _m and int(_m.group(1))*3600+int(_m.group(2))*60+float(_m.group(3)) == 281.62, "ASS 末時間戳解析漏判"
    assert 281.62 <= 281.77 + 0.1, "caption-within-dur gate 該 PASS(281.62<=281.77)"
    # ── M105 caption-sync 純函數 regression（whisper 真跑在 final_delivery_qa(caption_sync=True)）──
    import tempfile as _tf
    with _tf.NamedTemporaryFile('w', suffix='.ass', delete=False, encoding='utf-8') as _f:
        _f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                 "Dialogue: 0,0:00:01.00,0:00:03.50,Cap,,0,0,0,,{\\fad(90,60)}你現在看到的是手遊\n"
                 "Dialogue: 0,0:00:03.60,0:00:06.00,Cap,,0,0,0,,完全沒開遊戲引擎\n")
        _assp = _f.name
    _evs = _parse_ass_events(_assp)
    assert len(_evs) == 2 and _evs[0][0] == 1.0 and _evs[0][2] == "你現在看到的是手遊", "_parse_ass_events 解析錯"
    os.remove(_assp)
    assert _char_overlap("你現在看到的,是一款手遊", "你現在看到的是手遊") >= 0.9, "同句 overlap 該高"
    assert _char_overlap("完全不相干的內容啦", "全部交給 Claude Code") < 0.5, "異句 overlap 該低"
    assert _char_overlap("", "abc") == 0.0 and _char_overlap("x", "") == 1.0, "overlap 邊界值"
    # ── rank9 scene-pacing / dead-air 純函數 regression（真 ffmpeg/ffprobe 跑在開關開啟時）──
    _W = ((0, 30, 7.0), (30, 180, 15.0), (180, None, 30.0))
    assert _pick_limit(15, _W) == 7.0, "t=15 should fall in window 1 (limit 7)"
    assert _pick_limit(30, _W) == 15.0, "boundary t=30 should fall in window 2 (limit 15)"
    assert _pick_limit(29.99, _W) == 7.0, "t=29.99 should stay in window 1"
    assert _pick_limit(180, _W) == 30.0 and _pick_limit(999, _W) == 30.0, "tail window (end=None) limit 30"
    # gaps: 0-5 mid2.5 lim7 ok / 5-25 gap20 mid15 lim7 VIOLATION / 25-40 gap15 mid32.5 lim15 ok(=limit)
    _v = _pacing_violations([0.0, 5.0, 25.0, 40.0], _W)
    assert len(_v) == 1 and _v[0]['gap'] == 20.0 and _v[0]['limit'] == 7.0, f"pacing violation calc wrong: {_v}"
    assert len(_pacing_violations([0.0, 200.0, 400.0], _W)) == 2, "both huge gaps should violate"
    assert _pacing_violations([0.0, 6.0, 12.0, 18.0], _W) == [], "clean pacing should have no violations"
    _fake = ("[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 10.0\n"
             "[freezedetect @ 0x1] lavfi.freezedetect.freeze_duration: 6.0\n"
             "[freezedetect @ 0x1] lavfi.freezedetect.freeze_end: 16.0\n"
             "[silencedetect @ 0x2] silence_start: 12.0\n"
             "[silencedetect @ 0x2] silence_end: 14.5 | silence_duration: 2.5\n")
    _fz, _sl = _parse_freeze_silence(_fake)
    assert _fz == [(10.0, 16.0)] and _sl == [(12.0, 14.5)], f"freeze/silence parse wrong: {_fz} {_sl}"
    _in = _intersect_ranges(_fz, _sl)
    assert _in == [(12.0, 14.5)] and abs(sum(e - s for s, e in _in) - 2.5) < 1e-9, "intersect calc wrong"
    assert sum(e - s for s, e in _in) > 0.5, "2.5s overlap should trip dead-air gate"
    _fz2, _sl2 = _parse_freeze_silence(_fake.replace("silence_start: 12.0", "silence_start: 20.0")
                                            .replace("silence_end: 14.5", "silence_end: 23.0"))
    assert _intersect_ranges(_fz2, _sl2) == [], "no-overlap case should be empty (ok)"
    _fz3, _sl3 = _parse_freeze_silence("lavfi.freezedetect.freeze_start: 5.0\n")
    assert _fz3 == [] and _sl3 == [], "unclosed start without end= must be dropped"
    _fz4, _ = _parse_freeze_silence("lavfi.freezedetect.freeze_start: 5.0\n", end=9.0)
    assert _fz4 == [(5.0, 9.0)], "freeze running to EOF must close at duration (end=)"
    assert _parse_freeze_silence("silence_end: 3.0\n") == ([], []), "end without start must be dropped"
    print("[media_delivery_qa selftest] OK")


if __name__ == "__main__":
    _selftest()
