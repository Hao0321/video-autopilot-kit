"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

if __package__:
    from .shorts_music_selection import _run, _probe_dur, find_music_highlight
else:
    from shorts_music_selection import _run, _probe_dur, find_music_highlight
import os, json, hashlib


_NORMV = ('scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
          'setsar=1,fps=30,format=yuv420p')


def _music_breath_filter(visual_plan):
    """把 visual plan 的 payoff 前呼吸真正套到 BGM；room tone 類素材則由別條 pipeline 保留。

    使用短線性 ramp 而非瞬間音量跳變，避免 click。回傳可直接接在 ffmpeg audio chain
    後面的 filter 片段；沒有計畫時保持舊行為。
    """
    win = ((visual_plan or {}).get("audio_plan") or {}).get("pre_payoff_space") or {}
    try:
        start, end = float(win["start"]), float(win["end"])
        gain = 10 ** (float(win.get("music_db_delta", -8)) / 20.0)
    except (KeyError, TypeError, ValueError):
        return ""
    if end - start < .12 or start < 0:
        return ""
    ramp = min(.14, (end - start) / 3.0)
    up = end - ramp
    expr = ("if(lt(t,{s:.3f}),1,"
            "if(lt(t,{sr:.3f}),1-(1-{g:.5f})*(t-{s:.3f})/{r:.3f},"
            "if(lt(t,{u:.3f}),{g:.5f},"
            "if(lt(t,{e:.3f}),{g:.5f}+(1-{g:.5f})*(t-{u:.3f})/{r:.3f},1))))"
            ).format(s=start, sr=start+ramp, g=gain, r=ramp, u=up, e=end)
    return ",volume='%s':eval=frame" % expr


def _render_short_visuals(segs, visual_plan, base, work_dir, out):
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for p, ss, d in segs:
        cmd += ['-ss', str(ss), '-t', str(d), '-i', p]
    parts, labs = [], ''
    grade_reports, grade_filters = [], {}
    color_system = (visual_plan or {}).get("color_system") or {}
    if color_system:
        from visual_master import source_filter
        grade_cache = os.path.join(work_dir or os.path.dirname(os.path.abspath(out)), "color_luts")
        os.makedirs(grade_cache, exist_ok=True)
        for source, _start, _duration in segs:
            if source not in grade_filters:
                grade_filters[source], report = source_filter(source, color_system, grade_cache)
                grade_reports.append(report)
    for i, (source, _, d) in enumerate(segs):
        grade = grade_filters.get(source, "")
        grade = ("," + grade) if grade else ""
        parts.append(f'[{i}:v]{_NORMV}{grade},trim=duration={d},setpts=PTS-STARTPTS[v{i}]'); labs += f'[v{i}]'
    fc = ';'.join(parts) + ';' + labs + f'concat=n={len(segs)}:v=1:a=0[vout]'
    vis = base + '_vis.mp4'
    # ── 視覺層快取（2026-07-29 R6）：迭代最常見的是「改字幕/換 BGM 重 build」，
    # segs 沒動就不必重跑最貴的 concat+encode。key=segs 全量 + 各來源檔 mtime，
    # 存 sidecar json；任何一項變了就重編，**寧可多編不可錯用**。
    # Bind the cache to the renderer implementation as well as media inputs.
    # Otherwise a normalization/grade/layout fix can keep reusing pixels made
    # by an older runtime and make a genuine system upgrade look ineffective.
    _renderer_sha = hashlib.sha256(open(__file__, 'rb').read()).hexdigest()
    _vis_key = {"renderer_sha256": _renderer_sha,
                "segs": [[p, ss, d] for p, ss, d in segs],
                "mtimes": [os.path.getmtime(p) for p, _s, _d in segs],
                "color_system": color_system,
                "grade_filters": grade_filters}
    _vis_side = base + '_vis.json'

    def _vis_cache_ok():
        try:
            return (os.path.exists(vis)
                    and json.load(open(_vis_side, encoding='utf-8')) == _vis_key)
        except Exception:
            return False

    if _vis_cache_ok():
        print('  [cache] visual concat unchanged -> reuse %s' % os.path.basename(vis))
        r = type('R', (), {'returncode': 0})()
    else:
        r = _run(cmd + ['-filter_complex', fc, '-map', '[vout]', '-an', '-c:v', 'libx264',
                        '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '30', vis])
        if not r.returncode:
            json.dump(_vis_key, open(_vis_side, 'w', encoding='utf-8'))
    if r.returncode:
        raise RuntimeError('build_one_short visual failed: ' + r.stderr[-500:])
    return vis, grade_reports, color_system


def _mix_short_audio(base, bgm, bgm_start, cap_for_mux, fade, total, visual_plan, vol):
    start = find_music_highlight(bgm, total) if bgm_start == 'auto' else float(bgm_start)
    fo = max(0.3, total - fade)
    fi = 0.3  # 高光段是從歌中間切入 → 0.3s 快淡入避免硬切爆音
    # acompressor 壓平 BGM 動態（歌的副歌/breakdown 起伏 = 用戶聽到「忽大忽小」）；
    # 壓峰貼近安靜段但保留每拍瞬態(beat 還在)。dynaudnorm/loudnorm 對此無效(實測)，要壓縮器。
    comp = 'acompressor=threshold=-24dB:ratio=4:attack=15:release=200:makeup=3'
    breath_filter = _music_breath_filter(visual_plan)
    if _probe_dur(bgm) < total + 0.5:
        # 歌比影片短 → 會 loop，接縫處跳音(也是忽大忽小一種)。換更長的歌，別硬 loop 短曲。
        print(f'[build_one_short] ⚠ BGM 比影片短會 loop 跳音：{os.path.basename(bgm)} '
              f'({_probe_dur(bgm):.0f}s < {total:.0f}s) — 建議換 ≥{total:.0f}s 的曲子')
    # M115：永遠先產 work candidate，不讓 ffmpeg 在現行成片 inode 上直接 truncate。
    # 這也讓同 volume 的已發布 hard link 保持舊版，不會被下一輪修改連動覆寫。
    mux = base + '_mux.mp4'
    r = _run(['ffmpeg', '-v', 'error', '-y', '-i', cap_for_mux,
              '-ss', f'{start:.2f}', '-stream_loop', '-1', '-i', bgm,
              '-filter_complex',
                f'[1:a]{comp},volume={vol}{breath_filter},afade=t=in:st=0:d={fi},afade=t=out:st={fo:.2f}:d={fade}[a]',
              '-map', '0:v:0', '-map', '[a]', '-t', str(total),
              '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', mux])
    if r.returncode:
        raise RuntimeError('build_one_short mux failed: ' + r.stderr[-500:])
    return mux
