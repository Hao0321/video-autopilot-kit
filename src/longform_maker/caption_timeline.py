"""Longform maker/caption timeline; one implementation behind the compatibility facade."""
from __future__ import annotations




def to_master_events(beat_lines, offsets, trims, hold=0.6, min_show=0.30):
    """beat 內真實時間 → master 時間軸事件。
       beat_lines={bk:[(s,e,text)]}（beat 原始秒）；offsets=narration_offsets.json dict（含 _speed）；
       trims={bk: beat 被 voice_chain 剪掉的頭秒數 = f0 - lead_pad}。
       s_master = beat_start + (s-trim)/SP；end 撐到下一行開始前(hold 上限)不留字幕盒閃爍空檔（M93）。"""
    sp = float(offsets.get("_speed", 1.0))
    evs = []
    for bk, lines in beat_lines.items():
        off, dur, tr = offsets[bk]["start"], offsets[bk]["dur"], trims[bk]
        for j, (rs, re_, txt) in enumerate(lines):
            s = max(off, off + (rs - tr) / sp)
            e = off + (re_ - tr) / sp
            if j + 1 < len(lines):
                nxt = off + (lines[j + 1][0] - tr) / sp
                e = min(nxt - 0.02, e + hold)
            e = min(off + dur + 0.25, e)
            if e - s >= min_show:
                evs.append((round(s, 3), round(e, 3), txt))
    evs.sort()
    return evs

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
