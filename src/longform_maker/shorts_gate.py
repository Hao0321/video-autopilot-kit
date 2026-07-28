# -*- coding: utf-8 -*-
"""shorts_gate.py — 直式 Shorts 機械閘門 · fill-in-your-own-numbers

把「剪 Shorts 的所有規則」變成 build 時就擋的 assert，不靠任何人記得。
知識面（為什麼是這些規則）→ `knowledge/shorts-mastery-2026.md`。

⚙️ **DEFAULT_RULES 裡的數字是【範例校準值】**，不是宇宙常數 ——
它們來自某一種題材（無旁白、單一驚奇型的美食/旅遊直式短片）的實測。
**採用者請用自己的 3-5 支片重新校準**（方法：把你自己表現最好的 3-5 支的實際
片長 / 第一刀時間 / 非白字比例量出來，取區間；再拿表現最差的 3 支確認被擋下）。
覆寫方式不用改本檔：

    my_rules = {"dur_min": 26.0, "dur_max": 60.0, "dur_deadzone": None}
    ok, rep = gate_shorts(spec, my_rules)      # 只寫要改的鍵，其餘沿用預設
    ready = assert_shorts(spec, my_rules)      # build 前呼叫，不過直接 raise

規則分三層（本檔機械化前兩層；第三層靠人看畫面）：
  【結構】S-A 開場識別 / S-B 片長帶 / S-C 首刀 / S-D loop 對齊 / S-E 地址常駐
  【字幕】S-F 綁 segment 索引（禁手算時間）/ S-G loop 段禁字幕 / S-H 不跨 cut / S-I 白字為底
  【內容】S-J 讀畫面上的字（品名/價格）/ S-K 運鏡不移開主體 / S-L 只取主體正上方那張牌

API:
    expand_caps(spec, rules=None)   -> [(start, end, blocks, kind)]   # 由 segment 索引算時間
    gate_shorts(spec, rules=None)   -> (ok, report)                   # 全規則檢查
    assert_shorts(spec, rules=None) -> spec（含展開後 caps + 地址常駐條）

spec 結構（一支 Short）:
    {
      "name": "short_01",
      "place": "<地名/店名>",                 # 開場識別大字（必填）
      "what":  "<一句話說明這是什麼>",          # 必填
      "addr":  "<常駐資訊條：店名｜地址>",       # 必填（旅遊/美食題材＝地址；其他題材填你的常駐資訊）
      "segs":  [(clip, in_sec, dur), ...],
      "caps_by_seg": [(seg_idx, [(text, color)], kind), ...],
      "bgm_folder": "<your-bgm-subfolder>",
    }

自測：`python shorts_gate.py`

⚠️ **「純 Python」指的是這個檔案本身**：本檔不 import Pillow / numpy / ffmpeg。
但 `longform_maker/__init__.py` 會 eager-import `fx_lib`（那個要 numpy + Pillow），
所以 **`from longform_maker.shorts_gate import ...` 在沒裝 numpy 的機器上會炸**。
要真的零相依用這個閘門，就**平面 import**（`examples/04_shorts_gate.py` 示範的就是這個）：

    import sys, os
    sys.path.insert(0, os.path.join("<repo>", "src", "longform_maker"))
    from shorts_gate import gate_shorts, assert_shorts, DEFAULT_RULES

或者直接把 `shorts_gate.py` + `gate_core.py` 兩個檔複製走 —— 它們只互相依賴。
cp950 安全：print 只 ASCII；I/O utf-8。
共用外殼（回傳結構 / assert 訊息 / self-test 印法）→ gate_core.py；規則本體留在本檔。
"""
from __future__ import annotations

import math
import os
import sys
from collections import defaultdict

try:
    from gate_core import make_assert, report as _report, selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import make_assert, report as _report, selftest_runner


# ────────────────────────────────────────────── 可覆寫的門檻
# ⚠️ 全部是【範例校準值】——請用你自己的片重新量（見檔頭）。

