# -*- coding: utf-8 -*-
"""teardown.py — 競品直式短片一鍵拆解（節奏量測 ＋ 選配 OCR 字幕抽取）

一個指令把任何一支直式短片拆成可比較的數字：

    python src/teardown.py <影片檔或資料夾> [--band wide|top|mid|bottom]

輸出：刀速／刀距分布（中位＋標準差＋最短）、字幕換句速率、
「換句÷剪點」節奏主體判讀、整合響度（LUFS），
以及（裝了選配 OCR 套件時）**自動抽出的字幕逐字稿**。

這些數字怎麼讀、門檻怎麼校準、哪些量是平台假象 →
[`knowledge/vertical-teardown-method.md`](../knowledge/vertical-teardown-method.md)。

--------------------------------------------------------------------------
## 依賴分層（缺了只降級，不崩潰）

**必要**：`ffmpeg` / `ffprobe` 在 PATH 上。節奏量測（刀點／刀距／響度）全靠這兩支。

**選配**：`rapidocr-onnxruntime`（本機實測裝完約 25MB 量級，**不拉 torch / paddle**）
        ＋ `opencc-python-reimplemented`（簡轉繁）

- 兩者都沒裝 → **跳過 OCR 段並印出安裝指令，節奏量測照跑、退出碼不變**。
- 只缺 `opencc` → OCR 照跑，只是不做簡轉繁（抽出的稿會混雜簡體字，人工複核時要注意）。
- 這條降級路徑有機械驗證：`python examples/06_teardown.py` 全程不需要這兩個套件。

--------------------------------------------------------------------------
## ⚠️ OCR 的能力邊界（實測值，寫死在這裡免得被誤用）

| 對象 | 準確率 | 可用性 |
|---|---|---|
| 燒錄字幕（純色／描邊、粗體、無透視） | 0.92 - 1.00 | **可用** |
| 實景招牌／標價牌（透視、雜背景、藝術字） | ≈ 0（不是低，是幾乎全錯或零輸出） | **不可用** |

而且**錯的時候信心值仍有 0.85-0.92** —— 所以**不能靠拉高 `min_conf` 門檻擋掉錯字**，
門檻只擋得掉「模型自己也知道不確定」的那一類，擋不掉「模型很有把握地讀錯」。

→ 這支工具的定位因此只有一個：**把別人已經燒好的字幕讀回來**做競品拆解，
   讓拆解從「逐幀人眼看接觸表」變成「先拿到稿再抽查」。

→ **不可以**拿它自動生成你自己影片的字幕 —— 尤其是品名、價格、規格、人名。
   那些欄位讀不到就人工看畫面，看不清就不寫。**機器編出來的錯品名比沒有更糟**，
   因為它讀起來像真的（同理見 `knowledge/meta-lessons.md` 的「不編造數字」原則）。

簡繁混雜是 OCR 字典偏誤，`opencc s2twp` 可修掉約 8 成；剩下的是真誤認，
**特徵是讀起來就不像話**（字看得懂但湊起來不成句），人工複核抓得到 —— 所以要複核。

--------------------------------------------------------------------------
## 公開 API（純 Python，不需要影片、不需要 ffmpeg、不需要 OCR 套件）

    rhythm_stats(timestamps, duration)              -> dict
    pace_profile(cut_times, caption_times, duration) -> dict

拿 §2 那些 ffprobe/ffmpeg 指令自己導出的時間戳餵進來也可以 ——
量測與統計是分開的，統計這半邊零依賴。示範：`python examples/06_teardown.py`。

cp950 安全：console 只印 ASCII 標記與檔名；檔案 I/O 一律 utf-8。
"""
from __future__ import annotations

import argparse
import glob
import os
import statistics as st
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                   # noqa: BLE001 — 舊版 Python / 已重導向
    pass

# 字幕帶（比例值，任何解析度通用）：(起始高度比, 帶高比, 右緣裁掉比)
# ⚠️ 預設是 wide 而不是精準窄帶 —— 實測發現**字幕位置在片內會移動**
# （某支樣本 t=6s 在畫面高度 24-27%、t=12s 掉到 30%），
# 窄帶會**靜默漏掉整段字幕而且不報錯**，你只會覺得「這支字幕比較少」。
# 右緣裁 18% 是為了避開直式平台右欄的按鈕列（讚數／留言數會被 OCR 讀成字幕）。
BANDS = {
    "wide":   (0.12, 0.66, 0.18),   # 狀態列以下、帳號列以上，全部掃（預設）
    "bottom": (0.58, 0.20, 0.18),
    "top":    (0.12, 0.24, 0.18),
    "mid":    (0.42, 0.24, 0.18),
}

