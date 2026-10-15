"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

if __package__:
    from .brand_code_cards import BRAND, fmono
else:
    from brand_code_cards import BRAND, fmono
from PIL import Image, ImageDraw, ImageFilter


def device_frame(shot, kind="browser", url="localhost"):
    """截圖（路徑或 PIL Image）→ 質感裝置框（RGBA 含投影，直接 overlay 到 canvas 上）。
    kind="browser"：titlebar + 三圓點 + 假網址列（url 參數顯示文字）。
    kind="phone"：直式手機框（聽筒/鏡頭 + home bar）。"""
    if isinstance(shot, str):
        shot = Image.open(shot)
    shot = shot.convert("RGB")
    if kind == "phone":
        cw = 560
        ch = max(1, round(cw * shot.height / shot.width))
        content = shot.resize((cw, ch), Image.LANCZOS)
        bez, top, bot, rad = 20, 78, 78, 72
        fw, fh = cw + bez * 2, ch + top + bot
        frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([0, 0, fw - 1, fh - 1], radius=rad,
                             fill=(24, 22, 40, 255), outline=(255, 255, 255, 42), width=3)
        fd.rounded_rectangle([fw // 2 - 70, top // 2 - 7, fw // 2 + 70, top // 2 + 7],
                             radius=7, fill=(72, 68, 104, 255))
        fd.ellipse([fw // 2 + 94, top // 2 - 9, fw // 2 + 112, top // 2 + 9],
                   fill=(72, 68, 104, 255))
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, fill=255)
        frame.paste(content, (bez, top), m)
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([fw // 2 - 92, fh - bot // 2 - 6, fw // 2 + 92, fh - bot // 2 + 6],
                             radius=6, fill=(92, 88, 124, 255))
    else:  # browser
        cw = 1560
        ch = max(1, round(cw * shot.height / shot.width))
        content = shot.resize((cw, ch), Image.LANCZOS)
        tb, bez, rad = 96, 12, 26
        fw, fh = cw + bez * 2, ch + tb + bez
        frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([0, 0, fw - 1, fh - 1], radius=rad,
                             fill=(27, 24, 46, 255), outline=(255, 255, 255, 38), width=2)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = 46 + i * 44
            fd.ellipse([cx - 12, tb // 2 - 12, cx + 12, tb // 2 + 12], fill=c + (255,))
        # 假網址列
        ux0, ux1 = 190, fw - 46
        fd.rounded_rectangle([ux0, tb // 2 - 27, ux1, tb // 2 + 27], radius=27,
                             fill=(13, 11, 25, 255), outline=(255, 255, 255, 24), width=2)
        fd.ellipse([ux0 + 24, tb // 2 - 7, ux0 + 38, tb // 2 + 7],
                   fill=BRAND["green"] + (255,))  # 小綠點 = 假鎖
        fd.text((ux0 + 58, tb // 2), url, font=fmono(30),
                fill=(190, 188, 215, 255), anchor="lm")
        m = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=16, fill=255)
        frame.paste(content, (bez, tb), m)
    # 投影 + 邊距
    mg = 90
    out = Image.new("RGBA", (fw + mg * 2, fh + mg * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([mg + 6, mg + 28, mg + fw + 6, mg + fh + 28],
                                         radius=rad, fill=(0, 0, 0, 150))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(36)))
    out.alpha_composite(frame, (mg, mg))
    return out
