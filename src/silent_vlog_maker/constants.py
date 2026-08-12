"""
silent_vlog_maker.constants — Shared constants for R10-R21 rules.

All other modules import from this. No logic, only data.
"""

# ─────────────────────────────────────────────────────────────────────
# R12: Safe Zone (2026 YT/Shorts spec)
# ─────────────────────────────────────────────────────────────────────

SAFE_ZONE = {
    "top": 260,        # text y ≥ 260 (status bar + camera notch)
    "bottom": 1660,    # text y ≤ 1660 (description + subscribe button)
    "right": 930,      # text x ≤ 930 (like/comment/share + add-to-playlist 2026)
}


# ─────────────────────────────────────────────────────────────────────
# R10: HDR HLG/HDR10 → SDR BT.709 (tonemap=hable, npl=250 for iPhone HLG)
# ─────────────────────────────────────────────────────────────────────

TONEMAP_FILTER = (
    "zscale=t=linear:npl=250,"
    "format=gbrpf32le,"
    "zscale=p=bt709,"
    "tonemap=tonemap=hable:desat=0,"
    "zscale=t=bt709:m=bt709:r=tv,"
    "format=yuv420p"
)


# ─────────────────────────────────────────────────────────────────────
# R11 v2: Platform-aware export configs (2026-05-24 — mass production ready)
# ─────────────────────────────────────────────────────────────────────
# 不同平台 spec 不同。用 ENCODE_ARGS_BY_PLATFORM[platform] 取對應 args。

ENCODE_ARGS_BY_PLATFORM = {
    "yt_shorts": [
        # YouTube Shorts (1080×1920 / 30fps / <60s)
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "8M", "-maxrate", "12M", "-bufsize", "16M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-movflags", "+faststart",
    ],
    "yt_longform": [
        # YouTube long-form (1920×1080 / 30fps / 1-15 min)
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-movflags", "+faststart",
    ],
    "ig_reels": [
        # Instagram Reels (1080×1920 / 30fps / <90s) — slightly lower bitrate for IG compression
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "6M", "-maxrate", "9M", "-bufsize", "12M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
    ],
    "tiktok": [
        # TikTok (1080×1920 / 30fps / <3 min) — H.264 high profile, faststart for upload
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
    ],
    "threads": [
        # Threads (1080×1080 square or 1080×1920 portrait / <5 min)
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
        "-b:v", "5M", "-maxrate", "7M", "-bufsize", "10M",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
    ],
}

# Backward compat alias (used by build_filter_complex / older scripts)
YT_SHORTS_ENCODE_ARGS = ENCODE_ARGS_BY_PLATFORM["yt_shorts"]


# Platform display dimensions (informational — for filter pre-scaling decision)
PLATFORM_DIMENSIONS = {
    "yt_shorts": (1080, 1920),
    "yt_longform": (1920, 1080),
    "ig_reels": (1080, 1920),
    "tiktok": (1080, 1920),
    "threads_portrait": (1080, 1920),
    "threads_square": (1080, 1080),
}


def encode_args_for(platform: str = "yt_shorts") -> list[str]:
    """Get ffmpeg encode args for a target platform.

    Raises KeyError if platform unknown. Use `list(ENCODE_ARGS_BY_PLATFORM.keys())` to enumerate.
    """
    if platform not in ENCODE_ARGS_BY_PLATFORM:
        raise KeyError(f"Unknown platform '{platform}'. Available: {list(ENCODE_ARGS_BY_PLATFORM.keys())}")
    return list(ENCODE_ARGS_BY_PLATFORM[platform])  # return copy to avoid mutation


# ─────────────────────────────────────────────────────────────────────
# R17: Fonts — Noto Sans TC (Google 思源黑體)
# ─────────────────────────────────────────────────────────────────────
# Strict hierarchy: Black for main titles / Bold for timestamps / Regular for subtitles
# M43 (2026-05-22): 用戶嫌 NotoSansTC generic → Vlog narrative 改 Noto Serif CJK Bold

try:
    from platform_compat import find_cjk_font
except ImportError:  # package execution fallback
    find_cjk_font = lambda prefer=None: None

def _ffmpeg_font(prefer=None) -> str:
    path = find_cjk_font(prefer=prefer)
    return str(path).replace(":", r"\:") if path else "sans-serif"

FONT_NOTO_BLACK = _ffmpeg_font(["Black", "Heavy", "Bold"])
FONT_NOTO_BOLD = _ffmpeg_font(["Bold", "Black", "bd"])
FONT_NOTO_REG = _ffmpeg_font(["Regular", "Noto", "PingFang"])
FONT_NOTO_SERIF_BOLD = _ffmpeg_font(["Serif", "Song", "Ming"])

# Legacy fonts (微軟正黑體 — kept for backward compat, NEW builds 用 Noto)
FONT_BOLD = "C\\:/Windows/Fonts/msjhbd.ttc"
FONT_REG = "C\\:/Windows/Fonts/msjh.ttc"


# ─────────────────────────────────────────────────────────────────────
# R17: Cinematic Color Grade — ffmpeg curves film-look
# ─────────────────────────────────────────────────────────────────────
# Effect: lift shadows (warmer), roll-off highlights, slight teal-orange shift
# Output: subtle film-look while preserving natural skin tones

CINEMATIC_CURVES = (
    "curves=master='0/0 0.25/0.22 0.5/0.5 0.75/0.78 1/1':"
    "red='0/0 0.5/0.52 1/0.98':"      # Warmer mids, cooler highlights
    "blue='0/0.02 0.5/0.48 1/1':"     # Lift blues in shadows (teal-orange feel)
    "green='0/0 0.5/0.5 1/1',"        # Neutral green
    "eq=saturation=0.95:contrast=1.05"  # Slight desat + contrast lift
)


# ─────────────────────────────────────────────────────────────────────
# R12 + R17: Typography color palette
# ─────────────────────────────────────────────────────────────────────

COLOR_GOLD = "0xFFD700"          # Main title
COLOR_WHITE = "white"            # Subtitles / timestamps
COLOR_CREAM = "0xFFF8E7"         # Subtle warm white (alternative to pure white)
BOX_DARK = "black@0.55"          # Main title box
BOX_SUBTLE = "black@0.5"         # Lower-third timestamp box
BOX_CINEMATIC = "black@0.6"      # Time-jump dramatic card


# ─────────────────────────────────────────────────────────────────────
# R19 + M5: Unified center-bottom subtitle position (Shorts portrait)
# ─────────────────────────────────────────────────────────────────────
# 用戶 v6 → v7 challenge：「字都應該在畫面中間，像是字幕那樣，跳來跳去有夠不明顯」
# Reference: TikTok safe zone 2026 (900×1492 centered) / YT Shorts 984×1500

SUBTITLE_CENTER_Y = 1280       # 主標題垂直位置（中央偏下，像 IG/TikTok subtitle）
SUBTITLE_DETAIL_Y = 1400       # 副標 / 細節說明垂直位置（主標下方）


# ─────────────────────────────────────────────────────────────────────
# R21 + M15: 綜藝字卡 vibrant color palette (landscape long-form)
# ─────────────────────────────────────────────────────────────────────

COLOR_VARIETY = {
    "gold": "0xFFD700",
    "cyan": "0x00E5FF",
    "magenta": "0xFF1493",
    "lime": "0x32FF6B",
    "orange": "0xFF8C00",
    "white": "white",
    "cream": "0xFFF8E7",
}