# 換句÷剪點 高於這個倍數 → 判定「節奏主體是字幕」。
# 校準基礎與樣本分布見 knowledge/vertical-teardown-method.md §3。
CAPTION_DRIVEN_RATIO = 1.15

# 選配套件（缺了只降級）
OPTIONAL_PKGS = ("rapidocr-onnxruntime", "opencc-python-reimplemented")


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True, errors="replace")


# ── 公開 API：純統計，不碰檔案 ───────────────────────────────────────────────

def rhythm_stats(timestamps, duration):
    """把一串事件時間戳（秒）變成可跨片比較的節奏統計。

    `timestamps` 可以是剪點（`cuts()` 的輸出）、換句時間（`caption_track()` 的
    第一欄），或你用 `knowledge/vertical-teardown-method.md` §2 的 ffprobe
    指令自己導出來的任何時間戳。純 Python，不需要 ffmpeg 也不需要影片。

    回傳 dict：
        n           事件數
        per_min     每分鐘幾次（duration <= 0 時為 0.0）
        gaps        相鄰間隔 list（長度 n-1）
        gap_median  中位間隔（不足兩點時 None）
        gap_stdev   間隔母體標準差（不足三點時 0.0；不足兩點 None）
        gap_min / gap_max

    **為什麼要看標準差**：中位刀距 1.1s 可能是「機械地每 1.1 秒一刀」，
    也可能是「0.4s 和 3s 交替」。這兩種片給人的感覺完全不同，
    只看中位數會混成同一種。
    """
    ts = sorted(float(t) for t in timestamps)
    dur = float(duration)
    gaps = [round(b - a, 3) for a, b in zip(ts, ts[1:])]
    out = {
        "n": len(ts),
        "per_min": round(len(ts) / dur * 60, 2) if dur > 0 else 0.0,
        "gaps": gaps,
        "gap_median": None,
        "gap_stdev": None,
        "gap_min": None,
        "gap_max": None,
    }
    if gaps:
        out["gap_median"] = round(st.median(gaps), 2)
        out["gap_stdev"] = round(st.pstdev(gaps), 2) if len(gaps) > 1 else 0.0
        out["gap_min"] = round(min(gaps), 2)
        out["gap_max"] = round(max(gaps), 2)
    return out


def pace_profile(cut_times, caption_times, duration):
    """比較「剪點」與「換句」兩條節奏軌，判定這支片的節奏主體是誰。

    這是整套拆解裡最有轉用價值的一個數字：換句速率高於刀速率，代表推進感
    是**文字**在扛而不是剪接在扛 —— 也就是說素材不夠、只有一顆長鏡頭時，
    不必硬切，把節奏交給字幕即可（`knowledge/vertical-teardown-method.md` §3）。

    參數皆為時間戳 list（秒）＋片長（秒）。純 Python。

    回傳 dict：
        cuts / captions   兩條軌各自的 `rhythm_stats()`
        ratio             換句每分 ÷ 剪點每分（剪點為 0 時 None）
        driver            'captions' / 'cuts' / 'unknown'
        verdict           一行 ASCII 判讀字串，可直接印

    ⚠️ 這條規則的證據等級是 PLAUSIBLE 不是 PROVEN（樣本全是成功片、沒有失敗
    對照組）。所以它在 `shorts_gate.py` 是 **warn 不是 fail** —— 這裡也一樣只
    報數字給人看，不替人決定。
    """
    cuts_s = rhythm_stats(cut_times, duration)
    caps_s = rhythm_stats(caption_times, duration)
    cpm, lpm = cuts_s["per_min"], caps_s["per_min"]

    if cpm <= 0:
        ratio, driver = None, "unknown"
        verdict = "no cuts detected -> cannot compare (single take, or lower --thresh)"
    else:
        ratio = round(lpm / cpm, 2)
        driver = "captions" if ratio > CAPTION_DRIVEN_RATIO else "cuts"
        verdict = "captions/cuts = %.2fx  ->  rhythm is %s-driven" % (
            ratio, "CAPTION" if driver == "captions" else "CUT")
    return {"cuts": cuts_s, "captions": caps_s, "ratio": ratio,
            "driver": driver, "verdict": verdict}


