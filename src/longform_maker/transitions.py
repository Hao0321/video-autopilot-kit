# -*- coding: utf-8 -*-
"""
transitions — 語意轉場庫（longform_maker skill 級，支支重用）

三種逐幀 PIL 轉場（零抖動、確定性、無 zoompan）+ 對應純 ffmpeg xfade 指令版。
輸入輸出都是 PIL Image list，直接餵給現有 frame pipeline（30fps 建議）。

【頻率 cap — 留存 > 炫技，寫死在這裡，違反 = audit 紅燈】
    - luma_wipe  ≤ 3 次 / 支影片（章節級切換限定）
    - zoom_punch ≤ 2 次 / 支影片（重點揭曉 / stat 卡登場限定）
    - whip_pan   高能量點限定（hook 收尾、大轉折），一般段落禁用
    - 其餘一律硬切（hard cut）— 硬切是預設，轉場是調味料
    - 每個轉場配 stinger SFX（見 stinger_sfx_map），沒 SFX 的轉場感知廉價

用法：
    from transitions import whip_pan_frames, luma_wipe_frames, zoom_punch_frames
    frames = luma_wipe_frames(imA, imB, n=15)   # -> [PIL.Image] * 15，首幀=A 尾幀=B
    # ffmpeg 版（兩段 mp4 之間）：
    cmd = xfade_cmd("a.mp4", "b.mp4", kind="wipe", offset=4.5)
    subprocess.run(cmd, encoding="utf-8", ...)
"""
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
from project_paths import asset_path  # noqa: E402

FPS = 30  # 建議幀率（frames 函式本身與 fps 無關，只是節奏參考：n=12 @30fps = 0.4s）

# 轉場 -> stinger SFX 檔名（由 workspace marker 解出 assets/sfx）
stinger_sfx_map = {
    "whip": "whoosh_2",
    "wipe": "whoosh_1",
    "zoom": "pop_1",
}
SFX_DIR = str(asset_path("sfx"))


# ---------------------------------------------------------------- helpers
def _to_rgb(im, size=None):
    im = im.convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im


def _hblur(im, radius):
    """水平向 box blur（等效 gblur sigmaV=0）— numpy 行方向 cumsum，垂直完全不動。"""
    r = int(round(radius))
    if r < 1:
        return im
    arr = np.asarray(im).astype(np.float32)          # (H, W, 3)
    k = 2 * r + 1
    pad = np.pad(arr, ((0, 0), (r + 1, r), (0, 0)), mode="edge")
    csum = np.cumsum(pad, axis=1)
    out = (csum[:, k:, :] - csum[:, :-k, :]) / k     # (H, W, 3)
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def _shift_x(im, dx, fill=(8, 8, 14)):
    """整張圖水平位移 dx（右正左負），露出處補深底色。逐幀整數位移 = 零抖動。"""
    w, h = im.size
    out = Image.new("RGB", (w, h), fill)
    out.paste(im, (int(round(dx)), 0))
    return out


def _center_zoom(im, z):
    """中心縮放 z 倍（z>=1 推近）。float 裁切框 + LANCZOS，確定性、無隨機。"""
    if z <= 1.0001:
        return im.copy()
    w, h = im.size
    cw, ch = w / z, h / z
    x0, y0 = (w - cw) / 2.0, (h - ch) / 2.0
    return im.resize((w, h), Image.LANCZOS,
                     box=(x0, y0, x0 + cw, y0 + ch))


def _radial_blur_approx(im, z, layers=4, step=0.022):
    """徑向模糊近似：多重中心縮放疊加平均（層數固定 = 確定性）。"""
    base = np.asarray(_center_zoom(im, z)).astype(np.float32)
    acc = base.copy()
    for j in range(1, layers):
        acc += np.asarray(_center_zoom(im, z * (1 + j * step))).astype(np.float32)
    return Image.fromarray(np.clip(acc / layers, 0, 255).astype("uint8"))


# ---------------------------------------------------------------- 1) whip pan
def whip_pan_frames(imA, imB, n=12, blur_max=26):
    """
    甩鏡轉場（高能量點限定，見模組頂頻率 cap）。
    前半：A 加速向左甩出 + 水平向模糊漸強；後半：B 反向從右甩入收住。
    逐幀 PIL、整數位移、零抖動。首幀 = A 原圖、尾幀 = B 原圖。
    n=12 @30fps = 0.4s。回傳 [PIL.Image] * n。
    """
    assert n >= 4, "whip_pan_frames: n >= 4"
    imA = _to_rgb(imA)
    imB = _to_rgb(imB, imA.size)
    w, _ = imA.size
    frames = []
    for i in range(n):
        p = i / (n - 1)                      # 0..1
        blur = blur_max * math.sin(math.pi * p)  # 兩端 0、中段最強
        if p < 0.5:
            q = p / 0.5                      # A 相位 0..1（加速甩出）
            dx = -w * (q ** 2) * 0.95
            fr = _shift_x(imA, dx)
        else:
            q = (1 - p) / 0.5                # B 相位 1..0（減速收住）
            dx = w * (q ** 2) * 0.95
            fr = _shift_x(imB, dx)
        frames.append(_hblur(fr, blur))
    frames[0] = imA.copy()                   # 首尾鎖死原圖（sin 端點本來就 0，保險）
    frames[-1] = imB.copy()
    return frames


