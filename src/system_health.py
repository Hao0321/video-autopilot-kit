# -*- coding: utf-8 -*-
"""system_health.py — one-command kit health check（穩定性中樞）

跑全部模組 self-test ＋ import-sanity ＋ 核心檔案存在檢查 → 單一 GREEN/RED 報告。
用法：python src/system_health.py           # 全跑（含真 ffmpeg 測試，~2-4 分鐘）
      python src/system_health.py --quick   # 跳過 ffmpeg 重測試
exit 0 = 全綠；1 = 有紅。console 輸出 cp950/UTF-8 皆安全。

三種檢查各自的意思，別混為一談：
  TESTS         模組自帶 self-test（有斷言、會驗行為）
  IMPORT_SANITY 模組**沒有** self-test，只驗「能 import ＋ CLI 起得來」。
                這是比較弱的保證，所以分開列、分開標示 —— 不假裝它是 self-test。
  CORE_FILES    檔案存在性
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
    ("gate_core",       [sys.executable, "gate_core.py"], LM, False),
    ("script_gate",     [sys.executable, "script_gate.py"], LM, False),
    ("plan_gate",       [sys.executable, "plan_gate.py"], LM, False),
    ("shorts_gate",     [sys.executable, "shorts_gate.py"], LM, False),
    ("word_captions",   [sys.executable, "word_captions.py"], LM, True),
    ("screen_clean",    [sys.executable, "screen_clean.py"], LM, True),
    ("fx_lib",          [sys.executable, "fx_lib.py"], LM, True),
    ("delivery_qa",     [sys.executable, "delivery_qa.py"], CH, True),
    ("draft_io",        [sys.executable, "draft_io.py"], CH, False),
    ("invariants",      [sys.executable, "invariants.py"], CH, False),
    ("post_export",     [sys.executable, "post_export.py"], CH, False),
    ("shorts_vertical", [sys.executable, "shorts_vertical.py"], SV, True),
    ("av_util",         [sys.executable, "av_util.py"], SRC, True),
    ("channel_tracker", [sys.executable, "channel_tracker.py", "--selftest"], SRC, False),
    ("interview_gate",  [sys.executable, "interview_gate.py"], SRC, False),
    ("interview_auto",  [sys.executable, "interview_autopilot.py", "--selftest"], SRC, False),
]

GREEN_MARKS = ("GREEN", "OK", "ALL PASS", "all checks passed", "self-test passed",
               "selftest ok", "PASS")

# ── import-sanity：沒有 self-test 的模組（分析工具，斷言不出「正確」長什麼樣）──
# 驗兩件事：(1) 在**選配套件全部缺席**的模擬環境下仍 import 得起來
#          (2) CLI `--help` 起得來（argparse 沒寫壞）
# (label, module, script, cwd, blocked_optional_pkgs)
IMPORT_SANITY = [
    ("teardown", "teardown", "teardown.py", SRC,
     ("rapidocr_onnxruntime", "opencc")),
]

# 在子行程裡把指定套件變成 ImportError，再 import 目標模組。
# 這條路徑是 teardown 的「缺選配套件只降級不崩潰」承諾的機械保證。
_IMPORT_PROBE = """
import sys
_blocked = set(%r)
class _Block(object):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _blocked:
            raise ImportError("simulated missing package: " + name)
        return None
sys.meta_path.insert(0, _Block())
import %s
print("IMPORT OK (optional packages simulated missing)")
"""

CORE_FILES = [
    os.path.join(ROOT, "README.md"),
    os.path.join(ROOT, "CHANGELOG.md"),
    os.path.join(ROOT, "config.example.py"),
    os.path.join(ROOT, "knowledge", "README.md"),
    os.path.join(ROOT, "knowledge", "viral-playbook-framework.md"),
    os.path.join(ROOT, "knowledge", "ai-content-compliance.md"),
    os.path.join(ROOT, "knowledge", "ai-content-compliance-sources.md"),
    os.path.join(ROOT, "knowledge", "ops-automation.md"),
    os.path.join(ROOT, "knowledge", "shorts-mastery-2026.md"),
    os.path.join(ROOT, "knowledge", "vertical-teardown-method.md"),
    os.path.join(ROOT, "knowledge", "interview-show-playbook.md"),
    os.path.join(ROOT, "templates", "interview", "format_bible.template.md"),
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
    for label, module, script, cwd, blocked in IMPORT_SANITY:
        try:
            probe = subprocess.run(
                [sys.executable, "-c", _IMPORT_PROBE % (sorted(blocked), module)],
                cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
                timeout=120)
            helped = subprocess.run(
                [sys.executable, script, "--help"], cwd=cwd, capture_output=True,
                encoding="utf-8", errors="replace", timeout=120)
            ok_i = probe.returncode == 0 and "IMPORT OK" in (probe.stdout or "")
            ok_h = helped.returncode == 0 and "usage:" in (helped.stdout or "")
            note = "%s / %s" % ("import OK w/o optional pkgs" if ok_i
                                else "IMPORT FAILED",
                                "--help OK" if ok_h else "--help FAILED")
            print("[%s] isanity %-15s %s"
                  % ("GREEN" if (ok_i and ok_h) else "RED  ", label, note))
            if not (ok_i and ok_h):
                reds.append("isanity:" + label)
                err = ((probe.stderr or "") if not ok_i else (helped.stderr or ""))
                if err.strip():
                    print("          %s" % err.strip().splitlines()[-1][:60])
        except Exception as e:  # noqa: BLE001
            print("[RED  ] isanity %-15s EXC %s" % (label, str(e)[:50]))
            reds.append("isanity:" + label)

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
