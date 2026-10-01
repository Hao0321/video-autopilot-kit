# -*- coding: utf-8 -*-
"""
fx_lib — 特效基礎庫（Python 逐幀 + ffmpeg 都用得到）
內容：easing / stagger / 質感層(grain·vignette·chromatic) / 亞像素 Ken Burns（取代 zoompan，零抖動）
      / glow pulse / 合成 SFX（whoosh·pop·tick，無素材也能有聲音設計）
鐵則：所有運動用 float 精度計算（🚫 ffmpeg zoompan 整數抖動 = Hao 禁令）。
"""
import math
import struct
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ---------------- easing（0..1 -> 0..1） ----------------
def ease_linear(t): return t
def ease_out_cubic(t): return 1 - (1 - t) ** 3
def ease_out_quint(t): return 1 - (1 - t) ** 5
def ease_in_out_sine(t): return -(math.cos(math.pi * t) - 1) / 2
def ease_out_back(t, s=1.70158):
    """收尾帶 overshoot（元素進場「彈一下」）"""
    t -= 1
    return t * t * ((s + 1) * t + s) + 1
def ease_out_elastic(t):
    if t in (0.0, 1.0): return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1
def ease_out_expo(t):
    """counter 滾動標配：極快起步、極慢落地（feel earned）"""
    return 1.0 if t >= 1.0 else 1 - 2 ** (-10 * t)
def smootherstep(t):
    """Manim/3B1B 招牌 smooth（鏡頭平移/連續變化用，非進場）"""
    t = max(0.0, min(1.0, t))
    return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3

def stagger(i, n_frames_total, per_ms=100, dur_ms=600, fps=30):
    """元素 i 的進場進度函數：回傳 frame->progress(0..1)。
    per_ms = 元素間隔；dur_ms = 單元素動畫時長。"""
    start_f = int(i * per_ms / 1000 * fps)
    dur_f = max(1, int(dur_ms / 1000 * fps))
    def prog(frame):
        return min(1.0, max(0.0, (frame - start_f) / dur_f))
    return prog

# ---------------- 質感層 ----------------
_GRAIN_RNG = np.random.RandomState(42)

def film_grain(im, strength=5, mono=True, seed=None):
    """細顆粒（strength=每像素 ±值，4-7 subtle）。每幀給不同 seed = 活的顆粒。"""
    rng = np.random.RandomState(seed) if seed is not None else _GRAIN_RNG
    arr = np.asarray(im, dtype=np.int16)
    if mono:
        g = rng.normal(0, strength, arr.shape[:2])[..., None]
    else:
        g = rng.normal(0, strength, arr.shape)
    return Image.fromarray(np.clip(arr + g, 0, 255).astype(np.uint8))

_VIGNETTE_CACHE = {}
def vignette(im, strength=0.16, power=2.2):
    """柔和暗角（strength=四角壓暗比例）。mask 有 cache，逐幀零成本。"""
    key = (im.size, strength, power)
    if key not in _VIGNETTE_CACHE:
        w, h = im.size
        y, x = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        r = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2) / math.sqrt(2)
        m = 1 - strength * np.clip(r, 0, 1) ** power
        _VIGNETTE_CACHE[key] = m[..., None]
    arr = np.asarray(im, dtype=np.float32) * _VIGNETTE_CACHE[key]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def chromatic_aberration(im, shift=2):
    """邊緣色差（R 左移 B 右移 shift px）——subtle 用 1-2。"""
    r, g, b = im.split()
    r = r.transform(im.size, Image.AFFINE, (1, 0, shift, 0, 1, 0), resample=Image.BILINEAR)
    b = b.transform(im.size, Image.AFFINE, (1, 0, -shift, 0, 1, 0), resample=Image.BILINEAR)
    return Image.merge("RGB", (r, g, b))

def texture_pass(im, grain=5, vig=0.14, seed=None):
    """一行套整套質感（grain + vignette）。"""
    return film_grain(vignette(im, vig), grain, seed=seed)

