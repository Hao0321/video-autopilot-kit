# -*- coding: utf-8 -*-
"""shorts_autopilot.py — 直式 Shorts 一鍵流程（2026-07-27；Hao「更簡單更傻瓜更輕鬆」）

把「Hao 丟素材 → 成片」中間所有機械步驟收成 3 個指令。
Hao 只需要做一件事：**丟素材到 _INBOX/直式-vertical-Shorts-Reels/<N>/**，然後說「剪 N」。

    步驟1  python shorts_autopilot.py scan 13 14 15
           → 正規化 9:16 + GPS 反查 + 抽接觸表 + 讀標價牌高解析度圖
           → 產出 <N>/_plan.py 骨架（segs 先填好、caps 留白等 Claude 看畫面填）

    步驟2  （Claude 看接觸表 + 標價牌圖 → 填 _plan.py 的 place/what/addr/caps_by_seg）

    步驟3  python shorts_autopilot.py build 13 14 15
           → 過 shorts_gate 全規則 → build → 自動 QA（片長/LUFS/loop/字幕對位抽幀）
           → 產出 _qa/ 驗證圖 + 一份 REPORT.md

規則 SoT → longform_maker/shorts_gate.py（機械）+ references/shorts-mastery-2026.md（知識）
機械小工具（subprocess/寫檔/ffprobe/抽幀/接觸表）SoT → av_util.py
cp950 安全：console 純 ASCII 標記；I/O utf-8。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

# Windows may expose a CP950 console even though project plans are UTF-8.
# Warnings must never abort a render merely because a caption contains a
# Japanese punctuation mark, emoji, or another otherwise valid glyph.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="backslashreplace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "longform_maker"))

from av_util import contact_sheet, duration as _dur, grab_frame, run as _run  # noqa: E402
from storage_lifecycle import (  # noqa: E402
    activate_policy,
    atomic_publish,
    canonical_output_path,
    finalize_success,
)
from project_paths import asset_path, discover_project_root, video_path  # noqa: E402
import publish_hub  # noqa: E402
from shorts_delivery import (  # noqa: E402
    apply_tracked_graphics,
    run_short_qa,
    write_short_report,
)

PROJECT_ROOT = str(discover_project_root(HERE))
INBOX = str(video_path("_INBOX", "直式-vertical-Shorts-Reels"))
BGM_ROOT = str(asset_path("bgm"))


# ───────────────────────────────────────────── 步驟1：scan

def scan(folder_id: str) -> dict:
    """正規化 + GPS + 接觸表 + 標價牌放大圖 + _plan.py 骨架。"""
    from silent_vlog_maker import normalize_to_portrait, extract_gps

    src_dir = os.path.join(INBOX, folder_id)
    assert os.path.isdir(src_dir), "找不到素材資料夾：" + src_dir
    work = os.path.join(src_dir, "_work")
    os.makedirs(work, exist_ok=True)

    # Windows 檔名不分大小寫 → 用 realpath 去重（*.MOV 與 *.mov 會抓到同一批）
    seen, raws = set(), []
    for pat in ("*.MOV", "*.mov", "*.mp4", "*.MP4"):
        for f in glob.glob(os.path.join(src_dir, pat)):
            k = os.path.normcase(os.path.realpath(f))
            if k not in seen:
                seen.add(k)
                raws.append(f)
    raws.sort()
    assert raws, "資料夾內沒有影片：" + src_dir

    info = {"folder": folder_id, "clips": [], "gps": []}

    # 1) 正規化 9:16（iPhone rotation 旗標 / 混向都吃）
    norm_files = []
    for f in raws:
        b = os.path.splitext(os.path.basename(f))[0]
        o = os.path.join(work, b + ".mp4")
        if not os.path.exists(o):
            normalize_to_portrait(f, o)
        norm_files.append(o)
        try:
            g = extract_gps(f)
        except Exception:
            g = None
        info["clips"].append({"name": b, "norm": o, "dur": round(_dur(o), 2), "gps": g})
        if g:
            info["gps"].append(g)
    print("[scan] %s: %d clips normalized" % (folder_id, len(norm_files)))

    # 2) 接觸表（每 clip 3 幀）
    sheet_dir = os.path.join(work, "_sheets")
    os.makedirs(sheet_dir, exist_ok=True)
    tiles = []
    for c in info["clips"]:
        for p in (0.15, 0.5, 0.85):
            t = round(c["dur"] * p, 2)
            jp = os.path.join(sheet_dir, "%s_%.2f.jpg" % (c["name"], p))
            if grab_frame(c["norm"], t, jp, vf="scale=190:-1"):
                tiles.append((jp, "%s@%.0f%%" % (c["name"][-4:], p * 100)))
    sheet = contact_sheet(tiles, os.path.join(work, "SHEET.jpg"))
    if sheet:
        print("[scan] contact sheet -> %s" % sheet)

    # 3) 標價牌/招牌放大圖（S-J：字幕要「讀」畫面上的字）
    sign_dir = os.path.join(work, "_signs")
    os.makedirs(sign_dir, exist_ok=True)
    n_sign = 0
    for c in info["clips"]:
        for p in (0.2, 0.5, 0.8):
            t = round(c["dur"] * p, 2)
            jp = os.path.join(sign_dir, "%s_%.0f.jpg" % (c["name"], p * 100))
            n_sign += grab_frame(c["norm"], t, jp,
                                 vf="crop=1080:760:0:80,scale=1500:-1")
    print("[scan] %d sign crops -> %s（Claude 讀品名/價格用）" % (n_sign, sign_dir))

    # 4) 自動排片段（機械可算的全做完）
    ap = auto_plan(info)

    # 5) _plan.py（片段已排好，只剩文字待填）
    plan_path = os.path.join(src_dir, "_plan.py")
    if not os.path.exists(plan_path):
        lines = ["# -*- coding: utf-8 -*-",
                 '"""自動產生的規劃骨架 — Claude 看 _work/SHEET.jpg + _work/_signs/ 後填。',
                 "",
                 "填表規則全文（不必再讀 shorts-mastery）：",
                 "1. S-J 讀畫面的字：品名+價格只取該主體正上方那張牌；讀不到留白不編",
                 "   （寫錯品名=比沒寫更糟；前科：焙茶$85 套到開心果盤）。",
                 "2. S-A 開場：首條字幕必含 place 大字，第二條=一句這是什麼。",
                 "3. S-N 首幀【人工項，gate 擋不了】：seg0 首幀=近景高對比主體。",
                 "   自動排的 hook 若是遠景/地面/空景→自己換（實測 36% vs 72.5% 續看率）。",
                 "   build 後看 _out/_qa/FIRSTFRAME.jpg 自查。",
                 "4. 白為底；重點用 gold（=奶油黃 y）；最多 2 個非白色（S-I）。",
                 "5. caps_by_seg 綁 segment 索引禁手算時間；末段(loop)禁字幕（S-F/S-G）。",
                 "6. S-R 讀得完優先：每條字幕 字數/停留 ≤5 字/秒（>7 gate 擋）；句子短、段拉長。",
                 "7. S-P【fail 級】：字幕含 絕對量詞(停滿/都是/整X/每X)/數量(三樣)/材質(原木)/",
                 "   深色(墨綠)/最高級(世界最/僅此一家)/方案(吃到飽) → evidence 必須有同文佐證，",
                 "   否則 build 直接擋。付不出證據就改寫成畫面撐得住的說法。",
                 "8. S-Q【warn 級】：首幀銳利度 < 全素材池最高的 60% 會列出更銳候選格——",
                 "   內容判斷可壓過技術分（瀑布動態模糊天生偏軟），但要親看過再定。",
                 "9. S-S 字幕美術：impact=巨字 hook/數字/payoff（≤12字）；ribbon=步驟/標籤（≤14字）；",
                 "   float_left/right=短反差詞（≤8字）。強效果最多約四成字幕，其餘 clean hold；",
                 "   build 會依語意與能量波自動路由，禁止為了熱鬧每句都浮動。\"\"\"",
                 "", "W = r\"%s\"" % work.replace("\\", "/"), "",
                 "SPEC = dict(",
                 '    name="s%s_TODO",' % folder_id,
                 '    niche="auto",  # auto / food / travel / cafe / toy / product / game / diy / ai / documentary / interview / automotive / fitness / fashion / architecture / business / nature / music',
                 '    place="TODO 地名/店名",',
                 '    what="TODO 一句這是什麼",',
                 '    addr="TODO 📍 名稱｜完整地址",',
                 "    segs=[",
                 "        # (clip, in_sec, dur)  ← 首段 ≤2.0s；末段須收在首段起點",
                 ]
        segs = ap.get("segs") or [(c["norm"], 0.0, 2.0) for c in info["clips"]]
        for i, (f, i_in, d) in enumerate(segs):
            tag = "HOOK（自動選：畫面最銳利/亮度適中/鏡頭最穩）" if i == 0 else (
                  "loop（結束點已對齊首段起點，勿改）" if i == len(segs) - 1 else "")
            lines.append('        (W + "/%s", %.2f, %.1f),   # seg%d %s'
                         % (os.path.basename(f), i_in, d, i, tag))
        lines += ["    ],",
                  "    # 每段一條字幕；(seg 索引, [(文字, 顏色)], kind)",
                  "    #   kind：hook/sub/main；需要明確指定時可用 impact/ribbon/float_left/float_right",
                  "    #   顏色：gold=重點（每支僅 1-2 處）/ white=其餘",
                  "    #   ⚠️ 品名+價格只能取「該主體正上方那張牌」；讀不到就不編",
                  "    caps_by_seg=[",
                  '        (0, [("TODO 地名/店名", "gold")], "hook"),',
                  '        (0, [("TODO 一句這是什麼", "white")], "sub"),']
        for i in range(1, max(1, len(segs) - 1)):
            lines.append('        (%d, [("TODO seg%d 的內容", "white")], "sub"),' % (i, i))
        lines += ["    ],",
                  "    # S-P：高風險宣稱的佐證（key=字幕原文；frame: 哪格看到什麼 / sign: 哪張牌逐字讀 /",
                  "    #      web: 出處 / user: Hao 告知）。沒命中風險詞的字幕可不填。",
                  "    evidence={},",
                  '    bgm_folder="TODO 見 assets/bgm/（美食/旅遊/森林自然/走路散步/咖啡廳甜點…）",',
                  '    bgm_policy="asset_hub",  # asset_hub / folder；人工已選定題材資料夾時用 folder',
                  '    bgm_prefer="energetic",  # energetic / chill',
                  ")",
                  "",
                  "# ── 上架文案（統一版：一稿三發。2026-08-04 Hao 裁決——Meta 演算法與 YT 同構，",
                  "#    不做平台分稿；隨意發線本來就不優化演算法。YT 只是多一個標題欄位。）",
                  "COPY = dict(",
                  '    yt_title="TODO 地名放最前｜一句 hook",',
                  '    text="TODO 2-4 句、只寫已驗證字幕裡有的事＋空行＋📍完整地址＋4-5 個 hashtag（含 #Shorts）",',
                  ")",
                  "",
                  "# 自動排片段結果：%d 段 / %.1fs（已在 13-25s 帶內、首刀 2.0s、loop 對齊）"
                  % (len(segs), sum(x[2] for x in segs))]
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("[scan] plan skeleton -> %s" % plan_path)
    else:
        print("[scan] plan exists (kept): %s" % plan_path)

    with open(os.path.join(work, "_scan.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return info



# ───────────────────────────────────────────── 自動排片段（更聰明）

def _clip_metrics(norm_path: str, dur: float, step: float = 0.5) -> list:
    """逐 step 秒量 (銳利度, 亮度, 與前一格的變化量) → 找「畫面穩定又有內容」的窗。

    銳利度用 Laplacian 變異數 proxy（對焦準/有主體的幀分數高）；
    變化量用相鄰幀差（低=鏡頭穩，高=在搖）。
    """
    import numpy as np
    from PIL import Image
    rows, prev = [], None
    t = 0.0
    tmp = norm_path + ".m.png"
    while t < dur - 0.05:
        if grab_frame(norm_path, "%.2f" % t, tmp, vf="scale=120:214"):
            a = np.asarray(Image.open(tmp).convert("L"), dtype=float)
            lap = float(np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean())
            bri = float(a.mean())
            mot = float(np.abs(a - prev).mean()) if prev is not None else 0.0
            rows.append({"t": round(t, 2), "sharp": round(lap, 2),
                         "bright": round(bri, 1), "motion": round(mot, 2)})
            prev = a
        t += step
    if os.path.exists(tmp):
        os.remove(tmp)
    return rows


def _best_window(rows: list, want: float, step: float = 0.5) -> tuple:
    """挑「銳利度高 + 亮度不過暗 + 鏡頭不亂晃」的連續窗；回 (in_sec, score)。"""
    n = max(1, int(round(want / step)))
    if len(rows) < n:
        return (0.0, 0.0)
    best, bi = -1e9, 0
    for i in range(0, len(rows) - n + 1):
        w = rows[i:i + n]
        sharp = sum(r["sharp"] for r in w) / n
        bright = sum(r["bright"] for r in w) / n
        motion = sum(r["motion"] for r in w) / n
        # 亮度懲罰：太暗(<60)或過曝(>210) 扣分（樣本11 暗綠遠景的教訓）
        pen = 0.0
        if bright < 60:
            pen += (60 - bright) * 0.8
        if bright > 210:
            pen += (bright - 210) * 0.8
        score = sharp * 1.6 - motion * 1.1 - pen
        if score > best:
            best, bi = score, i
    return (rows[bi]["t"], round(best, 1))


def _wave_segment_durations(count: int, budget: float) -> list[float]:
    """把中段排成快→推進→慢呼吸→快 payoff，而不是每顆等長。

    低能段的鏡頭較長、高能段較短。輸出仍守 Shorts gate 的單顆安全範圍，
    且總和盡量等於 budget；這只是畫面節奏，不替素材語意做假判斷。
    """
    if count <= 0:
        return []
    patterns = {
        1: [1.0],
        2: [.82, 1.18],
        3: [.76, 1.28, .82],
        4: [.78, .96, 1.34, .72],
        5: [.74, .94, 1.10, 1.34, .68],
        6: [.72, .90, 1.04, 1.36, .66, .86],
    }
    weights = patterns.get(count, [1.0] * count)
    unit = max(.01, float(budget)) / sum(weights)
    vals = [max(1.8, min(3.6, unit * w)) for w in weights]
    # clamp 後把誤差分散回仍有空間的鏡頭，避免最後一顆突然異常長／短。
    for _ in range(20):
        diff = float(budget) - sum(vals)
        if abs(diff) < .03:
            break
        room = [i for i, v in enumerate(vals)
                if (diff > 0 and v < 3.58) or (diff < 0 and v > 1.82)]
        if not room:
            break
        share = diff / len(room)
        for i in room:
            vals[i] = max(1.8, min(3.6, vals[i] + share))
    return [round(v, 2) for v in vals]


def auto_plan(info: dict, target: float = 16.0) -> dict:
    """挑 hook、排 cinematic wave 片段、算 loop 對齊、湊進 13-25s。

    留給 Claude 的只剩「文字」：place / what / addr / 每段字幕。
    """
    clips = [c for c in info["clips"] if c["dur"] >= 1.6]
    if not clips:
        return {}
    print("[auto] 分析 %d 支 clip 的畫面品質…" % len(clips))
    for c in clips:
        c["rows"] = _clip_metrics(c["norm"], c["dur"])
        c["best_in"], c["score"] = _best_window(c["rows"], min(2.6, c["dur"] - 0.2))

    # hook = 分數最高那支（銳利、亮度適中、鏡頭穩）
    hook = max(clips, key=lambda c: c["score"])
    others = [c for c in clips if c is not hook]
    others.sort(key=lambda c: c["score"], reverse=True)

    # 首段 2.0s；loop 段長度 1.6s（需 hook 的 best_in ≥1.6 才收得回，否則往後挪）
    loop_len = 1.6
    hook_in = max(hook["best_in"], loop_len + 0.1)
    if hook_in + 2.0 > hook["dur"]:
        hook_in = max(loop_len + 0.1, hook["dur"] - 2.1)
    segs = [(hook["norm"], round(hook_in, 2), 2.0)]

    # 中段：用能量波分配，不再機械等長。低能呼吸較長、payoff 前後較短。
    mid = others[:6] if others else []
    if mid:
        budget = target - 2.0 - loop_len
        wave_durations = _wave_segment_durations(len(mid), budget)
        for c, wanted in zip(mid, wave_durations):
            win, _ = _best_window(c["rows"], min(wanted, c["dur"] - 0.2))
            take = min(wanted, c["dur"] - win - 0.1)
            if take >= 1.8:
                segs.append((c["norm"], round(win, 2), round(take, 1)))
    # loop 段：結束點 == 首段起點
    segs.append((hook["norm"], round(hook_in - loop_len, 2), loop_len))

    total = round(sum(s[2] for s in segs), 1)
    # 落在 13-25 外 → 微調中段
    if total < 13.0 and len(segs) > 2:
        add = (13.2 - total) / (len(segs) - 2)
        segs = [segs[0]] + [(f, i, round(d + add, 1)) for f, i, d in segs[1:-1]] + [segs[-1]]
    elif total > 25.0 and len(segs) > 3:
        segs = [segs[0]] + segs[1:1 + 5] + [segs[-1]]
        over = round(sum(s[2] for s in segs), 1) - 24.5
        if over > 0:
            cut = over / (len(segs) - 2)
            segs = [segs[0]] + [(f, i, round(max(2.0, d - cut), 1)) for f, i, d in segs[1:-1]] + [segs[-1]]

    total = round(sum(s[2] for s in segs), 1)
    print("[auto] cinematic wave 排出 %d 段 / %.1fs（hook=%s，loop 已對齊）"
          % (len(segs), total, os.path.basename(hook["norm"])))
    return {"segs": segs, "hook": hook["norm"], "total": total}


# ───────────────────────────────────────────── 步驟3：build + QA

def _bgm_candidates(folder_name: str) -> list:
    """BGM 候選。2026-07-29 去靜默：

    舊版三層靜默疊加——資料夾名打錯→無聲換 _通用（氣氛全錯不會知道）→
    _通用 也空→pick_bgm 回 None→render 拿 None 繼續跑，要到 QA 的 LUFS
    才間接發現，訊息還跟真因無關。改成：fallback 大聲印、全空直接 raise。
    （順修：舊 fallback 只 glob *.mp3，_通用 放 wav 會被漏。）
    """
    def _glob(name):
        d = os.path.join(BGM_ROOT, name)
        return (sorted(glob.glob(os.path.join(d, "*.wav"))) +
                sorted(glob.glob(os.path.join(d, "*.mp3"))))

    if not os.path.isdir(os.path.join(BGM_ROOT, folder_name)):
        print("   WARN BGM folder does not exist: %r -> fallback _通用" % folder_name)
    cands = _glob(folder_name)
    if not cands:
        print("   WARN BGM folder %r has no wav/mp3 -> fallback _通用" % folder_name)
        cands = _glob("_通用")
    if not cands:
        raise AssertionError(
            "BGM candidates empty: folder %r and _通用 both have no wav/mp3 -- "
            "silent Short relies on BGM as the only audio; no BGM = broken deliverable. "
            "Fix the folder name in _plan.py or add tracks under %s" % (folder_name, BGM_ROOT))
    return cands


def _resolve_bgm(spec: dict, visual_plan: dict, folder_bgm: str) -> tuple[str, str]:
    """Respect an explicit editorial music lock; otherwise use Asset Hub ranking."""
    policy = str(spec.get("bgm_policy", "asset_hub"))
    if policy not in {"asset_hub", "folder"}:
        raise AssertionError("unknown bgm_policy %r; expected asset_hub/folder" % policy)
    if policy == "folder":
        return folder_bgm, "folder_lock"
    selected = (visual_plan.get("asset_intelligence") or {}).get("selected_bgm")
    if selected:
        selected_path = selected if os.path.isabs(selected) \
            else os.path.join(PROJECT_ROOT, selected.replace("/", os.sep))
        if os.path.isfile(selected_path):
            return selected_path, "asset_hub"
    return folder_bgm, "folder_fallback"


def build(folder_id: str) -> dict:
    from shorts_gate import assert_shorts
    from silent_vlog_maker import build_one_short, pick_bgm, NICHE_FONTS
    from caption_director import apply_caption_system
    from visual_director import write_visual_plan

    src_dir = os.path.join(INBOX, folder_id)
    plan_path = os.path.join(src_dir, "_plan.py")
    assert os.path.exists(plan_path), "還沒有 _plan.py，先跑 scan：" + plan_path

    import importlib.util
    spec_mod = importlib.util.spec_from_file_location("plan_%s" % folder_id, plan_path)
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    spec = mod.SPEC
    assert "TODO" not in json.dumps(spec, default=str), \
        "%s/_plan.py 還有 TODO 未填" % folder_id

    ready = assert_shorts(spec)          # ← 全規則機械閘門
    for w in ready.get("_warns", []):
        print("   WARN " + w)

    cands = _bgm_candidates(spec["bgm_folder"])
    bgm = pick_bgm(cands, ready["_dur"], prefer=spec.get("bgm_prefer", "energetic"))

    out_dir = os.path.join(src_dir, "_out")
    os.makedirs(out_dir, exist_ok=True)
    # M115：版本是 metadata，不是完整影片副本。每個 folder 永遠只寫 current.mp4；
    # 第一次啟用時把既有舊檔 freeze 成 legacy baseline，之後任何新 vN 輸出會被 gate 擋。
    policy = activate_policy(out_dir)
    out = str(canonical_output_path(out_dir))
    work_dir = os.path.join(out_dir, "_work")
    caption_rows = []
    for s, e, pieces, kind in ready["caps"]:
        caption_rows.append({
            "start": s, "end": e,
            "text": "".join(str(text) for text, _color in pieces), "kind": kind,
        })
    theme_text = " ".join(str(spec.get(k, "")) for k in
                          ("name", "place", "what", "bgm_folder")) + " " + \
                 " ".join(row["text"] for row in caption_rows)
    visual_plan_path = os.path.join(out_dir, "current_visual_plan.json")
    visual_plan = write_visual_plan(visual_plan_path, duration=ready["_dur"], captions=caption_rows,
                                    genre=spec.get("niche", "auto"), context_text=theme_text,
                                    format="short", seed=folder_id,
                                    color_profile=spec.get("color_profile"),
                                    color_strength=spec.get("color_strength"))
    if spec.get("motion_asset_policy") == "tracked_only":
        # Competitive/product footage already has high information density.
        # Keep real footage + verified tracking instead of generic decorative
        # stars, corners, dots or transition-like motion assets.
        visual_plan.setdefault("motion_assets", {})["cues"] = []
        visual_plan["motion_assets"]["policy"] = "tracked_only"
        with open(visual_plan_path, "w", encoding="utf-8") as handle:
            json.dump(visual_plan, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    # 視覺 plan 自動把少數 hook／數字／轉折路由成 impact／ribbon／float；
    # 文字內容與時間不變，white-first／動態密度由 caption_director 再驗一次。
    ready = dict(ready, caps=apply_caption_system(
        ready["caps"], visual_plan["caption_system"]))
    # Asset Hub ranks the whole indexed music library without re-probing every
    # song.  Keep the legacy spec-folder result only as a graceful fallback.
    bgm, bgm_source = _resolve_bgm(spec, visual_plan, bgm)
    if bgm_source == "asset_hub":
        print("[asset-hub] indexed BGM -> " + os.path.relpath(bgm, PROJECT_ROOT))
    elif bgm_source == "folder_lock":
        print("[music] plan-locked folder BGM -> " + os.path.relpath(bgm, PROJECT_ROOT))
    domain, theme = visual_plan["domain"], visual_plan["theme"]
    font = NICHE_FONTS.get(domain, NICHE_FONTS.get(theme, "Noto Sans TC"))
    print("[build] %s dur=%.1fs segs=%d domain=%s theme=%s font=%s"
          % (spec["name"], ready["_dur"], len(spec["segs"]), domain, theme, font))
    build_one_short(spec["segs"], ready["caps"], bgm, out, font=font, theme=theme,
                    visual_plan=visual_plan, work_dir=work_dir)

    tracked_report = apply_tracked_graphics(spec, ready, out, out_dir, work_dir)

    qa = run_short_qa(out, ready, out_dir)
    color_report_path = os.path.join(out_dir, "current_color_report.json")
    if os.path.isfile(color_report_path):
        with open(color_report_path, encoding="utf-8") as handle:
            qa["color_grade"] = json.load(handle)
    if tracked_report:
        qa["tracked_graphics"] = tracked_report
    qa["visual_theme"] = theme
    qa["editing_domain"] = domain
    qa["visual_plan"] = visual_plan_path
    qa["asset_plan"] = os.path.join(out_dir, "current_asset_plan.json")
    qa["selected_bgm"] = bgm
    from quality_95 import short_evidence, write_report as write_quality_report
    from review_loop import create_bundle as create_review_bundle
    quality_evidence = short_evidence(
        content_id="shorts-" + str(folder_id), spec=spec, ready=ready, qa=qa,
        visual_plan=visual_plan, tracked_report=tracked_report,
        project_root=PROJECT_ROOT,
    )
    quality = write_quality_report(os.path.join(out_dir, "_qa"), quality_evidence)
    qa["quality_95"] = {
        "status": quality["status"], "score": quality["score"],
        "report": quality["json"],
    }
    qa["hao_review"] = create_review_bundle(
        out, "shorts-" + str(folder_id), quality["json"])
    if qa.get("all_green"):
        from asset_registry import record_asset_paths
        used_assets = [bgm]
        used_assets.extend(cue.get("path") for cue in
                           ((visual_plan.get("motion_assets") or {}).get("cues") or [])
                           if cue.get("role") in ("overlay", "transition") and cue.get("path"))
        qa["asset_usage_recorded"] = record_asset_paths(
            used_assets, content_id="shorts-" + str(folder_id), project_root=PROJECT_ROOT)
    qa["storage"] = finalize_success(src_dir, out, work_dir, qa)
    qa["storage"]["grandfathered_legacy"] = len(policy.get("legacy_files") or [])
    # A render is not delivered until it is registered in the single publishing
    # control plane.  Persist a diagnostic report before the transaction, then
    # rewrite it with the authoritative package identity after success.
    write_short_report(src_dir, spec, ready, qa, out)
    qa["publishing"] = publish_hub.register_completed_short(folder_id, qa)
    write_short_report(src_dir, spec, ready, qa, out)
    return qa


def main():
    # Public-kit installs include a bounded, compatibility-gated updater.  The
    # private canonical workspace intentionally has no startup_update module,
    # so development runs remain local and deterministic.
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] != "selftest":
        try:
            from startup_update import ensure_current  # type: ignore
        except ImportError:
            pass
        else:
            ensure_current()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "build", "selftest"])
    ap.add_argument("folders", nargs="*")
    a = ap.parse_args()
    if a.cmd == "selftest":
        six = _wave_segment_durations(6, 12.4)
        assert len(six) == 6 and abs(sum(six) - 12.4) < .08
        assert max(six) - min(six) >= .8 and six[3] == max(six) and six[4] == min(six)
        four = _wave_segment_durations(4, 10.4)
        assert all(1.8 <= d <= 3.6 for d in four) and abs(sum(four) - 10.4) < .08
        locked, source = _resolve_bgm(
            {"bgm_policy": "folder"},
            {"asset_intelligence": {"selected_bgm": "assets/bgm/wrong.wav"}},
            "chosen-folder.wav",
        )
        assert locked == "chosen-folder.wav" and source == "folder_lock"
        print("shorts_autopilot self-test OK")
        return 0
    if not a.folders:
        ap.error("scan/build requires at least one folder id")
    for fid in a.folders:
        (scan if a.cmd == "scan" else build)(fid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