DEFAULT_RULES = {
    # S-B 片長帶：只收「梗 / 單一驚奇」型的短帶
    "dur_min": 13.0,
    "dur_max": 25.0,
    # S-B 死區：兩頭不沾的長度（太長不像梗、太短不像教學）。None = 不設死區
    "dur_deadzone": (25.001, 44.999),
    "dur_max_slack": 0.5,          # 上限容差（湊整秒用）
    # S-C 首刀：開場多久內一定要有第一次變化
    "first_cut_max": 2.05,
    # S-D loop：末段結束點 vs 首段起點容差（秒）
    "loop_tol": 0.35,
    "tail_clear": 0.5,             # 末字幕距片尾至少留這麼多（loop 接點要乾淨）
    # S-F 字幕在段內的留邊 / 同段多條之間的間隔
    "cap_pad": 0.15,
    "cap_gap": 0.12,
    "cap_min_each": 0.45,          # 每條字幕至少要有的秒數（塞不下就擋）
    # S-I white-first：白字為底，重點色是點綴
    "nonwhite_max_ratio": 0.35,
    "nonwhite_max_colors": 2,
    "white_tokens": ("white", "w"),   # 你的色表裡代表「白」的 token
}


def merge_rules(rules: dict = None) -> dict:
    """DEFAULT_RULES + 你的覆寫。鍵打錯直接 raise（省得默默沿用預設）。"""
    r = dict(DEFAULT_RULES)
    for k, v in (rules or {}).items():
        if k not in DEFAULT_RULES:
            raise AssertionError("unknown rule key %r; valid: %s"
                                 % (k, ", ".join(sorted(DEFAULT_RULES))))
        r[k] = v
    return r


# ────────────────────────────────────────────── 字幕展開（S-F）

def seg_bounds(spec: dict) -> list:
    """[(seg 起, seg 迄)]（秒，累加 segs 的長度）。"""
    bounds, acc = [], 0.0
    for _f, _i, d in spec["segs"]:
        bounds.append((round(acc, 3), round(acc + d, 3)))
        acc += d
    return bounds


def expand_caps(spec: dict, rules: dict = None) -> list:
    """caps_by_seg（綁 segment 索引）→ 時間軸字幕；同段多條自動平分。

    人不再手算時間 → 「字幕配錯段」在結構上不可能發生
    （手算時間最常見的災情：整組字幕晚一段，全片對不上畫面）。
    """
    r = merge_rules(rules)
    pad, gap = r["cap_pad"], r["cap_gap"]
    bounds = seg_bounds(spec)

    by = defaultdict(list)
    for idx, blocks, kind in spec["caps_by_seg"]:
        by[idx].append((blocks, kind))

    out = []
    for idx in sorted(by):
        if idx >= len(bounds):
            raise AssertionError("%s caps_by_seg 指到不存在的 seg%d" % (spec["name"], idx))
        b0, b1 = bounds[idx]
        items = by[idx]
        n = len(items)
        usable = (b1 - b0) - pad * 2 - gap * (n - 1)
        if usable <= r["cap_min_each"] * n:
            raise AssertionError(
                "%s seg%d 長 %.1fs 塞不下 %d 條字幕" % (spec["name"], idx, b1 - b0, n))
        each = usable / n
        for i, (blocks, kind) in enumerate(items):
            st = round(b0 + pad + i * (each + gap), 2)
            out.append((st, round(st + each, 2), blocks, kind))
    return sorted(out)


# ────────────────────────────────────────────── 總閘門