# ---------------------------------------------------------------- 2) luma wipe
def luma_wipe_frames(imA, imB, n=15, angle=45, soft=0.15):
    """
    品牌斜角軟邊 wipe（章節級切換限定，<=3 次/支，見模組頂頻率 cap）。
    numpy 對角漸層 mask 由 A 掃到 B，soft = 軟邊寬度（0..1 相對值）。
    首幀 = A 原圖、尾幀 = B 原圖。n=15 @30fps = 0.5s。回傳 [PIL.Image] * n。
    """
    assert n >= 3, "luma_wipe_frames: n >= 3"
    soft = max(soft, 1e-3)
    imA = _to_rgb(imA)
    imB = _to_rgb(imB, imA.size)
    w, h = imA.size
    a = np.asarray(imA).astype(np.float32)
    b = np.asarray(imB).astype(np.float32)
    rad = math.radians(angle)
    xs = np.linspace(0, 1, w)[None, :]
    ys = np.linspace(0, 1, h)[:, None]
    ramp = xs * math.cos(rad) + ys * math.sin(rad)
    ramp = (ramp - ramp.min()) / max(ramp.max() - ramp.min(), 1e-6)  # 0..1
    frames = []
    for i in range(n):
        p = i / (n - 1)
        m = np.clip((p * (1 + soft) - ramp) / soft, 0.0, 1.0)[:, :, None]
        fr = a * (1 - m) + b * m
        frames.append(Image.fromarray(fr.astype("uint8")))
    frames[0] = imA.copy()
    frames[-1] = imB.copy()
    return frames


# ---------------------------------------------------------------- 3) zoom punch
def zoom_punch_frames(imA, imB, n=10, z=1.18):
    """
    推近重擊（重點揭曉限定，<=2 次/支，見模組頂頻率 cap）。
    A 加速推近 + 徑向模糊近似（多重縮放疊加），最後一幀硬切 B。
    首幀 = A 原圖、尾幀 = B 原圖。n=10 @30fps = 0.33s。回傳 [PIL.Image] * n。
    配 stinger 'pop_1'，落在切 B 那一幀。
    """
    assert n >= 3, "zoom_punch_frames: n >= 3"
    imA = _to_rgb(imA)
    imB = _to_rgb(imB, imA.size)
    frames = [imA.copy()]
    for i in range(1, n - 1):
        p = i / (n - 2)                       # 0..1（A 相位）
        zi = 1.0 + (z - 1.0) * (p ** 2)       # 加速推近
        blur_strength = p                     # 越推越糊
        fr = _radial_blur_approx(imA, zi, layers=2 + int(round(blur_strength * 3)))
        frames.append(fr)
    frames.append(imB.copy())                 # 硬切 B
    return frames


# ---------------------------------------------------------------- 4) ffmpeg xfade
_XFADE_DUR = {"whip": 0.30, "wipe": 0.50, "zoom": 0.33}

# 斜角 wipe 的 xfade custom expr（P 由 1 遞減到 0）
_WIPE_EXPR = "if(gt((X+Y)/(W+H),1-P),A,B)"


def ffmpeg_version(ffmpeg="ffmpeg"):
    """回傳 (major, minor) 或 None（找不到 ffmpeg）。"""
    if shutil.which(ffmpeg) is None:
        return None
    try:
        out = subprocess.run([ffmpeg, "-version"], capture_output=True,
                             encoding="utf-8", errors="replace").stdout
    except OSError:
        return None
    return parse_ffmpeg_version(out)


def parse_ffmpeg_version(text):
    """從 `ffmpeg -version` 首行抓 (major, minor)；抓不到回 None。"""
    m = re.search(r"ffmpeg version n?(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def xfade_cmd(a_mp4, b_mp4, kind, offset, out_mp4="out.mp4",
              duration=None, ffmpeg="ffmpeg", check=True):
    """
    純 ffmpeg xfade 指令版（兩段 mp4 之間），回傳 list 直接丟 subprocess.run。
    kind: 'wipe'（custom expr 斜角）/ 'whip'（slideleft + sendcmd 動態 gblur，
    sigmaV=0 = 純水平模糊）/ 'zoom'（xfade=zoomin）。
    offset = A 內開始轉場的秒數（xfade offset 語意）。
    需要 ffmpeg 5.1+（xfade custom expr / sendcmd 對 gblur 下指令），
    check=True 時驗版本，過舊丟 RuntimeError；找不到 ffmpeg 也丟。
    頻率 cap 同 frames 版：wipe<=3、zoom<=2、whip 高能點限定。
    """
    if kind not in _XFADE_DUR:
        raise ValueError("kind must be one of: " + ", ".join(sorted(_XFADE_DUR)))
    if check:
        ver = ffmpeg_version(ffmpeg)
        if ver is None:
            raise RuntimeError("ffmpeg not found (need 5.1+ for xfade custom/sendcmd)")
        if ver < (5, 1):
            raise RuntimeError(
                "ffmpeg %d.%d too old, need 5.1+ for xfade custom expr / sendcmd gblur"
                % ver)
    dur = duration if duration is not None else _XFADE_DUR[kind]
    off = float(offset)
    if kind == "wipe":
        fc = ("[0:v][1:v]xfade=transition=custom:expr='%s':duration=%s:offset=%s[v]"
              % (_WIPE_EXPR, dur, off))
    elif kind == "whip":
        # slideleft + sendcmd 在轉場窗內把 gblur sigma 拉起再放掉（sigmaV=0 = 純水平）
        half = dur / 2.0
        send = ("%.3f gblur sigma 18;%.3f gblur sigma 26;%.3f gblur sigma 0"
                % (off, off + half, off + dur))
        fc = ("[0:v][1:v]xfade=transition=slideleft:duration=%s:offset=%s,"
              "sendcmd=c='%s',gblur=sigma=0:sigmaV=0[v]" % (dur, off, send))
    else:  # zoom
        fc = ("[0:v][1:v]xfade=transition=zoomin:duration=%s:offset=%s[v]"
              % (dur, off))
    return [ffmpeg, "-y", "-i", a_mp4, "-i", b_mp4,
            "-filter_complex", fc, "-map", "[v]",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out_mp4]


