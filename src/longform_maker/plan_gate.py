# -*- coding: utf-8 -*-
"""plan_gate.py — 規劃層機械閘門（viral-playbook 站1-2 的可執行版）

script_gate 管腳本，本檔管「腳本之前」：選題與包裝先行有沒有照爆款手冊做。
輸入 = 規劃文件純文字（格式見 examples/PLAN_TEMPLATE.md）。

fail 級（缺了=還沒想清楚，不准往下寫稿）：
  P1 框架標籤    框架：成就/蛻變 或 工具/教學（成就/蛻變框架通常強於工具框架，見 knowledge/viral-playbook-framework.md）
  P2 機器歸屬    機器：推薦 或 搜尋（雙機器分流，viral-playbook 站1）
  P3 包裝先行    「## 包裝候選」段 ≥8 組「標題 | 縮圖」配對（kill 門檻）
  P4 合規        合規：通過（平台 AI 內容政策 checklist 先過）
  P5 cluster    cluster關鍵字：XXX（語義方向盤）
warn 級：
  W1 無 Expected Views 對標行（快篩基準）
  W2 工具框架 + 機器：推薦 組合（documented 反指標，見 knowledge/viral-playbook-framework.md）

API: gate_plan(text) -> (ok, report)
CLI: python plan_gate.py <plan.md> / python plan_gate.py （self-test）
cp950 安全：console ASCII+中文無 emoji；I/O utf-8。
"""
from __future__ import annotations

import io
import re
import sys

_FRAME_RE = re.compile(r"框架[:：]\s*(成就|蛻變|工具|教學|身分)")
_MACHINE_RE = re.compile(r"機器[:：]\s*(推薦|搜尋)")
_PKG_HEAD_RE = re.compile(r"^#+\s*包裝候選", re.MULTILINE)
_PAIR_RE = re.compile(r"^\s*(?:\d+[.)、]|[-*])\s*.+?\s*\|\s*.+$", re.MULTILINE)
_COMPLIANCE_RE = re.compile(r"合規[:：]\s*(通過|PASS|✓)")
_CLUSTER_RE = re.compile(r"cluster\s*關鍵字[:：]\s*\S+", re.IGNORECASE)
_EXPECTED_RE = re.compile(r"Expected\s*Views|期望值對標", re.IGNORECASE)


def gate_plan(text: str):
    fails, warns = [], []

    m_frame = _FRAME_RE.search(text)
    if not m_frame:
        fails.append("P1 缺框架標籤（框架：成就/工具...）")
    m_machine = _MACHINE_RE.search(text)
    if not m_machine:
        fails.append("P2 缺機器歸屬（機器：推薦/搜尋）")

    pkg = _PKG_HEAD_RE.search(text)
    n_pairs = 0
    if pkg:
        seg = text[pkg.end():]
        nxt = re.search(r"^#+\s", seg, re.MULTILINE)
        seg = seg[: nxt.start()] if nxt else seg
        n_pairs = len(_PAIR_RE.findall(seg))
    if n_pairs < 8:
        fails.append("P3 包裝候選不足（%d/8 組『標題 | 縮圖』；包不出來=砍題）" % n_pairs)

    if not _COMPLIANCE_RE.search(text):
        fails.append("P4 缺合規標記（合規：通過 = 平台 AI 內容政策 checklist 先過）")
    if not _CLUSTER_RE.search(text):
        fails.append("P5 缺 cluster 關鍵字")

    if not _EXPECTED_RE.search(text):
        warns.append("W1 無 Expected Views 對標行")
    if m_frame and m_machine and m_frame.group(1) in ("工具", "教學", "身分") \
            and m_machine.group(1) == "推薦":
        warns.append("W2 工具框架 x 推薦機 = documented 輸家組合（見 knowledge/viral-playbook-framework.md），改成就框架或改搜尋機定位")

    ok = not fails
    return ok, {"ok": ok, "fails": fails, "warns": warns, "pairs": n_pairs}


def _selftest() -> int:
    fails = []

    def check(name, cond):
        print("[%s] %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            fails.append(name)

    good = (
        "# 示範片0X 規劃\n框架：成就\n機器：推薦\ncluster關鍵字：示範主題\n"
        "合規：通過（政策 checklist 2026-01-01）\nExpected Views 對標：9,999 中位 x3\n"
        "## 包裝候選\n" + "\n".join(
            "%d. 標題候選%d | 縮圖概念%d" % (i, i, i) for i in range(1, 10)) + "\n## 其他\n"
    )
    ok1, r1 = gate_plan(good)
    check("good plan passes", ok1)
    check("good plan 9 pairs", r1["pairs"] == 9)
    check("good plan no W2", not any(w.startswith("W2") for w in r1["warns"]))

    bad = "# 規劃\n想做一支影片講 AI。\n"
    ok2, r2 = gate_plan(bad)
    check("empty plan fails", not ok2)
    check("all 5 fails flagged", len(r2["fails"]) == 5)

    loser = good.replace("框架：成就", "框架：工具")
    ok3, r3 = gate_plan(loser)
    check("tool-frame x browse warns W2",
          ok3 and any(w.startswith("W2") for w in r3["warns"]))

    few = good.replace("## 包裝候選\n", "## 包裝候選\n").split("## 包裝候選")
    few_text = few[0] + "## 包裝候選\n1. 只有一組 | 縮圖\n## 其他\n"
    ok4, r4 = gate_plan(few_text)
    check("few pairs fails P3", not ok4 and any("P3" in f for f in r4["fails"]))

    print("-" * 50)
    if fails:
        print("SELFTEST RED: %d failed" % len(fails))
        return 1
    print("SELFTEST GREEN: all checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok, rep = gate_plan(io.open(sys.argv[1], encoding="utf-8").read())
        print("PLAN GATE:", "PASS" if ok else "FAIL")
        for f in rep["fails"]:
            print("  FAIL -", f)
        for w in rep["warns"]:
            print("  WARN -", w)
        raise SystemExit(0 if ok else 1)
    raise SystemExit(_selftest())
