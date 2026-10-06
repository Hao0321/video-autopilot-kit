# -*- coding: utf-8 -*-
"""plan_gate.py — 規劃層機械閘門（playbook 站1-2 的可執行版，2026-07-24 R4）

script_gate 管腳本，本檔管「腳本之前」：選題與包裝先行有沒有照爆款手冊做。
輸入 = 規劃文件純文字（格式見 PLAN_TEMPLATE.md）。

fail 級（缺了=還沒想清楚，不准往下寫稿）：
  P1 框架標籤    框架：成就/蛻變 或 工具/教學（成就框架=唯一實錘，工具框架要標機器歸屬理由）
  P2 機器歸屬    機器：推薦 或 搜尋（雙機器分流，playbook 站1）
  P3 包裝先行    「## 包裝候選」段 ≥8 組「標題 | 縮圖」配對（E7 kill 門檻）
  P4 合規        合規：通過（R26-R38 10 項先過）
  P5 cluster    cluster關鍵字：XXX（語義方向盤）
warn 級：
  W1 無 Expected Views 對標行（快篩基準）
  W2 工具框架 + 機器：推薦 組合（實錘反指標：工具框架在推薦機是輸家）

API: gate_plan(text) -> (ok, report)
CLI: python plan_gate.py <plan.md> / python plan_gate.py （self-test）
cp950 安全：console ASCII+中文無 emoji；I/O utf-8。
共用外殼（回傳結構 / self-test 印法）→ gate_core.py；規則本體留在本檔。
"""
from __future__ import annotations

import io
import os
import re
import sys
from datetime import date, timedelta

try:
    from gate_core import is_placeholder, report as _report, selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import is_placeholder, report as _report, selftest_runner

_FRAME_RE = re.compile(r"框架[:：]\s*(成就|蛻變|工具|教學|身分)")
_MACHINE_RE = re.compile(r"機器[:：]\s*(推薦|搜尋)")
_PKG_HEAD_RE = re.compile(r"^#+\s*包裝候選", re.MULTILINE)
_PAIR_RE = re.compile(r"^\s*(?:\d+[.)、]|[-*])\s*(.+?)\s*\|\s*(.+)$", re.MULTILINE)
# P4 只認行首的合規章（可帶 - / 1. / > 前綴）；句中提到「合規：通過」不算數
_COMPLIANCE_LINE_RE = re.compile(
    r"^[ \t>]*(?:[-*+][ \t]+|\d+[.)、][ \t]*)?合規[:：][ \t]*(.*)$", re.MULTILINE)
