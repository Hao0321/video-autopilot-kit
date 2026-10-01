# -*- coding: utf-8 -*-
"""
grade_lib — 調色 looks 庫 + LUT（longform_maker skill 級，支支重用）

內容：
  LOOKS            6 組 ffmpeg filter 鏈（brand_splittone / teal_orange / clean_bright /
                   night_neon / warm_story / mono_focus），每組附使用時機
  apply_look()     套 look 到影片，strength<1 用 split+blend 混原片控強度
  load_cube_lut()  .cube 檔 -> ffmpeg lut3d 參數字串（含 Windows 路徑跳脫）
  validate_cube()  .cube 基本格式檢查（header + N^3 資料行）
  grade_strip()    同一幀 x 6 looks 拼對照條圖（選色用）

鐵則（Hao）：
  - 靜止不抖：本庫只做色彩，零幾何運動（不碰 zoompan）。
  - 一級校正在前、Look 在後（editing-craft-fundamentals 5 步順序）；
    素材白平衡/曝光先修好再套本庫的 look。
  - grain/vignette 單層原則：本庫「不」疊 noise/vignette——質感層歸 fx_lib.texture_pass
    或成片 finishing pass 管，避免雙層疊加（editing-techniques-2026 #6）。
  - 不加 eq 亮度 flicker（M93 頻閃教訓）。

用法：
  from grade_lib import apply_look, grade_strip, LOOKS
  apply_look("in.mp4", "out.mp4", "brand_splittone")            # 全強度
  apply_look("in.mp4", "out.mp4", "teal_orange", strength=0.6)  # 60% 混原片
  grade_strip("in.mp4", "_demo/grade_strip.png")                # 選色對照條
"""
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

import brand_templates as bt

FFMPEG = "ffmpeg"

# ---------------------------------------------------------------- LOOKS
# 每組 = 完整 -vf 可用的 filter 鏈字串（單入單出、無幾何運動、無 grain/vignette）。
LOOKS = {
    # 品牌預設：陰影推藍紫 / 亮部推暖金（深紫+金品牌色 = split-tone 結構）。教學長片成片 finishing 標配。
    "brand_splittone":
        "curves=master='0/0.02 0.5/0.5 1/0.98',"
        "colorbalance=rs=0.02:bs=0.06:rh=0.04:bh=-0.04",

    # 旅遊 / cinematic b-roll：陰影 teal、亮部 orange，膚色會被推暖——vlog 外景用，UI 錄影別用。
    "teal_orange":
        "curves=master='0/0.01 0.5/0.5 1/0.99',"
        "colorbalance=rs=-0.06:gs=0.02:bs=0.10:rh=0.08:gh=0.02:bh=-0.10,"
        "eq=saturation=1.08",

    # 教學清爽：提亮 + 微降飽和 + 輕對比——螢幕錄影 / 圖表 / 白底教學段，資訊可讀性優先。
    "clean_bright":
        "eq=brightness=0.05:contrast=1.04:saturation=0.92,"
        "curves=master='0/0.03 0.5/0.55 1/1'",

    # 夜景 / 科技感開場：整體壓暗 + 紫青增益（貼品牌 purple/cyan）——hook 段、夜拍、賽博感 b-roll。
    "night_neon":
        "eq=brightness=-0.05:contrast=1.12:saturation=1.05,"
        "curves=master='0/0 0.5/0.44 1/0.95',"
        "colorbalance=rs=0.04:bs=0.14:rm=0.03:bm=0.10:gm=-0.02",

    # 溫暖敘事：整體推暖 + 亮部微金——個人故事段、回憶、美食、室內談話感素材。
    "warm_story":
        "colorbalance=rs=0.05:rm=0.06:gm=0.02:bs=-0.05:bh=-0.04,"
        "eq=saturation=1.06:contrast=1.03,"
        "curves=master='0/0.02 0.5/0.52 1/0.98'",

    # 黑白聚焦（留金近似）：重去飽和後把暖金推回中亮部——嚴肅對比段、失敗案例、before 畫面。
    # 近似法 = eq 去飽和 + colorbalance 暖軸回推（非真 HSL keep，ffmpeg 單鏈可跑）。
    "mono_focus":
        "hue=s=0.22,"
        "eq=contrast=1.06,"
        "colorbalance=rm=0.08:gm=0.04:rh=0.07:gh=0.035:bm=-0.03:bh=-0.04,"
        "curves=master='0/0.02 0.5/0.5 1/0.98'",
}


# ---------------------------------------------------------------- helpers
def _run(cmd):
    """跑 ffmpeg（cp950 安全：encoding=utf-8, errors=replace）。失敗丟 RuntimeError。"""
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tail = (r.stderr or "")[-900:]
        raise RuntimeError("ffmpeg failed exit=%d cmd=%s\n%s"
                           % (r.returncode, " ".join(str(c) for c in cmd[:8]) + " ...", tail))
    return r