# ---------------- 亞像素 Ken Burns（取代 zoompan） ----------------
def ken_burns_frame(src, t, z0=1.0, z1=1.06, pan=(0.0, 0.0), ease=ease_in_out_sine,
                    out_size=(1920, 1080)):
    """float 精度推鏡：t=0..1。z0→z1 縮放、pan=(dx,dy) 佔畫面比例的平移。
    用 PIL affine + bicubic = 亞像素採樣，無整數 snap 抖動（M-rule 🚫zoompan）。"""
    e = ease(t)
    z = z0 + (z1 - z0) * e
    W, H = out_size
    sw, sh = src.size
    # 以 cover 方式先算基準縮放
    base = max(W / sw, H / sh)
    s = base * z
    dx = pan[0] * e * W
    dy = pan[1] * e * H
    # 反向 affine（輸出座標 -> 來源座標）
    a = 1 / s
    cx_src, cy_src = sw / 2, sh / 2
    cx_out, cy_out = W / 2 + dx, H / 2 + dy
    matrix = (a, 0, cx_src - cx_out * a, 0, a, cy_src - cy_out * a)
    return src.transform(out_size, Image.AFFINE, matrix, resample=Image.BICUBIC)

# ---------------- glow pulse ----------------
def glow_pulse(base_rgba, frame, fps=30, period_s=2.0, lo=0.55, hi=1.0):
    """回傳該幀光暈 alpha 係數（sin 呼吸）。"""
    ph = (frame / fps) / period_s * 2 * math.pi
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(ph))

def double_bloom(layer, tight=4, wide=16, tight_op=0.60, wide_op=0.30, boost=0.0):
    """雙層 additive bloom：tight blur + wide blur 疊在銳利元素下面。
    layer=RGBA（透明底上的亮元素）。boost 0..1 額外加亮（落地脈衝用）。
    回傳同尺寸 RGBA（glow 疊好 + 原元素在頂）。"""
    def _scaled(src, blur, op):
        g = src.filter(ImageFilter.GaussianBlur(blur))
        if op < 1.0:
            a = g.getchannel("A").point(lambda v: int(v * op))
            g.putalpha(a)
        return g
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(_scaled(layer, wide, min(1.0, wide_op * (1 + boost * 1.6))))
    out.alpha_composite(_scaled(layer, tight, min(1.0, tight_op * (1 + boost))))
    out.alpha_composite(layer)
    return out

def light_sweep(layer, t, band_ratio=0.6, peak_op=0.5):
    """45° 白色掃光帶掃過元素（以 layer alpha 為 mask）。t=0..1 linear（掃光不減速）。
    回傳掃光 RGBA 層（screen 感由白色+alpha 近似），呼叫端 alpha_composite 到 layer 上方。"""
    w, h = layer.size
    band_w = max(8, int(h * band_ratio))
    span = w + h + band_w * 2          # 45° 掃過全對角
    pos = -band_w + t * span
    xs = np.arange(w)[None, :] + np.arange(h)[:, None]   # x+y = 45° 等值線
    d = np.abs(xs - pos)
    band = np.clip(1 - d / band_w, 0, 1) ** 2 * 255 * peak_op
    alpha_src = np.asarray(layer.getchannel("A"), dtype=np.float32) / 255.0
    a = (band * alpha_src).astype(np.uint8)
    sweep = Image.new("RGBA", layer.size, (255, 255, 255, 0))
    sweep.putalpha(Image.fromarray(a))
    return sweep

# ---------------- 合成 SFX（無素材時的聲音設計） ----------------
SR = 48000

def _write_wav(path, sig):
    sig = np.clip(sig, -1, 1)
    data = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(data.tobytes())

