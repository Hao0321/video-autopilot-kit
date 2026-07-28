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

規則分四層（本檔機械化前三層；【內容】層靠人看畫面）：
  【結構】S-A 開場識別 / S-B 片長帶（**依平台**）/ S-C 首刀 / S-D loop 對齊 / S-E 地址常駐
  【字幕】S-F 綁 segment 索引（禁手算時間）/ S-G loop 段禁字幕 / S-H 不跨 cut / S-I 白字為底
  【節奏】S-O 換句速率（**warn 級，不擋出片**）
  【內容】S-J 讀畫面上的字（品名/價格）/ S-K 運鏡不移開主體 / S-L 只取主體正上方那張牌
  （S-M / S-N 是 `knowledge/shorts-mastery-2026.md` 的人工判斷項，本檔沒有這兩個標籤。
    新增規則往後接字母，**不要重用** —— 兩份文件各自編號就會撞號。）

**平台感知（S-B）**：`spec["platform"]` ∈ `PLATFORM_RULES`（yt_shorts / ig_reels / fb_reels）。
不寫就是 `DEFAULT_PLATFORM`。平台只提供**片長預設值**，`rules={...}` 仍逐項覆寫且優先：

    gate_shorts(dict(spec, platform="ig_reels"))            # 用 IG 的片長帶
    gate_shorts(dict(spec, platform="ig_reels"), {"dur_max": 45.0})   # 帶寬再收窄

平台名打錯 → **直接擋**（S-B fail），不靜默沿用預設。

API:
    merge_rules(rules=None, platform=None) -> dict   # 預設 ← 平台 ← 你的覆寫（後者優先）
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
      "platform": "yt_shorts",              # 選填；不寫 = DEFAULT_PLATFORM
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


# ────────────────────────────────────────────── 平台預設（只管 S-B 片長）
# ⚠️ **片長規則跟著平台走。** 26-44s 死區的來源是 YouTube Shorts 那一側的第三方研究；
# 拿去套 IG / FB Reels 會擋掉沒問題的片（實測樣本裡落在該區間、表現正常的不只一支）。
# 不分平台硬擋 = **假 BLOCK**：閘門看起來很嚴格，其實是在擋好片 —— 比沒有閘門更糟，
# 因為你會信任它。方法論與量測 → `knowledge/vertical-teardown-method.md` §8。
# 這幾組同樣是【範例校準值】：加自己的平台就往這裡加一列（鍵名必須是 DEFAULT_RULES 既有的鍵）。

PLATFORM_RULES = {
    "yt_shorts": {"dur_min": 13.0, "dur_max": 25.0, "dur_deadzone": (25.001, 44.999)},
    "ig_reels":  {"dur_min": 13.0, "dur_max": 60.0, "dur_deadzone": None},
    "fb_reels":  {"dur_min": 13.0, "dur_max": 60.0, "dur_deadzone": None},
}
DEFAULT_PLATFORM = "yt_shorts"     # spec 不寫 platform 就是這組（＝ v0.10 行為，向後相容）


# ────────────────────────────────────────────── 可覆寫的門檻
# ⚠️ 全部是【範例校準值】——請用你自己的片重新量（見檔頭）。

DEFAULT_RULES = {
    # S-B 片長帶 + 死區：**由 PLATFORM_RULES 提供**，這裡展開的是 DEFAULT_PLATFORM 那組。
    # 從單一來源展開（而不是再抄一次數字）→ 平台表與預設值不可能對不上。
    **PLATFORM_RULES[DEFAULT_PLATFORM],
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
    # S-O 換句節奏（warn 級，不擋出片）：直式的推進感主要來自「換句」不是「剪點」
    "cap_dwell_warn": 1.8,         # 內容字幕**中位停留**超過這麼久 = 太黏
    "cap_rate_warn": 30.0,         # 換句/分低於這個數 = 字幕太稀
}


