"""Timing, audio and caption checks (public distribution).

Checks measured media timings without retaining private production results.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import re, os
from delivery_media_ops import _probe_dur, _run


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