def sfx_whoosh(path, dur=0.55, f0=220, f1=2400, vol=0.5):
    """noise sweep whoosh：帶通中心由低掃高 + 前快後慢 envelope。"""
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    noise = np.random.RandomState(3).normal(0, 1, n)
    # 簡易時變帶通：用共振濾波器逐段
    out = np.zeros(n)
    y1 = y2 = 0.0
    for i in range(n):
        fc = f0 * (f1 / f0) ** (i / n)
        q = 2.2
        w = 2 * math.pi * fc / SR
        alpha = math.sin(w) / (2 * q)
        b0 = alpha; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * math.cos(w); a2 = 1 - alpha
        x = noise[i]
        y = (b0 * x + b2 * (noise[i - 2] if i >= 2 else 0) - a1 * y1 - a2 * y2) / a0
        y2, y1 = y1, y
        out[i] = y
    env = np.sin(np.pi * np.clip(t / dur, 0, 1) ** 0.65)
    _write_wav(path, out * env * vol)

def sfx_pop(path, dur=0.18, f0=520, f1=180, vol=0.55):
    """pop：短 sine 滑落 + 快衰減（元素進場落點）。"""
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    freq = f0 * (f1 / f0) ** (t / dur)
    ph = np.cumsum(2 * np.pi * freq / SR)
    env = np.exp(-t * 26)
    _write_wav(path, np.sin(ph) * env * vol)

def sfx_tick(path, dur=0.05, vol=0.32):
    """tick：counter 滾動時的細小咔嗒。"""
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    sig = np.random.RandomState(9).normal(0, 1, n) * np.exp(-t * 180)
    _write_wav(path, sig * vol)

def sfx_hit(path, dur=1.0, vol=0.6):
    """低頻落點 thud（金數字落地）：80Hz 指數下滑 sine + 快衰減。"""
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    freq = 80 * np.exp(-2.5 * t) + 38
    ph = np.cumsum(2 * np.pi * freq / SR)
    body = np.sin(ph) * np.exp(-4 * t)
    click = np.random.RandomState(11).normal(0, 0.4, n) * np.exp(-t * 90)
    _write_wav(path, (body * 0.9 + click) * vol)

def sfx_riser(path, dur=1.2, f0=160, f1=980, vol=0.35):
    """riser：段落轉場前的上升鋪墊。"""
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    freq = f0 * (f1 / f0) ** (t / dur)
    ph = np.cumsum(2 * np.pi * freq / SR)
    body = np.sin(ph) * 0.6 + np.random.RandomState(5).normal(0, 0.25, n)
    env = np.clip(t / dur, 0, 1) ** 1.6
    _write_wav(path, body * env * vol)

# ---------------- self-test ----------------
if __name__ == "__main__":
    import os, tempfile
    _TD = tempfile.mkdtemp(prefix="fxlib_")
    os.makedirs(os.path.join(_TD, "anim", "sfx"), exist_ok=True)
    os.chdir(_TD)
    # easing 單調性 + 端點
    for fn in (ease_out_cubic, ease_out_quint, ease_in_out_sine, ease_out_back,
               ease_out_elastic, ease_out_expo, smootherstep):
        assert abs(fn(0.0)) < 1e-6 and abs(fn(1.0) - 1) < 1e-3, fn.__name__
    assert ease_out_back(0.7) > 1.0  # overshoot 存在
    # 新特效 smoke
    lay = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((40, 60), "888", fill=(255, 210, 63, 255))
    assert double_bloom(lay).size == lay.size
    assert light_sweep(lay, 0.5).size == lay.size
    sfx_hit("anim/sfx/hit.wav")
    import os as _os; assert _os.path.getsize("anim/sfx/hit.wav") > 1000
    # 圖像 pass 尺寸不變
    im = Image.new("RGB", (640, 360), (30, 20, 60))
    assert texture_pass(im).size == (640, 360)
    assert chromatic_aberration(im).size == (640, 360)
    kb = ken_burns_frame(Image.new("RGB", (2400, 1350), (10, 10, 30)), 0.5, out_size=(1920, 1080))
    assert kb.size == (1920, 1080)
    # SFX 檔生成
    sfx_whoosh("anim/sfx/whoosh.wav"); sfx_pop("anim/sfx/pop.wav")
    sfx_tick("anim/sfx/tick.wav"); sfx_riser("anim/sfx/riser.wav")
    for f in ("whoosh", "pop", "tick", "riser"):
        assert os.path.getsize(f"anim/sfx/{f}.wav") > 1000
    print("fx_lib self-test OK")