def merge_rules(rules: dict = None, platform: str = None) -> dict:
    """DEFAULT_RULES ← platform 預設 ← 你的 `rules` 覆寫（**後者永遠贏**）。

    platform=None → 完全等同 v0.10 的 `merge_rules(rules)`（DEFAULT_RULES 本來就是
    DEFAULT_PLATFORM 那組），所以舊呼叫端一個字都不用改。
    平台名 / 鍵名打錯都直接 raise —— 靜默沿用預設 = 你以為覆寫了其實沒有。
    """
    r = dict(DEFAULT_RULES)
    if platform is not None:
        if platform not in PLATFORM_RULES:
            raise AssertionError("unknown platform %r; valid: %s"
                                 % (platform, ", ".join(sorted(PLATFORM_RULES))))
        r.update(PLATFORM_RULES[platform])
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
    fails, warns = [], []

    # ── 平台（S-B 片長帶的來源）。打錯名字就擋，不猜、不靜默 fallback。
    plat = spec.get("platform", DEFAULT_PLATFORM)
    if plat not in PLATFORM_RULES:
        fails.append("S-B 未知平台 %r（可用：%s）—— 不靜默沿用預設，請自己加一列到 PLATFORM_RULES"
                     % (plat, "/".join(sorted(PLATFORM_RULES))))
        plat = DEFAULT_PLATFORM          # 後面的檢查還是要跑完，好一次看到所有問題
    r = merge_rules(rules, plat)
    # 預設平台不加尾註 → 訊息與 v0.10 逐字相同（文件裡引用的範例訊息不會漂）
    ptag = "" if plat == DEFAULT_PLATFORM else "；平台=%s" % plat

    # ── 必填欄位（S-A / S-E）
    for k in ("place", "what", "addr"):
        if not spec.get(k):
            fails.append("S-A/E 缺 %s（開場識別/常駐資訊條是鐵則）" % k)
    if fails:
        return False, _report(fails, warns, platform=plat)

    segs = spec["segs"]
    dur = round(sum(s[2] for s in segs), 3)

    # ── S-B 片長帶（帶寬與死區由平台決定；rules= 可再逐項覆寫）
    if not (r["dur_min"] - 0.01 <= dur <= r["dur_max"] + r["dur_max_slack"]):
        dz = r["dur_deadzone"]
        if dz and dz[0] <= dur <= dz[1]:
            fails.append("S-B 片長 %.1fs 落在 %d-%ds 死區（兩頭不沾）%s"
                         % (dur, math.ceil(dz[0]), math.floor(dz[1]), ptag))
        else:
            fails.append("S-B 片長 %.1fs 不在 %.0f-%.0fs 帶%s"
                         % (dur, r["dur_min"], r["dur_max"], ptag))

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
        return False, _report(fails, warns, dur=dur, platform=plat)

    # ── 展開字幕後再驗（S-H 不跨 cut 由 expand 保證；這裡驗尾淨空）
    caps = expand_caps(spec, r)
    content = [c for c in caps if c[3] != "addr"]
    if content and content[-1][1] > dur - r["tail_clear"]:
        fails.append("S-D 末字幕距片尾 <%.1fs（loop 接點要乾淨）" % r["tail_clear"])

    # ── S-O 換句節奏（**warn 級**：報數字給人看，不擋出片）
    # 逐幀量市面直式短片的結論：節奏主體是「換句」不是「剪點」——
    # 樣本裡每一支的換句速率都高於剪點速率，最極端的一支 5 刀換了 40 次字幕。
    # 只 warn 不 fail 的理由：那批樣本**全是成功片、沒有失敗對照組**，
    # 只能說「成功的都這樣」，不能說「這樣才會成功」（→ vertical-teardown-method.md §1）。
    cap_rate = cap_dwell = None
    if content:
        dwells = sorted(round(c[1] - c[0], 3) for c in content)
        mid = len(dwells) // 2
        cap_dwell = (dwells[mid] if len(dwells) % 2
                     else round((dwells[mid - 1] + dwells[mid]) / 2, 3))
        cap_rate = round(len(content) / dur * 60, 1)
        if cap_dwell > r["cap_dwell_warn"]:
            warns.append("S-O 字幕中位停留 %.2fs > %.1fs —— 直式的節奏主體是換句不是剪點，"
                         "素材不夠就讓字幕推進，別硬切" % (cap_dwell, r["cap_dwell_warn"]))
        if cap_rate < r["cap_rate_warn"]:
            warns.append("S-O 換句 %.1f 句/分 < %.0f —— 字幕偏稀（門檻 = cap_rate_warn，"
                         "請用你自己的片重新校準）" % (cap_rate, r["cap_rate_warn"]))

    rep = _report(fails, warns, dur=dur, caps=caps, bounds=seg_bounds(spec),
                  platform=plat, cap_rate=cap_rate, cap_dwell=cap_dwell)
    return rep["ok"], rep


def _attach_addr(spec: dict, rep: dict) -> dict:
    """過關後的加工：附常駐資訊條（S-E）+ 展開後 caps + 片長。"""
    caps = list(rep["caps"])
    # 0.2s → 片尾全程常駐（渲染端用 kind="addr" 套自己的樣式）
    caps.append((0.2, round(rep["dur"] - 0.15, 2), [(spec["addr"], "white")], "addr"))
    return dict(spec, caps=sorted(caps), _dur=rep["dur"], _warns=rep["warns"])