_STATUS_RE = re.compile(r"(?:通過|PASS|✓)")
_STAMP_NEGATION_RE = re.compile(
    r"待|尚未|還沒|之前|以前|撤回|否|未(?:通過|完成|複核|審|確認|跑)"
    r"|不(?:准|得|可|能|通過|合規|行)|沒(?:有|通過|過|跑)"
    r"|(?<![A-Za-z])(?:not|pending|todo|tbd)(?![A-Za-z])", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_REVIEWER_RE = re.compile(
    r"(?:複核人?|審核人?|reviewer|reviewed by)[ \t]*[:：][ \t]*([^\s,，;；、/／()（）|｜]+)",
    re.IGNORECASE)
_MACHINE_REVIEWERS = {"ai", "bot", "auto", "agent", "machine", "codex", "claude", "gpt",
                      "chatgpt", "程式", "機器", "自動", "系統"}
_CLUSTER_RE = re.compile(r"cluster\s*關鍵字[:：][ \t]*(\S+)", re.IGNORECASE)
_EXPECTED_RE = re.compile(r"Expected\s*Views|期望值對標", re.IGNORECASE)


def _pair_stats(text: str):
    """P3：回傳 (有效且不重複的配對數, 被剔除數)。佔位字 / 標題=縮圖 / 重複配對都不算。"""
    pkg = _PKG_HEAD_RE.search(text)
    if not pkg:
        return 0, 0
    seg = text[pkg.end():]
    nxt = re.search(r"^#+\s", seg, re.MULTILINE)
    seg = seg[: nxt.start()] if nxt else seg
    seen, rejected = set(), 0
    for title, thumb in _PAIR_RE.findall(seg):
        key = tuple(re.sub(r"\s+", " ", part).strip().casefold() for part in (title, thumb))
        if is_placeholder(title) or is_placeholder(thumb) or key[0] == key[1] or key in seen:
            rejected += 1
        else:
            seen.add(key)
    return len(seen), rejected


def _stamp_problem(rest: str):
    """單一合規章 → 問題描述；None = 有效（通過 + 真實 ISO 日期 + 真人複核人，無否定/佔位字）。"""
    rest = re.sub(r"\s+", " ", rest).strip()
    status = _STATUS_RE.match(rest)
    if not status:
        return "合規狀態不是『通過』（%s）" % rest[:24]
    tail = rest[status.end():]
    if _STAMP_NEGATION_RE.search(tail) or (tail.strip() and is_placeholder(tail)):
        return "合規章含否定、待辦或佔位字（%s）" % rest[:40]
    day = _ISO_DATE_RE.search(tail)
    if not day:
        return "合規章缺 ISO 日期"
    try:
        stamped = date(*(int(part) for part in day.groups()))
    except ValueError:
        return "合規章日期不存在（%s）" % day.group(0)
    if stamped > date.today() + timedelta(days=1):
        return "合規章日期在未來（%s）" % day.group(0)
    who = _REVIEWER_RE.search(tail)
    if not who or is_placeholder(who.group(1)) \
            or who.group(1).casefold() in _MACHINE_REVIEWERS:
        return "合規章缺真人複核人"
    return None


def _compliance_problem(text: str):
    """P4：每一個行首合規章都要有效（矛盾的多個章 = 不過）；None = 過。"""
    stamps = _COMPLIANCE_LINE_RE.findall(text)
    if not stamps:
        return "缺合規標記"
    for rest in stamps:
        problem = _stamp_problem(rest)
        if problem:
            return problem
    return None


def gate_plan(text: str):
    fails, warns = [], []

    m_frame = _FRAME_RE.search(text)
    if not m_frame:
        fails.append("P1 缺框架標籤（框架：成就/工具...）")
    m_machine = _MACHINE_RE.search(text)
    if not m_machine:
        fails.append("P2 缺機器歸屬（機器：推薦/搜尋）")

    n_pairs, n_rejected = _pair_stats(text)
    if n_pairs < 8:
        fails.append("P3 包裝候選不足（%d/8 組有效『標題 | 縮圖』，另剔除 %d 組佔位/重複；"
                     "E7：包不出來=砍題）" % (n_pairs, n_rejected))

    problem = _compliance_problem(text)
    if problem:
        fails.append("P4 %s（行首寫：合規：通過 YYYY-MM-DD 複核：姓名 = R26-R38 10 項人工先過）"
                     % problem)
    m_cluster = _CLUSTER_RE.search(text)
    if not m_cluster:
        fails.append("P5 缺 cluster 關鍵字")
    elif is_placeholder(m_cluster.group(1)):
        fails.append("P5 cluster 關鍵字還是佔位字（%s）" % m_cluster.group(1))

    if not _EXPECTED_RE.search(text):
        warns.append("W1 無 Expected Views 對標行")
    if m_frame and m_machine and m_frame.group(1) in ("工具", "教學", "身分") \
            and m_machine.group(1) == "推薦":
        warns.append("W2 framing and recommendation conflict: " "PUBLIC_FIXTURE uses no maintainer analytics")

    rep = _report(fails, warns, pairs=n_pairs, pairs_rejected=n_rejected)
    return rep["ok"], rep


def _stamp(day=None, who="編輯甲") -> str:
    """self-test 用的合規章；日期在執行時算（原始碼不寫死日期）。"""
    return "合規：通過 %s 複核：%s（R26-R38 checklist）" % (
        (day or date.today()).isoformat(), who)


def _selftest_body(check):
    good = (
        "# 長片0X 規劃\n框架：成就\n機器：推薦\ncluster關鍵字：AI 剪輯\n"
        + _stamp() + "\nExpected Views 對標：1,200 中位 x3\n"
        "## 包裝候選\n" + "\n".join(
            "%d. 新手卡關的第 %d 個原因 | 卡關畫面 %d 紅圈＋大字" % (i, i, i)
            for i in range(1, 10)) + "\n## 其他\n"
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
    _selftest_placeholder_plans(check, good)
    _selftest_compliance_stamps(check, good)


def _fails_on(text: str, *rules) -> bool:
    ok, rep = gate_plan(text)
    return (not ok) and all(any(f.startswith(rule) for f in rep["fails"]) for rule in rules)


def _template_path():
    """examples/PLAN_TEMPLATE.md 只在公開 kit 存在：往上找三層，找不到回 None。"""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        candidate = os.path.join(here, "examples", "PLAN_TEMPLATE.md")
        if os.path.isfile(candidate):
            return candidate
        here = os.path.dirname(here)
    return None


def _filled(template: str) -> str:
    """把模板的佔位內容換成真內容（模擬使用者照模板填完）。"""
    text = template.replace("你的主題詞", "AI 剪輯")
    text = _COMPLIANCE_LINE_RE.sub(lambda m: _stamp(), text)
    for i, n in enumerate("一二三四五六七八", 1):
        text = text.replace("標題候選%s | 縮圖概念%s" % (n, n),
                            "新手卡關的第 %d 個原因 | 卡關畫面 %d 紅圈" % (i, i))
    return text


def _selftest_placeholder_plans(check, good):
    """回歸：原樣模板、佔位配對、重複配對、佔位 cluster 都不准過；照模板填完要過。"""
    shipped = ("框架：成就\n機器：推薦\ncluster關鍵字：你的主題詞\n合規：待複核\n## 包裝候選\n"
               + "\n".join("%d. 標題候選%s | 縮圖概念%s" % (i, n, n)
                           for i, n in enumerate("一二三四五六七八", 1)) + "\n")
    check("template-shaped placeholder plan fails P3+P4+P5",
          _fails_on(shipped, "P3", "P4", "P5"))
    check("template-shaped plan passes once filled", gate_plan(_filled(shipped))[0])
    tpl = _template_path()
    if tpl is None:
        print("[SKIP] examples/PLAN_TEMPLATE.md not in this layout (embedded copy checked)")
    else:
        shipped_file = io.open(tpl, encoding="utf-8").read()
        check("PLAN_TEMPLATE.md as shipped fails P3+P4+P5",
              _fails_on(shipped_file, "P3", "P4", "P5"))
        check("PLAN_TEMPLATE.md passes once filled", gate_plan(_filled(shipped_file))[0])
    head, _sep, _tail = good.partition("## 包裝候選\n")
    dup = head + "## 包裝候選\n" + "1. 新手卡關原因 | 卡關畫面紅圈\n" * 8
    ok_dup, rep_dup = gate_plan(dup)
    check("8 identical pairs fail P3 (1 distinct)", not ok_dup and rep_dup["pairs"] == 1)
    same = head + "## 包裝候選\n" + "".join("%d. 同一句%d | 同一句%d\n" % (i, i, i)
                                            for i in range(1, 10))
    check("title == thumbnail pairs fail P3", _fails_on(same, "P3"))
    check("placeholder cluster fails P5",
          _fails_on(good.replace("cluster關鍵字：AI 剪輯", "cluster關鍵字：{你的cluster關鍵字}"), "P5"))


def _selftest_compliance_stamps(check, good):
    """回歸：P4 只收行首、日期真實、有真人複核人、無否定/待辦字的合規章。"""
    stamp, today = _stamp(), date.today()
    bad = {
        "negated note line": "說明：合規：通過 之前不准開錄（待人工複核）",
        "line-start negation": "合規：通過 之前不准開錄（待人工複核）",
        "negated despite date": _stamp(who="編輯甲 之前不准開錄"),
        "pending": "合規：待複核",
        "placeholder date": "合規：通過（政策 checklist YYYY-MM-DD）",
        "no reviewer": "合規：通過 %s（R26-R38 checklist）" % today.isoformat(),
        "placeholder reviewer": _stamp(who="{你的名字}"),
        "machine reviewer": _stamp(who="AI"),
        "future date": _stamp(day=today + timedelta(days=30)),
        "impossible date": "合規：通過 %d-02-30 複核：編輯甲" % today.year,
        "conflicting stamps": stamp + "\n合規：待複核",
    }
    for name, line in bad.items():
        check("P4 blocks %s" % name, _fails_on(good.replace(stamp, line), "P4"))
    check("bullet-prefixed stamp passes", gate_plan(good.replace(stamp, "- " + stamp))[0])


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=50)


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
