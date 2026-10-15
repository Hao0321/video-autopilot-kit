"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _selftest_fixture(_module_globals):
    here = _module_globals['os'].path.dirname(_module_globals['os'].path.abspath(_module_globals['__file__']))
    dummy = _module_globals['os'].path.join(here, "shorts_gate.py")   # 用本檔當「存在的檔案」

    def mk(**kw):
        base = dict(
            name="t", place="測試地", what="測試說明", addr="📍 測試地｜某路1號",
            segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                  (dummy, 13.0, 3.5), (dummy, 0.0, 2.0)],
            caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                         (0, [("測試說明", "white")], "sub"),
                         (1, [("內容一", "white")], "sub"),
                         (2, [("內容二", "white")], "sub"),
                         (3, [("內容三", "white")], "sub")],
            bgm_folder="_通用",
        )
        base.update(kw)
        return base

    good = mk()
    return dummy, mk, good

def _selftest_battle_rules(_module_globals, check, mk, good):
    ok, rep = _module_globals['gate_shorts'](good)
    check("good spec passes", ok)
    check("good dur in 13-25 band", 13.4 < rep["dur"] < 13.6)

    battle_caps = [
        (0, [("三角龍 VS 榮耀女武神", "gold")], "impact"),
        (1, [("高速對撞", "white")], "sub"),
        (2, [("轉速還在", "white")], "sub"),
        (3, [("WIN｜三角龍", "white")], "sub"),
    ]
    battle_data = {
        "left": {"name": "三角龍", "authenticity": "official"},
        "right": {"name": "榮耀女武神", "authenticity": "official"},
        "label_policy": "names_only_when_same_authenticity",
    }
    battle_good = mk(
        place="三角龍 VS 榮耀女武神", what="三角龍 VS 榮耀女武神",
        caps_by_seg=battle_caps, battle_matchup=battle_data, loop_policy="forbidden",
        battle_edit_contract={
            "showcase_segments": [0], "result_segments": [3], "result_once": True,
            "ending": "single_pass",
        },
        tracked_graphics={
            "tracked_labels": [
                {"text": "三角龍", "evidence": "verified", "style": "typography"},
                {"text": "榮耀女武神", "evidence": "verified", "style": "typography"},
            ],
            "mask_sheens": [
                {"target_kind": "subject_object", "subject_class": "battle_top",
                 "shape": "auto_sequence", "reveal_mode": "black_to_color",
                 "evidence": "verified left matte"},
                {"target_kind": "subject_object", "subject_class": "battle_top",
                 "shape": "auto_sequence", "reveal_mode": "black_to_color",
                 "evidence": "verified right matte"},
            ],
        },
    )
    ok_bt, r_bt = _module_globals['gate_shorts'](battle_good)
    check("S-T official vs official uses names only", ok_bt and not r_bt["fails"])
    battle_bad = dict(
        battle_good,
        tracked_graphics={"tracked_labels": [
            {"text": "正版"}, {"text": "榮耀女武神"},
        ]},
    )
    ok_bt_bad, r_bt_bad = _module_globals['gate_shorts'](battle_bad)
    check("S-T official vs official rejects authentic label",
          not ok_bt_bad and any("S-T" in f for f in r_bt_bad["fails"]))
    mixed_data = {
        "left": {"name": "榮耀女武神", "authenticity": "official"},
        "right": {"name": "黃金神杖", "authenticity": "counterfeit"},
    }
    mixed_bad = dict(battle_good, battle_matchup=mixed_data)
    ok_mixed, r_mixed = _module_globals['gate_shorts'](mixed_bad)
    check("S-T official vs counterfeit requires authenticity labels",
          not ok_mixed and any("正版對盜版" in f for f in r_mixed["fails"]))
    slogan_bad = dict(
        battle_good,
        caps_by_seg=battle_caps + [(2, [("3・2・1 發射", "white")], "impact")],
    )
    r_slogan_bad = _module_globals['_battle_matchup_failures'](slogan_bad)
    check("S-U rejects translated launch slogan",
          any("S-U" in f for f in r_slogan_bad))
    slogan_good = dict(
        battle_good,
        caps_by_seg=battle_caps + [(2, [("3・2・1 Go Shoot！", "white")], "impact")],
    )
    r_slogan_good = _module_globals['_battle_matchup_failures'](slogan_good)
    check("S-U official Go Shoot slogan passes",
          not any("S-U" in f for f in r_slogan_good))
    unlabeled_result = dict(
        battle_good,
        caps_by_seg=battle_caps + [(3, [("BURST FINISH +2", "white")], "impact")],
    )
    r_result_missing, _ = _module_globals['_battle_result_findings'](unlabeled_result)
    check("S-V official Finish label requires structured evidence",
          any("S-V" in f for f in r_result_missing))
    verified_result = dict(
        unlabeled_result,
        battle_result={
            "finish": "burst",
            "winner": "三角龍",
            "human_verified": True,
            "evidence": {
                "sequence_reviewed": True,
                "confidence": 0.95,
                "first_event": "burst",
                "opponent_parts_separated": True,
                "opponent_intact_immediately_before": True,
                "same_opponent_transition_observed": True,
                "separation_event_visible": True,
                "loose_part_preexisting": False,
                "simultaneous": False,
            },
        },
    )
    r_result_good, _ = _module_globals['_battle_result_findings'](verified_result)
    check("S-V verified Burst Finish passes", not r_result_good)

