"""
silent_vlog_maker.screen_rec_cleaner — Auto-clean OBS screen recordings (2026-05-25 M60-M62).

用 OBS 錄螢幕時，3 個常見 garbage 永遠要 strip：
1. M60 — 上方 Chrome tab + URL bar（~80-100 px）
2. M60 — 下方 Windows taskbar（~40-50 px）
3. M61 — 開頭「按開始錄影」段（前 1-2 sec OBS UI 過場）
4. M61 — 結尾「按停止錄影」段（後 3-5 sec OBS UI 出現）
5. M62 — 旁白語氣瑕疵（嗯/啊 + 長停頓）silence trim

Cleaned output 保持原 1920×1080（用 letterbox 填補裁掉的）以無縫塞進 landscape 長片 timeline。
"""
import subprocess
from pathlib import Path


# Default crop for Windows 11 + Chrome (2026-05-25 實測 (a past project) a teaching screen-recording build)
# v1: 80/50 → 截不乾淨（tab + bookmark bar 還在）
# v2: 150/50 → tab title 還漏一條
# v3: 200/80 → 完全乾淨（涵蓋 tab + URL + bookmark + extra padding）+ zoom fill mode 消除黑邊
DEFAULTS_OBS_CHROME_WIN11 = {
    "top_crop_px": 200,      # Chrome window title (30) + tabs (36) + URL (48) + bookmark (32) + extra padding = 200 conservative
    "bottom_crop_px": 80,    # Windows 11 taskbar + extra padding
    "trim_start_sec": 1.5,
    "trim_end_sec": 4.0,
    "fill_mode": "zoom",     # zoom 模式無黑邊（letterbox 模式上下有 100 px 黑邊不專業）
}

# More aggressive crop for full-screen 4K Chrome (1.5× scale)
DEFAULTS_OBS_CHROME_4K = {
    "top_crop_px": 220,
    "bottom_crop_px": 70,
    "trim_start_sec": 1.5,
    "trim_end_sec": 4.0,
}


def clean_screen_recording(
    input_mp4: Path,
    output_mp4: Path,
    top_crop_px: int = DEFAULTS_OBS_CHROME_WIN11["top_crop_px"],        # 200 (M60 v3)
    bottom_crop_px: int = DEFAULTS_OBS_CHROME_WIN11["bottom_crop_px"],  # 80  (M60 v3)
    trim_start_sec: float = 1.5,
    trim_end_sec: float = 4.0,
    target_width: int = 1920,
    target_height: int = 1080,
    fill_mode: str = DEFAULTS_OBS_CHROME_WIN11["fill_mode"],            # "zoom" (M60 v3)
) -> Path:
    """M60 + M61 — strip OBS / browser chrome + trim start/end.

    ⚠️ 2026-06-10 audit fix: 預設值之前是 v1 的 80/50/letterbox（檔頭 changelog 自己
    標記「截不乾淨」的版本）— 現在直接 wire DEFAULTS_OBS_CHROME_WIN11 (v3 200/80/zoom)。

    Pipeline:
    1. ffprobe duration
    2. Trim t = [trim_start, duration - trim_end]
    3. Crop top + bottom (preserve full width)
    4. Re-scale to target (letterbox = pad black bars / zoom = crop sides)
    5. Re-encode H.264 12M

    Args:
        input_mp4: source OBS recording
        output_mp4: cleaned output
        top_crop_px: pixels to strip from top (default 200 — Chrome tab+bookmark bar on Win11, M60 v3)
        bottom_crop_px: pixels to strip from bottom (default 80 — Win11 taskbar, M60 v3)
        trim_start_sec: drop first N sec (OBS UI / scene switch)
        trim_end_sec: drop last N sec ("stop recording" UI)
        target_width / target_height: final canvas (default 1920×1080)
        fill_mode: "letterbox" (black bars) or "zoom" (crop sides to maintain ratio)
    """
    # Get duration
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(input_mp4)],
        capture_output=True, text=True
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"ffprobe 讀不到時長: {input_mp4}（檔案壞或非媒體檔）; stderr={r.stderr[-200:]}")
    duration = float(r.stdout.strip())
    trimmed_dur = max(0.5, duration - trim_start_sec - trim_end_sec)

    # Get source resolution
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", "-select_streams", "v:0", str(input_mp4)],
        capture_output=True, text=True
    )
    src_w, src_h = [int(x) for x in r.stdout.strip().split("x")[:2]]

    # Crop dimensions
    cropped_h = src_h - top_crop_px - bottom_crop_px
    crop_filter = f"crop={src_w}:{cropped_h}:0:{top_crop_px}"

    # Fill to target
    if fill_mode == "letterbox":
        # Scale to fit width, pad black top/bottom if needed
        fill_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )
    elif fill_mode == "zoom":
        # Scale up + center-crop to maintain aspect (no black bars but loses sides)
        fill_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},setsar=1"
        )
    else:
        raise ValueError(f"Unknown fill_mode: {fill_mode}")

    vf = f"{crop_filter},{fill_filter}"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(trim_start_sec),
        "-i", str(input_mp4),
        "-t", str(trimmed_dur),
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-an",  # screen recs usually have system audio we don't want
        "-movflags", "+faststart",
        str(output_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"clean_screen_recording failed: {result.stderr[-500:]}")

    return output_mp4


