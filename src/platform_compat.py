"""
platform_compat — 跨平台相容層（Win / Mac / Linux）.

Standalone module：不 import 本 kit 其他模組（constants / paths 反過來 import 這裡）。
設計原則：**Windows 為第一公民**（現值當首選、行為不變），Mac/Linux 走探測 fallback。

    from platform_compat import IS_WIN, find_cjk_font, capcut_drafts_dir

找不到 → 回 None，由呼叫端自行 fallback（PIL load_default / 保留原 Windows 值 /
清楚報錯），這裡不 raise。

來源標註（2026-07 查證）：
- CapCut Win 草稿路徑：對 CapCut 8.9.x（Windows）直讀驗證（draft_content.json 明文 JSON）
- CapCut Mac 草稿路徑 ~/Movies/...：blog.usro.net 2025-08 + capcut-srt-export README（likely）
- 剪映 JianyingPro Win/Mac：僅 app 資料夾名不同，com.lveditor.draft 層相同（likely）
- Mac avfoundation 選項/範例：ffmpeg.org/ffmpeg-devices.html 官方文件逐字核對（verified）
- PingFang.ttc 於 macOS 15 Sequoia 從公開路徑消失 → 不能 hardcode，需多候選 + fallback
  （mpv issue #14878 + Apple forums thread 758189，verified）
"""
import glob
import os
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


# ─────────────────────────────────────────────────────────────────────
# CJK 字型探測（繁中優先）
# ─────────────────────────────────────────────────────────────────────
# 每平台候選依序試；Windows 順序 = kit 既有現值順序（Noto TC > 微軟正黑 > 雅黑），
# 保證 Windows 上解析結果與舊 hardcode 相同。

def _win_font_candidates() -> list:
    fonts = Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "Fonts"
    user_fonts = (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
                  if os.environ.get("LOCALAPPDATA") else None)
    names = [
        "NotoSansTC-Black.otf", "NotoSansTC-Bold.otf", "NotoSansTC-Regular.otf",
        "NotoSansCJK-Black.ttc",
        "msjhbd.ttc", "msjh.ttc",   # 微軟正黑（繁中系統必有）
        "msyh.ttc",                 # 微軟雅黑（簡中，最後備援）
    ]
    cands = [str(fonts / n) for n in names]
    if user_fonts:  # 使用者「只為我安裝」的字型裝在這（Win10 1809+）
        cands += sorted(glob.glob(str(user_fonts / "NotoSans*C*")))
    return cands


def _mac_font_candidates() -> list:
    cands = [
        # 傳統位置：一個 ttc 內含 PingFang TC/SC/HK 全家族
        "/System/Library/Fonts/PingFang.ttc",
        # macOS 15 Sequoia 起公開路徑消失、系統實際引用這裡（mpv #14878）
        "/System/Library/PrivateFrameworks/FontServices.framework/Resources/Reserved/PingFangUI.ttc",
    ]
    # 使用者/全域手裝的 Noto（跨版本最穩：自帶字型檔勝過賭系統路徑）
    for root in ("/Library/Fonts", str(Path.home() / "Library" / "Fonts")):
        cands += sorted(glob.glob(root + "/NotoSans*TC*.*"))
        cands += sorted(glob.glob(root + "/NotoSansCJK*.*"))
    return cands


def _linux_font_candidates() -> list:
    cands = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-TC-Regular.otf",
    ]
    cands += sorted(glob.glob("/usr/share/fonts/**/NotoSansCJK*.*", recursive=True))
    cands += sorted(glob.glob("/usr/share/fonts/**/NotoSansTC*.*", recursive=True))
    return cands


