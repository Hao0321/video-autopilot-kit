# -*- coding: utf-8 -*-
"""longform_maker/audio_chain.py — 教學長片 pro 音訊鏈【可重用模組】(M103, 2026-06-27).

把長片 build script 裡 inline 的人聲處理 / room-tone / sidechain-duck mix / two-pass loudnorm
抽成【路徑無關純函數】，下支長片直接 `from audio_chain import voice_chain, build_bgm, master_mix`
即可，零 copy-paste（M75：build-time helper > copy-paste；reference_impl_longform01 是 inline 範例）。

鐵則（M103）：
  人聲鏈 = highpass(去隆隆) → acompressor(壓平忽大忽小, 真壓縮器) → atempo(加速保持音高) → dynaudnorm(beat 間等響)
  master = + pink room-tone bed(補 M95 死數位靜音, ~-53dB)
  mix    = BGM sidechaincompress 人聲當 key(自動 duck) → two-pass loudnorm(精準 -14) → 對齊【實際影片長】淡出(防 outro 硬切)
  加速   = speed 一參數 → offsets['_speed'] → 下游 scene/字幕 /SP 同步 (assert_sp_sync 當 regression guard)

self-test（M97 真 end-to-end）：`python audio_chain.py` — 合成假旁白+BGM 真跑 ffmpeg 驗時長/LUFS/SP 數學。
M102：所有 subprocess 捕捉用 encoding=utf-8 errors=replace，stdout reconfigure utf-8。
"""
import os, json, subprocess, re, sys
for _s in (sys.stdout, sys.stderr):   # M102 cp950 redirect 防炸
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass


def _run(a):
    r = subprocess.run([str(x) for x in a], capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg/ffprobe failed: " + " ".join(map(str, a))[:200] + "\n" + (r.stderr or "")[-800:])
    return r


def _dur(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(f)],
                       capture_output=True, encoding="utf-8", errors="replace")
    return float((r.stdout or "0").strip() or 0)


def measure_lufs(media, I=-14, TP=-1.5):
    """loudnorm 量測模式抓 input_i (整合 LUFS)。抓不到回 None。投遞響度驗收用。"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(media),
                        "-af", f"loudnorm=I={I}:TP={TP}:print_format=json", "-f", "null", "-"],
                       capture_output=True, encoding="utf-8", errors="replace")
    m = re.search(r'"input_i"\s*:\s*"([-\d.]+)"', r.stderr or "")
    return float(m.group(1)) if m else None


# ──────────────────────────────────────────── 人聲鏈 + room-tone bed → master_voice
def voice_chain(beats, narration_dir, work_dir, speed=1.08,
                lead_pad=0.25, tail_pad=0.40, gap=0.35,
                comp="acompressor=threshold=-18dB:ratio=3:attack=15:release=250",
                roomtone_amp=0.0022):
    """beats = [(tag, wav_basename, speech_first, speech_last), ...]（秒，whisper 量）。
    回 (master_voice_path, offsets_dict)。offsets 含每 beat master start/dur + _total_voice/_gap/_speed。
    人聲鏈每 beat: highpass→acompressor→atempo(speed)→dynaudnorm；concat→鋪 pink room-tone bed。
    ⚠ speed 寫進 offsets['_speed'] → 下游 build_video(scene /speed) + build_final(字幕 /speed) 必須同步讀。"""
    os.makedirs(work_dir, exist_ok=True)
    parts, offsets, t = [], {}, 0.0
    for tag, base, f0, f1 in beats:
        src = os.path.join(narration_dir, base + ".wav")
        start = max(0.0, f0 - lead_pad)
        end = f1 + tail_pad
        out = os.path.join(work_dir, f"voice_{tag}.wav")
        _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", src,
              "-af", f"highpass=f=80,{comp},atempo={speed},dynaudnorm=f=200:g=6",
              "-ar", "48000", "-ac", "2", out])
        real = round(_dur(out), 3)
        offsets[tag] = {"start": round(t, 3), "dur": real, "text_tag": tag}
        parts.append(out)
        t = round(t + real + gap, 3)
    sil = os.path.join(work_dir, "gap.wav")
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{gap}",
          "-i", "anullsrc=r=48000:cl=stereo", sil])
    items = []
    for i, p in enumerate(parts):
        items.append(p)
        if i < len(parts) - 1:
            items.append(sil)
    lst = os.path.join(work_dir, "voice_concat.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for p in items:
            fh.write(f"file '{p.replace(chr(92), '/')}'\n")
    voice_raw = os.path.join(work_dir, "voice_raw.wav")
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", voice_raw])
    total = round(_dur(voice_raw), 3)
    # room-tone bed (M95)：全長極低暖色底噪 → beat 間換氣不再數位零靜音
    rt = os.path.join(work_dir, "roomtone.wav")
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{total:.3f}",
          "-i", f"anoisesrc=c=pink:a={roomtone_amp}:r=48000", "-af", "lowpass=f=1500", "-ac", "2", rt])
    master = os.path.join(work_dir, "master_voice.wav")
    _run(["ffmpeg", "-v", "error", "-y", "-i", voice_raw, "-i", rt,
          "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
          "-map", "[a]", "-ar", "48000", "-ac", "2", master])
    total = round(_dur(master), 3)
    offsets["_total_voice"] = total
    offsets["_gap"] = gap
    offsets["_speed"] = speed
    offsets["_lead_pad"] = lead_pad   # 跨檔契約：build_captions trims 必用同值（別再兩檔各寫 0.18 靠註解同步）
    return master, offsets


# ──────────────────────────────────────────── two-pass loudnorm
def loudnorm_2pass(src, out, I=-14, TP=-1.5, LRA=11):
    """pass1 量測 → pass2 measured_*+linear=true 精準正規化。pass1 抓不到 graceful fallback 單 pass。"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src),
                        "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                       capture_output=True, encoding="utf-8", errors="replace")
    m = re.search(r'\{[^{}]*"input_i"[\s\S]*?\}', r.stderr or "")
    if not m:
        _run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}",
              "-ar", "48000", "-c:a", "pcm_s24le", out])
        return out
    j = json.loads(m.group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:"
          f"offset={j['target_offset']}:linear=true:print_format=summary")
    _run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "48000", "-c:a", "pcm_s24le", out])
    return out