def assert_shorts(spec: dict, rules: dict = None) -> dict:
    """build 前呼叫：不過直接 raise；過了回傳含展開 caps 的 spec（附常駐資訊條）。"""
    merge_rules(rules)          # 先驗鍵名：打錯的話當場 raise，不用等跑完 gate
    # ⚠️ 往下傳的是**原始 rules**，不是先 merge 好的 dict ——
    # merge 好的 dict 會蓋掉 spec["platform"] 帶進來的片長帶（平台層在覆寫層之前）。
    _assert = make_assert(lambda s: gate_shorts(s, rules),
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

    # ── S-B 平台感知：**同一支 35.5s 的片**，YT 要擋 / IG-FB 要放行 / 未知平台要擋。
    # 只驗「會擋」抓不到壞掉的 gate —— 一個永遠擋人的 gate 看起來也很嚴格。
    ok_ig, r_ig = gate_shorts(dict(dead, platform="ig_reels"))
    check("ig_reels passes the YT dead-zone length",
          ok_ig and not any("S-B" in f for f in r_ig["fails"]))
    check("ig_reels passes assert_shorts too",          # 抓「先 merge 蓋掉平台」那種 bug
          assert_shorts(dict(dead, platform="ig_reels"))["_dur"] > 35.0)
    ok_fb, _r_fb = gate_shorts(dict(dead, platform="fb_reels"))
    check("fb_reels passes the same length", ok_fb)
    ok_yt, r_yt = gate_shorts(dict(dead, platform="yt_shorts"))
    check("explicit yt_shorts still blocks", not ok_yt and any("S-B" in f for f in r_yt["fails"]))
    # 不指定平台 = 舊行為，訊息**逐字**相同（文件裡引用的範例訊息不會漂）
    check("default platform == explicit yt_shorts (verbatim)",
          r2["fails"] == r_yt["fails"] and r2["warns"] == r_yt["warns"])
    check("report carries the platform it used",
          r2["platform"] == "yt_shorts" and r_ig["platform"] == "ig_reels")
    # 未知平台：擋，不靜默 fallback
    ok_bad, r_bad = gate_shorts(dict(dead, platform="tiktok"))
    check("unknown platform is blocked", not ok_bad and any("未知平台" in f for f in r_bad["fails"]))
    try:
        merge_rules(None, "tiktok")
        check("merge_rules raises on unknown platform", False)
    except AssertionError as e:
        check("merge_rules raises on unknown platform", "unknown platform" in str(e))
    # 平台只給預設值，rules= 仍然優先（兩個方向都驗）
    check("rules= overrides the platform band",
          not gate_shorts(dict(dead, platform="ig_reels"), {"dur_max": 25.0})[0])
    check("rules= can also widen the default platform",
          gate_shorts(dead, {"dur_max": 60.0, "dur_deadzone": None})[0])
    check("platform layer only touches the duration keys",
          merge_rules(None, "ig_reels")["dur_deadzone"] is None
          and merge_rules(None, "ig_reels")["first_cut_max"] == DEFAULT_RULES["first_cut_max"])
    check("merge_rules(None) == merge_rules(None, DEFAULT_PLATFORM)",
          merge_rules() == merge_rules(None, DEFAULT_PLATFORM))

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

    # ── S-O 換句節奏（warn 級）雙向驗證
    # 一個「永遠不 warn」和一個「天天 warn」的規則都等於沒有規則：前者抓不到問題，
    # 後者會被當成雜訊直接無視。所以稀要 warn、密不可 warn，兩邊都得驗。
    # ⚠️ 稀疏案例**必須保留 S-A 的開場兩條**，否則 gate 在 S-A 就 return，根本跑不到 S-O。
    OPEN2 = [(0, [("測試地", "gold")], "hook"), (0, [("測試說明", "white")], "sub")]

    # 稀：開場兩條 + 中間一條 = 3 條 / 13.5s ≈ 13.3 句/分（非白 33% < 35%，不會先被 S-I 擋掉）
    sparse = mk(caps_by_seg=OPEN2 + [(1, [("內容一", "white")], "sub")])
    ok_sp, r_sp = gate_shorts(sparse)
    check("S-O warns when captions are sparse", any("S-O" in w for w in r_sp["warns"]))
    check("S-O never blocks the build", ok_sp is True)
    check("S-O reports cap_rate / cap_dwell",
          r_sp["cap_rate"] is not None and r_sp["cap_dwell"] is not None)

    # 密：開場兩條 + 中間三段各三條 = 11 條 / 13.5s ≈ 48.9 句/分 → 一個字都不該吵
    dense = mk(caps_by_seg=OPEN2 + [(i, [("字%d%d" % (i, j), "white")], "sub")
                                    for i in (1, 2, 3) for j in range(3)])
    ok_dn, r_dn = gate_shorts(dense)
    check("S-O stays quiet on a dense cut", ok_dn and not any("S-O" in w for w in r_dn["warns"]))
    check("S-O dense cut still measured", r_dn["cap_rate"] > 40.0)

    # 兩條門檻各自可覆寫（也證明停留/速率是兩個獨立分支，不是同一個判斷）
    check("cap_rate_warn is overridable",
          any("句/分" in w for w in gate_shorts(dense, {"cap_rate_warn": 99.0})[1]["warns"]))
    check("cap_dwell_warn is a separate branch",
          any("停留" in w for w in gate_shorts(dense, {"cap_dwell_warn": 0.5})[1]["warns"]))

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
