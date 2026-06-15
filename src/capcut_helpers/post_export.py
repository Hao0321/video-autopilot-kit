"""
capcut_helpers.post_export — ffmpeg post-process MANDATORY final step (M55).

關鍵教訓 M55：CapCut Export 即使 JSON 4-level mute 100% 仍漏 B-roll 原音。
必須 ffmpeg post-process force-mix BGM 才是真的 clean audio。

加 M56：美食 vlog outro card 標準（店名 + 地址 + 可選電話/時間）。
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def escape_textfile_path(p: Path) -> str:
    """ffmpeg textfile= path 必須 escape backslash + colon."""
    return str(p).replace("\\", "/").replace(":", "\\:")


def _probe_duration(media_path) -> float:
    """ffprobe format=duration with returncode check (2026-05-29 audit #3 fix).

    Raises clear RuntimeError on ffprobe failure instead of opaque ValueError
    from float("") when stdout is empty.
    """
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(media_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(
            f"ffprobe duration failed for {media_path}: "
            f"rc={r.returncode} stderr={r.stderr[-200:]}"
        )
    return float(r.stdout.strip())


def _player_safe_vcodec_flags(fps: int = 30, crf: int = 18) -> list:
    """M83 (2026-05-27) 保守 player-safe libx264 video flags — single source of truth.

    v11-FINAL-conservative.mp4 出貨 profile。被 reencode_player_safe() +
    trim_to_voice_end(player_safe=True) 共用，避免 ffmpeg flag drift（DRY）。
    刻意 **不含** -movflags +faststart（M83：線性 moov box 在尾，避免 player
    對 NVENC/B-frame ordering 的 time-counter quirk）。
    """
    return [
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        "-bf", "0",                                    # 無 B-frames
        "-vsync", "cfr", "-r", str(fps),               # Force CFR
        "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0",  # closed GOP
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    ]


def _bgm_loopfill_chain(bgm_dur: float, total: float, vol: float,
                        fade_in: float, fade_out: float,
                        xfade: float = 1.5, loop_fill: bool = True) -> str:
    """M79 v2 (2026-06-01): build ffmpeg `[1:a] ... [a]` audio chain filling `total` sec.

    若 bgm_dur < total 且 loop_fill → `asplit` N 份用 `acrossfade` 串接 loop 填滿，
    接縫 xfade 秒疊化（song-end ⨯ song-start），**畫面還在播音樂就不能停**（絕不 fade-to-silence）。
    推翻 v1 的 no-loop/apad-silence（用戶「我不是說過要循環嗎」）。
    """
    import math
    fo_start = max(0.0, total - fade_out)
    if (bgm_dur >= total) or (not loop_fill):
        end = min(bgm_dur, total)
        return (f"[1:a]atrim=0:{end},afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={fo_start}:d={fade_out},volume={vol}[a]")
    advance = max(0.1, bgm_dur - xfade)
    n = max(2, math.ceil((total - xfade) / advance))
    parts = ["[1:a]asplit=" + str(n) + "".join(f"[c{i}]" for i in range(n)) + ";"]
    prev = "c0"
    for i in range(1, n):
        out = f"x{i}"
        parts.append(f"[{prev}][c{i}]acrossfade=d={xfade}:c1=tri:c2=tri[{out}];")
        prev = out
    parts.append(f"[{prev}]atrim=0:{total},afade=t=in:st=0:d={fade_in},"
                 f"afade=t=out:st={fo_start}:d={fade_out},volume={vol}[a]")
    return "".join(parts)


def force_mix_bgm(
    input_mp4: Path,
    output_mp4: Path,
    bgm_path: Path,
    bgm_volume: float = 0.25,
    fade_in_sec: float = 0.5,
    fade_out_sec: float = 2.0,
    duration_sec: Optional[float] = None,
    loop_fill: bool = True,   # 🆕 M79 v2 (2026-06-01): loop BGM 填滿全片 + crossfade 接縫
    no_loop=None,             # deprecated alias (M79 v1) — 若給值: loop_fill = not no_loop
) -> Path:
    """M55 + M79: ffmpeg 完全 replace audio with BGM-only.

    🚨 2026-05-27 DEPRECATED for教學長片 (M84)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    這個函數 strip 掉 voiceover 只留 BGM — **不適用人聲教學影片**。
    #006 試了多次 force_mix_bgm 替換 audio → 全部出 sync drift 因為:
      - -c:v copy 保留 video PTS (CapCut 出來)
      - 但 audio 從 filter graph 重組 (atrim/apad/volume)
      - 兩條 timestamp 軸沒 -shortest 對齊 → 0.1-0.5s drift 累積
    教學長片 / 有人聲影片，請改用 **single-pass ffmpeg with -t**：
      ffmpeg -i v_capcut.mp4 -filter_complex "...trim=0:{voice_end},apad=whole_dur={total}..." \
             -c:v libx264 -bf 0 -vsync cfr -r 30 -shortest output.mp4
    只有「silent vlog 純 BGM 影片」適合用這個函數。
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    用法：CapCut Export 完 → 一定要跑這個 → 才是真的 clean。

    🆕 M79 v2 (2026-06-01 修正): loop_fill=True default — BGM 短於 video 時 **loop 填滿到片尾**
    + 1.5s crossfade 接縫（song-end ⨯ song-start 疊化），畫面還在播音樂就不能停。
    **推翻 v1 的 no-loop / fade-to-silence**（用戶看 v12「我不是說過要循環嗎」）。
    舊 `no_loop=` 參數保留為 deprecated alias（給值 → loop_fill = not no_loop）。

    Args:
        input_mp4: source mp4 (audio leaked)
        output_mp4: destination (can be same as input — atomic via temp)
        bgm_path: BGM mp3
        bgm_volume: 0.25 (25%) default
        fade_in_sec / fade_out_sec
        duration_sec: clip duration (if None, ffprobe input)
        loop_fill: if True (default M79 v2), BGM loops to fill video w/ crossfade seam
        no_loop: DEPRECATED (M79 v1) — if set, loop_fill = not no_loop

    Returns: output_mp4 path
    """
    if duration_sec is None:
        duration_sec = _probe_duration(input_mp4)

    # 🆕 M79 v2: auto-detect BGM source duration + deprecated no_loop alias
    bgm_source_dur = _probe_duration(bgm_path)
    if no_loop is not None:                      # back-compat: old callers passing no_loop=
        loop_fill = not no_loop

    # Use temp file for atomic write (avoid corrupting if output == input)
    tmp = output_mp4.with_name(output_mp4.stem + "_tmp.mp4")

    # 🆕 M79 v2: loop BGM 填滿全片 + crossfade 接縫 (絕不 fade-to-silence)
    audio_chain = _bgm_loopfill_chain(
        bgm_source_dur, duration_sec, bgm_volume,
        fade_in_sec, fade_out_sec, loop_fill=loop_fill,
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-i", str(bgm_path),
        "-filter_complex", audio_chain,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",  # don't re-encode video (faster + no quality loss)
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        str(tmp),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"force_mix_bgm failed: {result.stderr[-500:]}")

    import shutil
    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def _resolve_cjk_font() -> str:
    """找一個系統 CJK 字型 → 回 ffmpeg-escaped 路徑。找不到 raise 清楚錯誤。"""
    import glob as _g
    cands = [
        "C:/Windows/Fonts/NotoSansTC-Black.otf", "C:/Windows/Fonts/NotoSansCJK-Black.ttc",
        "C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/msyh.ttc",  # 微軟正黑/雅黑
        "/System/Library/Fonts/PingFang.ttc",                       # macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",   # Linux
    ]
    cands += _g.glob("/usr/share/fonts/**/NotoSansCJK*.*", recursive=True)
    for p in cands:
        if os.path.exists(p):
            return p.replace(":", "\\:")  # ffmpeg drawtext 需 escape 磁碟代號冒號
    raise FileNotFoundError(
        "找不到 CJK 字型 — 請傳 font_path= 指定（ffmpeg drawtext 用），"
        "或安裝 Noto Sans CJK / 微軟正黑體。")


def add_outro_card(
    input_mp4: Path,
    output_mp4: Path,
    title_line: str,
    address_line: str,
    extra_line: Optional[str] = None,
    outro_start_sec: float = -5.0,  # negative = "from end"
    outro_end_sec: Optional[float] = None,  # default = full duration
    font_path: Optional[str] = None,   # None → runtime 找 CJK 字型（不寫死作者機器路徑）
    text_dir: Optional[Path] = None,
) -> Path:
    """M56: 美食 vlog 結尾 outro card (店名 + 地址 + 可選電話/時間).

    Args:
        input_mp4: source (must already have force_mix_bgm done)
        output_mp4: destination
        title_line: 店名 + 分店 (e.g. "長生塩人 淡水店")
        address_line: 地址 (e.g. "新北市淡水區重建街 206 號")
        extra_line: optional 3rd line（電話 / 營業時間）
        outro_start_sec: negative = N seconds from end (default last 5 sec)
        outro_end_sec: default = video duration
        font_path: ffmpeg-escaped font path
        text_dir: where to write text files (default same as output)
    """
    # 字型 runtime 解析（不寫死作者機器的絕對路徑）— 找系統 CJK 字型，找不到清楚報錯
    if font_path is None:
        font_path = _resolve_cjk_font()

    # Get duration (2026-05-29 audit #3: returncode-checked helper)
    duration_sec = _probe_duration(input_mp4)

    if outro_end_sec is None:
        outro_end_sec = duration_sec
    if outro_start_sec < 0:
        outro_start_sec = duration_sec + outro_start_sec

    # Write text files (M38 — no emoji)
    text_dir = text_dir or output_mp4.parent / "_outro_txt"
    text_dir.mkdir(exist_ok=True)
    t_title = text_dir / "outro_title.txt"
    t_address = text_dir / "outro_address.txt"
    t_title.write_text(title_line, encoding="utf-8")
    t_address.write_text(address_line, encoding="utf-8")

    tf_title = escape_textfile_path(t_title)
    tf_address = escape_textfile_path(t_address)

    fade_in = 0.4
    fade_out = 0.5
    alpha_expr = (
        f"if(lt(t,{outro_start_sec}),0,"
        f"if(lt(t,{outro_start_sec + fade_in}),(t-{outro_start_sec})/{fade_in},"
        f"if(gt(t,{outro_end_sec - fade_out}),({outro_end_sec}-t)/{fade_out},1)))"
    )
    enable_expr = f"between(t,{outro_start_sec},{outro_end_sec})"

    fc_parts = [
        f"[0:v]"
        # Line 1 — title (店名 gold)
        f"drawtext=fontfile='{font_path}':textfile='{tf_title}':"
        f"fontsize=64:fontcolor=#FFD700:"
        f"borderw=4:bordercolor=black@0.8:"
        f"box=1:boxcolor=black@0.7:boxborderw=24:"
        f"x=(w-tw)/2:y=h-380:"
        f"alpha='{alpha_expr}':enable='{enable_expr}',"
        # Line 2 — address (白)
        f"drawtext=fontfile='{font_path}':textfile='{tf_address}':"
        f"fontsize=44:fontcolor=white:"
        f"borderw=3:bordercolor=black@0.8:"
        f"box=1:boxcolor=black@0.6:boxborderw=18:"
        f"x=(w-tw)/2:y=h-280:"
        f"alpha='{alpha_expr}':enable='{enable_expr}'"
    ]

    if extra_line:
        t_extra = text_dir / "outro_extra.txt"
        t_extra.write_text(extra_line, encoding="utf-8")
        tf_extra = escape_textfile_path(t_extra)
        fc_parts[0] += (
            f","
            f"drawtext=fontfile='{font_path}':textfile='{tf_extra}':"
            f"fontsize=36:fontcolor=white:"
            f"borderw=2:bordercolor=black@0.8:"
            f"box=1:boxcolor=black@0.5:boxborderw=14:"
            f"x=(w-tw)/2:y=h-200:"
            f"alpha='{alpha_expr}':enable='{enable_expr}'"
        )

    fc_parts[0] += "[v]"
    fc = ";".join(fc_parts)

    tmp = output_mp4.with_name(output_mp4.stem + "_outro_tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "8M", "-maxrate", "12M", "-bufsize", "16M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "copy",  # audio already clean from force_mix_bgm
        "-movflags", "+faststart",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"add_outro_card failed: {result.stderr[-500:]}")

    import shutil
    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def _parse_silencedetect(stderr: str, total: float) -> float:
    """M82 純解析層 — silencedetect stderr → 人聲真結尾秒數。

    抽成獨立 pure function（不碰 subprocess）→ 可 unit-test，防 ffmpeg 版本
    輸出格式漂移 silently 弄壞 M82 邏輯（見檔尾 __main__ self-test）。
    """
    starts, ends = [], []
    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.split("silence_start:")[1].strip().split()[0]))
            except (ValueError, IndexError):
                pass
        elif "silence_end:" in line:
            try:
                seg = line.split("silence_end:")[1].strip()
                ends.append(float(seg.split("|")[0].strip().split()[0]))
            except (ValueError, IndexError):
                pass
    if starts:
        last_start = starts[-1]
        trailing = (len(ends) < len(starts))                  # 末段 silence 無 end → 跑到 EOF
        if not trailing and ends and (total - ends[-1]) < 0.5:  # 或末段 silence 緊貼 EOF
            trailing = True
        if trailing and 0 < last_start < total:
            return round(last_start, 3)
    return round(total, 3)


def detect_voice_end(
    media_path: Path,
    noise_db: float = -30.0,
    min_silence_sec: float = 2.0,
) -> float:
    """M82 (2026-05-27): 找人聲真結尾 = 最後一段有聲內容的結束點。

    用 ffmpeg silencedetect 掃 silence 區間。若末段是長 silence（b-roll 撐到
    timeline 末段純靜音，#006 v10 45s 空白尾 bug），回傳該 trailing silence 的
    start（= 人聲真結尾），讓 caller trim 到這。若全程有聲 / 無 trailing silence，
    回傳完整 duration。

    回傳秒數（float, 3dp）。
    """
    total = _probe_duration(media_path)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(media_path),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_sec}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return _parse_silencedetect(r.stderr, total)   # silencedetect 輸出在 stderr


def reencode_player_safe(
    input_mp4: Path,
    output_mp4: Path,
    fps: int = 30,
    crf: int = 18,
) -> Path:
    """M83 (2026-05-27): 保守 re-encode → 對 PotPlayer 等 player time-counter 友善。

    v11-FINAL-conservative.mp4 出貨用的就是這個 profile。NVENC + B-frames +
    faststart 會讓某些 player 時間軸 counter 對不上實際畫面（B-frame ordering
    quirk）；ffprobe PTS 正確 / YouTube 沒問題，但用戶本機檢查會誤判為檔案 bug。

    video 用 _player_safe_vcodec_flags()（libx264 / -bf 0 / CFR / closed GOP /
    無 faststart）。audio 直接 copy（假設來源 audio 已 clean / 已對齊，M83 只處理
    video 編碼層）。

    Returns: output_mp4 path
    """
    tmp = output_mp4.with_name(output_mp4.stem + "_psafe_tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        *_player_safe_vcodec_flags(fps=fps, crf=crf),
        "-c:a", "copy",   # M83: 不動 audio（避免 re-encode drift）
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"reencode_player_safe failed: {result.stderr[-500:]}")
    import shutil
    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def trim_to_voice_end(
    input_mp4: Path,
    output_mp4: Path,
    tail_pad_sec: float = 0.0,
    noise_db: float = -30.0,
    min_silence_sec: float = 2.0,
    player_safe: bool = True,
) -> dict:
    """M82 + M83: trim timeline 到人聲真結尾（+ 可選 outro tail pad），一步出 ship。

    timeline 長度由人聲（content）決定，不是讓素材（form）撐到末段純靜音
    （#006 v10 45s 空白尾 bug）。tail_pad_sec 給 outro card 留尾（例：5-7s）。

    player_safe=True（預設）→ 用 M83 保守 profile 重編碼，FINAL ship 一步到位。
    player_safe=False → -c:v copy（快，但切點 snap 到 keyframe，非 final 用）。

    Returns: {original_dur, voice_end, trimmed_to, trimmed_sec}
    """
    total = _probe_duration(input_mp4)
    voice_end = detect_voice_end(input_mp4, noise_db, min_silence_sec)
    cut_at = round(min(voice_end + tail_pad_sec, total), 3)

    vcodec = _player_safe_vcodec_flags() if player_safe else ["-c:v", "copy"]
    tmp = output_mp4.with_name(output_mp4.stem + "_trim_tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-t", f"{cut_at}",
        *vcodec,
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"trim_to_voice_end failed: {result.stderr[-500:]}")
    import shutil
    shutil.move(str(tmp), str(output_mp4))
    return {
        "original_dur": total,
        "voice_end": voice_end,
        "trimmed_to": cut_at,
        "trimmed_sec": round(total - cut_at, 3),
    }


def finalize_export(
    capcut_export_mp4: Path,
    final_mp4: Path,
    bgm_path: Path,
    outro_title: str,
    outro_address: str,
    outro_extra: Optional[str] = None,
    bgm_volume: float = 0.25,
) -> dict:
    """One-shot M55+M56: force-mix BGM → add outro card → save final.

    Returns dict with verification stats.
    """
    print(f"  [1/2] M55 force-mix BGM ({bgm_volume * 100:.0f}% vol)...")
    intermediate = final_mp4.with_name(final_mp4.stem + "_bgm_only.mp4")
    force_mix_bgm(capcut_export_mp4, intermediate, bgm_path, bgm_volume=bgm_volume)
    print(f"    ✓ Audio replaced — B-roll原音 stripped")

    print(f"  [2/2] M56 add outro card...")
    add_outro_card(intermediate, final_mp4,
                   title_line=outro_title,
                   address_line=outro_address,
                   extra_line=outro_extra)
    intermediate.unlink(missing_ok=True)
    print(f"    ✓ Outro added: {outro_title} / {outro_address}")

    # Verify
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", str(final_mp4)],
        capture_output=True, text=True
    )
    stats = {}
    for line in result.stdout.splitlines():
        for k in ("width=", "height=", "duration=", "bit_rate=", "size="):
            if line.startswith(k):
                stats.setdefault(k.rstrip("="), line.split("=", 1)[1])
                break
    stats["file_size_mb"] = final_mp4.stat().st_size // 1024 // 1024
    return stats


if __name__ == "__main__":
    # ── M82 _parse_silencedetect regression self-test (synthetic ffmpeg stderr) ──
    # 防 ffmpeg 版本輸出格式漂移 silently 弄壞 voice-end 偵測。純邏輯，不需檔案。
    def _t(name, stderr, total, expect):
        got = _parse_silencedetect(stderr, total)
        ok = abs(got - expect) < 0.01
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} expect={expect}")
        assert ok, f"{name}: {got} != {expect}"

    # 1) 末段 silence 跑到 EOF（無 matching silence_end）→ 人聲結束於 silence_start
    _t("trailing-to-EOF",
       "[silencedetect @ 0x55] silence_start: 165.381\n", 171.711, 165.381)
    # 2) 末段 silence 有 end 但緊貼 total（< 0.5s）→ trailing，回 start
    _t("trailing-near-EOF",
       "silence_start: 100.0\nsilence_end: 171.5 | silence_duration: 71.5\n", 171.711, 100.0)
    # 3) 中段 silence 後人聲又恢復（gap 非 trailing）→ 回完整 duration
    _t("mid-gap-not-trailing",
       "silence_start: 50.0\nsilence_end: 52.0 | silence_duration: 2.0\n", 171.711, 171.711)
    # 4) 全程有聲 / 無 silence → 回完整 duration
    _t("no-silence", "", 171.711, 171.711)
    # 5) 多段 silence，最後一段 trailing-to-EOF
    _t("multi-then-trailing",
       "silence_start: 10\nsilence_end: 12 | x\nsilence_start: 160.0\n", 171.711, 160.0)
    print("post_export _parse_silencedetect self-test: ALL PASS")