def clean_voice_pauses(
    input_voice: Path,
    output_voice: Path,
    silence_threshold_db: int = -30,
    min_silence_sec: float = 0.8,
    keep_silence_sec: float = 0.2,
) -> Path:
    """M62 — Trim long silence pauses + normalize loudness.

    錄旁白偶有「嗯」「啊」+ 長停頓。**不能自動 detect 「嗯啊」**（要 Whisper + manual edit）
    但可以 trim 長 silence（>0.8s）保持自然 pace。

    Args:
        input_voice: source voice mp4/m4a
        output_voice: cleaned voice
        silence_threshold_db: below this dB = silence (default -30 dB)
        min_silence_sec: silence longer than this gets trimmed (default 0.8s)
        keep_silence_sec: leave this much silence in (default 0.2s for natural)
    """
    # ffmpeg silenceremove filter
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_voice),
        "-af", (
            # stop_duration = min_silence_sec：只修剪「長於 0.8s」的停頓 — 之前漏傳
            # 導致 ffmpeg 預設 0s = 所有自然小停頓全被壓扁、語速機械化（2026-06-10 audit）
            f"silenceremove="
            f"start_periods=1:start_threshold={silence_threshold_db}dB:start_silence={keep_silence_sec}:"
            f"stop_periods=-1:stop_threshold={silence_threshold_db}dB:stop_silence={keep_silence_sec}:"
            f"stop_duration={min_silence_sec}:"
            f"detection=peak,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11"
        ),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        str(output_voice),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"clean_voice_pauses failed: {result.stderr[-500:]}")
    return output_voice


def batch_clean_screen_recs(
    input_paths: list[Path],
    output_dir: Path,
    **screen_clean_kwargs,
) -> list[Path]:
    """Apply clean_screen_recording to multiple files. Returns output paths."""
    output_dir.mkdir(exist_ok=True, parents=True)
    outputs = []
    for inp in input_paths:
        out = output_dir / f"{inp.stem}_cleaned.mp4"
        clean_screen_recording(inp, out, **screen_clean_kwargs)
        outputs.append(out)
    return outputs


def batch_clean_voice_tracks(
    input_paths: list[Path],
    output_dir: Path,
    **voice_clean_kwargs,
) -> list[Path]:
    """Apply clean_voice_pauses to multiple files."""
    output_dir.mkdir(exist_ok=True, parents=True)
    outputs = []
    for inp in input_paths:
        out = output_dir / f"{inp.stem}_voice_clean.m4a"
        clean_voice_pauses(inp, out, **voice_clean_kwargs)
        outputs.append(out)
    return outputs


# ─────────────────────────────────────────────────────────────────────
# 🆕 M85 (2026-05-29) — B-roll asset intake auto-normalize
# 通用 b-roll 素材入庫時一鍵：strip audio (M29) + conform fps (M81)
# Born from: transitions/ 資料夾反覆塞 24fps + 帶 BGM 的 AI 生成素材，
#            每次都靠人手動 ffmpeg strip + conform → 違反「規則→自動機制」家族。
# 整合 M29 (strip b-roll audio) + M81 (fps conform) + M84 (全域掃描收尾)。
# ─────────────────────────────────────────────────────────────────────


