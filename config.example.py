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

# Editkin projects, receipts and rendered candidates stay under this workspace.
# Editor execution is negotiated through the Editkin v4 workflow contract; there
# is no second editor-specific runtime path to configure here.

# ── Optional: where your BGM / fonts / b-roll live (else <project>/assets/...) ──
# os.environ["VIDEO_KIT_PROJECT_ROOT"] already covers assets/bgm, assets/fonts

# ── Interview line (src/interview_autopilot.py) ──
# Where the per-episode planning kit is written. Default:
#   <VIDEO_KIT_PROJECT_ROOT>/videos/_planning/  (episode dirs are generated ASCII-only)
# os.environ["VIDEO_KIT_PLAN_ROOT"] = r"D:\my-videos\_planning"
#   ⚠️ 訪談產物含 **來賓真名、成就資料、授權書**。
#      那是別人的個資，不是你的 —— 指向 repo 外部最安全。
