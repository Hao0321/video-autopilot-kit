"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import subprocess, os, re, json


def _run(args):
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _probe_dur(f):
    return float(_run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                       '-of', 'csv=p=0', f]).stdout.strip())


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
    return round(peaks / (len(M) * 0.1), 2)


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
