# -*- coding: utf-8 -*-
"""interview_gate.py — 訪談企劃機械閘門

擋掉「資料不足就開錄」與「來賓數據沒來源」兩類事故。

I-A 必填齊全      name/one_line/start_state/demo 缺一不可（沒這些寫不出主持台本）
I-B 成就有來源    achievements 每筆都要標**可驗證的型別化來源**；空的直接擋——**沒真數據的來賓不上**
                  `url:https://…`（http/https）／`file:<路徑>`（檔案要存在；相對路徑以 base_dir 為準）／
                  `sha256:<64 位 hex>`。TODO／待補／待來賓提供／?／YYYY 這類佔位字一律不算來源
                  （knowledge/production-safety-principles.md：不編造數字；他人數據沒真截圖不上鏡）
I-C 截圖授權對齊  screenshots_ok 內每項都要能對應到某筆 achievement（授權書才寫得出來）
I-D 連結存在      至少一個 links（發布套件/置頂留言要用）
I-E 無佔位殘留    每一個字串欄位（含 list 內）都不准留 TODO/TBD/待補/YYYY 類佔位字

API: gate_guest(guest_dict, base_dir=None) -> (ok, report)
     assert_guest(guest_dict, base_dir=None) -> guest_dict
CLI: python src/interview_gate.py   （self-test）

外殼（回傳結構 / assert 訊息 / self-test 印法）走 `longform_maker/gate_core.py`；
單檔複製出去（沒帶 gate_core）時自動退到檔頭內嵌 fallback，行為完全一致。
cp950 安全：console 純 ASCII 標記；I/O utf-8。
"""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse

_GATE_CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "longform_maker")

try:
    if _GATE_CORE_DIR not in sys.path:
        sys.path.insert(0, _GATE_CORE_DIR)
    from gate_core import is_placeholder, make_assert, report as _report, selftest_runner
except ImportError:                       # ── fallback：單檔複製也要能跑（規則與 gate_core 同步）
    _PH_RE = re.compile(
        r"(?<![A-Za-z])(?:TODO|TBD|FIXME|XXX|YYYY|MM-DD)(?![A-Za-z])"
        r"|(?<![期等對接招款看虐優善])待(?:補|填|定|查|寫|確|提供|來賓|對方|人工|複核|審|核實|處理|更新)"
        r"|未(?:提供|填)|(?:候選|概念)[一二三四五六七八九十0-9０-９]|你的(?:主題詞|名字|cluster)"
        r"|\{[^{}\n]*\}", re.IGNORECASE)
    _PH_WHOLE_RE = re.compile(
        r"[?？.。…\-—_＿\s]*|N/?A|none|null|無|沒有|不明|未知", re.IGNORECASE)

    def is_placeholder(text):
        s = str(text if text is not None else "").strip()
        return bool(_PH_WHOLE_RE.fullmatch(s) or _PH_RE.search(s))

    def _report(fails=None, warns=None, **extra):
        fails, warns = list(fails or []), list(warns or [])
        rep = {"ok": not fails, "fails": fails, "warns": warns}
        rep.update(extra)
        return rep

    def make_assert(gate_fn, label_fn, title, print_warns=False, post=None):
        def _assert(spec):
            ok, rep = gate_fn(spec)
            fails = rep.get("fails") if isinstance(rep, dict) else None
            if not isinstance(fails, (list, tuple)):
                fails = ["gate report has no 'fails' list (contract violation)"]
            elif not fails and (not ok or not rep.get("ok", True)):
                fails = ["gate returned ok=False without listing a reason"]
            if fails:
                raise AssertionError("[%s] %s:\n  - %s"
                                     % (label_fn(spec), title,
                                        "\n  - ".join(str(f) for f in fails)))
            if print_warns:
                for w in rep.get("warns") or []:
                    print("   WARN " + w)
            return post(spec, rep) if post else spec
        return _assert

    def selftest_runner(cases, width=50, list_fails=False):
        """Small emergency runner used only when the shared gate core is absent."""
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))
            print("[%s] %s" % ("PASS" if cond else "FAIL", name))

        cases(check) if callable(cases) else [check(name, cond) for name, cond in cases]
        failed = [name for name, passed in results if not passed]
        print("-" * width)
        if not results:
            print("SELFTEST RED: no checks ran")
            return 1
        if not failed:
            print("SELFTEST GREEN: all checks passed")
            return 0
        print("SELFTEST RED: %d failed" % len(failed))
        if list_fails:
            print("\n".join("  - " + name for name in failed))
        return 1


REQUIRED = ("name", "one_line", "start_state", "demo")
_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
_SOURCE_HINT = "要寫 url:https://… / file:<截圖路徑> / sha256:<64 位 hex>"


def source_problem(source, base_dir=None):
    """I-B：來源必須是可驗證的型別化參照；回問題描述，None = 合格。

    url:    只收 http/https 且有主機名
    file:   檔案必須存在（相對路徑以 base_dir 為準；沒給就以目前工作目錄為準）
    sha256: 64 位十六進位（釘住截圖內容）
    """
    s = str(source if source is not None else "").strip()
    if not s:
        return "沒標來源"
    if is_placeholder(s):
        return "來源還是佔位字（%r）" % s
    kind, sep, ref = s.partition(":")
    kind, ref = kind.strip().lower(), ref.strip()
    if not sep or kind not in ("url", "file", "sha256"):
        return "來源沒有型別（%s）" % _SOURCE_HINT
    if kind == "url":
        parsed = urlparse(ref)
        ok = parsed.scheme in ("http", "https") and bool(parsed.netloc)
        return None if ok else "url: 只收 http(s) 連結（%r）" % ref
    if kind == "file":
        path = ref if os.path.isabs(ref) or not base_dir else os.path.join(base_dir, ref)
        return None if ref and os.path.isfile(path) else "file: 指向的檔案不存在（%r）" % ref
    return None if _SHA256_RE.fullmatch(ref) else "sha256: 必須是 64 位十六進位（%r）" % ref


