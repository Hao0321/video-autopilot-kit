# -*- coding: utf-8 -*-
"""system_health.py — one-command kit health check（穩定性中樞）

跑全部模組 self-test + 核心檔案存在檢查 → 單一 GREEN/RED 報告。
用法：python src/system_health.py           # 全跑（含真 ffmpeg 測試，~2-4 分鐘）
      python src/system_health.py --quick   # 跳過 ffmpeg 重測試
exit 0 = 全綠；1 = 有紅。console 輸出 cp950/UTF-8 皆安全。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

SRC = os.path.dirname(os.path.abspath(__file__))       # src/
ROOT = os.path.dirname(SRC)                             # repo root
LM = os.path.join(SRC, "longform_maker")
CH = os.path.join(SRC, "capcut_helpers")
SV = os.path.join(SRC, "silent_vlog_maker")

# (label, argv, cwd, slow)  slow=True 含真 ffmpeg，--quick 跳過
TESTS = [
    ("script_gate",     [sys.executable, "script_gate.py"], LM, False),
    ("plan_gate",       [sys.executable, "plan_gate.py"], LM, False),
    ("word_captions",   [sys.executable, "word_captions.py"], LM, True),
    ("screen_clean",    [sys.executable, "screen_clean.py"], LM, True),
    ("fx_lib",          [sys.executable, "fx_lib.py"], LM, True),
    ("delivery_qa",     [sys.executable, "delivery_qa.py"], CH, True),
    ("draft_io",        [sys.executable, "draft_io.py"], CH, False),
    ("invariants",      [sys.executable, "invariants.py"], CH, False),
    ("post_export",     [sys.executable, "post_export.py"], CH, False),
    ("shorts_vertical", [sys.executable, "shorts_vertical.py"], SV, True),
    ("channel_tracker", [sys.executable, "channel_tracker.py", "--selftest"], SRC, False),
]

GREEN_MARKS = ("GREEN", "OK", "ALL PASS", "all checks passed", "self-test passed",
               "selftest ok", "PASS")

CORE_FILES = [
    os.path.join(ROOT, "README.md"),
    os.path.join(ROOT, "CHANGELOG.md"),
    os.path.join(ROOT, "config.example.py"),
    os.path.join(ROOT, "knowledge", "README.md"),
    os.path.join(ROOT, "knowledge", "viral-playbook-framework.md"),
    os.path.join(ROOT, "knowledge", "ops-automation.md"),
    os.path.join(ROOT, "examples", "channel_state.example.json"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    reds = []
    print("=" * 56)
    print("KIT SYSTEM HEALTH  (quick=%s)" % args.quick)
    print("=" * 56)

    for label, argv, cwd, slow in TESTS:
        if args.quick and slow:
            print("[SKIP ] %-16s (slow)" % label)
            continue
        try:
            r = subprocess.run(argv, cwd=cwd, capture_output=True,
                               encoding="utf-8", errors="replace", timeout=420)
            out = (r.stdout or "") + (r.stderr or "")
            tail = out.strip().splitlines()[-1] if out.strip() else "(no output)"
            ok = r.returncode == 0 and any(m in out for m in GREEN_MARKS)
            print("[%s] %-16s %s" % ("GREEN" if ok else "RED  ", label, tail[:70]))
            if not ok:
                reds.append(label)
        except Exception as e:  # noqa: BLE001
            print("[RED  ] %-16s EXC %s" % (label, str(e)[:60]))
            reds.append(label)

    print("-" * 56)
    for p in CORE_FILES:
        ok = os.path.exists(p)
        print("[%s] file %s" % ("GREEN" if ok else "RED  ", os.path.basename(p)))
        if not ok:
            reds.append("file:" + os.path.basename(p))

    print("=" * 56)
    if reds:
        print("HEALTH RED: %d failing -> %s" % (len(reds), ", ".join(reds)))
        return 1
    print("HEALTH GREEN: all tests + core files OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