def _selftest_gate_rules(_module_globals, check, dummy, mk, good):
    # 片長死區
    dead = mk(segs=[(dummy, 2.0, 2.0)] + [(dummy, 5.0, 8.0)] * 4 + [(dummy, 0.5, 1.5)])
    ok2, r2 = _module_globals['gate_shorts'](dead)
    check("dead-zone duration fails", not ok2 and any("S-B" in f for f in r2["fails"]))

    # 平台感知：同一支 ~35.5s 的片，YT Shorts 要擋、IG/FB Reels 要放行
    # （2026-07-28 競品實測：IG/FB 上 30-32s 表現正常，硬擋=假 BLOCK）
    # ⚠️ 兩個方向都驗 —— 只驗「會擋」的話，一個永遠擋人的 gate 看起來也像很嚴格（M111）
    ok_ig, r_ig = _module_globals['gate_shorts'](dict(dead, platform="ig_reels"))
    check("ig_reels 放行死區長度", ok_ig and not any("S-B" in f for f in r_ig["fails"]))
    ok_fb, _ = _module_globals['gate_shorts'](dict(dead, platform="fb_reels"))
    check("fb_reels 放行死區長度", ok_fb)
    ok_yt, r_yt = _module_globals['gate_shorts'](dict(dead, platform="yt_shorts"))
    check("yt_shorts 明寫平台仍擋", not ok_yt and any("S-B" in f for f in r_yt["fails"]))
    ok_bad, r_bad = _module_globals['gate_shorts'](dict(dead, platform="tiktok"))
    check("未知平台被擋", not ok_bad and any("未知平台" in f for f in r_bad["fails"]))
    # 預設不帶 platform 時行為必須跟舊版一模一樣（向後相容）
    check("預設平台=yt_shorts 舊行為不變",
          [f for f in r2["fails"] if "S-B" in f] == [f for f in r_yt["fails"] if "S-B" in f])

    # 首刀過長
    slow = mk(segs=[(dummy, 2.0, 3.5), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                    (dummy, 13.0, 3.5), (dummy, 0.0, 2.0)])
    ok3, r3 = _module_globals['gate_shorts'](slow)
    check("slow first cut fails", not ok3 and any("S-C" in f for f in r3["fails"]))

    # loop 未對齊
    noloop = mk(segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                      (dummy, 13.0, 3.5), (dummy, 8.0, 2.0)])
    ok4, r4 = _module_globals['gate_shorts'](noloop)
    check("misaligned loop fails", not ok4 and any("S-D" in f for f in r4["fails"]))

    # S-A 新語意（2026-08-06）：seg0 一條（place）+ what 在 seg1 首條 = 合法（warn 頂多）
    oneopen = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                             (1, [("測試說明", "white")], "sub"),
                             (2, [("內容二", "white")], "sub"),
                             (3, [("內容三", "white")], "sub")])
    ok5a, r5a = _module_globals['gate_shorts'](oneopen)
    check("S-A seg0 單條+what 在 seg1 首條可過",
          ok5a and not any("S-A" in f for f in r5a["fails"]))
    # seg0 完全沒字幕 → 仍必須擋
    noopen = mk(caps_by_seg=[(1, [("內容一", "white")], "sub"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    ok5, r5 = _module_globals['gate_shorts'](noopen)
    check("S-A seg0 零字幕仍擋", not ok5 and any("S-A" in f for f in r5["fails"]))

    # 首條不是 place
    wrongname = mk(caps_by_seg=[(0, [("隨便寫", "gold")], "hook"),
                               (0, [("測試說明", "white")], "sub"),
                               (1, [("內容一", "white")], "sub"),
                               (2, [("內容二", "white")], "sub"),
                               (3, [("內容三", "white")], "sub")])
    ok6, r6 = _module_globals['gate_shorts'](wrongname)
    check("first caption must be place", not ok6)

    # loop 段掛字幕
    loopcap = mk(caps_by_seg=good["caps_by_seg"] + [(4, [("多的", "white")], "sub")])
    ok7, r7 = _module_globals['gate_shorts'](loopcap)
    check("caption on loop seg fails", not ok7 and any("S-G" in f for f in r7["fails"]))

    # 缺地址
    noaddr = mk(addr="")
    ok8, _ = _module_globals['gate_shorts'](noaddr)
    check("missing address fails", not ok8)
    noaddr_product = mk(addr="", persistent_label_policy="omit")
    ok8b, _ = _module_globals['gate_shorts'](noaddr_product)
    check("non-location content can explicitly omit persistent label", ok8b)

    # 非白色超標
    colorful = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                              (0, [("測試說明", "cream")], "sub"),
                              (1, [("內容一", "orange")], "sub"),
                              (2, [("內容二", "green")], "sub"),
                              (3, [("內容三", "blue")], "sub")])
    ok9, r9 = _module_globals['gate_shorts'](colorful)
    check("too many accent colors fails", not ok9 and any("S-I" in f for f in r9["fails"]))

def _selftest_caption_rendering(_module_globals, check, mk, good):
    # S-S：巨字／票券／浮空可用，但只能短、只能少數語意節點
    selective = mk(caps_by_seg=[(0, [("測試地", "gold")], "impact"),
                                (0, [("測試說明", "white")], "ribbon"),
                                (1, [("內容一", "white")], "sub"),
                                (2, [("內容二", "white")], "sub"),
                                (3, [("內容三", "white")], "sub")])
    oks, rs = _module_globals['gate_shorts'](selective)
    check("S-S selective kinetic captions pass", oks and not any("S-S" in f for f in rs["fails"]))
    bad_kind = mk(caps_by_seg=[(0, [("測試地", "gold")], "explode"),
                               (0, [("測試說明", "white")], "sub")])
    okk, rk = _module_globals['gate_shorts'](bad_kind)
    check("S-S unknown kind fails", not okk and any("S-S" in f for f in rk["fails"]))
    long_float = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                                 (0, [("測試說明", "white")], "sub"),
                                 (1, [("這一句浮空文字真的太長", "white")], "float_left")])
    okl, rl = _module_globals['gate_shorts'](long_float)
    check("S-S long float fails", not okl and any("S-S" in f for f in rl["fails"]))
    noisy = mk(caps_by_seg=[(0, [("測試地", "gold")], "impact"),
                            (0, [("測試說明", "white")], "ribbon"),
                            (1, [("內容一", "white")], "float_left"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    okn, rn = _module_globals['gate_shorts'](noisy)
    check("S-S too many kinetic captions fail", not okn and any("動態字幕" in f for f in rn["fails"]))

    # expand_caps 不跨 cut + 同段平分
    caps = _module_globals['expand_caps'](good)
    bounds = _module_globals['seg_bounds'](good)
    inside = all(any(b0 - 0.01 <= s and e <= b1 + 0.01 for b0, b1 in bounds)
                 for s, e, _b, _k in caps)
    check("expanded caps never cross cuts", inside)
    seg0caps = [c for c in caps if c[0] < bounds[0][1]]
    check("same-seg captions split evenly", len(seg0caps) == 2 and seg0caps[0][1] < seg0caps[1][0])

    # assert_shorts 附地址軌
    done = _module_globals['assert_shorts'](good)
    check("assert_shorts attaches addr track",
          any(k == "addr" for _s, _e, _b, k in done["caps"]))
    check("addr track spans whole video",
          any(k == "addr" and s <= 0.25 and e >= done["_dur"] - 0.3
              for s, e, _b, k in done["caps"]))
    done_noaddr = _module_globals['assert_shorts'](mk(addr="", persistent_label_policy="omit"))
    check("omit policy does not attach addr track",
          not any(k == "addr" for _s, _e, _b, k in done_noaddr["caps"]))
    done_intro = _module_globals['assert_shorts'](mk(persistent_label_policy="intro"))
    check("intro policy attaches a short semantic chip",
          any(k == "chip" and s >= .3 and e <= 3.01
              for s, e, _b, k in done_intro["caps"]))

def _selftest_semantic_rules(_module_globals, check, mk, good):
    # ── S-O 字幕節奏（warn 級）雙向驗證（M111：只驗會 warn 抓不到壞掉的規則）
    # ⚠️ 稀疏案例**必須保留 S-A 的開場兩條**，否則 gate 在 S-A 就 return，根本跑不到 S-O
    OPEN2 = [(0, [("測試地", "gold")], "hook"), (0, [("測試說明", "white")], "sub")]

    # 開場兩條 + 中間一條 = 3 條 / 13.5s ≈ 13.3 句/分（非白字 33% < 35% 不會先被 S-I 擋）
    sparse = mk(caps_by_seg=OPEN2 + [(1, [("內容一", "white")], "sub")])
    ok_sp, r_sp = _module_globals['gate_shorts'](sparse)
    check("S-O 字幕太稀會 warn", any("S-O" in w for w in r_sp["warns"]))
    check("S-O 只 warn 不擋出片", ok_sp is True)
    check("S-O 回報 cap_rate/cap_dwell",
          r_sp.get("cap_rate") is not None and r_sp.get("cap_dwell") is not None)

    # 密：開場兩條 + 中間三段各三條 = 11 條 / 13.5s ≈ 48.9 句/分 → 不可以 warn
    dense = mk(caps_by_seg=OPEN2 + [(i, [("字%d%d" % (i, j), "white")], "sub")
                                    for i in (1, 2, 3) for j in range(3)])
    ok_dn, r_dn = _module_globals['gate_shorts'](dense)
    check("S-O 字幕夠密不 warn", ok_dn and not any("S-O" in w for w in r_dn["warns"]))

    # ── S-P 高風險宣稱 lint（雙向：無佐證要擋、有佐證要放、平凡句不誤傷）
    risky = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                            (0, [("測試說明", "white")], "sub"),
                            (1, [("樹上停滿獨角仙", "white")], "sub"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    okp, rp = _module_globals['gate_shorts'](risky)
    check("S-P 絕對量詞無佐證被擋", not okp and any("S-P" in f for f in rp["fails"]))
    okp2, rp2 = _module_globals['gate_shorts'](dict(risky, evidence={"樹上停滿獨角仙": "frame: IMG@1.4 數過 8 隻"}))
    check("S-P 附佐證即放行", okp2 and not any("S-P" in f for f in rp2["fails"]))
    for cls_txt in ("欄杆都是原木做的", "一盤裝三樣", "墨綠色水潭",
                    "世界最大跨距", "小菜吃到飽"):
        r_ = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                             (0, [("測試說明", "white")], "sub"),
                             (1, [(cls_txt, "white")], "sub"),
                             (2, [("內容二", "white")], "sub"),
                             (3, [("內容三", "white")], "sub")])
        ok_, rr_ = _module_globals['gate_shorts'](r_)
        check("S-P 抓到 %r" % cls_txt[:6], not ok_ and any("S-P" in f for f in rr_["fails"]))
    check("S-P 平凡句不誤傷", _module_globals['gate_shorts'](good)[0])   # good 無風險詞、無 evidence，必須過

def _selftest_first_frame_rules(_module_globals, check, mk, good):
    # ── S-Q 首幀品質（雙向：軟首幀要 warn、銳首幀不 warn；無 _scan.json 靜默跳過）
    import shutil as _sh
    import tempfile as _tf
    td = _tf.mkdtemp()
    try:
        clip = _module_globals['os'].path.join(td, "C1.mp4")
        io_open = open(clip, "w")
        io_open.write("x")
        io_open.close()
        scan = {"clips": [
            {"name": "C1", "rows": [{"t": 2.0, "sharp": 12.0, "bright": 120},
                                    {"t": 5.0, "sharp": 31.0, "bright": 120}]},
            {"name": "C2", "rows": [{"t": 1.0, "sharp": 28.0, "bright": 120},
                                    {"t": 3.0, "sharp": 200.0, "bright": 240}]},  # 過曝不算候選
        ]}
        with open(_module_globals['os'].path.join(td, "_scan.json"), "w", encoding="utf-8") as f:
            _module_globals['json'].dump(scan, f)
        soft = mk(segs=[(clip, 2.0, 2.0), (clip, 5.0, 3.0), (clip, 9.0, 3.0),
                        (clip, 13.0, 3.5), (clip, 0.0, 2.0)])
        _oq, rq = _module_globals['gate_shorts'](soft)
        check("S-Q 軟首幀（12 vs 31）會 warn", any("S-Q" in w for w in rq["warns"]))
        check("S-Q 過曝幀不當候選", not any("200" in w for w in rq["warns"]))
        sharp_ff = mk(segs=[(clip, 5.0, 2.0), (clip, 9.0, 3.0), (clip, 2.0, 3.0),
                            (clip, 13.0, 3.5), (clip, 3.0, 2.0)])
        _oq2, rq2 = _module_globals['gate_shorts'](sharp_ff)
        check("S-Q 銳首幀（31=池最高）不 warn", not any("S-Q" in w for w in rq2["warns"]))
        check("S-Q 無 _scan.json 靜默跳過", not any("S-Q" in w for w in _module_globals['gate_shorts'](good)[1]["warns"]))
    finally:
        _sh.rmtree(td, ignore_errors=True)

def _selftest_reading_rules(_module_globals, check, mk, good):
    # ── S-R 閱讀速率（雙向：讀不完要擋、偏快要 warn、正常不誤傷）
    # seg0 兩條各 ~0.74s：14 字 = 18.9 字/秒 → fail
    toolong = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                              (0, [("排骨蛋炒飯號稱平價版鼎泰豐", "white")], "sub"),
                              (1, [("內容一", "white")], "sub"),
                              (2, [("內容二", "white")], "sub"),
                              (3, [("內容三", "white")], "sub")])
    okr, rr = _module_globals['gate_shorts'](toolong)
    check("S-R 讀不完（18.9 字/秒）被擋", not okr and any("S-R" in f for f in rr["fails"]))
    check("S-R 正常長句不誤傷",                      # 7 字配 2.7s 段 = 2.9 字/秒
          not any("S-R" in w for w in _module_globals['gate_shorts'](mk(caps_by_seg=[
              (0, [("測試地", "gold")], "hook"),
              (1, [("七個字的內容句", "white")], "sub"),
              (2, [("內容二", "white")], "sub"),
              (3, [("內容三", "white")], "sub")]))[1]["warns"]))
    check("S-R 偏快（5.4 字/秒）有 warn",            # base seg0 第二條 4 字/0.74s
          any("S-R" in w for w in _module_globals['gate_shorts'](good)[1]["warns"]))

    # assert_shorts 不過必須 raise（訊息帶片名 + Shorts gate FAIL）
    try:
        _module_globals['assert_shorts'](mk(addr=""))
        check("assert_shorts raises on fail", False)
    except AssertionError as e:
        check("assert_shorts raises on fail", "Shorts gate FAIL" in str(e))

def _selftest_body(_module_globals, check):
    dummy, mk, good = _module_globals['_selftest_fixture']()
    _module_globals['_selftest_battle_rules'](check, mk, good)
    _module_globals['_selftest_gate_rules'](check, dummy, mk, good)
    _module_globals['_selftest_caption_rendering'](check, mk, good)
    _module_globals['_selftest_semantic_rules'](check, mk, good)
    _module_globals['_selftest_first_frame_rules'](check, mk, good)
    _module_globals['_selftest_reading_rules'](check, mk, good)

def _selftest(_module_globals) -> int:
    return _module_globals['selftest_runner'](_module_globals['_selftest_body'], width=52)
