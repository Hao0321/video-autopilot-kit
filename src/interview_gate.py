# -*- coding: utf-8 -*-
"""interview_gate.py — 訪談企劃機械閘門

擋掉「資料不足就開錄」與「來賓數據沒來源」兩類事故。

I-A 必填齊全      name/one_line/start_state/demo 缺一不可（沒這些寫不出主持台本）
I-B 成就有來源    achievements 每筆都要標來源；空的直接擋——**沒真數據的來賓不上**
                  （knowledge/meta-lessons.md M10 不編造數字 + M107 他人數據沒真截圖不上鏡）
I-C 截圖授權對齊  screenshots_ok 內每項都要能對應到某筆 achievement（授權書才寫得出來）
I-D 連結存在      至少一個 links（發布套件/置頂留言要用）
I-E 無 TODO 殘留  _guest.py 沒填完不准產套件

API: gate_guest(guest_dict) -> (ok, report) / assert_guest(guest_dict) -> guest_dict
CLI: python src/interview_gate.py   （self-test）

外殼（回傳結構 / assert 訊息 / self-test 印法）走 `longform_maker/gate_core.py`；
單檔複製出去（沒帶 gate_core）時自動退到檔頭內嵌 fallback，行為完全一致。
cp950 安全：console 純 ASCII 標記；I/O utf-8。
"""
from __future__ import annotations

import os
import sys

_GATE_CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "longform_maker")

try:
    if _GATE_CORE_DIR not in sys.path:
        sys.path.insert(0, _GATE_CORE_DIR)
    from gate_core import make_assert, report as _report, selftest_runner
except ImportError:                       # ── fallback：單檔複製也要能跑
    def _report(fails=None, warns=None, **extra):
        fails, warns = list(fails or []), list(warns or [])
        rep = {"ok": not fails, "fails": fails, "warns": warns}
        rep.update(extra)
        return rep

    def make_assert(gate_fn, label_fn, title, print_warns=False, post=None):
        def _assert(spec):
            _ok, rep = gate_fn(spec)
            if rep.get("fails"):
                raise AssertionError("[%s] %s:\n  - %s"
                                     % (label_fn(spec), title,
                                        "\n  - ".join(rep["fails"])))
            if print_warns:
                for w in rep.get("warns") or []:
                    print("   WARN " + w)
            return post(spec, rep) if post else spec
        return _assert

    def selftest_runner(cases, width=50, list_fails=False):
        failed = []

        def check(name, cond):
            print("[%s] %s" % ("PASS" if cond else "FAIL", name))
            if not cond:
                failed.append(name)

        if callable(cases):
            cases(check)
        else:
            for name, cond in cases:
                check(name, cond)
        print("-" * width)
        if failed:
            print("SELFTEST RED: %d failed" % len(failed))
            if list_fails:
                for f in failed:
                    print("  - " + f)
            return 1
        print("SELFTEST GREEN: all checks passed")
        return 0


REQUIRED = ("name", "one_line", "start_state", "demo")


def gate_guest(g: dict):
    fails, warns = [], []

    for k in REQUIRED:
        v = (g.get(k) or "").strip()
        if not v:
            fails.append("I-A 缺 %s" % k)
        elif v.startswith("TODO"):
            fails.append("I-E %s 還是 TODO" % k)

    achv = g.get("achievements") or []
    if not achv:
        fails.append("I-B 沒有任何可驗證成就——**沒真數據的來賓不上**"
                     "（節目底線，見 knowledge/meta-lessons.md M107）")
    for i, a in enumerate(achv):
        if not isinstance(a, (list, tuple)) or len(a) < 2:
            fails.append("I-B achievements[%d] 格式應為 (成果, 來源)" % i)
            continue
        if not str(a[1]).strip():
            fails.append("I-B achievements[%d] %r 沒標來源（M10：每個數字都要有出處）"
                         % (i, a[0]))

    shots = g.get("screenshots_ok") or []
    if not shots:
        warns.append("I-C 尚無同意上鏡的截圖項目——授權書第 3 條會是空的，錄前要補")
    else:
        blob = " ".join(str(a[0]) for a in achv if isinstance(a, (list, tuple)))
        for s in shots:
            if not any(tok and tok in blob for tok in str(s).split()):
                warns.append("I-C 截圖項 %r 對不到任何 achievement（授權書描述可能不精確）" % s)

    if not (g.get("links") or []):
        warns.append("I-D 沒有來賓連結——發布套件/置頂留言會開天窗")

    if not g.get("audience"):
        warns.append("發布日同步分享沒有目標平台（來賓受眾在哪未填）")

    rep = _report(fails, warns)
    return rep["ok"], rep


# 產套件前呼叫：不過直接 raise；過了印 warns 並原樣回傳來賓資料。
assert_guest = make_assert(
    gate_guest,
    lambda g: "EP%s %s" % (g.get("ep", "?"), g.get("name", "?")),
    "來賓資料 gate FAIL",
    print_warns=True,
)


def _selftest_body(check):
    good = dict(ep="01", name="小明", one_line="兩個月做出上架的 App",
                achievements=[("App 下載 5,000", "來賓提供 App Store 後台截圖")],
                links=["https://example.com"], start_state="完全不會寫程式",
                struggle="卡在上架審核", demo="用 AI 生成一個小工具",
                audience="你的短文平台", screenshots_ok=["App Store 後台 下載 5,000"])
    ok, _ = gate_guest(good)
    check("complete guest passes", ok)

    ok2, r2 = gate_guest(dict(good, achievements=[]))
    check("no achievement blocked", not ok2 and any("I-B" in f for f in r2["fails"]))

    ok3, r3 = gate_guest(dict(good, achievements=[("下載 5,000", "")]))
    check("achievement without source blocked", not ok3)

    ok4, r4 = gate_guest(dict(good, one_line="TODO 一句話"))
    check("TODO residue blocked", not ok4 and any("I-E" in f for f in r4["fails"]))

    ok5, r5 = gate_guest(dict(good, demo=""))
    check("missing demo blocked", not ok5)

    ok6, r6 = gate_guest(dict(good, links=[]))
    check("no links warns not blocks", ok6 and any("I-D" in w for w in r6["warns"]))

    try:
        assert_guest(dict(good, achievements=[]))
        check("assert_guest raises", False)
    except AssertionError as e:
        check("assert_guest raises", "來賓資料 gate FAIL" in str(e))

    check("assert_guest returns guest on pass", assert_guest(good) is good)


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=48)


if __name__ == "__main__":
    raise SystemExit(_selftest())
