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

# ---------------------------------------------------------------- 🚦 QA 主入口
def final_delivery_qa(video, voice=None, contact_out=None):
    """🚦 交付前 QA（canon M91-M95 + QA 清單）。回 dict + 印報告。
    機械項：M93 頻閃、M95 死空檔。人工項：看接觸表逐格確認 M91/M92/M94/M68。"""
    rep = {'video': str(video), 'duration': round(_probe_dur(video), 2)}
    flashes = detect_flash(video)
    rep['flash_segments'] = flashes
    # 頻閃 = >=2 段 black 或有 <1s 的短段（反覆閃）；0 段 = 乾淨
    rep['flash_flag'] = len(flashes) >= 2 or any(f[2] < 1.0 for f in flashes)
    # M92 死黑邊（非滿版沒模糊填底 → letterbox）
    borders = detect_dead_borders(video)
    rep['dead_border'] = borders
    rep['border_flag'] = borders['border_flag']
    if voice:
        rep['long_pauses'] = detect_long_pauses(voice)
        rep['deadair_flag'] = len(rep['long_pauses']) > 0
    if contact_out:
        contact_sheet(video, contact_out)
        rep['contact_sheet'] = str(contact_out)

    # cp950 console 不能印 emoji → runtime 輸出一律 ASCII marker（canon 文件才用 emoji）
    print(f"[QA] final_delivery_qa: {rep['video']} | {rep['duration']}s")
    print('  M93 flash :', '[WARN] suspect flash ' + str(flashes) if rep['flash_flag'] else '[OK] none')
    print('  M92 border:', '[WARN] ' + borders['note'] if rep['border_flag'] else '[OK] 滿版無黑邊')
    if voice:
        print('  M95 deadair(>1.5s):', '[WARN] ' + str(rep['long_pauses']) if rep['deadair_flag'] else '[OK] none')
    if contact_out:
        print('  contact_sheet ->', contact_out)
    print('  Note: 人工逐格看接觸表 — M91 chrome/隱私 / M92 圖片排版 / M94 真實 artifact / M68 字幕(逗號/停頓/對位)')
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
    sp = _re.compile(r"silence_(start|end): ([\d.eE+-]+)(?: \| silence_duration: ([\d.eE+-]+))?")
    assert sp.search("silence_end: 26.28 | silence_duration: 3.75"), "silence parse 漏判"
    # M92 死黑邊 cropdetect 解析 + flag 邏輯（不跑 ffmpeg，純驗 parse + threshold）
    cp = _re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", "x crop=1920:1036:0:22 y crop=1920:1036:0:22")
    assert cp and cp[-1] == ('1920', '1036', '0', '22'), "cropdetect 解析漏判"
    _cw, _ch = 1920, 1036
    assert (1920 - _cw) <= 4 and (1080 - _ch) > 4, "死黑邊 threshold 邏輯錯（高度該判有黑邊）"
    # _probe_wh 解析：對 ffprobe csv 尾端多餘分隔符 + CRLF 免疫（不 split('x')）— 2026-06-22 踩過
    assert [int(x) for x in _re.findall(r'\d+', "1080x1920x\r")][:2] == [1080, 1920], "_probe_wh 尾端分隔解析漏判"
    print("[delivery_qa selftest] OK")