def _fc_list_cjk() -> list:
    """Linux 最後手段：fc-list 問 fontconfig 有哪些繁中字型。失敗回 []。"""
    try:
        r = subprocess.run(
            ["fc-list", ":lang=zh-tw", "file"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=10,
        )
        if r.returncode != 0:
            return []
        # 輸出每行 "path: " — 偏好 Noto，其餘照 fontconfig 順序
        paths = [ln.split(":")[0].strip() for ln in r.stdout.splitlines() if ln.strip()]
        return sorted(paths, key=lambda p: ("noto" not in p.lower(), p))
    except (OSError, subprocess.SubprocessError):
        return []


def find_cjk_font(prefer=None):
    """跨平台找一個繁中（CJK）字型檔 → 回純路徑 str；找不到回 None。

    Args:
        prefer: str 或 list[str] — 檔名關鍵字（不分大小寫），例如 ["Black", "bd"]。
                有符合的候選優先回；沒有就回第一個存在的候選。
    Note:
        回的是「未 escape」路徑。ffmpeg drawtext 用時呼叫端自己
        `p.replace(":", "\\\\:")`（constants._drawtext_font 已包好）。
        全找不到 → None，呼叫端 fallback（如 PIL ImageFont.load_default()）。
    """
    if IS_WIN:
        cands = _win_font_candidates()
    elif IS_MAC:
        cands = _mac_font_candidates()
    else:
        cands = _linux_font_candidates() or _fc_list_cjk()

    existing = [p for p in cands if os.path.exists(p)]
    if not existing and IS_LINUX:
        existing = [p for p in _fc_list_cjk() if os.path.exists(p)]
    if not existing:
        return None
    if prefer:
        keys = [prefer] if isinstance(prefer, str) else list(prefer)
        for k in keys:
            for p in existing:
                if k.lower() in os.path.basename(p).lower():
                    return p
    return existing[0]


# ─────────────────────────────────────────────────────────────────────
# CapCut / 剪映 草稿根目錄
# ─────────────────────────────────────────────────────────────────────

def capcut_drafts_dir():
    """偵測 CapCut（國際版）/ 剪映專業版（JianyingPro）草稿根目錄 → Path|None。

    佈局（兩品牌只有 app 資料夾名不同，com.lveditor.draft 層相同）：
      Windows: %LOCALAPPDATA%/<CapCut|JianyingPro>/User Data/Projects/com.lveditor.draft
               — 對 CapCut 8.9.x（Windows）直讀驗證（verified）
      macOS:   ~/Movies/<CapCut|JianyingPro>/User Data/Projects/com.lveditor.draft
               — blog.usro.net + capcut-srt-export README（likely）
      Linux:   無桌面版 → None

    加密備註：CapCut 國際版至 9.x（2026）draft_content.json 仍為明文 JSON；
    中國版剪映 6.0+ 已 AES 加密（≤5.9.x 明文）— 本函式只找路徑不做解密。
    """
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA")
        roots = [Path(base)] if base else []
    elif IS_MAC:
        roots = [Path.home() / "Movies"]
    else:
        return None
    for root in roots:
        for brand in ("CapCut", "JianyingPro"):
            d = root / brand / "User Data" / "Projects" / "com.lveditor.draft"
            if d.is_dir():
                return d
    return None


# ─────────────────────────────────────────────────────────────────────
# ffmpeg 螢幕錄影 input args
# ─────────────────────────────────────────────────────────────────────

def screen_capture_args(framerate: int = 30) -> list:
    """平台建議的 ffmpeg 螢幕錄影 **input** args（接在 output 參數之前用）。

    Windows: gdigrab 全桌面。
    macOS:   avfoundation（ffmpeg.org/ffmpeg-devices.html 官方文件，verified）
             - 列裝置：ffmpeg -f avfoundation -list_devices true -i ""
               螢幕會列成 "Capture screen N"（可用索引或名稱）
             - 輸入格式 "[video]:[audio]"，"none" = 不收音
             - 預設 framerate 是 ntsc≈29.97 → 這裡明確給 -framerate
             - 可加 -capture_cursor 1（錄游標）/ -capture_mouse_clicks 1（錄點擊）
             - 需在系統設定把「螢幕錄製」權限授權給執行 ffmpeg 的終端機（macOS 10.15+）
    Linux:   x11grab，input = $DISPLAY（預設 :0）。
    """
    fr = str(framerate)
    if IS_WIN:
        return ["-f", "gdigrab", "-framerate", fr, "-i", "desktop"]
    if IS_MAC:
        return ["-f", "avfoundation", "-framerate", fr,
                "-capture_cursor", "1", "-i", "Capture screen 0:none"]
    return ["-f", "x11grab", "-framerate", fr, "-i", os.environ.get("DISPLAY", ":0")]


# ─────────────────────────────────────────────────────────────────────
# stdout UTF-8（cp950 防線）
# ─────────────────────────────────────────────────────────────────────

def ensure_utf8_stdout():
    """Windows console 常是 cp950 → print 中文炸 UnicodeEncodeError；
    這裡 reconfigure 成 UTF-8。Mac/Linux 本來就 UTF-8 → no-op。"""
    if not IS_WIN:
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass  # e.g. stream 已關閉／被替換 — 不致命


# ─────────────────────────────────────────────────────────────────────
# self-test（ASCII-only prints — cp950 rule）
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[platform_compat] self-test")
    flags = [IS_WIN, IS_MAC, IS_LINUX]
    assert sum(flags) <= 1, "platform flags must be mutually exclusive"
    print(f"  platform: win={IS_WIN} mac={IS_MAC} linux={IS_LINUX}")

    f = find_cjk_font()
    assert f is None or os.path.exists(f), "find_cjk_font returned non-existent path"
    print(f"  find_cjk_font() -> {'FOUND' if f else 'None (caller falls back)'}")
    if f:
        fb = find_cjk_font(prefer=["Black", "bd"])
        assert fb is None or os.path.exists(fb)
        print(f"  find_cjk_font(prefer=[Black,bd]) basename ok: {os.path.basename(fb) if fb else None!r}"
              .encode("ascii", "replace").decode())

    d = capcut_drafts_dir()
    assert d is None or d.is_dir(), "capcut_drafts_dir returned non-dir"
    print(f"  capcut_drafts_dir() -> {'FOUND' if d else 'None'}")

    args = screen_capture_args()
    assert "-f" in args and "-i" in args and len(args) >= 6
    print(f"  screen_capture_args() -> {args}")

    ensure_utf8_stdout()  # must not raise on any platform
    print("  ensure_utf8_stdout() ok")
    print("[platform_compat] ALL GREEN")
