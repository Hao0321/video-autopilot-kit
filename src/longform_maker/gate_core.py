# -*- coding: utf-8 -*-
"""gate_core.py — 四個機械閘門的共用外殼（2026-07-28 抽出）

script_gate / plan_gate / shorts_gate / interview_gate 長年是同一個三件套：

    gate_x(spec)   -> (ok, {"fails": [...], "warns": [...], ...})
    assert_x(spec) -> 不過就 raise AssertionError（訊息格式一致）
    _selftest()    -> 逐條印 [PASS]/[FAIL]，末行 SELFTEST GREEN/RED，回 0/1

本檔只收「外殼」（回傳結構 / raise 格式 / self-test 印法）。
**判定規則一律留在各 gate 自己的檔案**——規則不集中，才不會互相污染，
也才守得住「重構不是重寫」（既有 assert 的邏輯與訊息語意一字不改）。

API:
    report(fails, warns, **extra) -> dict        # 標準回傳 dict
    raise_if_failed(rep, label, title)           # "[label] title:\n  - f1\n  - f2"
    make_assert(gate_fn, label_fn, title, print_warns=False, post=None) -> assert_x
    selftest_runner(cases, width=50, list_fails=False) -> 0/1

cp950 安全：本檔 print 只有 ASCII 標記；不做任何檔案 I/O。
"""
from __future__ import annotations

import re


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

    fail-closed：rep 不是 dict、缺 fails list、或 ok 為假卻沒列理由，也一律 raise。
    """
    fails = _failure_lines(rep)
    if fails:
        raise AssertionError("[%s] %s:\n  - %s" % (label, title, "\n  - ".join(fails)))


def _failure_lines(rep) -> list:
    """rep -> 要列出的失敗理由；回空 list 才算真的過關。"""
    if not isinstance(rep, dict):
        return ["gate report is not a dict (contract violation)"]
    fails = rep.get("fails")
    if not isinstance(fails, (list, tuple)):
        return ["gate report has no 'fails' list (contract violation)"]
    if fails:
        return [str(f) for f in fails]
    if not rep.get("ok", True):
        return ["gate returned ok=False without listing a reason"]
    return []


def make_assert(gate_fn, label_fn, title: str, print_warns: bool = False, post=None):
    """產生統一的 assert_x(spec)。

    gate_fn     : spec -> (ok, rep)
    label_fn    : spec -> 中括號內的識別字串（片名 / EP+來賓…）
    title       : "Shorts gate FAIL" 這類標題（訊息語意由各 gate 自己決定）
    print_warns : True = 過關後把 warns 印成 "   WARN xxx"（interview 慣例）
    post        : (spec, rep) -> 回傳值；None = 原樣回傳 spec

    ok 為假、或 rep 缺 fails list（契約不符）都會 raise——不靠 fails 單一欄位放行。
    """
    def _assert(spec):
        ok, rep = gate_fn(spec)
        if not ok and isinstance(rep, dict):
            rep = dict(rep, ok=False)                # tuple 的 ok 為準
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
    回傳 0=全綠 / 1=有紅（給 `raise SystemExit(...)` 用）；一條 check 都沒跑 = 紅。
    """
    failed, ran = [], []

    def check(name, cond):
        print("[%s] %s" % ("PASS" if cond else "FAIL", name))
        ran.append(name)
        if not cond:
            failed.append(name)

    if callable(cases):
        cases(check)
    else:
        for name, cond in cases:
            check(name, cond)

    print("-" * width)
    if not ran:
        print("SELFTEST RED: no checks ran")
        return 1
    if failed:
        print("SELFTEST RED: %d failed" % len(failed))
        if list_fails:
            for f in failed:
                print("  - " + f)
        return 1
    print("SELFTEST GREEN: all checks passed")
    return 0


# ────────────────────────────────────────────── 佔位字偵測（各 gate 共用）

_PLACEHOLDER_RE = re.compile(
    r"(?<![A-Za-z])(?:TODO|TBD|FIXME|XXX|YYYY|MM-DD)(?![A-Za-z])"
    r"|(?<![期等對接招款看虐優善])待(?:補|填|定|查|寫|確|提供|來賓|對方|人工|複核|審|核實|處理|更新)"
    r"|未(?:提供|填)|(?:候選|概念)[一二三四五六七八九十0-9０-９]|你的(?:主題詞|名字|cluster)"
    r"|\{[^{}\n]*\}", re.IGNORECASE)
_PLACEHOLDER_WHOLE_RE = re.compile(
    r"[?？.。…\-—_＿\s]*|N/?A|none|null|無|沒有|不明|未知", re.IGNORECASE)


def is_placeholder(text) -> bool:
    """True = 空字串或仍是模板佔位字（TODO/TBD/待補/待來賓提供/YYYY/候選一/{你的…}/?/N/A）。

    各 gate 擋「看起來有填、其實是佔位」的欄位都走這裡，避免每個 gate 各寫一套漏網規則。
    """
    s = str(text if text is not None else "").strip()
    return bool(_PLACEHOLDER_WHOLE_RE.fullmatch(s) or _PLACEHOLDER_RE.search(s))


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
        _selftest_fail_closed(check)
        _selftest_placeholders(check)

    return selftest_runner(body, width=54)


def _raises(fn) -> bool:
    try:
        fn()
    except AssertionError:
        return True
    return False


def _selftest_fail_closed(check):
    """回歸：ok=False / 缺 fails（script_gate 型 report）/ 零條 check 都不准放行。"""
    label = lambda s: "x"                            # noqa: E731
    check("make_assert raises on ok=False with empty fails", _raises(lambda: make_assert(
        lambda s: (False, {"fails": [], "warns": []}), label, "Demo gate FAIL")({})))
    check("make_assert raises when report has no fails list", _raises(lambda: make_assert(
        lambda s: (True, {"ok": True, "warnings": []}), label, "Demo gate FAIL")({})))
    check("make_assert raises when rep says ok=False", _raises(lambda: make_assert(
        lambda s: (True, {"ok": False, "fails": []}), label, "Demo gate FAIL")({})))
    check("raise_if_failed raises on non-dict / missing fails",
          _raises(lambda: raise_if_failed(None, "t", "T"))
          and _raises(lambda: raise_if_failed({"ok": True}, "t", "T")))
    import contextlib
    import io as _io
    with contextlib.redirect_stdout(_io.StringIO()):
        rc_empty = selftest_runner([], width=8)
        rc_noop = selftest_runner(lambda c: None, width=8)
    check("selftest_runner with zero checks -> RED", rc_empty == 1 and rc_noop == 1)


def _selftest_placeholders(check):
    for text in ("", "  ", "TODO 補來源", "todo", "待來賓提供", "（待補）", "TBD", "?", "N/A",
                 "YYYY-MM-DD", "標題候選一", "縮圖概念八", "你的主題詞", "{你的名字}", "未提供"):
        check("is_placeholder(%s)" % ascii(text), is_placeholder(text))
    for text in ("App 下載 5,000", "url:https://example.com/proof", "期待的那一天",
                 "等待審核三週", "AI 剪輯", "怎麼做到的？", "Todoist 教學"):
        check("not placeholder %s" % ascii(text), not is_placeholder(text))


if __name__ == "__main__":
    raise SystemExit(_selftest())