# ──────────────────────────────────────────── BGM 串接 + sidechain duck + mux
def _xfade_chain(paths, xfade, out):
    """把 paths（可重複同一檔）依序 acrossfade 串成一條 → out。crossfade 藏接縫。"""
    ins = []
    for p in paths:
        ins += ["-i", str(p)]
    if len(paths) == 1:
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(paths[0]), "-c:a", "aac", "-b:a", "256k", out])
        return out
    parts, prev = [], "[0:a]"
    for i in range(1, len(paths)):
        lbl = "[a]" if i == len(paths) - 1 else f"[a{i}]"
        parts.append(f"{prev}[{i}:a]acrossfade=d={xfade}:c1=tri:c2=tri{lbl}")
        prev = lbl
    _run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(parts), "-map", "[a]", out])
    return out


def bgm_paths_from_asset_plan(plan_path, project_root=None, limit=3):
    """Resolve ranked Hub candidates for ``build_bgm`` without re-analysis."""
    data = json.load(open(plan_path, encoding="utf-8"))
    root = os.path.abspath(project_root or os.environ.get(
        "VIDEO_KIT_PROJECT_ROOT", os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
    rows = (data.get("music") or {}).get("candidates") or []
    paths = []
    for row in rows:
        value = str(row.get("path", ""))
        path = value if os.path.isabs(value) else os.path.join(root, value.replace("/", os.sep))
        if os.path.isfile(path) and path not in paths:
            paths.append(path)
        if len(paths) >= int(limit):
            break
    if not paths:
        raise FileNotFoundError("asset plan has no resolvable BGM candidates: " + str(plan_path))
    return paths


def build_bgm(bgm_list, work_dir, xfade=2.0, target_dur=None):
    """多軌 BGM crossfade 串成一條，並【loop-fill 補到 target_dur 蓋滿全片】(M79：畫面在播音樂就不能停)。
    - 先把 bgm_list 依序 crossfade 成 base（多軌 = 不同曲交錯，接縫用 acrossfade 藏）。
    - base 不夠長 → 把 base 整條再 crossfade loop 補到 ≥ target_dur（crossfade 接縫 = 不是硬跳 loop）。
      傳 2 支同系列變體（如 AI科技/AI科技2）→ loop 變 A→B→A→B 交錯，重播感比單曲 loop 弱很多。
    - target_dur=None → 不補（向下相容舊行為）。回 bgm_cat 路徑。"""
    out = os.path.join(work_dir, "bgm_cat.m4a")
    base = out if target_dur is None else os.path.join(work_dir, "bgm_base.m4a")
    _xfade_chain(list(bgm_list), xfade, base)
    if target_dur is None:
        return base
    bdur = _dur(base)
    if bdur >= target_dur - 0.5:                       # 夠長 → base 即成品
        if base != out:
            _run(["ffmpeg", "-v", "error", "-y", "-i", base, "-c", "copy", out])
        return out
    import math
    n = max(2, math.ceil((target_dur - xfade) / max(1.0, bdur - xfade)))  # loop 幾份才蓋滿
    _xfade_chain([base] * n, xfade, out)               # base 自身 crossfade loop
    return out


def master_mix(voice, bgm_cat, burned_video, out, work_dir,
               bgm_vol=0.32, duck="sidechaincompress=threshold=0.03:ratio=8:attack=5:release=300:makeup=1",
               I=-14, TP=-1.5, LRA=11):
    """voice + sidechain-ducked BGM → two-pass loudnorm → mux 到 burned_video。
    BGM/mix 淡出對齊【實際影片長 VDUR】(影片逐幀量化比音訊短 ~0.2s；不對齊 -shortest 會砍 BGM
    在 ~-23dB 硬切 = outro click，M103 對抗 review 抓到)。回 final 路徑。"""
    vdur = _dur(burned_video)
    bdur = _dur(bgm_cat)
    # M79 模組層防線（2026-07-13：長片03 只丟 57s BGM 蓋 339s 片，後段 4.5 分靜音被 Hao 抓包）
    assert bdur >= vdur - 0.5, (
        f"M79: BGM({bdur:.1f}s) < 影片({vdur:.1f}s) — 音樂會中途停。"
        f"用 build_bgm(bgm_list, work_dir, target_dur=vdur+4) loop-fill 蓋滿再進 master_mix")
    mix_raw = os.path.join(work_dir, "mix_raw.wav")
    fc = ("[0:a]asplit=2[v1][vsc];"
          f"[1:a]atrim=0:{vdur:.2f},volume={bgm_vol},afade=t=in:st=0:d=2,"
          f"afade=t=out:st={max(0, vdur - 3):.2f}:d=3[bg];"
          f"[bg][vsc]{duck}[bgd];"
          f"[v1][bgd]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"afade=t=out:st={max(0, vdur - 0.15):.2f}:d=0.15[mx]")
    _run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", bgm_cat,
          "-filter_complex", fc, "-map", "[mx]", "-ar", "48000", "-ac", "2", mix_raw])
    mix_final = os.path.join(work_dir, "mix_final.wav")
    loudnorm_2pass(mix_raw, mix_final, I=I, TP=TP, LRA=LRA)
    _run(["ffmpeg", "-v", "error", "-y", "-i", burned_video, "-i", mix_final,
          "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", out])
    return out


# ──────────────────────────────────────────── SPEED→/SP 同步 regression guard（純函數）
def assert_sp_sync(offsets, scenes, phrases, speed=None, tol=0.30):
    """驗加速時間軸同步：每 beat 的 scene 時長總和 /SP ≈ beat dur；末 phrase end /SP 不溢出 beat。
    raise AssertionError 列出 desync 的 beat。build 後或 self-test 當 guard（不需 ffmpeg）。
    scenes = {beat: [{'d':秒},...]}（beat-local 未 /SP）；phrases = {beat: [{'end':秒},...]}。"""
    sp = speed if speed else float(offsets.get("_speed", 1.0))
    bad = []
    for bk, scs in scenes.items():
        if bk not in offsets:
            continue
        scene_sum = sum(s["d"] for s in scs) / sp
        if abs(scene_sum - offsets[bk]["dur"]) > tol:
            bad.append(f"{bk}: scenes/SP={scene_sum:.2f} vs dur={offsets[bk]['dur']:.2f}")
    for bk, phs in phrases.items():
        if bk not in offsets or not phs:
            continue
        last_end = max(p["end"] for p in phs) / sp
        if last_end > offsets[bk]["dur"] + tol + 0.5:   # +0.5 容 trim 起點偏移
            bad.append(f"{bk}: last_phrase_end/SP={last_end:.2f} > dur={offsets[bk]['dur']:.2f}")
    if bad:
        raise AssertionError("SP sync desync:\n  " + "\n  ".join(bad))
    return True


# ──────────────────────────────────────────── self-test（M97：真 ffmpeg end-to-end）
if __name__ == "__main__":
    import tempfile, shutil
    work = tempfile.mkdtemp(prefix="audiochain_selftest_")
    try:
        nd = os.path.join(work, "narration")
        os.makedirs(nd, exist_ok=True)
        # 合成 2 段假旁白（200Hz sine 4s）
        for b in ("b1", "b2"):
            _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                  "-i", "sine=frequency=200:duration=4:sample_rate=48000", "-ac", "1",
                  os.path.join(nd, b + ".wav")])
        beats = [("1", "b1", 0.30, 3.50), ("2", "b2", 0.30, 3.50)]
        speed = 1.08
        master, off = voice_chain(beats, nd, work, speed=speed)
        # 期望 ≈ 2*((3.5+0.40)-(0.3-0.25))/speed + 1*gap
        exp = sum(((3.5 + 0.40) - (0.3 - 0.25)) for _ in beats) / speed + 0.35
        got = _dur(master)
        assert abs(got - exp) < 0.30, f"voice_chain dur {got:.2f} != ~{exp:.2f}"
        assert off["_speed"] == speed and "_total_voice" in off, "offsets 欄位漏"

        # loudnorm_2pass → 量測 ≈ -14
        ln = os.path.join(work, "ln.wav")
        loudnorm_2pass(master, ln)
        lufs = measure_lufs(ln)
        assert lufs is not None and abs(lufs + 14) < 1.5, f"loudnorm_2pass 沒收斂到 ~-14 (got {lufs})"

        # master_mix：合成 burned 影片(色塊=master 長) + BGM(sine) → 成片
        vdur = _dur(master)
        burned = os.path.join(work, "burned.mp4")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
              "-i", f"color=c=navy:s=320x180:r=30:d={vdur:.2f}",
              "-c:v", "libx264", "-pix_fmt", "yuv420p", burned])
        bgm = os.path.join(work, "bgm.wav")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
              "-i", f"sine=frequency=330:duration={vdur + 2:.2f}:sample_rate=48000", "-ac", "2", bgm])
        bcat = build_bgm([bgm], work)
        fin = os.path.join(work, "final.mp4")
        master_mix(master, bcat, burned, fin, work)
        assert os.path.exists(fin) and _dur(fin) > vdur - 0.3, "master_mix 成片時長異常"
        fin_lufs = measure_lufs(fin)
        assert fin_lufs is not None and abs(fin_lufs + 14) < 2.0, f"成片 LUFS 沒收斂 (got {fin_lufs})"

        # M79 loop-fill：短 BGM 必須被 crossfade loop 補到 target（否則後段變靜音）
        shortb = os.path.join(work, "shortbgm.wav")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
              "-i", "sine=frequency=440:duration=5:sample_rate=48000", "-ac", "2", shortb])
        filled = build_bgm([shortb], work, target_dur=20.0)
        assert _dur(filled) >= 19.5, f"M79 build_bgm loop-fill 沒蓋滿 target 20s (got {_dur(filled):.1f})"
        plan_path = os.path.join(work, "current_asset_plan.json")
        json.dump({"music": {"candidates": [{"path": "shortbgm.wav"}]}},
                  open(plan_path, "w", encoding="utf-8"))
        assert bgm_paths_from_asset_plan(plan_path, work) == [shortb]

        # assert_sp_sync 正例 + 負例
        assert assert_sp_sync({"b": {"dur": 3.0}, "_speed": 1.08},
                              {"b": [{"d": 3.24}]}, {"b": [{"end": 3.24}]}), "sp_sync 正例該過"
        _neg = False
        try:
            assert_sp_sync({"b": {"dur": 3.0}, "_speed": 1.08}, {"b": [{"d": 5.0}]}, {}, tol=0.3)
        except AssertionError:
            _neg = True
        assert _neg, "sp_sync 負例(scene 對不上)該被抓到"

        print("[audio_chain selftest] OK — voice_chain / loudnorm_2pass / master_mix / assert_sp_sync "
              "真 ffmpeg end-to-end 通過")
    finally:
        shutil.rmtree(work, ignore_errors=True)