def _label_font(size):
    """標籤字型：走 brand_templates.BRAND（look 名是 ASCII -> font_num=Anton），缺字型退 default。"""
    try:
        return ImageFont.truetype(bt.BRAND["font_num"], size)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- apply_look
def apply_look(in_mp4, out_mp4, look, strength=1.0, crf=18):
    """套 look 到影片。
    strength=1.0 直接套鏈；<1.0 用 split -> 套鏈 -> blend(normal, all_opacity=strength) 混原片。
    音軌原樣 copy（有才帶）。crf 預設 18（grain 吃碼率不可調高 crf 的同一鐵則）。
    """
    if look not in LOOKS:
        raise KeyError("unknown look: %s (have: %s)" % (look, ", ".join(sorted(LOOKS))))
    strength = max(0.0, min(1.0, float(strength)))
    chain = LOOKS[look]
    if strength >= 0.999:
        graph = "[0:v]%s[vout]" % chain
    else:
        # blend: 第一輸入=top(調色後)、第二=bottom(原片)；normal 模式 all_opacity=s -> top*s + bottom*(1-s)
        graph = ("[0:v]split=2[org][gsrc];[gsrc]%s[grd];"
                 "[grd][org]blend=all_mode=normal:all_opacity=%.4f[vout]"
                 % (chain, strength))
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(in_mp4),
           "-filter_complex", graph,
           "-map", "[vout]", "-map", "0:a?",
           "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-movflags", "+faststart", str(out_mp4)]
    _run(cmd)
    return str(out_mp4)


# ---------------------------------------------------------------- LUT
def validate_cube(path):
    """.cube 基本格式檢查 -> (ok: bool, msg: str)。
    檢查：檔案存在 / LUT_3D_SIZE N 存在且 2<=N<=256 / 資料行數 == N^3 / 每行 3 個 float 且在 domain 附近。
    """
    if not os.path.isfile(path):
        return False, "file not found: %s" % path
    n = None
    data_rows = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                up = line.upper()
                if up.startswith("LUT_3D_SIZE"):
                    parts = line.split()
                    if len(parts) < 2 or not parts[1].isdigit():
                        return False, "bad LUT_3D_SIZE line: %r" % line
                    n = int(parts[1])
                    if not (2 <= n <= 256):
                        return False, "LUT_3D_SIZE out of range: %d" % n
                    continue
                if up.startswith(("TITLE", "DOMAIN_MIN", "DOMAIN_MAX", "LUT_1D_SIZE")):
                    if up.startswith("LUT_1D_SIZE"):
                        return False, "1D LUT not supported (need LUT_3D_SIZE)"
                    continue
                parts = line.split()
                if len(parts) != 3:
                    return False, "bad data row (need 3 floats): %r" % line[:60]
                try:
                    vals = [float(p) for p in parts]
                except ValueError:
                    return False, "non-numeric data row: %r" % line[:60]
                if any(v < -0.5 or v > 2.0 for v in vals):
                    return False, "data value out of sane range: %r" % line[:60]
                data_rows += 1
    except OSError as e:
        return False, "read error: %s" % e
    if n is None:
        return False, "missing LUT_3D_SIZE header"
    if data_rows != n ** 3:
        return False, "data rows %d != N^3 (%d)" % (data_rows, n ** 3)
    return True, "ok (N=%d, %d rows)" % (n, data_rows)


def load_cube_lut(path):
    """驗證 .cube 後回傳 ffmpeg lut3d 參數字串（可直接塞 -vf）。
    Windows 路徑跳脫：反斜線轉 /、冒號跳脫（filter option 語法要求）。
    """
    ok, msg = validate_cube(path)
    if not ok:
        raise ValueError("invalid .cube: %s" % msg)
    p = str(path).replace("\\", "/").replace(":", "\\:")
    return "lut3d=file='%s':interp=tetrahedral" % p


