# -*- coding: utf-8 -*-
"""shorts_autopilot.py — 直式 Shorts 一鍵流程（丟素材 → 成片）

把「丟素材 → 成片」中間所有機械步驟收成 2 個指令，中間只留一件人（或 AI）要做的事：
**看畫面寫字**。

    步驟1  python src/shorts_autopilot.py scan 01 02
           → 正規化 9:16 + 讀 GPS + 抽接觸表 + 抽「畫面上的字」放大圖
           → 在素材夾產出 <N>/_plan.py 骨架（片段已自動排好，文字留白）

    步驟2  （你 or AI 看 _work/SHEET.jpg + _work/_signs/ → 填 _plan.py 的
            place / what / addr / caps_by_seg —— 只寫畫面上真的看得到的東西）

    步驟3  python src/shorts_autopilot.py build 01 02
           → 過 shorts_gate 全規則 → build → 自動 QA（規格/片長/響度/loop/字幕對位抽幀）
           → 產出 _out/_qa/ 驗證圖 + 一份 REPORT.md

⚙️ 路徑全部走環境變數（沿用 kit 慣例，見 config.example.py）：
    VIDEO_KIT_SHORTS_INBOX   素材收件匣  預設 <project_root>/videos/_INBOX/shorts
    VIDEO_KIT_BGM_ROOT       BGM 根目錄  預設 <project_root>/assets/bgm
    VIDEO_KIT_PROJECT_ROOT   專案根（其餘兩者的預設值由它推導）
素材放 `<inbox>/<N>/`（N 是你自己取的資料夾名，建議純 ASCII），然後 `scan N` → `build N`。

📦 需求：Python 3.9+ / `ffmpeg` + `ffprobe` 在 PATH / **Pillow + numpy**
   （畫面品質分析與接觸表要；`longform_maker/shorts_gate.py` 本身是純 Python，
     只想用規則閘門的話不需要裝任何套件）。

規則 SoT → `longform_maker/shorts_gate.py`（機械，門檻值可覆寫）
知識 SoT → `knowledge/shorts-mastery-2026.md`
機械小工具（subprocess/寫檔/ffprobe/抽幀/接觸表）SoT → `av_util.py`
cp950 安全：console 純 ASCII 標記；I/O utf-8。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # src/
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "longform_maker"))

from av_util import contact_sheet, duration as _dur, grab_frame, run as _run, write_text  # noqa: E402
from shorts_gate import DEFAULT_PLATFORM, PLATFORM_RULES, merge_rules  # noqa: E402


# ───────────────────────────────────────────── 路徑（env 覆寫）

def _project_root() -> str:
    """VIDEO_KIT_PROJECT_ROOT > 最近一個含 assets/ 或 videos/ 的祖先 > repo 根。"""
    env = os.environ.get("VIDEO_KIT_PROJECT_ROOT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    p = HERE
    for _ in range(4):
        p = os.path.dirname(p)
        if os.path.isdir(os.path.join(p, "assets")) or os.path.isdir(os.path.join(p, "videos")):
            return p
    return os.path.dirname(HERE)          # repo 根（src/ 的上一層）


def inbox_root() -> str:
    return os.environ.get("VIDEO_KIT_SHORTS_INBOX") or \
        os.path.join(_project_root(), "videos", "_INBOX", "shorts")


def bgm_root() -> str:
    return os.environ.get("VIDEO_KIT_BGM_ROOT") or \
        os.path.join(_project_root(), "assets", "bgm")


BGM_FALLBACK_FOLDER = "_general"    # <bgm_root>/ 下的萬用資料夾（指定的分類沒檔案時退這裡）

# QA 期望值（改前先確認你的發布平台規格）
EXPECT_W, EXPECT_H, EXPECT_FPS = 1080, 1920, 30
LUFS_TARGET, LUFS_TOL = -14.0, 1.5   # 主流平台大約正規化到 -14 LUFS
LOOP_SEG_LEN = 1.6                   # 末段（回到首格做 loop）長度


# ───────────────────────────────────────────── 步驟1：scan

def scan(folder_id: str, rules: dict = None, platform: str = None) -> dict:
    """正規化 + GPS + 接觸表 + 畫面文字放大圖 + _plan.py 骨架。

    platform 決定自動排片段要瞄準哪個片長帶（YT 有 26-44s 死區，IG/FB 沒有），
    並寫進 _plan.py 的 SPEC，讓 build 用同一組門檻 —— 兩邊用不同的帶就會前後矛盾。
    """
    from silent_vlog_maker import normalize_to_portrait, extract_gps

    r = merge_rules(rules, platform)
    src_dir = os.path.join(inbox_root(), folder_id)
    assert os.path.isdir(src_dir), "找不到素材資料夾：" + src_dir
    work = os.path.join(src_dir, "_work")
    os.makedirs(work, exist_ok=True)

    # 有些檔案系統不分大小寫 → 用 realpath 去重（*.MOV 與 *.mov 會抓到同一批）
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

    # 1) 正規化 9:16（手機 rotation 旗標 / 混向都吃）
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

    # 3) 畫面文字（招牌/標價牌/螢幕）放大圖 —— S-J：字幕要「讀」畫面上的字，不是憑印象寫
    sign_dir = os.path.join(work, "_signs")
    os.makedirs(sign_dir, exist_ok=True)
    n_sign = 0
    for c in info["clips"]:
        for p in (0.2, 0.5, 0.8):
            t = round(c["dur"] * p, 2)
            jp = os.path.join(sign_dir, "%s_%.0f.jpg" % (c["name"], p * 100))
            n_sign += grab_frame(c["norm"], t, jp,
                                 vf="crop=1080:760:0:80,scale=1500:-1")
    print("[scan] %d text crops -> %s (read names/prices from these)" % (n_sign, sign_dir))

    # 4) 自動排片段（機械可算的全做完）
    ap = auto_plan(info, rules=r)

    # 5) _plan.py（片段已排好，只剩文字待填）
    plan_path = os.path.join(src_dir, "_plan.py")
    if not os.path.exists(plan_path):
        segs = ap.get("segs") or [(c["norm"], 0.0, 2.0) for c in info["clips"]]
        write_text(plan_path, _plan_skeleton(folder_id, work, segs, r, platform))
        print("[scan] plan skeleton -> %s" % plan_path)
    else:
        print("[scan] plan exists (kept): %s" % plan_path)

    write_text(os.path.join(work, "_scan.json"),
               json.dumps(info, ensure_ascii=False, indent=1), announce=False)
    return info


def _plan_skeleton(folder_id: str, work: str, segs: list, r: dict,
                   platform: str = None) -> str:
    """產生待填的 _plan.py 原始碼字串（片段已排好，文字留 TODO）。"""
    lines = ["# -*- coding: utf-8 -*-",
             '"""自動產生的規劃骨架 — 看 _work/SHEET.jpg + _work/_signs/ 後填。',
             "規則：place/what/addr 必填；caps_by_seg 綁 segment 索引（禁手算時間）。",
             "品名/價格/名稱只能取「該主體正上方那張牌」；讀不到就不編。\"\"\"",
             "", "W = r\"%s\"" % work.replace("\\", "/"), "",
             "SPEC = dict(",
             '    name="short_%s_TODO",' % folder_id,
             '    place="TODO 地名/店名/主題（開場大字）",',
             '    what="TODO 一句這是什麼",',
             '    addr="TODO 常駐資訊條（例：名稱｜完整地址）",',
             '    platform="%s",   # 片長帶依平台（yt_shorts 有 26-44s 死區；ig/fb 沒有）'
             % (platform or DEFAULT_PLATFORM),
             "    segs=[",
             "        # (clip, in_sec, dur)  <- 首段 <=%.1fs；末段須收在首段起點"
             % r["first_cut_max"],
             ]
    for i, (f, i_in, d) in enumerate(segs):
        tag = "HOOK（自動選：畫面最銳利/亮度適中/鏡頭最穩）" if i == 0 else (
              "loop（結束點已對齊首段起點，勿改）" if i == len(segs) - 1 else "")
        lines.append('        (W + "/%s", %.2f, %.1f),   # seg%d %s'
                     % (os.path.basename(f), i_in, d, i, tag))
    lines += ["    ],",
              "    # 每段一條字幕；(seg 索引, [(文字, 顏色)], kind)",
              "    #   顏色：白字為底（>=%.0f%%），重點色每支僅 1-2 處"
              % ((1 - r["nonwhite_max_ratio"]) * 100),
              "    #   注意：品名/價格只能取「該主體正上方那張牌」；讀不到就不編",
              "    caps_by_seg=[",
              '        (0, [("TODO 地名/店名/主題", "gold")], "hook"),',
              '        (0, [("TODO 一句這是什麼", "white")], "sub"),']
    for i in range(1, max(1, len(segs) - 1)):
        lines.append('        (%d, [("TODO seg%d 的內容", "white")], "sub"),' % (i, i))
    lines += ["    ],",
              '    # <your-bgm-subfolder>：<bgm_root>/ 底下的資料夾名（依情緒/場景分類，',
              '    # 例如 upbeat / calm / walking …）。找不到就退 %r' % BGM_FALLBACK_FOLDER,
              '    bgm_folder="TODO <your-bgm-subfolder>",',
              ")",
              "",
              "# 自動排片段結果：%d 段 / %.1fs（已在 %.0f-%.0fs 帶內、首刀 %.1fs、loop 對齊）"
              % (len(segs), sum(x[2] for x in segs), r["dur_min"], r["dur_max"], segs[0][2])]
    return "\n".join(lines) + "\n"