def _iter_strings(value, path=""):
    """遞迴走過每個字串欄位（list/tuple/dict 內的也算）→ (路徑, 字串)。"""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            yield from _iter_strings(item, "%s[%d]" % (path, i))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, "%s.%s" % (path, key) if path else str(key))


def _achievement_fails(achv, base_dir=None) -> list:
    if not achv:
        return ["I-B 沒有任何可驗證成就——**沒真數據的來賓不上**"
                "（節目底線，見 knowledge/production-safety-principles.md）"]
    fails = []
    for i, a in enumerate(achv):
        if not isinstance(a, (list, tuple)) or len(a) < 2:
            fails.append("I-B achievements[%d] 格式應為 (成果, 來源)" % i)
            continue
        if not str(a[0]).strip():
            fails.append("I-B achievements[%d] 成果是空的" % i)
        problem = source_problem(a[1], base_dir)
        if problem:
            fails.append("I-B achievements[%d] %r %s（M10：每個數字都要有可驗證出處）"
                         % (i, a[0], problem))
    return fails


def gate_guest(g: dict, base_dir=None):
    fails, warns = [], []

    for k in REQUIRED:
        if not str(g.get(k) or "").strip():
            fails.append("I-A 缺 %s" % k)
    for path, text in _iter_strings(g):
        if re.fullmatch(r"achievements\[\d+\]\[1\]", path):
            continue                          # 來源由 I-B 專門判（避免同一件事報兩次）
        if text.strip() and is_placeholder(text):
            fails.append("I-E %s 還是佔位字（%r）" % (path, text[:40]))

    achv = g.get("achievements") or []
    fails.extend(_achievement_fails(achv, base_dir))

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


def _guest_label(g) -> str:
    return "EP%s %s" % (g.get("ep", "?"), g.get("name", "?"))


def assert_guest(g: dict, base_dir=None) -> dict:
    """產套件前呼叫：不過直接 raise；過了印 warns 並原樣回傳來賓資料。

    base_dir = 相對 `file:` 來源的基準資料夾（plan 傳 _guest.py 所在的 EP 目錄）。
    """
    return make_assert(lambda item: gate_guest(item, base_dir), _guest_label,
                       "來賓資料 gate FAIL", print_warns=True)(g)


def _selftest_body(check):
    good = dict(ep="01", name="小明", one_line="兩個月做出上架的 App",
                achievements=[("App 下載 5,000", "url:https://example.com/app-store-downloads")],
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
    _selftest_sources(check, good)
    _selftest_residue(check, good)


def _passes(guest, base_dir=None) -> bool:
    return gate_guest(guest, base_dir)[0]


def _selftest_sources(check, good):
    """H4 回歸：佔位 / 無型別 / 壞掉的來源一律擋；三種型別化來源放行。"""
    import hashlib
    import tempfile
    ok, rep = gate_guest(dict(good, achievements=[("App 下載 50,000", "TODO 補來源"),
                                                  ("月營收 30 萬", "待來賓提供")]))
    check("placeholder sources blocked (TODO / pending-guest)",
          not ok and sum(f.startswith("I-B") for f in rep["fails"]) == 2)
    for src in ("?", "YYYY-06", "TBD", "未提供", "待補", "guest-supplied screenshot",
                "url:ftp://example.com/x", "url:https://", "file:no/such/shot.png",
                "sha256:abc", "sha256:" + "g" * 64):
        check("source %s blocked" % ascii(src),
              not _passes(dict(good, achievements=[("下載 5,000", src)])))
    here, name = os.path.split(os.path.abspath(__file__))
    typed = (("url", "url:https://example.com/app-store-downloads", None),
             ("absolute file", "file:" + os.path.join(here, name), None),
             ("relative file + base_dir", "file:" + name, here),
             ("sha256", "sha256:" + hashlib.sha256(b"screenshot").hexdigest(), None))
    for label, src, base in typed:
        check("typed source accepted: %s" % label,
              _passes(dict(good, achievements=[("下載 5,000", src)]), base))
    with tempfile.TemporaryDirectory() as empty:
        check("relative file: resolves against base_dir only",
              not _passes(dict(good, achievements=[("下載 5,000", "file:" + name)]), empty))


def _selftest_residue(check, good):
    """I-E 回歸：任何字串欄位（含 list 內）留佔位字都要擋。"""
    for field, value in (("struggle", "TODO 最卡的一次"), ("audience", "（待補）"),
                         ("links", ["TODO 連結"]), ("screenshots_ok", ["待確認"]),
                         ("achievements", [("TODO 數字", "url:https://example.com/x")])):
        ok, rep = gate_guest(dict(good, **{field: value}))
        check("placeholder in %s blocked (I-E)" % field,
              not ok and any(f.startswith("I-E") for f in rep["fails"]))


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=48)


if __name__ == "__main__":
    raise SystemExit(_selftest())
