# -*- coding: utf-8 -*-
'Competitor vertical-video teardown utilities.\n\nThe OCR path is suitable for extracting candidate captions from burned-in text, but visible product claims still require human verification.\n\nPUBLIC_FIXTURE: documentation and tests use synthetic examples only.'
from __future__ import annotations

import argparse
import glob
import os
import statistics as st
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 字幕帶（比例值，任何解析度通用）：(起始高度比, 帶高比, 右緣裁掉比)
# PUBLIC_FIXTURE: behavior is covered by synthetic tests.
# （某支片 t=6 在 24-27%、t=12 掉到 30%），窄帶會靜默漏掉整段字幕而且不報錯。
# 右緣裁 18% 是為了避開 IG/FB 右欄按鈕列（讚數/留言數會被 OCR 讀成字幕）。
BANDS = {
    "wide":   (0.12, 0.66, 0.18),   # 狀態列以下、帳號列以上，全部掃
    "bottom": (0.58, 0.20, 0.18),
    "top":    (0.12, 0.24, 0.18),
    "mid":    (0.42, 0.24, 0.18),
}


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True, errors="replace")


def probe(path):
    o = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height,r_frame_rate",
              "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout
    vals = [x for x in o.replace("\n", ",").split(",") if x]
    w, h = int(vals[0]), int(vals[1])
    fr = vals[2]
    dur = float(vals[-1])
    num, den = (fr.split("/") + ["1"])[:2]
    return w, h, round(float(num) / float(den), 2), dur


def cuts(path, thresh=0.25):
    'Detect scene changes while retaining the ffmpeg diagnostic stream required by showinfo.'
    out = _run(["ffmpeg", "-hide_banner", "-i", path, "-vf",
                "select='gt(scene,%g)',showinfo" % thresh, "-f", "null", "-"]).stderr
    ts = [float(x.split(":")[1]) for x in out.split() if x.startswith("pts_time:")]
    return [t for t in ts if t > 0.2]


def loudness(path):
    out = _run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128",
                "-f", "null", "-"]).stderr
    vals = [l for l in out.splitlines() if l.strip().startswith("I:")]
    return vals[-1].split()[1] if vals else "?"


def _stats(ts, dur, label):
    iv = [round(b - a, 2) for a, b in zip(ts, ts[1:])]
    print("  %-10s %3d 次 / %5.1f 次每分" % (label, len(ts), len(ts) / dur * 60), end="")
    if iv:
        print("  中位間隔 %.2fs  標準差 %.2f  最短 %.2f" %
              (st.median(iv), st.pstdev(iv) if len(iv) > 1 else 0,
               min(iv)))
    else:
        print()
    return iv


def caption_track(path, band, dur, w, h, step=0.5, min_conf=0.75):
    """抽字幕帶 → OCR → 簡轉繁 → 去重，回 [(t, text)]。缺套件就回 None。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    try:
        from opencc import OpenCC
        cc = OpenCC("s2twp").convert
    except Exception:
        def cc(x):
            return x

    top_r, hgt_r, rcut = BANDS[band]
    y, bh = int(h * top_r), int(h * hgt_r)
    cw = int(w * (1 - rcut))
    crop = "crop=%d:%d:0:%d" % (cw, bh, y)

    # 引擎模組級快取：RapidOCR() 初始化 ~2-3s，掃資料夾時每支重建=N 倍浪費
    global _ENGINE
    try:
        _ENGINE
    except NameError:
        _ENGINE = RapidOCR()
    engine = _ENGINE

    # 前置濾波：帶內畫面沒變就不跑 OCR（OCR 是整條流程最貴的一步，~1-2s/幀）。
    # 字幕換句必造成帶內像素變化，門檻取很低（灰階平均差 2.0/255）不會漏真換句；
    # PUBLIC_FIXTURE: behavior is covered by synthetic tests.
    import numpy as _np
    from PIL import Image as _Im

    def _band_sig(fp):
        return _np.asarray(_Im.open(fp).convert("L").resize((64, 16)), dtype=_np.int16)

    rows = []
    with tempfile.TemporaryDirectory() as td:
        _run(["ffmpeg", "-hide_banner", "-v", "error", "-i", path, "-vf",
              "%s,fps=%g" % (crop, 1 / step), os.path.join(td, "f_%04d.png")])
        prev_key = None
        prev_sig = None
        for i, fp in enumerate(sorted(glob.glob(os.path.join(td, "f_*.png")))):
            sig = _band_sig(fp)
            _th = float(os.environ.get("TEARDOWN_SKIP_THRESH", "2.0"))
            if prev_sig is not None and _np.abs(sig - prev_sig).mean() < _th:
                continue                      # 帶內沒變 → 這幀不可能有新字幕
            prev_sig = sig
            res, _ = engine(fp)
            parts = []
            for _b, t, s in (res or []):
                t = t.strip()
                # 濾掉平台 UI 噪音：純數字/純符號（讚數、留言數會滲進字幕帶）
                if float(s) < min_conf or not t:
                    continue
                if all(ch.isdigit() or ch in ".,+-%萬KkMm" for ch in t):
                    continue
                parts.append(t)
            if not parts:
                continue
            txt = cc(" ".join(parts))
            key = "".join(ch for ch in txt if ch.isalnum())
            if prev_key and _near_dup(key, prev_key):
                continue
            rows.append((round(i * step, 1), txt))
            prev_key = key
    return rows


def _near_dup(a, b, ratio=0.86):
    'Compare adjacent OCR strings with an order-sensitive similarity metric.'
    if not a or not b:
        return False
    if a == b:
        return True
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= ratio


def teardown(path, band="wide"):
    w, h, fps, dur = probe(path)
    print("=" * 62)
    print("%s   %dx%d  %gfps  %.1fs  LUFS %s" %
          (os.path.basename(path), w, h, fps, dur, loudness(path)))
    print("=" * 62)

    ct = cuts(path)
    cut_iv = _stats(ct, dur, "剪點")

    caps = caption_track(path, band, dur, w, h)
    if caps is None:
        print("  [SKIP] OCR 套件未安裝 -> pip install rapidocr-onnxruntime "
              "opencc-python-reimplemented")
        return
    cap_ts = [t for t, _x in caps]
    cap_iv = _stats(cap_ts, dur, "換句")

    if cut_iv and cap_iv:
        r = (len(cap_ts) / dur) / max(len(ct) / dur, 1e-9)
        print("  換句/剪點 = %.1fx  ->  %s" %
              (r, "節奏主體是字幕" if r > 1.15 else "節奏主體是剪點"))

    print("\n  -- 自動抽出的字幕腳本（OCR + s2twp；**需人工複核**）--")
    for t, txt in caps:
        print("  %6.1fs  %s" % (t, txt))
    print("\n  [!] 讀起來不像話的字（例：属害/墩到/代們）＝ OCR 誤認，不是對方真的那樣寫")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="影片檔或含影片的資料夾")
    ap.add_argument("--band", default="wide", choices=sorted(BANDS),
                    help="字幕帶（預設 wide：字幕會在片內移動，窄帶會靜默漏掉）")
    a = ap.parse_args()

    vids = ([a.target] if os.path.isfile(a.target)
            else sorted(glob.glob(os.path.join(a.target, "**", "*.mp4"), recursive=True)))
    if not vids:
        print("找不到 mp4：%s" % a.target)
        return 1
    for v in vids:
        teardown(v, a.band)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