def normalize_broll_asset(
    asset_path: Path,
    target_fps: int = 30,
    strip_audio: bool = True,
    backup: bool = True,
    backup_dir_name: str = "_intake_bak",
    reencode_crf: int = 18,
) -> dict:
    """M85 — Normalize ONE b-roll asset for CapCut import.

    Detects + fixes the 2 recurring intake problems:
      - M29: b-roll carries source audio / BGM → strip (b-roll 不該帶原音)
      - M81: source fps ≠ timeline fps → conform (否則 CapCut 播放速度 bug)

    Smart re-encode strategy:
      - audio-only fix (fps already OK)  → `-c:v copy -an` (LOSSLESS, fast)
      - fps fix (with or without audio)  → `-vf fps=N -c:v libx264` (re-encode)
      - already clean                    → skip, no-op

    Args:
        asset_path: video file to normalize (modified in-place via temp swap)
        target_fps: timeline fps to conform to (default 30)
        strip_audio: True = remove any audio track (M29)
        backup: True = copy original to {parent}/{backup_dir_name}/ before touching
        backup_dir_name: subfolder name for backups
        reencode_crf: libx264 CRF when fps re-encode needed (18 = high quality)

    Returns: dict {
        asset: str, action: str ("skip"|"strip_only"|"conform"|"strip+conform"),
        orig_fps: str, orig_has_audio: bool, final_fps: str, backed_up: bool,
    }
    """
    asset_path = Path(asset_path)

    def _probe(stream, entry):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", stream,
             "-show_entries", f"stream={entry}", "-of", "default=nw=1:nk=1",
             str(asset_path)],
            capture_output=True, text=True,
        )
        return r.stdout.strip()

    orig_fps = _probe("v:0", "avg_frame_rate")
    orig_audio_codec = _probe("a:0", "codec_name")
    has_audio = bool(orig_audio_codec)

    need_strip = strip_audio and has_audio
    need_conform = orig_fps != f"{target_fps}/1"

    if not need_strip and not need_conform:
        return {"asset": asset_path.name, "action": "skip",
                "orig_fps": orig_fps, "orig_has_audio": has_audio,
                "final_fps": orig_fps, "backed_up": False}

    if backup:
        bak_dir = asset_path.parent / backup_dir_name
        bak_dir.mkdir(exist_ok=True)
        backup_target = bak_dir / asset_path.name
        if not backup_target.exists():   # don't overwrite an earlier original
            import shutil
            shutil.copy2(str(asset_path), str(backup_target))

    tmp = asset_path.with_name(asset_path.stem + "_normtmp.mp4")

    if need_conform:
        # fps change forces re-encode
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-i", str(asset_path), "-vf", f"fps={target_fps}",
               "-c:v", "libx264", "-crf", str(reencode_crf), "-preset", "medium",
               "-pix_fmt", "yuv420p"]
        cmd += ["-an"] if strip_audio else ["-c:a", "copy"]
        action = "strip+conform" if need_strip else "conform"
    else:
        # audio-only strip → lossless video copy
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-i", str(asset_path), "-c:v", "copy", "-an"]
        action = "strip_only"
    cmd.append(str(tmp))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"normalize_broll_asset failed ({asset_path.name}): {result.stderr[-300:]}")

    import shutil
    shutil.move(str(tmp), str(asset_path))

    final_fps = _probe("v:0", "avg_frame_rate")
    return {"asset": asset_path.name, "action": action,
            "orig_fps": orig_fps, "orig_has_audio": has_audio,
            "final_fps": final_fps, "backed_up": backup}


def batch_normalize_broll_folder(
    folder: Path,
    target_fps: int = 30,
    strip_audio: bool = True,
    exts: tuple = (".mp4", ".mov", ".m4v", ".mkv", ".avi"),
    skip_dirs: tuple = ("_intake_bak", "_24fps_bak", "_with_audio_bak",
                        "_archive", "_pending_delete", "__pycache__"),
    verbose: bool = True,
) -> dict:
    """M85 + M84 — Normalize ALL b-roll in a folder (asset library intake sweep).

    Walks `folder` (NON-recursive by default into skip_dirs), runs
    normalize_broll_asset on every video. This is the「素材入庫」one-liner
    that固化 the manual strip+conform pipeline + M84 全域掃描收尾 內建.

    Usage (new assets dropped into transitions/):
        from silent_vlog_maker import batch_normalize_broll_folder
        report = batch_normalize_broll_folder("D:/.../assets/broll/transitions/")
        # → every file guaranteed 30fps + no-audio, originals backed up

    Returns: dict {
        total: int, normalized: int, skipped: int,
        results: [normalize_broll_asset() dict, ...],
        still_dirty: [str, ...],   # M84 收尾: any file NOT 30fps+silent after run
    }
    """
    folder = Path(folder)
    results = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        if any(sd in str(f) for sd in skip_dirs):
            continue
        r = normalize_broll_asset(f, target_fps=target_fps, strip_audio=strip_audio)
        results.append(r)
        if verbose:
            icon = "·" if r["action"] == "skip" else "✓"
            print(f"  {icon} [{r['action']:13}] {r['asset'][:45]}  "
                  f"{r['orig_fps']}→{r['final_fps']} audio={r['orig_has_audio']}")

    # 🆕 M84 收尾驗證：re-grep entire folder, assert all clean
    still_dirty = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        if any(sd in str(f) for sd in skip_dirs):
            continue
        fps_r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=avg_frame_rate", "-of", "default=nw=1:nk=1", str(f)],
            capture_output=True, text=True).stdout.strip()
        aud_r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", str(f)],
            capture_output=True, text=True).stdout.strip()
        if fps_r != f"{target_fps}/1" or (strip_audio and aud_r):
            still_dirty.append(f"{f.name} (fps={fps_r} audio={aud_r or 'none'})")

    normalized = sum(1 for r in results if r["action"] != "skip")
    return {
        "total": len(results),
        "normalized": normalized,
        "skipped": len(results) - normalized,
        "results": results,
        "still_dirty": still_dirty,
    }