# ---------------------------------------------------------------- grade_strip
def grade_strip(in_media, out_png, frame_ss=0.5, cell_w=480, cols=3):
    """同一幀 x 全部 6 looks 拼對照條圖（各標 look 名），選色用。
    in_media 可以是 mp4（抽 frame_ss 秒那幀）或 png/jpg（直接用）。
    """
    out_png = str(out_png)
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="grade_strip_")

    ext = os.path.splitext(str(in_media))[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
        base_frame = str(in_media)
    else:
        base_frame = os.path.join(tmp, "frame.png")
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
              "-ss", str(frame_ss), "-i", str(in_media),
              "-frames:v", "1", base_frame])

    names = list(LOOKS.keys())
    cells = []
    for name in names:
        graded = os.path.join(tmp, "look_%s.png" % name)
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
              "-i", base_frame, "-vf", LOOKS[name], "-frames:v", "1", graded])
        im = Image.open(graded).convert("RGB")
        h = max(1, round(im.height * cell_w / im.width))
        cells.append((name, im.resize((cell_w, h), Image.LANCZOS)))

    label_h = 46
    cell_h = cells[0][1].height + label_h
    rows = (len(cells) + cols - 1) // cols
    pad = 8
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * pad,
                              rows * cell_h + (rows + 1) * pad), bt.BRAND["bg_top"])
    d = ImageDraw.Draw(sheet)
    font = _label_font(26)
    for i, (name, im) in enumerate(cells):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + pad)
        sheet.paste(im, (x, y))
        # 標籤：white-first（純白字、深底、無多色）
        d.rectangle([x, y + im.height, x + cell_w, y + im.height + label_h],
                    fill=bt.BRAND["bg_bot"])
        d.text((x + cell_w // 2, y + im.height + label_h // 2), name,
               font=font, fill=bt.BRAND["white"], anchor="mm")
    sheet.save(out_png)
    return out_png


# ---------------------------------------------------------------- self-test
if __name__ == "__main__":
    # 全合成素材測（testsrc2 + sine），不碰真媒體；print 只 ASCII（cp950）。
    here = os.path.dirname(os.path.abspath(__file__))
    demo_dir = os.path.join(here, "_demo")
    os.makedirs(demo_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="grade_selftest_")
    passed, total = 0, 0

    def check(label, fn):
        global passed, total
        total += 1
        try:
            fn()
            passed += 1
            print("[OK]   " + label)
        except Exception as e:
            print("[FAIL] " + label + " :: " + repr(e)[:300])

    # 0) 合成測試片（含音軌，順便驗 apply_look 的 -map 0:a? + copy 路徑）
    src = os.path.join(work, "src.mp4")
    def make_src():
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
              "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=1",
              "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
              "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
              "-c:a", "aac", src])
        assert os.path.getsize(src) > 1000
    check("synth test clip (testsrc2 + sine)", make_src)

    # 1) apply_look 每組 look 全強度跑通
    def make_look_test(name):
        def t():
            out = os.path.join(work, "out_%s.mp4" % name)
            apply_look(src, out, name)
            assert os.path.getsize(out) > 1000
        return t
    for _name in LOOKS:
        check("apply_look full strength: " + _name, make_look_test(_name))

    # 2) strength=0.5 走 split+blend 路徑
    def half_strength():
        out = os.path.join(work, "out_half.mp4")
        apply_look(src, out, "teal_orange", strength=0.5)
        assert os.path.getsize(out) > 1000
    check("apply_look strength=0.5 (split+blend)", half_strength)

    # 3) validate_cube：假爛檔要 fail
    def bad_cube():
        bad = os.path.join(work, "bad.cube")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("this is not a lut\n1 2\nhello world\n")
        ok, msg = validate_cube(bad)
        assert not ok, "bad cube wrongly passed: " + msg
        ok2, _ = validate_cube(os.path.join(work, "nope.cube"))
        assert not ok2, "missing file wrongly passed"
    check("validate_cube rejects fake/missing file", bad_cube)

    # 4) validate_cube + load_cube_lut：合成 identity 2x2x2 LUT 要 pass，且 lut3d 字串真的能跑
    def good_cube():
        good = os.path.join(work, "identity.cube")
        with open(good, "w", encoding="utf-8") as f:
            f.write("TITLE \"identity\"\nLUT_3D_SIZE 2\n")
            for b in (0.0, 1.0):
                for g in (0.0, 1.0):
                    for r in (0.0, 1.0):
                        f.write("%.1f %.1f %.1f\n" % (r, g, b))
        ok, msg = validate_cube(good)
        assert ok, msg
        vf = load_cube_lut(good)
        assert vf.startswith("lut3d=file="), vf
        frame = os.path.join(work, "lutframe.png")
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
              "-ss", "0.2", "-i", src, "-frames:v", "1", frame])
        outp = os.path.join(work, "lut_applied.png")
        _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
              "-i", frame, "-vf", vf, "-frames:v", "1", outp])
        assert os.path.getsize(outp) > 500
    check("load_cube_lut string runs in ffmpeg (identity 2^3)", good_cube)

    # 5) grade_strip 產出 demo 對照條
    def strip():
        out = grade_strip(src, os.path.join(demo_dir, "grade_strip.png"))
        assert os.path.getsize(out) > 10000
        im = Image.open(out)
        assert im.width > 1000 and im.height > 400, str(im.size)
    check("grade_strip -> _demo/grade_strip.png", strip)

    print("SELF-TEST: %d/%d %s" % (passed, total, "GREEN" if passed == total else "RED"))
    raise SystemExit(0 if passed == total else 1)
