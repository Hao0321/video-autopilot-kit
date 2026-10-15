"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _selftest_body(_module_globals, check):
    # ── 正向：一致的成片（小幅自然波動）必須過
    rng = _module_globals['np'].random.RandomState(7)
    consistent = [_module_globals['_mk'](luma=120 + rng.uniform(-8, 8),
                      contrast=50 + rng.uniform(-5, 5),
                      sat=0.35 + rng.uniform(-0.03, 0.03),
                      warm=6 + rng.uniform(-3, 3),
                      tint=2 + rng.uniform(-2, 2)) for _ in range(24)]
    ok, rep = _module_globals['gate_grade'](stats=consistent, profile="teaching_longform")
    check("consistent grade passes", ok)
    check("consistent grade has no warns", not rep["warns"])

    # ── G-B 白平衡漂移：一半暖一半冷 → fail（這是「色調不統一」核心症狀）
    wb = ([_module_globals['_mk'](warm=-22.0) for _ in range(12)] + [_module_globals['_mk'](warm=26.0) for _ in range(12)])
    okB, repB = _module_globals['gate_grade'](stats=wb, profile="teaching_longform")
    check("G-B blocks white-balance drift", (not okB) and any(
        f.startswith("G-B") for f in repB["fails"]))

    # ── G-A 曝光漂移
    ex = ([_module_globals['_mk'](luma=45.0) for _ in range(12)] + [_module_globals['_mk'](luma=205.0) for _ in range(12)])
    okA, repA = _module_globals['gate_grade'](stats=ex, profile="teaching_longform")
    check("G-A blocks exposure drift", (not okA) and any(
        f.startswith("G-A") for f in repA["fails"]))

    # ── G-D 飽和漂移（**同群內**才算 —— 低飽和 UI vs 高飽和實拍是結構不是缺陷）
    sa = ([_module_globals['_mk'](sat=0.34) for _ in range(12)] + [_module_globals['_mk'](sat=0.78) for _ in range(12)])
    okD, repD = _module_globals['gate_grade'](stats=sa, profile="teaching_longform")
    check("G-D blocks saturation drift within footage", (not okD) and any(
        f.startswith("G-D") for f in repD["fails"]))

    # 低飽和 UI + 高飽和實拍分屬兩群、各自一致 → **不可**判 fail（初版會誤殺）
    mixed = ([_module_globals['_mk'](sat=0.12, luma=160.0, warm=14.0) for _ in range(10)]
             + [_module_globals['_mk'](sat=0.55, luma=30.0, warm=-18.0) for _ in range(10)])
    okM, repM = _module_globals['gate_grade'](stats=mixed, profile="teaching_longform")
    check("mixed screen-rec + b-roll NOT flagged (structure, not grading)",
          okM and not repM["fails"])
    check("both groups detected", set(repM["metrics"]["groups"]) == {"ui", "footage"})
    check("cross-group warm gap reported, not judged",
          abs(repM["metrics"]["cross_group_warm_gap"] - 32.0) < 0.5)

    # ── 結構幀（純白品牌卡 / 黑場）必須被剔除，不得污染判定
    struct = ([_module_globals['_mk'](sat=0.35, luma=120.0, warm=5.0) for _ in range(10)]
              + [_module_globals['_mk'](sat=0.00, luma=240.0, clip_hi=0.68)]      # 白卡
              + [_module_globals['_mk'](sat=0.01, luma=17.0, clip_lo=0.61)])      # 黑場 outro
    okS, repS = _module_globals['gate_grade'](stats=struct, profile="teaching_longform")
    check("structural frames excluded", repS["metrics"]["n_structural"] == 2)
    check("structural frames do not cause failure", okS)

    # ── G-F 相鄰跳色：整體 spread 不大但每一顆都在跳（鋸齒）
    saw = [_module_globals['_mk'](warm=-20.0 if i % 2 else 20.0) for i in range(24)]
    okF, repF = _module_globals['gate_grade'](stats=saw, profile="teaching_longform")
    check("G-F blocks alternating jumps", (not okF) and any(
        f.startswith("G-F") for f in repF["fails"]))

    # ── G-G clipping
    cl = [_module_globals['_mk'](clip_hi=0.15) for _ in range(24)]
    okG, repG = _module_globals['gate_grade'](stats=cl, profile="teaching_longform")
    check("G-G blocks blown highlights", (not okG) and any(
        f.startswith("G-G") for f in repG["fails"]))

    # ── profile 差異：vlog 較寬鬆
    mid = ([_module_globals['_mk'](warm=-13.0) for _ in range(12)] + [_module_globals['_mk'](warm=17.0) for _ in range(12)])
    ok_t, _ = _module_globals['gate_grade'](stats=mid, profile="teaching_longform")
    ok_v, _ = _module_globals['gate_grade'](stats=mid, profile="vlog")
    check("mid drift warns/fails tighter on longform than vlog",
          ok_v and not ok_t or (ok_v == ok_t))   # vlog 至少不比長片嚴
    check("vlog profile is looser than shorts",
          _module_globals['PROFILES']["vlog"]["warm_spread"][1] > _module_globals['PROFILES']["shorts"]["warm_spread"][1])

    # ── frame_stats 數學正確性（合成影像，答案可手算）
    grey = _module_globals['np'].full((16, 16, 3), 128, dtype=_module_globals['np'].uint8)
    s = _module_globals['frame_stats'](grey)
    check("grey frame: luma=128", abs(s["luma"] - 128.0) < 0.5)
    check("grey frame: sat=0", s["sat"] < 1e-6)
    check("grey frame: warm=0", abs(s["warm"]) < 1e-6)
    check("grey frame: contrast=0", s["contrast"] < 1e-6)

    warm_img = _module_globals['np'].zeros((16, 16, 3), dtype=_module_globals['np'].uint8)
    warm_img[..., 0] = 200        # R
    warm_img[..., 2] = 100        # B
    sw = _module_globals['frame_stats'](warm_img)
    check("warm frame: warm=+100", abs(sw["warm"] - 100.0) < 0.5)

    black = _module_globals['np'].zeros((16, 16, 3), dtype=_module_globals['np'].uint8)
    check("black frame: clip_lo=1.0", _module_globals['frame_stats'](black)["clip_lo"] == 1.0)
    white = _module_globals['np'].full((16, 16, 3), 255, dtype=_module_globals['np'].uint8)
    check("white frame: clip_hi=1.0", _module_globals['frame_stats'](white)["clip_hi"] == 1.0)

    # ── 邊界
    ok_e, rep_e = _module_globals['gate_grade'](stats=[_module_globals['_mk']()], profile="teaching_longform")
    check("single frame fails cleanly", (not ok_e) and rep_e["fails"])
    try:
        _module_globals['gate_grade'](stats=consistent, profile="nope")
        check("unknown profile rejected", False)
    except ValueError:
        check("unknown profile rejected", True)
    try:
        _module_globals['gate_grade']()
        check("no input rejected", False)
    except ValueError:
        check("no input rejected", True)

    # ── assert 契約
    try:
        _module_globals['assert_grade'](stats=wb, profile="teaching_longform", label="v9")
        check("assert_grade raises on fail", False)
    except AssertionError as e:
        check("assert_grade raises on fail", "[v9] Grade gate FAIL" in str(e))

    # ── report io
    demo = _module_globals['os'].path.join(_module_globals['_DEMO_DIR'], "grade_report.txt")
    _module_globals['write_report'](repB, demo)
    check("demo report written", _module_globals['os'].path.isfile(demo) and _module_globals['os'].path.getsize(demo) > 200)
    check("demo report json written",
          _module_globals['os'].path.isfile(_module_globals['os'].path.join(_module_globals['_DEMO_DIR'], "grade_report.json")))

def _selftest(_module_globals):
    return _module_globals['selftest_runner'](_module_globals['_selftest_body'], width=56, list_fails=True)
