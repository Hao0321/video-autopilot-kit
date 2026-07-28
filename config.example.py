"""
config.example.py — copy to `config.py` and fill in YOUR paths.

(Or just set these as environment variables — paths.py reads them either way.)
Nothing here hardcodes an account name; defaults auto-detect the current user.
Import this once at startup if you prefer a file over env vars.
"""
import os
from pathlib import Path

# ── Your video project workspace (where your assets/ videos/ live) ──
os.environ.setdefault("VIDEO_KIT_PROJECT_ROOT", str(Path(__file__).resolve().parent))

# ── CapCut Desktop user-data root (leave commented to auto-detect current user) ──
# os.environ["CAPCUT_USER_DATA"] = r"C:\Users\<you>\AppData\Local\CapCut\User Data"

# ── capcut-cli npm shim (only needed for the CapCut JSON automation) ──
# os.environ["CAPCUT_CLI"] = r"C:\Users\<you>\AppData\Roaming\npm\capcut.cmd"

# ── Optional: where your BGM / fonts / b-roll live (else <project>/assets/...) ──
# os.environ["VIDEO_KIT_PROJECT_ROOT"] already covers assets/bgm, assets/fonts

# ── Vertical-Shorts line (src/shorts_autopilot.py) ──
# Inbox: drop each Short's raw clips in <inbox>/<N>/ , then `scan N` -> `build N`.
# Keep <N> ASCII-only: non-ASCII folder names break on non-UTF-8 consoles (e.g. cp950).
# Default: <VIDEO_KIT_PROJECT_ROOT>/videos/_INBOX/shorts
# os.environ["VIDEO_KIT_SHORTS_INBOX"] = r"D:\my-videos\_INBOX\shorts"
#   ⚠️ 指向 **repo 外部**，或 repo 內的 videos/ 底下（videos/ 已整個 gitignored）。
#      掃描產物含 GPS 座標與原始素材路徑，放錯地方會跟著 commit 出去。

# BGM root: `build` picks the track from a SUBFOLDER of this dir (spec["bgm_folder"]),
# so keep one subfolder per mood — that way swapping the mood never touches the code.
# Default: <VIDEO_KIT_PROJECT_ROOT>/assets/bgm
# os.environ["VIDEO_KIT_BGM_ROOT"] = r"D:\my-videos\assets\bgm"

# ── Interview line (src/interview_autopilot.py) ──
# Where the per-episode planning kit is written. Default:
#   <VIDEO_KIT_PROJECT_ROOT>/videos/_planning/  (episode dirs are generated ASCII-only)
# os.environ["VIDEO_KIT_PLAN_ROOT"] = r"D:\my-videos\_planning"
#   ⚠️ 同上，而且更嚴：訪談產物含 **來賡真名、成就資料、授權書**。
#      那是別人的個資，不是你的 —— 指向 repo 外部最安全。
