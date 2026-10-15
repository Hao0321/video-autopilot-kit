"""Short-form autopilot orchestration (public distribution).

Routes scan, plan, build, QA and delivery around an explicit source folder and structured receipts.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import glob
import os
from av_util import contact_sheet, duration as _dur, grab_frame
from project_paths import video_path


INBOX = str(video_path("_INBOX", "直式-vertical-Shorts-Reels"))


def _scan_input_clips(folder_id):
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
    return info, src_dir, work


def _write_scan_previews(info, work):
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


def _write_scan_plan(ap, folder_id, info, src_dir, work):
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
                 "   Compare hook choices with creator-owned equal-window evidence; PUBLIC_FIXTURE ships no retention result.",
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
                  "    #      web: 出處 / user: creator-provided evidence）。沒命中風險詞的字幕可不填。",
                  "    evidence={},",
                  '    bgm_folder="TODO 見 assets/bgm/（美食/旅遊/森林自然/走路散步/咖啡廳甜點…）",',
                  '    bgm_policy="asset_hub",  # asset_hub / folder；人工已選定題材資料夾時用 folder',
                  '    bgm_prefer="energetic",  # energetic / chill',
                  ")",
                  "",
                  "# ── 上架文案（統一版：一稿三發。PUBLIC_FIXTURE generic publication rule——Meta 演算法與 YT 同構，",
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
