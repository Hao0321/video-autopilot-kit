# -*- coding: utf-8 -*-
"""av_util.py — autopilot 共用小工具（跟內容無關的機械動作）

任何 autopilot 腳本（`shorts_autopilot.py` 與你自己加的）都需要同一份
subprocess 包裝、寫檔、ffprobe 時長、抽幀、接觸表拼圖——
同一份東西兩處維護＝遲早漂移。本檔＝這些動作的唯一來源。

API:
    run(cmd, **kw)                         -> CompletedProcess（capture_output + errors=replace）
    write_text(path, text, announce=True)  -> path（自動建目錄；utf-8）
    duration(path)                         -> float 秒（ffprobe，失敗回 0.0）
    grab_frame(video, t, out, vf=None)     -> bool（抽單幀）
    contact_sheet(tiles, out, cols=None)   -> out|None（[(jpg, 標籤)] → 一張拼圖）

需求：`ffmpeg` / `ffprobe` 在 PATH 上（run/write_text 不需要）。
`contact_sheet` 需要 **Pillow**，且只在函式內 import——沒裝 Pillow 的環境仍可用其餘函式。
自測：`python av_util.py`（會用 ffmpeg 合成一支 2 秒測試片，不需要真素材）
cp950 安全：console 只印 ASCII 標記 + 檔名；檔案 I/O 一律 utf-8。
"""
from __future__ import annotations

import math
import os
import subprocess

# 接觸表版面（scan 的 SHEET.jpg 與 QA 的 CAPTION_match.jpg 共用同一組數字）
SHEET_BG = (18, 18, 22)
SHEET_LABEL = (255, 220, 60)
SHEET_PAD = 6            # tile 間距
SHEET_LABEL_H = 18       # 標籤列高
SHEET_LABEL_Y = 14       # 圖片在 tile 內的 y 位移（標籤在上）
SHEET_MAX_COLS = 6


def run(cmd, **kw):
    """subprocess.run 的統一包裝：抓 stdout/stderr、不因非 ASCII 輸出炸掉。"""
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", **kw)


def write_text(path: str, text: str, announce: bool = True) -> str:
    """建目錄 + utf-8 寫檔；announce=True 時印 '   -> 檔名'（看得到產出）。"""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if announce:
        print("   -> " + os.path.basename(path))
    return path


def duration(path: str) -> float:
    """ffprobe 秒數；讀不到回 0.0（呼叫端自己決定要不要擋）。"""
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def grab_frame(video: str, t, out: str, vf: str = None) -> bool:
    """抽 t 秒那一幀存成圖；回傳檔案是否真的產出。"""
    cmd = ["ffmpeg", "-v", "error", "-ss", "%s" % t, "-i", video, "-frames:v", "1"]
    if vf:
        cmd += ["-vf", vf]
    cmd += [out, "-y"]
    run(cmd)
    return os.path.exists(out)


def contact_sheet(tiles, out: str, cols: int = None, cleanup: bool = False,
                  quality: int = 90):
    """[(圖片路徑, 標籤)] → 一張帶黃字標籤的拼圖（人眼複核用）。

    cols=None → min(6, 張數)；cleanup=True → 拼完刪掉來源小圖。
    tiles 空的回 None（呼叫端不用先判斷）。需要 Pillow。
    """
    tiles = [t for t in tiles if t and os.path.exists(t[0])]
    if not tiles:
        return None
    from PIL import Image, ImageDraw
    w, h = Image.open(tiles[0][0]).size
    cols = cols or min(SHEET_MAX_COLS, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sh = Image.new("RGB", (cols * (w + SHEET_PAD), rows * (h + SHEET_LABEL_H)), SHEET_BG)
    dr = ImageDraw.Draw(sh)
    for i, (jp, lab) in enumerate(tiles):
        x = (i % cols) * (w + SHEET_PAD)
        y = (i // cols) * (h + SHEET_LABEL_H)
        sh.paste(Image.open(jp), (x, y + SHEET_LABEL_Y))
        dr.text((x + 3, y + 2), lab, fill=SHEET_LABEL)
    d = os.path.dirname(os.path.abspath(out))
    if d:
        os.makedirs(d, exist_ok=True)
    sh.save(out, quality=quality)
    if cleanup:
        for jp, _lab in tiles:
            try:
                os.remove(jp)
            except OSError:
                pass
    return out


# ────────────────────────────────────────────── self-test

def _selftest() -> int:
    import shutil
    import tempfile

    fails = []

    def check(name, cond):
        print("[%s] %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            fails.append(name)

    tmp = tempfile.mkdtemp(prefix="avutil_")
    try:
        p = write_text(os.path.join(tmp, "sub", "a.txt"), "中文 utf-8\n", announce=False)
        check("write_text creates dirs + utf-8",
              os.path.isfile(p) and open(p, encoding="utf-8").read().startswith("中文"))

        r = run(["ffprobe", "-version"])
        check("run captures stdout", r.returncode == 0 and "ffprobe" in r.stdout)

        # 造一支 2 秒測試片（testsrc）→ 量時長 + 抽幀 + 拼接觸表
        mp4 = os.path.join(tmp, "t.mp4")
        run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
             "-t", "2", "-pix_fmt", "yuv420p", mp4, "-y"])
        d = duration(mp4)
        check("duration reads seconds", 1.8 <= d <= 2.2)
        check("duration on missing file -> 0.0", duration(os.path.join(tmp, "nope.mp4")) == 0.0)

        shots = []
        for i, t in enumerate((0.2, 0.9, 1.6)):
            jp = os.path.join(tmp, "f%d.jpg" % i)
            if grab_frame(mp4, t, jp, vf="scale=120:-1"):
                shots.append((jp, "f%d" % i))
        check("grab_frame extracts frames", len(shots) == 3)

        sheet = contact_sheet(shots, os.path.join(tmp, "SHEET.jpg"))
        check("contact_sheet writes image", bool(sheet) and os.path.getsize(sheet) > 500)
        check("contact_sheet keeps tiles by default", os.path.exists(shots[0][0]))
        sheet2 = contact_sheet(shots, os.path.join(tmp, "ROW.jpg"),
                               cols=len(shots), cleanup=True)
        check("contact_sheet cleanup removes tiles",
              bool(sheet2) and not os.path.exists(shots[0][0]))
        check("contact_sheet empty -> None",
              contact_sheet([], os.path.join(tmp, "x.jpg")) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("-" * 50)
    if fails:
        print("SELFTEST RED: %d failed" % len(fails))
        return 1
    print("SELFTEST GREEN: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