# ---------------------------------------------------------------- self-test
if __name__ == "__main__":
    import os

    DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")
    os.makedirs(DEMO, exist_ok=True)
    SZ = (640, 360)
    # 合成素材：純色底 + 小方塊 marker（純色圖對 zoom 不可見，marker 讓中段幀可驗證）
    from PIL import ImageDraw as _ID
    imA = Image.new("RGB", SZ, (200, 40, 40))    # red
    _ID.Draw(imA).rectangle([80, 60, 180, 140], fill=(255, 255, 255))
    imB = Image.new("RGB", SZ, (40, 60, 200))    # blue
    _ID.Draw(imB).rectangle([460, 220, 560, 300], fill=(255, 210, 63))

    def _same(a, b):
        return list(a.getdata()) == list(b.getdata())

    ok = 0
    cases = [
        ("whip", whip_pan_frames, dict(n=12), 12),
        ("wipe", luma_wipe_frames, dict(n=15), 15),
        ("zoom", zoom_punch_frames, dict(n=10), 10),
    ]
    for name, fn, kw, want_n in cases:
        frames = fn(imA, imB, **kw)
        assert len(frames) == want_n, "%s: frame count %d != %d" % (name, len(frames), want_n)
        assert all(f.size == SZ for f in frames), "%s: size drift" % name
        assert all(f.mode == "RGB" for f in frames), "%s: mode drift" % name
        assert _same(frames[0], imA), "%s: first frame != A" % name
        assert _same(frames[-1], imB), "%s: last frame != B" % name
        mid = frames[len(frames) // 2]
        assert not _same(mid, imA) and not _same(mid, imB), "%s: mid frame not transitional" % name
        mid.save(os.path.join(DEMO, "trans_%s.png" % name))
        ok += 1
        print("[OK] %s_frames: n=%d size=%dx%d first=A last=B, demo saved" %
              (name, want_n, SZ[0], SZ[1]))

    # xfade_cmd: structure test with check=False (no real ffmpeg / media needed)
    for kind in ("wipe", "whip", "zoom"):
        cmd = xfade_cmd("a.mp4", "b.mp4", kind, offset=4.5, check=False)
        assert isinstance(cmd, list) and cmd[0] == "ffmpeg", "xfade_cmd: bad list"
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "xfade" in fc and "offset=4.5" in fc, "xfade_cmd(%s): bad filter" % kind
        if kind == "wipe":
            assert "transition=custom" in fc and "expr=" in fc
        if kind == "whip":
            assert "slideleft" in fc and "sendcmd" in fc and "sigmaV=0" in fc
        if kind == "zoom":
            assert "zoomin" in fc
    print("[OK] xfade_cmd: wipe/whip/zoom command structure valid")
    ok += 1

    # version gate parser
    assert parse_ffmpeg_version("ffmpeg version 6.1.1 Copyright") == (6, 1)
    assert parse_ffmpeg_version("ffmpeg version n5.1.4-something") == (5, 1)
    assert parse_ffmpeg_version("ffmpeg version 4.4.2-0ubuntu") == (4, 4)
    assert parse_ffmpeg_version("garbage") is None
    assert (4, 4) < (5, 1) and (6, 1) >= (5, 1)
    print("[OK] parse_ffmpeg_version: 6.1/5.1/4.4/garbage all parsed correctly")
    ok += 1

    # sfx map points at real files if the asset dir exists
    for k, v in stinger_sfx_map.items():
        p = os.path.join(SFX_DIR, v + ".wav")
        if os.path.isdir(SFX_DIR):
            assert os.path.isfile(p), "sfx missing: " + p
    print("[OK] stinger_sfx_map: whip/wipe/zoom -> existing sfx wavs")
    ok += 1

    print("SELF-TEST GREEN: %d/%d groups passed, demo -> _demo/trans_{whip,wipe,zoom}.png" % (ok, ok))
