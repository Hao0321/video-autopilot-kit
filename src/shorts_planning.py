"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import os
from av_util import grab_frame


def _clip_metrics(norm_path: str, dur: float, step: float = 0.5) -> list:
    """逐 step 秒量 (銳利度, 亮度, 與前一格的變化量) → 找「畫面穩定又有內容」的窗。

    銳利度用 Laplacian 變異數 proxy（對焦準/有主體的幀分數高）；
    變化量用相鄰幀差（低=鏡頭穩，高=在搖）。
    """
    import numpy as np
    from PIL import Image
    rows, prev = [], None
    t = 0.0
    tmp = norm_path + ".m.png"
    while t < dur - 0.05:
        if grab_frame(norm_path, "%.2f" % t, tmp, vf="scale=120:214"):
            a = np.asarray(Image.open(tmp).convert("L"), dtype=float)
            lap = float(np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean())
            bri = float(a.mean())
            mot = float(np.abs(a - prev).mean()) if prev is not None else 0.0
            rows.append({"t": round(t, 2), "sharp": round(lap, 2),
                         "bright": round(bri, 1), "motion": round(mot, 2)})
            prev = a
        t += step
    if os.path.exists(tmp):
        os.remove(tmp)
    return rows


def _best_window(rows: list, want: float, step: float = 0.5) -> tuple:
    """挑「銳利度高 + 亮度不過暗 + 鏡頭不亂晃」的連續窗；回 (in_sec, score)。"""
    n = max(1, int(round(want / step)))
    if len(rows) < n:
        return (0.0, 0.0)
    best, bi = -1e9, 0
    for i in range(0, len(rows) - n + 1):
        w = rows[i:i + n]
        sharp = sum(r["sharp"] for r in w) / n
        bright = sum(r["bright"] for r in w) / n
        motion = sum(r["motion"] for r in w) / n
        # 亮度懲罰：太暗(<60)或過曝(>210) 扣分（樣本11 暗綠遠景的教訓）
        pen = 0.0
        if bright < 60:
            pen += (60 - bright) * 0.8
        if bright > 210:
            pen += (bright - 210) * 0.8
        score = sharp * 1.6 - motion * 1.1 - pen
        if score > best:
            best, bi = score, i
    return (rows[bi]["t"], round(best, 1))


def _wave_segment_durations(count: int, budget: float) -> list[float]:
    """把中段排成快→推進→慢呼吸→快 payoff，而不是每顆等長。

    低能段的鏡頭較長、高能段較短。輸出仍守 Shorts gate 的單顆安全範圍，
    且總和盡量等於 budget；這只是畫面節奏，不替素材語意做假判斷。
    """
    if count <= 0:
        return []
    patterns = {
        1: [1.0],
        2: [.82, 1.18],
        3: [.76, 1.28, .82],
        4: [.78, .96, 1.34, .72],
        5: [.74, .94, 1.10, 1.34, .68],
        6: [.72, .90, 1.04, 1.36, .66, .86],
    }
    weights = patterns.get(count, [1.0] * count)
    unit = max(.01, float(budget)) / sum(weights)
    vals = [max(1.8, min(3.6, unit * w)) for w in weights]
    # clamp 後把誤差分散回仍有空間的鏡頭，避免最後一顆突然異常長／短。
    for _ in range(20):
        diff = float(budget) - sum(vals)
        if abs(diff) < .03:
            break
        room = [i for i, v in enumerate(vals)
                if (diff > 0 and v < 3.58) or (diff < 0 and v > 1.82)]
        if not room:
            break
        share = diff / len(room)
        for i in room:
            vals[i] = max(1.8, min(3.6, vals[i] + share))
    return [round(v, 2) for v in vals]


def auto_plan(info: dict, target: float = 16.0) -> dict:
    """挑 hook、排 cinematic wave 片段、算 loop 對齊、湊進 13-25s。

    留給 Claude 的只剩「文字」：place / what / addr / 每段字幕。
    """
    clips = [c for c in info["clips"] if c["dur"] >= 1.6]
    if not clips:
        return {}
    print("[auto] 分析 %d 支 clip 的畫面品質…" % len(clips))
    for c in clips:
        c["rows"] = _clip_metrics(c["norm"], c["dur"])
        c["best_in"], c["score"] = _best_window(c["rows"], min(2.6, c["dur"] - 0.2))

    # hook = 分數最高那支（銳利、亮度適中、鏡頭穩）
    hook = max(clips, key=lambda c: c["score"])
    others = [c for c in clips if c is not hook]
    others.sort(key=lambda c: c["score"], reverse=True)

    # 首段 2.0s；loop 段長度 1.6s（需 hook 的 best_in ≥1.6 才收得回，否則往後挪）
    loop_len = 1.6
    hook_in = max(hook["best_in"], loop_len + 0.1)
    if hook_in + 2.0 > hook["dur"]:
        hook_in = max(loop_len + 0.1, hook["dur"] - 2.1)
    segs = [(hook["norm"], round(hook_in, 2), 2.0)]

    # 中段：用能量波分配，不再機械等長。低能呼吸較長、payoff 前後較短。
    mid = others[:6] if others else []
    if mid:
        budget = target - 2.0 - loop_len
        wave_durations = _wave_segment_durations(len(mid), budget)
        for c, wanted in zip(mid, wave_durations):
            win, _ = _best_window(c["rows"], min(wanted, c["dur"] - 0.2))
            take = min(wanted, c["dur"] - win - 0.1)
            if take >= 1.8:
                segs.append((c["norm"], round(win, 2), round(take, 1)))
    # loop 段：結束點 == 首段起點
    segs.append((hook["norm"], round(hook_in - loop_len, 2), loop_len))

    total = round(sum(s[2] for s in segs), 1)
    # 落在 13-25 外 → 微調中段
    if total < 13.0 and len(segs) > 2:
        add = (13.2 - total) / (len(segs) - 2)
        segs = [segs[0]] + [(f, i, round(d + add, 1)) for f, i, d in segs[1:-1]] + [segs[-1]]
    elif total > 25.0 and len(segs) > 3:
        segs = [segs[0]] + segs[1:1 + 5] + [segs[-1]]
        over = round(sum(s[2] for s in segs), 1) - 24.5
        if over > 0:
            cut = over / (len(segs) - 2)
            segs = [segs[0]] + [(f, i, round(max(2.0, d - cut), 1)) for f, i, d in segs[1:-1]] + [segs[-1]]

    total = round(sum(s[2] for s in segs), 1)
    print("[auto] cinematic wave 排出 %d 段 / %.1fs（hook=%s，loop 已對齊）"
          % (len(segs), total, os.path.basename(hook["norm"])))
    return {"segs": segs, "hook": hook["norm"], "total": total}
