# -*- coding: utf-8 -*-
"""
asset_forge — 合成素材工廠（skill 級）：題材美術包 loopable 動態底 b-roll + SFX 變體包。
永遠零個資、無版權問題；填「講解段沒畫面」的空檔 / 疊字卡底 / 轉場墊。
產出：
  assets/broll/generated/{signal_grid,editorial_panels,particle_net,
  gradient_flow,grid_pulse,bokeh_drift}.mp4  (8s 無縫 loop, 1080p30)
  assets/sfx/{whoosh_1..3,pop_1..3,tick_1..2,riser_1..2,hit_1..2}.wav
跑法：python asset_forge.py   （渲染 ~數分鐘）
"""
import os, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import fx_lib as fx

_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
import art_direction as art
from motion_asset_pack import build_pack as build_motion_pack, choose_asset as choose_motion_asset
from project_paths import asset_path

BROLL_DIR = str(asset_path("broll", "generated"))
SFX_DIR = str(asset_path("sfx"))
RW, RH = 960, 540          # 半解析渲染→LANCZOS 放大（背景底可接受、4x 提速）
W, H = 1920, 1080
FPS, DUR = 30, 8.0
N = int(FPS * DUR)
PURPLE, CYAN, GOLD = (138, 92, 255), (69, 212, 255), (255, 210, 63)

def _base():
    im = Image.new("RGB", (RW, RH), (13, 11, 34))
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(0, RW, 60): d.line([(x, 0), (x, RH)], fill=(255, 255, 255, 7))
    for y in range(0, RH, 60): d.line([(0, y), (RW, y)], fill=(255, 255, 255, 7))
    return im

def _finish(im, seed):
    im = im.resize((W, H), Image.LANCZOS)
    return fx.texture_pass(im, grain=4, vig=0.18, seed=seed)

# ---- 1) particle_net：漂浮粒子 + 鄰近連線（週期運動=無縫 loop）----
def gen_particle_net(out):
    rng = np.random.RandomState(5)
    n = 36
    cx, cy = rng.rand(n) * RW, rng.rand(n) * RH
    ax, ay = 20 + rng.rand(n) * 45, 15 + rng.rand(n) * 35
    p1, p2 = rng.rand(n) * 2*math.pi, rng.rand(n) * 2*math.pi
    k1, k2 = rng.randint(1, 3, n), rng.randint(1, 3, n)     # 整數倍頻=完美循環
    def frames():
        for i in range(N):
            t = i / N * 2 * math.pi
            xs = cx + ax * np.sin(k1 * t + p1)
            ys = cy + ay * np.cos(k2 * t + p2)
            im = _base()
            layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for a in range(n):
                for b in range(a + 1, n):
                    dist = math.hypot(xs[a]-xs[b], ys[a]-ys[b])
                    if dist < 130:
                        al = int(90 * (1 - dist / 130))
                        d.line([(xs[a], ys[a]), (xs[b], ys[b])], fill=PURPLE + (al,), width=1)
            for a in range(n):
                c = CYAN if a % 3 else PURPLE
                d.ellipse([xs[a]-3, ys[a]-3, xs[a]+3, ys[a]+3], fill=c + (220,))
            base = im.convert("RGBA"); base.alpha_composite(fx.double_bloom(layer, 2, 8))
            yield _finish(base.convert("RGB"), i)
    _encode(frames(), out)

# ---- 2) gradient_flow：斜向色帶流動 ----
def gen_gradient_flow(out):
    yy, xx = np.mgrid[0:RH, 0:RW]
    diag = (xx / RW + yy / RH) / 2
    def frames():
        for i in range(N):
            ph = i / N * 2 * math.pi
            v = 0.5 + 0.5 * np.sin(diag * 6 * math.pi + ph)
            w = 0.5 + 0.5 * np.sin(diag * 3 * math.pi - ph * 2)
            r = 13 + v * 30 + w * 18;  g = 11 + v * 14 + w * 10;  b = 34 + v * 66 + w * 34
            arr = np.stack([r, g, b], -1).astype(np.uint8)
            yield _finish(Image.fromarray(arr), i)
    _encode(frames(), out)

# ---- 3) grid_pulse：格線上跑光 ----
def gen_grid_pulse(out):
    lines_v = list(range(0, RW + 1, 96)); lines_h = list(range(0, RH + 1, 96))
    def frames():
        for i in range(N):
            t = i / N
            im = _base()
            layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for j, x in enumerate(lines_v):
                y = ((t * 2 + j * 0.23) % 1.0) * RH          # 週期整數倍=loop
                d.ellipse([x-3, y-14, x+3, y+14], fill=(CYAN if j % 2 else PURPLE) + (170,))
            for j, y in enumerate(lines_h):
                x = ((t + j * 0.31) % 1.0) * RW
                d.ellipse([x-14, y-3, x+14, y+3], fill=(PURPLE if j % 2 else GOLD) + (120,))
            base = im.convert("RGBA"); base.alpha_composite(fx.double_bloom(layer, 3, 10))
            yield _finish(base.convert("RGB"), i)
    _encode(frames(), out)