# ───────────────────────────────────────────── 自動排片段

def _clip_metrics(norm_path: str, dur: float, step: float = 0.5) -> list:
    """逐 step 秒量 (銳利度, 亮度, 與前一格的變化量) → 找「畫面穩定又有內容」的窗。

    銳利度用相鄰像素差當 Laplacian proxy（對焦準/有主體的幀分數高）；
    變化量用相鄰抽樣幀差（低=鏡頭穩，高=在搖）。需要 numpy + Pillow。
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
    """挑「銳利度高 + 亮度不過暗/過曝 + 鏡頭不亂晃」的連續窗；回 (in_sec, score)。"""
    n = max(1, int(round(want / step)))
    if len(rows) < n:
        return (0.0, 0.0)
    best, bi = -1e9, 0
    for i in range(0, len(rows) - n + 1):
        w = rows[i:i + n]
        sharp = sum(r["sharp"] for r in w) / n
        bright = sum(r["bright"] for r in w) / n
        motion = sum(r["motion"] for r in w) / n
        # 亮度懲罰：太暗(<60)或過曝(>210) 扣分（暗綠遠景最容易被誤選成 hook）
        pen = 0.0
        if bright < 60:
            pen += (60 - bright) * 0.8
        if bright > 210:
            pen += (bright - 210) * 0.8
        score = sharp * 1.6 - motion * 1.1 - pen
        if score > best:
            best, bi = score, i
    return (rows[bi]["t"], round(best, 1))


def auto_plan(info: dict, target: float = None, rules: dict = None) -> dict:
    """把「機械可算的」全部算好：挑 hook、排片段長度、算 loop 對齊、湊進片長帶。

    留下來要人（或 AI）看畫面決定的只剩「文字」：place / what / addr / 每段字幕。
    """
    r = merge_rules(rules)
    lo, hi = r["dur_min"], r["dur_max"]
    if target is None:
        target = lo + 0.25 * (hi - lo)      # 預設瞄準片長帶的前段（留湊整空間）

    clips = [c for c in info["clips"] if c["dur"] >= 1.6]
    if not clips:
        return {}
    print("[auto] analyzing frame quality of %d clips..." % len(clips))
    for c in clips:
        c["rows"] = _clip_metrics(c["norm"], c["dur"])
        c["best_in"], c["score"] = _best_window(c["rows"], min(2.6, c["dur"] - 0.2))

    # hook = 分數最高那支（銳利、亮度適中、鏡頭穩）
    hook = max(clips, key=lambda c: c["score"])
    others = [c for c in clips if c is not hook]
    others.sort(key=lambda c: c["score"], reverse=True)

    # 首段吃滿首刀門檻；loop 段需 hook 的 best_in >= loop 長度才收得回，否則往後挪
    first_len = round(min(2.0, r["first_cut_max"]), 2)
    loop_len = LOOP_SEG_LEN
    hook_in = max(hook["best_in"], loop_len + 0.1)
    if hook_in + first_len > hook["dur"]:
        hook_in = max(loop_len + 0.1, hook["dur"] - first_len - 0.1)
    segs = [(hook["norm"], round(hook_in, 2), first_len)]

    # 中段：平均分配剩餘時間（每段 2.2-3.2s）
    mid = others[:6] if others else []
    if mid:
        budget = target - first_len - loop_len
        each = max(2.2, min(3.2, budget / len(mid)))
        for c in mid:
            win, _ = _best_window(c["rows"], min(each, c["dur"] - 0.2))
            take = min(each, c["dur"] - win - 0.1)
            if take >= 1.8:
                segs.append((c["norm"], round(win, 2), round(take, 1)))
    # loop 段：結束點 == 首段起點
    segs.append((hook["norm"], round(hook_in - loop_len, 2), loop_len))

    total = round(sum(s[2] for s in segs), 1)
    # 落在片長帶外 → 微調中段
    if total < lo and len(segs) > 2:
        add = (lo + 0.2 - total) / (len(segs) - 2)
        segs = [segs[0]] + [(f, i, round(d + add, 1)) for f, i, d in segs[1:-1]] + [segs[-1]]
    elif total > hi and len(segs) > 3:
        segs = [segs[0]] + segs[1:1 + 5] + [segs[-1]]
        over = round(sum(s[2] for s in segs), 1) - (hi - 0.5)
        if over > 0:
            cut = over / (len(segs) - 2)
            segs = ([segs[0]]
                    + [(f, i, round(max(2.0, d - cut), 1)) for f, i, d in segs[1:-1]]
                    + [segs[-1]])

    total = round(sum(s[2] for s in segs), 1)
    print("[auto] %d segments / %.1fs (hook=%s, loop aligned)"
          % (len(segs), total, os.path.basename(hook["norm"])))
    return {"segs": segs, "hook": hook["norm"], "total": total}


# ───────────────────────────────────────────── 步驟3：build + QA

def build(folder_id: str, rules: dict = None) -> dict:
    from shorts_gate import assert_shorts
    from silent_vlog_maker import build_one_short, pick_bgm

    src_dir = os.path.join(inbox_root(), folder_id)
    plan_path = os.path.join(src_dir, "_plan.py")
    assert os.path.exists(plan_path), "還沒有 _plan.py，先跑 scan：" + plan_path

    import importlib.util
    spec_mod = importlib.util.spec_from_file_location("plan_%s" % folder_id, plan_path)
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    spec = mod.SPEC
    assert "TODO" not in json.dumps(spec, default=str), \
        "%s/_plan.py 還有 TODO 未填" % folder_id

    # ⚠️ 傳**原始 rules**，不能傳先 merge 好的 dict —— merge 順序是
    # 預設 → 平台 → 你的覆寫，先 merge 等於用預設平台的片長帶蓋掉 spec["platform"]。
    ready = assert_shorts(spec, rules)      # ← 全規則機械閘門
    # 之後的 QA / 報告要用**同一組**門檻，否則會拿 YT 的帶去判一支 IG Reel
    r = merge_rules(rules, spec.get("platform"))
    for w in ready.get("_warns", []):
        print("   WARN " + w)

    folder = os.path.join(bgm_root(), spec["bgm_folder"])
    cands = (sorted(glob.glob(os.path.join(folder, "*.wav"))) +
             sorted(glob.glob(os.path.join(folder, "*.mp3"))))
    if not cands:
        fb = os.path.join(bgm_root(), BGM_FALLBACK_FOLDER)
        cands = sorted(glob.glob(os.path.join(fb, "*.mp3"))) + \
            sorted(glob.glob(os.path.join(fb, "*.wav")))
    assert cands, "找不到 BGM：%s（也沒有 %s/）" % (folder, BGM_FALLBACK_FOLDER)
    bgm = pick_bgm(cands, ready["_dur"])

    out_dir = os.path.join(src_dir, "_out")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, spec["name"] + ".mp4")
    print("[build] %s dur=%.1fs segs=%d" % (spec["name"], ready["_dur"], len(spec["segs"])))
    build_one_short(spec["segs"], ready["caps"], bgm, out)

    qa = _qa(out, ready, out_dir, r)
    _write_report(src_dir, spec, ready, qa, out, r)
    return qa


def _qa(video: str, ready: dict, out_dir: str, r: dict) -> dict:
    """自動 QA：規格 / 響度 / loop 相似度 / 每條字幕中點抽幀（人眼複核用）。需要 Pillow + numpy。"""
    from PIL import Image
    import numpy as np

    qa_dir = os.path.join(out_dir, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    res = {}

    wh = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate",
               "-of", "csv=p=0", video]).stdout.strip()
    res["format"] = wh
    res["spec_ok"] = wh.startswith("%d,%d,%d" % (EXPECT_W, EXPECT_H, EXPECT_FPS))

    d = _dur(video)
    res["dur"] = round(d, 2)
    res["dur_ok"] = r["dur_min"] - 0.01 <= d <= r["dur_max"] + r["dur_max_slack"]

    lo = _run(["ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128=peak=true",
               "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", lo.stderr)
    res["lufs"] = float(m[-1]) if m else None
    res["lufs_ok"] = res["lufs"] is not None and abs(res["lufs"] - LUFS_TARGET) <= LUFS_TOL
    if res["lufs"] is not None and not res["lufs_ok"]:
        # 最常見原因：BGM 音樂庫沒做響度正規化（不是這支片剪壞）
        print("[qa] LUFS %.1f vs target %.0f+/-%.1f -> normalize your BGM library, "
              "or pass a different vol= to build_one_short" % (res["lufs"], LUFS_TARGET, LUFS_TOL))

    def fr(t):
        p = os.path.join(qa_dir, "_t.png")
        if not grab_frame(video, t, p, vf="scale=90:160"):
            return None
        a = np.asarray(Image.open(p).convert("L"), dtype=float)
        os.remove(p)
        return a

    a, b = fr(0.08), fr(d - 0.25)
    res["loop_sim"] = round(float(np.corrcoef(a.ravel(), b.ravel())[0, 1]), 2) \
        if a is not None and b is not None else None

    # 每條內容字幕中點抽幀 → 一張對位驗證圖
    tiles = []
    for st, en, blocks, kind in ready["caps"]:
        if kind == "addr":
            continue
        lab = "".join(t for t, _c in blocks)[:10]
        p = os.path.join(qa_dir, "_c%.2f.jpg" % st)
        if grab_frame(video, round((st + en) / 2, 2), p, vf="scale=180:-1"):
            tiles.append((p, lab))
    # 一列排開（每條字幕一格），拼完刪掉來源小圖
    cm = contact_sheet(tiles, os.path.join(qa_dir, "CAPTION_match.jpg"),
                       cols=max(1, len(tiles)), cleanup=True)
    if cm:
        res["caption_sheet"] = cm

    res["all_green"] = bool(res["spec_ok"] and res["dur_ok"] and res["lufs_ok"])
    print("[qa] %s dur=%.1fs LUFS=%s loop=%s %s"
          % (os.path.basename(video), res["dur"], res["lufs"], res["loop_sim"],
             "GREEN" if res["all_green"] else "RED"))
    return res


def _write_report(src_dir, spec, ready, qa, out, r):
    lines = ["# Shorts 建置報告 — %s" % spec["name"], "",
             "- 開場識別：**%s**（%s）" % (spec["place"], spec["what"]),
             "- 常駐資訊條：%s" % spec["addr"],
             "- 片長：%.1fs（%.0f-%.0fs 帶）｜段數 %d"
             % (ready["_dur"], r["dur_min"], r["dur_max"], len(spec["segs"])),
             "- 規格：%s｜LUFS %s（目標 %.0f±%.1f）｜loop 相似度 %s"
             % (qa.get("format"), qa.get("lufs"), LUFS_TARGET, LUFS_TOL, qa.get("loop_sim")),
             "- 機械閘門：**全過**（shorts_gate 全規則）"]
    if not qa.get("lufs_ok"):
        lines.append("- ⚠️ 響度未達標：先確認你的 BGM 音樂庫有做響度正規化"
                     "（或調 `build_one_short(vol=...)`），不是這支片剪壞")
    lines += ["", "## 字幕（綁 segment，程式算時間）"]
    for st, en, blocks, kind in ready["caps"]:
        if kind == "addr":
            continue
        lines.append("- %.1f-%.1fs　%s" % (st, en, "".join(t for t, _c in blocks)))
    lines += ["", "## 人眼複核（交付前必看）",
              "- `_out/_qa/CAPTION_match.jpg` — 每條字幕中點幀，確認畫面主體＝字幕所述",
              "- 成片：`%s`" % out]
    write_text(os.path.join(src_dir, "REPORT.md"), "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="direct-to-Shorts autopilot (scan -> fill -> build)")
    ap.add_argument("cmd", choices=["scan", "build"])
    ap.add_argument("folders", nargs="+", help="素材夾名（<inbox>/<N>/）")
    ap.add_argument("--platform", choices=sorted(PLATFORM_RULES), default=None,
                    help="目標平台（決定片長帶；預設 %s）。build 讀 _plan.py 裡的 platform"
                         % DEFAULT_PLATFORM)
    a = ap.parse_args()
    print("[paths] inbox=%s" % inbox_root())
    for fid in a.folders:
        if a.cmd == "scan":
            scan(fid, platform=a.platform)
        else:
            build(fid)          # 平台寫在 _plan.py 的 SPEC 裡，不從 CLI 再給一次


if __name__ == "__main__":
    raise SystemExit(main())