def gate_shorts(spec: dict, rules: dict = None):
    """回傳 (ok, report)。report["fails"] 非空 = 不准出片。"""
    r = merge_rules(rules)
    fails, warns = [], []

    # ── 必填欄位（S-A / S-E）
    for k in ("place", "what", "addr"):
        if not spec.get(k):
            fails.append("S-A/E 缺 %s（開場識別/常駐資訊條是鐵則）" % k)
    if fails:
        return False, _report(fails, warns)

    segs = spec["segs"]
    dur = round(sum(s[2] for s in segs), 3)

    # ── S-B 片長帶
    if not (r["dur_min"] - 0.01 <= dur <= r["dur_max"] + r["dur_max_slack"]):
        dz = r["dur_deadzone"]
        if dz and dz[0] <= dur <= dz[1]:
            fails.append("S-B 片長 %.1fs 落在 %d-%ds 死區（兩頭不沾）"
                         % (dur, math.ceil(dz[0]), math.floor(dz[1])))
        else:
            fails.append("S-B 片長 %.1fs 不在 %.0f-%.0fs 帶"
                         % (dur, r["dur_min"], r["dur_max"]))

    # ── S-C 首刀
    if segs[0][2] > r["first_cut_max"]:
        fails.append("S-C 首刀 %.1fs > %.1fs（開場這麼久內要有變化）"
                     % (segs[0][2], r["first_cut_max"]))

    # ── S-D loop：末段須回首段同 clip，且結束點對齊首段起點
    if segs[-1][0] != segs[0][0]:
        fails.append("S-D 末段未回首段 clip（loop 不成立）")
    else:
        lend = segs[-1][1] + segs[-1][2]
        if abs(lend - segs[0][1]) > r["loop_tol"]:
            fails.append("S-D loop 未對齊：末段收在 %.1fs、首段起於 %.1fs"
                         "（運鏡片必須對齊末幀==首幀）" % (lend, segs[0][1]))

    # ── 檔案存在
    for f, _i, _d in segs:
        if not os.path.isfile(f):
            fails.append("素材不存在：%s" % os.path.basename(f))

    # ── S-A 開場識別：首段內必須有 place + what 兩條
    caps_bs = spec["caps_by_seg"]
    seg0 = [c for c in caps_bs if c[0] == 0]
    if len(seg0) < 2:
        fails.append("S-A 開場少於 2 條字幕（要【地名/主題】+【一句這是什麼】）")
    else:
        first_txt = "".join(t for t, _c in seg0[0][1])
        if spec["place"] not in first_txt:
            fails.append("S-A 首條字幕 %r 不是 place=%r" % (first_txt, spec["place"]))
        second_txt = "".join(t for t, _c in seg0[1][1])
        if spec["what"] not in second_txt:
            warns.append("S-A 第二條 %r 與 what=%r 不一致" % (second_txt, spec["what"]))

    # ── S-G loop 段（末段）禁掛內容字幕
    last_idx = len(segs) - 1
    if any(i == last_idx for i, _b, _k in caps_bs):
        fails.append("S-G 有字幕綁在 loop 段（接點要乾淨）")

    # ── S-I white-first
    toks = [t for _i, blocks, _k in caps_bs for t in blocks]
    if toks:
        white = tuple(r["white_tokens"])
        nonwhite = [t for t in toks if t[1] not in white]
        ratio = len(nonwhite) / len(toks)
        cols = set(t[1] for t in nonwhite)
        if ratio > r["nonwhite_max_ratio"]:
            fails.append("S-I 非白字比例 %.0f%% > %.0f%%"
                         % (ratio * 100, r["nonwhite_max_ratio"] * 100))
        if len(cols) > r["nonwhite_max_colors"]:
            fails.append("S-I 非白色數 %d > %d 種：%s"
                         % (len(cols), r["nonwhite_max_colors"], sorted(cols)))

    if fails:
        return False, _report(fails, warns, dur=dur)

    # ── 展開字幕後再驗（S-H 不跨 cut 由 expand 保證；這裡驗尾淨空）
    caps = expand_caps(spec, r)
    content = [c for c in caps if c[3] != "addr"]
    if content and content[-1][1] > dur - r["tail_clear"]:
        fails.append("S-D 末字幕距片尾 <%.1fs（loop 接點要乾淨）" % r["tail_clear"])

    rep = _report(fails, warns, dur=dur, caps=caps, bounds=seg_bounds(spec))
    return rep["ok"], rep