# ---- 4) bokeh_drift：柔焦光斑漂移 ----
def gen_bokeh_drift(out):
    rng = np.random.RandomState(9)
    n = 14
    cx, cy = rng.rand(n) * RW, rng.rand(n) * RH
    rad = 18 + rng.rand(n) * 55
    ax, ay = 25 + rng.rand(n) * 50, 18 + rng.rand(n) * 30
    ph = rng.rand(n) * 2 * math.pi
    kk = rng.randint(1, 3, n)
    cols = [PURPLE, CYAN, GOLD]
    def frames():
        for i in range(N):
            t = i / N * 2 * math.pi
            im = _base()
            layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for a in range(n):
                x = cx[a] + ax[a] * math.sin(kk[a] * t + ph[a])
                y = cy[a] + ay[a] * math.cos(kk[a] * t + ph[a] * 1.7 % (2*math.pi))
                al = int(60 + 40 * math.sin(t * kk[a] + ph[a]))
                d.ellipse([x-rad[a], y-rad[a], x+rad[a], y+rad[a]],
                          fill=cols[a % 3] + (max(20, al),))
            layer = layer.filter(ImageFilter.GaussianBlur(9))
            base = im.convert("RGBA"); base.alpha_composite(layer)
            yield _finish(base.convert("RGB"), i)
    _encode(frames(), out)


# ---- 5/6) Hao Signal Grid：黑底白線條格＋題材色／編輯面板 ----
def gen_signal_grid(out, theme="general", variant="signal_grid"):
    """低頻呼吸、可 loop 的原創品牌底；字卡空檔不再只有深紫漸層。"""
    def frames():
        for i in range(N):
            im = art.render_background(RW, RH, theme=theme, variant=variant, progress=i / N,
                                       seed=f"{theme}:{variant}")
            # 紙張顆粒固定在畫布上，不能每幀換 seed：動態噪點會 shimmer、loop 跳一下，
            # 也讓 H.264 每幀都像新畫面（實測 8s 暴增到 44MB）。
            yield _finish(im, 17)
    _encode(frames(), out)

def _encode(frames, out):
    """逐幀 pipe 給 ffmpeg：不再囤 1.4GB PIL frames，也不寫 240 張暫存 PNG。"""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            p.stdin.write(frame.convert("RGB").tobytes())
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", errors="replace")
        code = p.wait()
    except Exception:
        p.kill()
        raise
    if code:
        raise RuntimeError("asset forge encode failed: " + err[-600:])
    print(os.path.basename(out), "ok")

# ---- SFX 變體包（同類輪替 2-3 變體不膩）----
def gen_sfx_pack():
    os.makedirs(SFX_DIR, exist_ok=True)
    fx.sfx_whoosh(f"{SFX_DIR}/whoosh_1.wav", dur=0.55, f0=220, f1=2400)
    fx.sfx_whoosh(f"{SFX_DIR}/whoosh_2.wav", dur=0.42, f0=320, f1=3200, vol=0.45)
    fx.sfx_whoosh(f"{SFX_DIR}/whoosh_3.wav", dur=0.70, f0=150, f1=1600, vol=0.5)
    fx.sfx_pop(f"{SFX_DIR}/pop_1.wav", f0=520, f1=180)
    fx.sfx_pop(f"{SFX_DIR}/pop_2.wav", f0=680, f1=240, dur=0.14)
    fx.sfx_pop(f"{SFX_DIR}/pop_3.wav", f0=420, f1=140, dur=0.22, vol=0.5)
    fx.sfx_tick(f"{SFX_DIR}/tick_1.wav")
    fx.sfx_tick(f"{SFX_DIR}/tick_2.wav", dur=0.04, vol=0.26)
    fx.sfx_riser(f"{SFX_DIR}/riser_1.wav")
    fx.sfx_riser(f"{SFX_DIR}/riser_2.wav", dur=1.6, f0=120, f1=760, vol=0.3)
    fx.sfx_hit(f"{SFX_DIR}/hit_1.wav")
    fx.sfx_hit(f"{SFX_DIR}/hit_2.wav", dur=0.7, vol=0.5)
    print("sfx pack ok (12 files)")

if __name__ == "__main__":
    os.makedirs(BROLL_DIR, exist_ok=True)
    gen_sfx_pack()
    gen_gradient_flow(f"{BROLL_DIR}/gradient_flow.mp4")
    gen_grid_pulse(f"{BROLL_DIR}/grid_pulse.mp4")
    gen_bokeh_drift(f"{BROLL_DIR}/bokeh_drift.mp4")
    gen_particle_net(f"{BROLL_DIR}/particle_net.mp4")
    gen_signal_grid(f"{BROLL_DIR}/signal_grid.mp4", "general", "signal_grid")
    gen_signal_grid(f"{BROLL_DIR}/editorial_panels.mp4", "ai", "editorial")
    build_motion_pack()
    print("ASSET FORGE DONE")