def ocr_status():
    """探測選配套件是否可用。回傳 (ocr_ok, s2t_ok, hint)。

    hint 是給使用者看的 `pip install ...` 字串（全裝好時為空字串）。
    只做 import 探測，不建立 OCR engine（建 engine 會載模型、很慢）。
    """
    missing = []
    try:
        import rapidocr_onnxruntime            # noqa: F401
        ocr_ok = True
    except Exception:                          # noqa: BLE001 — 缺套件或 onnx 載入失敗都算沒有
        ocr_ok = False
        missing.append(OPTIONAL_PKGS[0])
    try:
        import opencc                          # noqa: F401
        s2t_ok = True
    except Exception:                          # noqa: BLE001
        s2t_ok = False
        missing.append(OPTIONAL_PKGS[1])
    return ocr_ok, s2t_ok, ("pip install " + " ".join(missing)) if missing else ""


# ── 量測層：需要 ffmpeg / ffprobe ────────────────────────────────────────────

def probe(path):
    """-> (width, height, fps, duration_seconds)。需要 ffprobe 在 PATH 上。"""
    o = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height,r_frame_rate",
              "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout
    vals = [x for x in o.replace("\n", ",").split(",") if x]
    if len(vals) < 4:
        raise RuntimeError(
            "ffprobe gave no usable stream info for %r. "
            "Check that ffprobe is on PATH and the file is a readable video." % path)
    w, h = int(vals[0]), int(vals[1])
    num, den = (vals[2].split("/") + ["1"])[:2]
    return w, h, round(float(num) / float(den), 2), float(vals[-1])


def cuts(path, thresh=0.25):
    """剪點偵測 -> 時間戳 list（秒）。

    `thresh` 是起點不是定值：太高會漏掉同色調的硬切（一盤菜切到另一盤菜，
    直方圖差異很小），太低會把手持晃動／推鏡／閃光當成剪點。
    **校準必做**：挑片中任意 10 秒自己逐格數一次，差超過 ±1 就調門檻重跑。

    ⚠️ 這行指令**不可以加 `-v error`** —— `showinfo` 走 stderr 的 INFO 等級，
    壓掉之後會**回報 0 刀而且完全不報錯**（一度誤判整批片都是單鏡到底）。
    """
    out = _run(["ffmpeg", "-hide_banner", "-i", path, "-vf",
                "select='gt(scene,%g)',showinfo" % thresh, "-f", "null", "-"]).stderr
    ts = [float(x.split(":")[1]) for x in out.split() if x.startswith("pts_time:")]
    return [t for t in ts if t > 0.2]


def loudness(path):
    """整合響度（LUFS）字串，測不到回 '?'。

    ⚠️ 這個數字**是拿來排除的，不是拿來學的**：如果整批競品的值都擠在同一個
    數字附近，那是平台正規化的結果，不是作者的選擇。
    """
    out = _run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128",
                "-f", "null", "-"]).stderr
    vals = [l for l in out.splitlines() if l.strip().startswith("I:")]
    return vals[-1].split()[1] if vals else "?"


def caption_track(path, band, w, h, step=0.5, min_conf=0.75):
    """抽字幕帶 → OCR → 簡轉繁 → 去重，回 [(t_seconds, text)]。

    **缺 `rapidocr-onnxruntime` 時回 None**（呼叫端據此印安裝提示並跳過此段）。
    缺 `opencc` 時照跑，只是跳過簡轉繁。

    ⚠️ `min_conf` 擋不掉「模型很有把握地讀錯」的那一類（見檔頭能力邊界表），
    所以輸出**一律當草稿看待，必須人工複核**。
    """
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:                          # noqa: BLE001 — 沒裝就降級，不崩潰
        return None
    try:
        from opencc import OpenCC
        cc = OpenCC("s2twp").convert
    except Exception:                          # noqa: BLE001 — 沒裝就不轉，其餘照跑
        def cc(x):
            return x

    top_r, hgt_r, rcut = BANDS[band]
    crop = "crop=%d:%d:0:%d" % (int(w * (1 - rcut)), int(h * hgt_r), int(h * top_r))

    engine = RapidOCR()
    rows = []
    with tempfile.TemporaryDirectory() as td:
        _run(["ffmpeg", "-hide_banner", "-v", "error", "-i", path, "-vf",
              "%s,fps=%g" % (crop, 1 / step), os.path.join(td, "f_%04d.png")])
        prev_key = None
        for i, fp in enumerate(sorted(glob.glob(os.path.join(td, "f_*.png")))):
            res, _ = engine(fp)
            parts = []
            for _box, txt, score in (res or []):
                txt = txt.strip()
                if float(score) < min_conf or not txt:
                    continue
                # 濾掉平台 UI 噪音：純數字／純符號（讚數、留言數會滲進字幕帶）
                # 尾綴含 CJK 的計數單位（萬／億）也算 UI 數字，不是字幕
                if all(ch.isdigit() or ch in ".,+-%KkMm萬億" for ch in txt):
                    continue
                parts.append(txt)
            if not parts:
                continue
            line = cc(" ".join(parts))
            key = "".join(ch for ch in line if ch.isalnum())
            if prev_key and near_dup(key, prev_key):
                continue
            rows.append((round(i * step, 1), line))
            prev_key = key
    return rows


