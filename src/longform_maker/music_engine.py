# -*- coding: utf-8 -*-
"""longform_maker/music_engine.py — beat 卡點 + BGM 能量曲線【可重用模組】(2026-07-11).

四個入口（路徑無關純函數，下支長片 `from music_engine import ...` 直接用）：
  detect_beats(wav)            -> {bpm, beats:[sec], confidence:'librosa'|'numpy-fallback'}
  snap_to_beat(t, beats)       -> float（cut 時間吸附最近拍點，>max_shift 不動）
  energy_arc_filters(chapters) -> list（每章 BGM filter 段 + acrossfade 建議 + riser 標記）
  analyze_bgm_folder(dir)      -> dict（掃 BGM 庫 bpm/時長/RMS/建議用途 → bgm_index.json）

設計鐵則：
  - 音訊一律經 ffmpeg pipe 解碼成 mono f32（librosa 只當 beat_track 演算法用，不靠它讀檔
    → mp3/m4a/flac 都吃、沒 librosa 也有 numpy 自實作 fallback）。
  - Hao 能量 cap（留存>炫技）：reveal riser 至少隔 RISER_MIN_GAP 秒，超頻自動略過。
  - M102：文字 subprocess 一律 encoding='utf-8' errors='replace'；print 只 ASCII。

self-test（M97 真 end-to-end）：`python music_engine.py` — ffmpeg 合成 120/90 BPM 節拍軌，
librosa + numpy-fallback 雙路驗 BPM 誤差 <5、snap 正確、arc filter 真丟 ffmpeg 驗合法；
demo 產物 _demo/beats.png（波形 + 拍點線）。
"""
import os, sys, json, math, subprocess

import numpy as np

for _s in (sys.stdout, sys.stderr):   # M102 cp950 redirect 防炸
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

_HOP = 512                 # onset envelope hop (samples)
_SR = 22050                # 分析取樣率
RISER_MIN_GAP = 30.0       # Hao 能量 cap：riser 最小間隔（秒）
_RISER_LEN = 1.2           # 對齊 fx_lib.sfx_riser 預設長度

MOOD_FILTERS = {
    "hook":    "volume=0dB",                      # 全頻全能量
    "explain": "lowpass=f=2000,volume=-4dB",      # 悶化退後
    "reveal":  "volume=0dB",                      # 全頻 + 前置 riser 標記
}
_DEFAULT_MOOD = "explain"  # 未知 mood 安全預設：退後不搶戲（留存>炫技）

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


# ──────────────────────────────────────────────────────────── 解碼 / 量測
def _load_pcm(path, sr=_SR, max_sec=None):
    """ffmpeg pipe 解碼任意音訊 → (mono float32 ndarray, sr)。二進位 stdout，stderr 手動 decode。"""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if max_sec:
        cmd += ["-t", str(float(max_sec))]
    cmd += ["-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr), "-"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0 or not r.stdout:
        err = (r.stderr or b"").decode("utf-8", "replace")[-500:]
        raise RuntimeError("ffmpeg decode failed: %s\n%s" % (str(path)[-120:], err))
    y = np.frombuffer(r.stdout, dtype=np.float32).astype(np.float32)
    return y, sr


def _probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, encoding="utf-8", errors="replace")
    try:
        return float((r.stdout or "0").strip() or 0)
    except ValueError:
        return 0.0


