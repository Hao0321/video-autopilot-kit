# -*- coding: utf-8 -*-
"""gate_core.py — 機械閘門的共用外殼（所有 gate 共用）

kit 裡的每一道閘門（`script_gate` / `plan_gate` / `shorts_gate`，以及你自己加的）
長年都是同一個三件套：

    gate_x(spec)   -> (ok, {"fails": [...], "warns": [...], ...})
    assert_x(spec) -> 不過就 raise AssertionError（訊息格式一致）
    _selftest()    -> 逐條印 [PASS]/[FAIL]，末行 SELFTEST GREEN/RED，回 0/1

本檔只收「外殼」（回傳結構 / raise 格式 / self-test 印法）。
**判定規則一律留在各 gate 自己的檔案**——規則不集中，才不會互相污染。
要加自己的閘門，import 這三個函式就有一致的行為，不用複製貼上。

API:
    report(fails, warns, **extra) -> dict        # 標準回傳 dict
    raise_if_failed(rep, label, title)           # "[label] title:\n  - f1\n  - f2"
    make_assert(gate_fn, label_fn, title, print_warns=False, post=None) -> assert_x
    selftest_runner(cases, width=50, list_fails=False) -> 0/1

自測：`python gate_core.py`
純 Python，無第三方相依。cp950 安全：本檔 print 只有 ASCII 標記；不做任何檔案 I/O。
"""
from __future__ import annotations


# ────────────────────────────────────────────── 回傳結構

def report(fails=None, warns=None, **extra) -> dict:
    """建構標準 gate 回傳 dict：ok/fails/warns（+ 各 gate 自己的欄位）。"""
    fails = list(fails or [])
    warns = list(warns or [])
    rep = {"ok": not fails, "fails": fails, "warns": warns}
    rep.update(extra)
    return rep


# ────────────────────────────────────────────── assert 包裝

def raise_if_failed(rep: dict, label: str, title: str) -> None:
    """fails 非空就 raise，訊息格式全系統統一：

        [<label>] <title>:
          - 第一條
          - 第二條
    """
    fails = rep.get("fails") or []
    if fails:
        raise AssertionError("[%s] %s:\n  - %s" % (label, title, "\n  - ".join(fails)))


def make_assert(gate_fn, label_fn, title: str, print_warns: bool = False, post=None):
    """產生統一的 assert_x(spec)。

    gate_fn     : spec -> (ok, rep)
    label_fn    : spec -> 中括號內的識別字串（片名 / 集數…）
    title       : "Shorts gate FAIL" 這類標題（訊息語意由各 gate 自己決定）
    print_warns : True = 過關後把 warns 印成 "   WARN xxx"
    post        : (spec, rep) -> 回傳值；None = 原樣回傳 spec
    """
    def _assert(spec):
        _ok, rep = gate_fn(spec)
        raise_if_failed(rep, label_fn(spec), title)
        if print_warns:
            for w in rep.get("warns") or []:
                print("   WARN " + w)
        return post(spec, rep) if post else spec
    return _assert


# ────────────────────────────────────────────── self-test 外殼

def selftest_runner(cases, width: int = 50, list_fails: bool = False) -> int:
    """統一 PASS/FAIL 印法與 exit code。

    cases 兩種寫法：
      - callable(check)：把 check(name, cond) 交給你，body 內想怎麼跑都行（主用法）
      - [(name, cond), ...]：純資料表
    回傳 0=全綠 / 1=有紅（給 `raise SystemExit(...)` 用）。
    """
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


# ────────────────────────────────────────────── 自身 self-test

def _selftest() -> int:
    def body(check):
        r = report(["a"], ["w"], dur=1.0)
        check("report marks not ok when fails", r["ok"] is False and r["dur"] == 1.0)
        check("report ok when clean", report([], [])["ok"] is True)
        check("report tolerates None", report()["fails"] == [])

        try:
            raise_if_failed({"fails": ["X 壞了", "Y 也壞了"]}, "t1", "Demo gate FAIL")
            check("raise_if_failed raises", False)
        except AssertionError as e:
            msg = str(e)
            check("raise_if_failed raises", True)
            check("raise message format",
                  msg.startswith("[t1] Demo gate FAIL:\n  - X 壞了\n  - Y 也壞了"))
        raise_if_failed({"fails": []}, "t1", "Demo gate FAIL")   # 不該 raise

        af = make_assert(lambda s: (True, {"fails": [], "warns": ["w1"]}),
                         lambda s: s["n"], "Demo gate FAIL",
                         print_warns=True, post=lambda s, rep: dict(s, _w=rep["warns"]))
        out = af({"n": "x"})
        check("make_assert post applied", out["_w"] == ["w1"])
        ab = make_assert(lambda s: (False, {"fails": ["boom"], "warns": []}),
                         lambda s: s["n"], "Demo gate FAIL")
        try:
            ab({"n": "x"})
            check("make_assert raises on fail", False)
        except AssertionError as e:
            check("make_assert raises on fail", "[x] Demo gate FAIL" in str(e))

        # 巢狀跑 runner 會污染輸出 → 收進 buffer 只看 exit code
        import contextlib
        import io as _io
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_green = selftest_runner([("inner ok", True)], width=8)
            rc_red = selftest_runner([("inner red", False)], width=8)
        check("selftest_runner green -> 0", rc_green == 0)
        check("selftest_runner red -> 1", rc_red == 1)
        check("selftest_runner prints per-case lines", "[PASS] inner ok" in buf.getvalue())

    return selftest_runner(body, width=54)


if __name__ == "__main__":
    raise SystemExit(_selftest())