def near_dup(a, b, ratio=0.86):
    """近似重複判定：連續幀的 OCR 會有 1-2 字抖動，不該算成新的一句。

    ⚠️ 用 difflib（**順序敏感**）不要用「字元集合重疊率」——中文常用字
    （的／了／是／我）到處都有，集合法會把不同句子判成同一句。
    第一版就是這樣寫的，一支 22 條字幕的片只抽出 9 條，**而且不會報錯**，
    看起來只像是「這支片字幕比較少」。這類靜默錯誤最貴。
    """
    if not a or not b:
        return False
    if a == b:
        return True
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= ratio


# ── CLI ────────────────────────────────────────────────────────────────────

def _print_rhythm(label, s):
    print("  %-9s %3d hits / %6.1f per min" % (label, s["n"], s["per_min"]), end="")
    if s["gap_median"] is None:
        print()
    else:
        print("   gap median %.2fs  stdev %.2f  min %.2f"
              % (s["gap_median"], s["gap_stdev"], s["gap_min"]))


def teardown(path, band="wide", thresh=0.25):
    w, h, fps, dur = probe(path)
    print("=" * 66)
    print("%s   %dx%d  %gfps  %.1fs  LUFS %s"
          % (os.path.basename(path), w, h, fps, dur, loudness(path)))
    print("=" * 66)

    cut_ts = cuts(path, thresh)
    _print_rhythm("cuts", rhythm_stats(cut_ts, dur))

    caps = caption_track(path, band, w, h)
    if caps is None:
        _ok, _s2t, hint = ocr_status()
        print("  [SKIP] caption OCR: optional packages not installed")
        print("         %s" % (hint or "pip install " + " ".join(OPTIONAL_PKGS)))
        print("         (rhythm numbers above are complete and unaffected)")
        return

    cap_ts = [t for t, _txt in caps]
    _print_rhythm("captions", rhythm_stats(cap_ts, dur))
    print("  " + pace_profile(cut_ts, cap_ts, dur)["verdict"])

    _ocr, s2t, _hint = ocr_status()
    print("\n  -- auto-extracted caption script (OCR%s; NEEDS HUMAN REVIEW) --"
          % (" + s2twp" if s2t else ", no opencc -> mixed simplified/traditional"))
    for t, txt in caps:
        print("  %6.1fs  %s" % (t, txt))
    print("\n  [!] Lines that read like nonsense are OCR misreads, not what they wrote.")
    print("  [!] Never reuse these strings as product names / prices in your own video.")


def main():
    ap = argparse.ArgumentParser(
        description="Teardown one vertical short (or a folder of them) into "
                    "comparable rhythm numbers. See knowledge/vertical-teardown-method.md")
    ap.add_argument("target", help="a video file, or a folder containing .mp4 files")
    ap.add_argument("--band", default="wide", choices=sorted(BANDS),
                    help="caption band to OCR (default: wide -- captions move "
                         "within a clip, and a narrow band drops them silently)")
    ap.add_argument("--thresh", type=float, default=0.25,
                    help="scene-change threshold for cut detection (default 0.25; "
                         "calibrate against 10s counted by hand)")
    a = ap.parse_args()

    vids = ([a.target] if os.path.isfile(a.target)
            else sorted(glob.glob(os.path.join(a.target, "**", "*.mp4"), recursive=True)))
    if not vids:
        print("no .mp4 found under: %s" % a.target)
        return 1
    for v in vids:
        teardown(v, a.band, a.thresh)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