def _onset_envelope(y, sr=_SR, hop=_HOP, win=1024):
    """RMS spectral-flux 風 onset envelope（numpy only）。回 (env, frame_times)。"""
    n = max(0, (len(y) - win) // hop + 1)
    if n < 4:
        return np.zeros(4, dtype=np.float64), np.arange(4) * hop / sr
    idx = np.arange(win)[None, :] + (np.arange(n) * hop)[:, None]
    frames = y[idx]
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    flux = np.maximum(0.0, np.diff(rms, prepend=rms[0]))          # 只取能量上升
    k = np.hanning(5); k /= k.sum()                               # 輕平滑
    env = np.convolve(flux, k, mode="same")
    times = np.arange(n) * hop / sr
    return env, times


# ──────────────────────────────────────────────────────────── 1. detect_beats
def _detect_beats_numpy(y, sr=_SR):
    """自相關找 BPM(60-180) + 相位搜尋鋪拍點格 + 局部峰值微調。"""
    hop = _HOP
    env, times = _onset_envelope(y, sr, hop)
    e = env - env.mean()
    if not np.any(np.abs(e) > 1e-12):
        return 0.0, []
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    lag_min = max(2, int(round((60.0 / 180.0) * sr / hop)))       # 180 BPM
    lag_max = min(len(ac) - 2, int(round((60.0 / 60.0) * sr / hop)))  # 60 BPM
    if lag_max <= lag_min:
        return 0.0, []
    seg = ac[lag_min:lag_max + 1]
    pk = int(np.argmax(seg)) + lag_min
    # octave 修正：週期性訊號在 2x 週期自相關一樣強 → 只要半 lag 也夠強就取小週期（快的 BPM）
    while pk // 2 >= lag_min and ac[pk // 2] >= 0.80 * ac[pk]:
        pk = pk // 2
    # 拋物線內插細化 lag（±1 bin → BPM 誤差壓到 <2）
    if 1 <= pk < len(ac) - 1:
        a, b, c = ac[pk - 1], ac[pk], ac[pk + 1]
        denom = (a - 2 * b + c)
        delta = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
        delta = float(np.clip(delta, -0.5, 0.5))
    else:
        delta = 0.0
    period = (pk + delta) * hop / sr
    bpm = 60.0 / period
    # 相位搜尋：把拍點格對到 envelope 峰
    dur = times[-1]
    phases = np.linspace(0.0, period, 32, endpoint=False)
    best_phase, best_score = 0.0, -1.0
    for ph in phases:
        grid = np.arange(ph, dur, period)
        score = float(np.interp(grid, times, env).sum())
        if score > best_score:
            best_score, best_phase = score, float(ph)
    beats = []
    half_win = 0.07
    for g in np.arange(best_phase, dur, period):
        m = (times >= g - half_win) & (times <= g + half_win)
        if np.any(m):
            g = float(times[m][int(np.argmax(env[m]))])           # 微調到局部峰
        beats.append(round(float(g), 4))
    return float(bpm), beats


def _fold_bpm(bpm, lo=60.0, hi=180.0):
    while bpm > hi:
        bpm /= 2.0
    while 0 < bpm < lo:
        bpm *= 2.0
    return bpm


def detect_beats(wav, force_fallback=False, max_sec=None):
    """回 {'bpm': float, 'beats': [sec,...], 'confidence': 'librosa'|'numpy-fallback'}。
    先試 librosa beat_track（onset 演算法較強）；沒裝或 force_fallback 走 numpy 自實作。"""
    y, sr = _load_pcm(wav, _SR, max_sec=max_sec)
    if not force_fallback:
        try:
            import librosa  # noqa: 延遲 import，沒裝直接 fallback
            tempo, beat_times = librosa.beat.beat_track(y=y, sr=sr, hop_length=_HOP,
                                                        units="time")
            bpm = _fold_bpm(float(np.atleast_1d(tempo)[0]))
            beats = [round(float(t), 4) for t in np.atleast_1d(beat_times)]
            if bpm > 0 and beats:
                return {"bpm": round(bpm, 2), "beats": beats, "confidence": "librosa"}
        except Exception:
            pass  # librosa 沒裝 / 版本炸 → numpy fallback
    bpm, beats = _detect_beats_numpy(y, sr)
    return {"bpm": round(_fold_bpm(bpm), 2), "beats": beats, "confidence": "numpy-fallback"}


# ──────────────────────────────────────────────────────────── 2. snap_to_beat
def snap_to_beat(t, beats, max_shift=0.25):
    """cut 時間吸附最近拍點；最近拍點距離 > max_shift 就原值不動（不硬拉破壞對白節奏）。"""
    if not beats:
        return float(t)
    arr = np.asarray(beats, dtype=np.float64)
    i = int(np.argmin(np.abs(arr - float(t))))
    return float(arr[i]) if abs(arr[i] - float(t)) <= max_shift else float(t)


# ──────────────────────────────────────────────────────────── 3. energy_arc_filters
def energy_arc_filters(chapters):
    """chapters=[{start,end,mood}] → 每章一個 dict：
      start/end/mood/filter        — (start,end,filter) 可直接組 filter_complex 分段
      enable_filter                — 同 filter 加 enable='between(t,s,e)'（單軌 BGM 一條鏈用）
      riser_at                     — reveal 前置 riser 起點（fx_lib.sfx_riser 對齊 1.2s）；
                                     Hao 能量 cap：距上一個 riser < RISER_MIN_GAP 秒自動 None
      crossfade_to_next            — 章節交界建議 'acrossfade=d=1'（最後一章 None）
    未知 mood 一律降級 explain（安全退後）。"""
    out, last_riser = [], -1e9
    chs = sorted(chapters, key=lambda c: float(c["start"]))
    for i, ch in enumerate(chs):
        s, e = float(ch["start"]), float(ch["end"])
        mood = str(ch.get("mood", _DEFAULT_MOOD)).lower()
        filt = MOOD_FILTERS.get(mood, MOOD_FILTERS[_DEFAULT_MOOD])
        enable = "enable='between(t,%s,%s)'" % (_fmt(s), _fmt(e))
        enable_filter = ",".join("%s:%s" % (f, enable) for f in filt.split(","))
        riser_at = None
        if mood == "reveal":
            cand = max(0.0, s - _RISER_LEN)
            if cand - last_riser >= RISER_MIN_GAP:
                riser_at, last_riser = round(cand, 3), cand
        out.append({
            "start": s, "end": e, "mood": mood, "filter": filt,
            "enable_filter": enable_filter, "riser_at": riser_at,
            "crossfade_to_next": "acrossfade=d=1" if i < len(chs) - 1 else None,
        })
    return out


def arc_filter_chain(chapters):
    """把 energy_arc_filters 的分段合成【單軌 BGM 一條 -af 鏈】（timeline enable 版）。
    直接塞 filter_complex：'[bgm]' + arc_filter_chain(chs) + '[bgm_arc]'。"""
    segs = energy_arc_filters(chapters)
    return ",".join(s["enable_filter"] for s in segs)


def _fmt(x):
    return ("%.3f" % float(x)).rstrip("0").rstrip(".")


# ──────────────────────────────────────────────────────────── 4. analyze_bgm_folder
def _suggest_use(bpm, rms_db):
    if rms_db >= -18 and bpm >= 110:
        return "hook/reveal (high energy)"
    if rms_db < -28:
        return "explain/bed (low energy)"
    return "general/explain"


def analyze_bgm_folder(dir_path, max_sec=60, out_name="bgm_index.json"):
    """掃資料夾每首：bpm / 時長 / 平均能量(RMS dBFS) / 建議用途 → 寫 dir/bgm_index.json 並回 dict。
    只分析每首前 max_sec 秒（BGM bpm/能量穩定，夠準又快）。"""
    dir_path = str(dir_path)
    tracks = []
    for name in sorted(os.listdir(dir_path)):
        p = os.path.join(dir_path, name)
        if not os.path.isfile(p) or os.path.splitext(name)[1].lower() not in AUDIO_EXTS:
            continue
        entry = {"file": name}
        try:
            entry["duration_sec"] = round(_probe_duration(p), 2)
            y, sr = _load_pcm(p, _SR, max_sec=max_sec)
            rms = float(np.sqrt(np.mean(y.astype(np.float64) ** 2)))
            rms_db = 20 * math.log10(rms) if rms > 1e-9 else -120.0
            det = detect_beats(p, max_sec=max_sec)
            entry.update({
                "bpm": det["bpm"], "beat_confidence": det["confidence"],
                "rms_mean": round(rms, 5), "rms_db": round(rms_db, 1),
                "suggested_use": _suggest_use(det["bpm"], rms_db),
            })
        except Exception as ex:
            entry["error"] = str(ex)[:200]
        tracks.append(entry)
    index = {"dir": dir_path, "count": len(tracks), "tracks": tracks}
    out_path = os.path.join(dir_path, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    index["index_path"] = out_path
    return index


# ──────────────────────────────────────────────────────────── self-test (M97)
def _make_click_track(path, bpm, dur=12, freq=880, blip=0.05):
    """ffmpeg aevalsrc 合成節拍音軌：每 60/bpm 秒一個 blip 秒的 sine 短脈衝。"""
    period = 60.0 / bpm
    expr = "sin(2*PI*%d*t)*lt(mod(t\\,%.6f)\\,%.3f)" % (freq, period, blip)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error",
                        "-f", "lavfi", "-i",
                        "aevalsrc=exprs=%s:s=%d:d=%d" % (expr, _SR, dur),
                        "-ac", "1", str(path)],
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("click track synth failed:\n" + (r.stderr or "")[-500:])


def _validate_af(filter_str):
    """arc filter 字串丟真 ffmpeg（lavfi sine → -f null）驗合法。"""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=2", "-af", filter_str,
                        "-f", "null", "-"],
                       capture_output=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, (r.stderr or "")[-300:]