def _attach_addr(spec: dict, rep: dict) -> dict:
    """過關後的加工：附常駐資訊條（S-E）+ 展開後 caps + 片長。"""
    caps = list(rep["caps"])
    # 0.2s → 片尾全程常駐（渲染端用 kind="addr" 套自己的樣式）
    caps.append((0.2, round(rep["dur"] - 0.15, 2), [(spec["addr"], "white")], "addr"))
    return dict(spec, caps=sorted(caps), _dur=rep["dur"], _warns=rep["warns"])


def assert_shorts(spec: dict, rules: dict = None) -> dict:
    """build 前呼叫：不過直接 raise；過了回傳含展開 caps 的 spec（附常駐資訊條）。"""
    r = merge_rules(rules)
    _assert = make_assert(lambda s: gate_shorts(s, r),
                          lambda s: s.get("name", "?"),
                          "Shorts gate FAIL",
                          post=_attach_addr)
    return _assert(spec)


# ────────────────────────────────────────────── self-test

def _selftest_body(check):
    here = os.path.dirname(os.path.abspath(__file__))
    dummy = os.path.join(here, "shorts_gate.py")   # 用本檔當「存在的檔案」

    def mk(**kw):
        base = dict(
            name="t", place="測試地", what="測試說明", addr="測試地｜某路1號",
            segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                  (dummy, 13.0, 3.5), (dummy, 0.0, 2.0)],
            caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                         (0, [("測試說明", "white")], "sub"),
                         (1, [("內容一", "white")], "sub"),
                         (2, [("內容二", "white")], "sub"),
                         (3, [("內容三", "white")], "sub")],
            bgm_folder="_general",
        )
        base.update(kw)
        return base

    good = mk()
    ok, rep = gate_shorts(good)
    check("good spec passes", ok)
    check("good dur inside default band", 13.4 < rep["dur"] < 13.6)

    # 片長死區
    dead = mk(segs=[(dummy, 2.0, 2.0)] + [(dummy, 5.0, 8.0)] * 4 + [(dummy, 0.5, 1.5)])
    ok2, r2 = gate_shorts(dead)
    check("dead-zone duration fails", not ok2 and any("S-B" in f for f in r2["fails"]))

    # 首刀過長
    slow = mk(segs=[(dummy, 2.0, 3.5), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                    (dummy, 13.0, 3.5), (dummy, -1.5, 3.5)])
    ok3, r3 = gate_shorts(slow)
    check("slow first cut fails", not ok3 and any("S-C" in f for f in r3["fails"]))

    # loop 未對齊
    noloop = mk(segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                      (dummy, 13.0, 3.5), (dummy, 8.0, 2.0)])
    ok4, r4 = gate_shorts(noloop)
    check("misaligned loop fails", not ok4 and any("S-D" in f for f in r4["fails"]))

    # 缺開場識別
    noopen = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                            (1, [("內容一", "white")], "sub"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    ok5, r5 = gate_shorts(noopen)
    check("missing intro line fails", not ok5 and any("S-A" in f for f in r5["fails"]))

    # 首條不是 place
    wrongname = mk(caps_by_seg=[(0, [("隨便寫", "gold")], "hook"),
                               (0, [("測試說明", "white")], "sub"),
                               (1, [("內容一", "white")], "sub"),
                               (2, [("內容二", "white")], "sub"),
                               (3, [("內容三", "white")], "sub")])
    ok6, _r6 = gate_shorts(wrongname)
    check("first caption must be place", not ok6)

    # loop 段掛字幕
    loopcap = mk(caps_by_seg=good["caps_by_seg"] + [(4, [("多的", "white")], "sub")])
    ok7, r7 = gate_shorts(loopcap)
    check("caption on loop seg fails", not ok7 and any("S-G" in f for f in r7["fails"]))

    # 缺常駐資訊條
    noaddr = mk(addr="")
    ok8, _ = gate_shorts(noaddr)
    check("missing standing info bar fails", not ok8)

    # 非白色超標
    colorful = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                              (0, [("測試說明", "cream")], "sub"),
                              (1, [("內容一", "orange")], "sub"),
                              (2, [("內容二", "green")], "sub"),
                              (3, [("內容三", "blue")], "sub")])
    ok9, r9 = gate_shorts(colorful)
    check("too many accent colors fails", not ok9 and any("S-I" in f for f in r9["fails"]))

    # expand_caps 不跨 cut + 同段平分
    caps = expand_caps(good)
    bounds = seg_bounds(good)
    inside = all(any(b0 - 0.01 <= s and e <= b1 + 0.01 for b0, b1 in bounds)
                 for s, e, _b, _k in caps)
    check("expanded caps never cross cuts", inside)
    seg0caps = [c for c in caps if c[0] < bounds[0][1]]
    check("same-seg captions split evenly",
          len(seg0caps) == 2 and seg0caps[0][1] < seg0caps[1][0])

    # assert_shorts 附常駐資訊條
    done = assert_shorts(good)
    check("assert_shorts attaches addr track",
          any(k == "addr" for _s, _e, _b, k in done["caps"]))
    check("addr track spans whole video",
          any(k == "addr" and s <= 0.25 and e >= done["_dur"] - 0.3
              for s, e, _b, k in done["caps"]))

    # assert_shorts 不過必須 raise（訊息帶片名 + Shorts gate FAIL）
    try:
        assert_shorts(mk(addr=""))
        check("assert_shorts raises on fail", False)
    except AssertionError as e:
        check("assert_shorts raises on fail", "Shorts gate FAIL" in str(e))

    # ── 覆寫門檻（fill-in-your-own）
    long_rules = {"dur_min": 26.0, "dur_max": 60.0, "dur_deadzone": None}
    long_spec = mk(segs=[(dummy, 4.0, 2.0), (dummy, 8.0, 9.0), (dummy, 20.0, 9.0),
                         (dummy, 30.0, 9.6), (dummy, 2.4, 1.6)])
    okA, rA = gate_shorts(long_spec)
    check("31s spec fails under default rules",
          not okA and any("S-B" in f for f in rA["fails"]))
    okB, rB = gate_shorts(long_spec, long_rules)
    check("same spec passes under custom band", okB and 31.0 < rB["dur"] < 31.4)
    check("custom rules keep other checks live",
          not gate_shorts(mk(addr=""), long_rules)[0])

    # 覆寫只影響傳入那次（DEFAULT_RULES 不被就地改寫）
    check("DEFAULT_RULES untouched by override", DEFAULT_RULES["dur_min"] == 13.0)

    # 打錯鍵要 raise（否則使用者以為覆寫了其實沒有）
    try:
        gate_shorts(good, {"dur_mn": 5.0})
        check("typo in rule key raises", False)
    except AssertionError as e:
        check("typo in rule key raises", "unknown rule key" in str(e))

    # 首刀門檻可放寬
    slow2 = mk(segs=[(dummy, 2.0, 3.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                     (dummy, 13.0, 3.0), (dummy, -1.0, 3.0)])
    check("looser first_cut_max lets a 3s opener through",
          gate_shorts(slow2, {"first_cut_max": 3.05})[0])

    # 白色 token 可換成自己的色表
    palette = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                             (0, [("測試說明", "#FFFFFF")], "sub"),
                             (1, [("內容一", "#FFFFFF")], "sub"),
                             (2, [("內容二", "#FFFFFF")], "sub"),
                             (3, [("內容三", "#FFFFFF")], "sub")])
    check("custom white_tokens accepted",
          gate_shorts(palette, {"white_tokens": ("#FFFFFF",)})[0])
    check("wrong white token trips S-I",
          not gate_shorts(palette)[0])


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=52)


if __name__ == "__main__":
    raise SystemExit(_selftest())