def _demo_beats_png(specs, out_png):
    """specs=[(wav, det, label), ...] → 波形 + 拍點線疊加圖。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(specs), 1, figsize=(12, 3 * len(specs)), squeeze=False)
    for ax, (wav, det, label) in zip(axes[:, 0], specs):
        y, sr = _load_pcm(wav, _SR)
        step = max(1, len(y) // 24000)
        t = np.arange(0, len(y), step) / sr
        ax.plot(t, y[::step], lw=0.5, color="#4a90d9", alpha=0.9)
        for b in det["beats"]:
            ax.axvline(b, color="#e0533d", lw=1.0, alpha=0.8)
        ax.set_title("%s  |  detected %.1f BPM  (%s)  |  %d beats"
                     % (label, det["bpm"], det["confidence"], len(det["beats"])))
        ax.set_xlabel("sec"); ax.set_ylabel("amp"); ax.set_xlim(0, t[-1] if len(t) else 1)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def _selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    demo = os.path.join(here, "_demo")
    os.makedirs(demo, exist_ok=True)
    fails = []

    def check(name, ok, detail=""):
        print(("[PASS] " if ok else "[FAIL] ") + name + ((" -- " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    # 1) ffmpeg 合成兩段不同 BPM 節拍軌
    wav120 = os.path.join(demo, "click_120bpm.wav")
    wav90 = os.path.join(demo, "click_90bpm.wav")
    _make_click_track(wav120, 120)
    _make_click_track(wav90, 90)
    check("synth click tracks", os.path.getsize(wav120) > 1000 and os.path.getsize(wav90) > 1000)

    # 2) detect_beats：librosa + numpy-fallback 雙路，BPM 誤差 <5
    dets = {}
    for wav, true_bpm, tag in ((wav120, 120, "120bpm"), (wav90, 90, "90bpm")):
        for ff in (False, True):
            det = detect_beats(wav, force_fallback=ff)
            key = "%s/%s" % (tag, det["confidence"])
            dets[key] = det
            err = abs(det["bpm"] - true_bpm)
            check("detect %s bpm=%.1f err=%.2f" % (key, det["bpm"], err), err < 5)
            check("detect %s has beats" % key, len(det["beats"]) >= 8)
    check("fallback path really ran",
          any(k.endswith("numpy-fallback") for k in dets))
    # 拍點間隔 sanity：中位數間隔 ~ 60/bpm
    d120 = dets.get("120bpm/librosa") or dets["120bpm/numpy-fallback"]
    ivl = float(np.median(np.diff(d120["beats"])))
    check("beat interval ~0.5s (got %.3f)" % ivl, abs(ivl - 0.5) < 0.05)

    # 3) snap_to_beat
    beats = d120["beats"]
    near = beats[10] + 0.1                      # 距拍點 0.1s → 吸附
    check("snap pulls to beat", abs(snap_to_beat(near, beats) - beats[10]) < 1e-6)
    far_probe = beats[10] + 0.26                # 若最近拍 >0.25 → 不動
    snapped = snap_to_beat(far_probe, beats, max_shift=0.2)
    nearest = min(abs(b - far_probe) for b in beats)
    check("snap respects max_shift", (snapped == far_probe) if nearest > 0.2 else True)
    check("snap empty beats no-op", snap_to_beat(3.3, []) == 3.3)

    # 4) energy_arc_filters：結構 + riser cap + ffmpeg 驗字串合法
    chs = [{"start": 0, "end": 20, "mood": "hook"},
           {"start": 20, "end": 80, "mood": "explain"},
           {"start": 80, "end": 100, "mood": "reveal"},
           {"start": 100, "end": 110, "mood": "reveal"},     # 距上個 riser <30s → cap 掉
           {"start": 110, "end": 130, "mood": "weird_mood"}]  # 未知 → explain
    arcs = energy_arc_filters(chs)
    check("arc count", len(arcs) == 5)
    check("hook full volume", arcs[0]["filter"] == "volume=0dB")
    check("explain muffled", arcs[1]["filter"] == "lowpass=f=2000,volume=-4dB")
    check("reveal riser marked", arcs[2]["riser_at"] == round(80 - 1.2, 3))
    check("riser frequency cap", arcs[3]["riser_at"] is None)
    check("unknown mood -> explain", arcs[4]["filter"] == MOOD_FILTERS["explain"])
    check("crossfade suggested", arcs[0]["crossfade_to_next"] == "acrossfade=d=1"
          and arcs[-1]["crossfade_to_next"] is None)
    for a in arcs[:3]:
        ok, err = _validate_af(a["filter"])
        check("ffmpeg accepts filter '%s'" % a["filter"], ok, err if not ok else "")
    chain = arc_filter_chain(chs)
    ok, err = _validate_af(chain)
    check("ffmpeg accepts full enable-chain (%d chars)" % len(chain), ok, err if not ok else "")

    # 5) analyze_bgm_folder：對 demo 資料夾（兩支 click 軌）出 bgm_index.json
    idx = analyze_bgm_folder(demo)
    check("bgm_index.json written", os.path.isfile(os.path.join(demo, "bgm_index.json")))
    good = [t for t in idx["tracks"] if "bpm" in t]
    check("bgm index >=2 tracks analyzed", len(good) >= 2)
    by_name = {t["file"]: t for t in good}
    if "click_120bpm.wav" in by_name:
        check("index bpm ~120 (got %.1f)" % by_name["click_120bpm.wav"]["bpm"],
              abs(by_name["click_120bpm.wav"]["bpm"] - 120) < 5)
    if "click_90bpm.wav" in by_name:
        check("index bpm ~90 (got %.1f)" % by_name["click_90bpm.wav"]["bpm"],
              abs(by_name["click_90bpm.wav"]["bpm"] - 90) < 5)
    check("index has rms + suggested_use",
          all(("rms_db" in t and "suggested_use" in t) for t in good))

    # 6) demo：beats 疊加圖
    png = os.path.join(demo, "beats.png")
    _demo_beats_png([(wav120, dets["120bpm/librosa"] if "120bpm/librosa" in dets
                      else dets["120bpm/numpy-fallback"], "click 120 BPM"),
                     (wav90, dets["90bpm/librosa"] if "90bpm/librosa" in dets
                      else dets["90bpm/numpy-fallback"], "click 90 BPM")], png)
    check("demo beats.png rendered", os.path.isfile(png) and os.path.getsize(png) > 10000)

    print("-" * 60)
    if fails:
        print("SELF-TEST RED: %d failed -> %s" % (len(fails), "; ".join(fails)))
        return 1
    print("SELF-TEST GREEN: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest())
