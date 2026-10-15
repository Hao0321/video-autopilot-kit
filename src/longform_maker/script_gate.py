# -*- coding: utf-8 -*-
"""Mechanical narration-script checks (public distribution).

Input is plain narration text; beat headers use ``**[mm:ss-mm:ss title]**``.
The public vocabulary and speaking-rate values are generic starter fixtures.
Creators must calibrate them from recordings they own; no private transcript
counts, dated evaluations or channel performance values ship in this module.

PUBLIC_FIXTURE: script calibration is synthetic and creator-neutral.
"""

from __future__ import annotations

import json
import os
import re
import sys

try:
    from gate_core import selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import selftest_runner

# ---------------------------------------------------------------- constants

CPM_DEFAULT = 250  # PUBLIC_FIXTURE generic starter chars/min
CPM_OK_RANGE = (220, 300)  # calibrate from creator-owned recordings

# beat header: **[mm:ss-mm:ss 標題]**
_BEAT_RE = re.compile(
    r"^\*\*\[(\d{1,2}):(\d{2})\s*[-–~]\s*(\d{1,2}):(\d{2})\s+([^\]]+)\]\*\*\s*$",
    re.MULTILINE,
)
# markdown chapter header fallback: ## 標題
_MD_HEAD_RE = re.compile(r"^#{1,4}\s+(.+?)\s*$", re.MULTILINE)

# 開場禁詞（前兩段）：自我介紹 / 打招呼 pattern
_BANNED_OPENERS = [
    ("大家好", re.compile(r"大家好")),
    ("哈囉", re.compile(r"哈囉|嗨大家|嗨各位")),
    ("歡迎回來/收看", re.compile(r"歡迎回來|歡迎收看|歡迎來到")),
    ("我是XX 自介", re.compile(r"我是[^，。,！!？?\s]{1,8}[，。,！!]")),
    ("自我介紹", re.compile(r"自我介紹")),
]

# 第一段需含「結果性」訊號 = 數字 or 結果動詞（R24 cold open：先給結果再說過程）
_RESULT_WORD_RE = re.compile(
    r"\d|[一二兩三四五六七八九十百千萬億]+[萬千百億倍%]"
    r"|做到|做出|剪出|輸出|完成|衝到|賺到|開啟|突破|翻倍|翻了|漲到|掉到|省下|成長|破紀錄|拿下"
)

_STAGE_NOTE_RE = re.compile(r"^\s*[>\s]*(?:📺|🎬|\(|（)")
_HAS_CONTENT_RE = re.compile(r"[一-鿿A-Za-z0-9]")

def _speakable_paras(text):
    """可唸段落 = 非舞台註記（📺/🎬/括號開頭）且含實際內容（中英數）。
    hook / outro CTA 檢查都以此為準，避免標題尾巴、end-screen 註記、分隔線誤判。"""
    return [p for p in _split_paragraphs(text)
            if not _STAGE_NOTE_RE.match(p) and _HAS_CONTENT_RE.search(p)]

# interrupt 訊號：問句 / 數字 / 轉折詞（M95 死空檔用）
_QUESTION_RE = re.compile(r"[？?]")
_DIGIT_RE = re.compile(r"\d")
_TWIST_RE = re.compile(r"但是|結果|沒想到|可是|居然|竟然|反而|問題是|轉折")

# outro 強制元素
_CTA_SUBSCRIBE_RE = re.compile(r"訂閱")
_CTA_COMMUNITY_RE = re.compile(r"社群|留言|下一支")  # PUBLIC_FIXTURE configurable CTA classes

_INTERRUPT_GAP_SEC = 90        # 連續無 interrupt 訊號上限
_FIRST_INTERRUPT_SEC = 30      # 30s 首發
_INTERRUPT_PERIOD_SEC = 75     # 之後每 75±15s 一發
_INTERRUPT_JITTER_SEC = 15
_REHOOK_FRACS = (0.25, 0.50, 0.75)   # re-hook 位（2026-07 研究收斂：25/50/75%，
                                     #  中段 50% 那發 8min+ 影片不可省）

# ---------------- M110 觀眾語言（旁白層的路人 0.5 秒懂鐵則；包裝層另見演算法 supplement）
# 行話三層分級：
#   NEED_PAIR  = 可講，但【同 beat】必須有白話同伴詞（先白話後術語 / 術語即解）
#   HARD_BAN   = 內部工程詞，旁白永遠不出現（fail 級）
# 新詞先進 unknown warn，人工判級後入表。SoT 詳表+句式範例 →
# video-autopilot/references/script-retention-2026.md
SPOKEN_OK = {  # PUBLIC_FIXTURE generic starter vocabulary
    "ai", "app", "youtube", "google", "shorts", "short", "vlog", "api",
    "windows", "mac", "wifi", "email", "podcast", "diy", "hook", "loop",
    "mp3", "wav", "excel", "chrome", "github",
}
# 說「工作流/流程」不說 workflow、說「示範/操作給大家看」不說 demo。
# 用英文版 = 掉 voice(M101) + 掉觀眾語言(M110) 雙違規。
SUBSTITUTE = {
    "prompt": "提示詞",
    "prompts": "提示詞",
    "workflow": "流程/工作流",
    "demo": "示範/操作給大家看",
    "deploy": "部署",
}
NEED_PAIR = {
    "qa":   ["品管", "驗收", "檢查", "抓錯", "把關"],
    "fork": ["改", "拿去", "複製", "自己的版本", "回去"],
    "repo": ["github", "開源", "工具包", "專案", "頁面"],
    "debug": ["抓錯", "修", "找問題"],
}
HARD_BAN = [
    "assert", "lufs", "loudnorm", "schema", "endpoint", "regex",
    "refactor", "linter", "pipeline", "gate", "changelog", "commit",
    "merge",
]
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]*")

# ---------------- M110 節奏（讓人一直看下去；warn 級 craft 檢查）
_MOMENTUM_RE = re.compile(
    r"但|結果|然後|所以|沒想到|居然|竟然|反而|問題是|直接"
    r"|最[扯猛狂強重要屌誇]|其實|真正|接下來|再來|後來|現在"
)
# open loop：hook 區（前兩可唸段）要有懸念訊號
_CURIOSITY_RE = re.compile(
    r"更[扯猛狂強誇厲]|連[^，。,]{0,8}都|沒想到|居然|竟然|其中"
    r"|待會|等一下|最後你|秘密|沒(有)?人|你絕對|[？?]"
)
# 中段禁總結感（收尾語氣出現在非最後 beat = 發放離場許可 → 跳出）
_CLOSING_FEEL_RE = re.compile(
    r"^(總而言之|總結一下|以上就是|最後總結|來總結|今天就到|總之|回顧一下)")
# and-then 弱連接（段首 然後/接著/再來/另外 密度 >2/min = beat 間無推進力，
# 該是 but/therefore 因果鏈不是流水帳）
_ANDTHEN_RE = re.compile(r"^(然後|接著|再來|另外)")
_ANDTHEN_MAX_PER_MIN = 2.0
_BEAT_MAX_SEC = 45.0           # 單 beat 超過 45s 無新 payoff = 拖（wave5）
_PUNCH_MAX_CHARS = 14          # 「短句打點」門檻：≤14 可唸字算 punch
_LONGBEAT_MIN_CHARS = 160      # beat 這麼長還全是長句 → 沒節奏
                               #   門檻放 160 只抓真的一路不換氣的段落）

_DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")


# ---------------------------------------------------------------- parsing

def _strip_markup(s: str) -> str:
    """去 markdown 記號，留純旁白字。

    blockquote 行（> 開頭）＝檔頭註記/M10 對帳注釋，不是旁白 → 整行剔除
    （否則 gate 會把註記裡的 fork/M79/BGM 當旁白掃，時長也灌水）。"""
    s = re.sub(r"(?m)^\s*>.*$", "", s)
    s = _BEAT_RE.sub("", s)
    s = _MD_HEAD_RE.sub("", s)
    s = re.sub(r"[*_`>#\[\]|]+", "", s)
    return s


def _count_chars(s: str) -> int:
    """可念字數：只算 CJK + 英數（去標點/空白）。"""
    return len(re.findall(r"[一-鿿A-Za-z0-9]", _strip_markup(s)))


def _split_paragraphs(text: str) -> list:
    """段落塊 = 空行分隔、去掉 beat/markdown header 行後仍有內容的塊。"""
    paras = []
    for block in re.split(r"\n\s*\n", text):
        body = _strip_markup(block).strip()
        if body:
            paras.append(body)
    return paras


def parse_beats(text: str) -> list:
    """切 beats。優先 **[mm:ss-mm:ss 標題]**，退 markdown header，再退整篇一章。

    回傳 [{title, t_start, t_end, body}]（t_* 秒；無標時 None）。
    """
    beats = []
    matches = list(_BEAT_RE.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            start = int(m.group(1)) * 60 + int(m.group(2))
            end = int(m.group(3)) * 60 + int(m.group(4))
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            beats.append({
                "title": m.group(5).strip(),
                "t_start": start,
                "t_end": end,
                "body": text[body_start:body_end].strip(),
            })
        return beats

    md = list(_MD_HEAD_RE.finditer(text))
    if md:
        for i, m in enumerate(md):
            body_start = m.end()
            body_end = md[i + 1].start() if i + 1 < len(md) else len(text)
            beats.append({
                "title": m.group(1).strip(),
                "t_start": None,
                "t_end": None,
                "body": text[body_start:body_end].strip(),
            })
        return beats

    return [{"title": "(all)", "t_start": None, "t_end": None, "body": text.strip()}]


# ---------------------------------------------------------------- 1. duration

def estimate_duration(text: str, cpm: int = CPM_DEFAULT) -> dict:
    """去標點/標記後字數 ÷ cpm。cpm 在 240-280 區間外給 warn。"""
    warnings = []
    if not (CPM_OK_RANGE[0] <= cpm <= CPM_OK_RANGE[1]):
        warnings.append(
            "cpm=%d outside calibrated range %d-%d; est_min unreliable"
            % (cpm, CPM_OK_RANGE[0], CPM_OK_RANGE[1])
        )

    chars = _count_chars(text)
    est_min = chars / float(cpm) if cpm else 0.0

    per_beat = []
    for b in parse_beats(text):
        b_chars = _count_chars(b["body"])
        b_est_sec = round(b_chars / float(cpm) * 60.0, 1) if cpm else 0.0
        entry = {
            "title": b["title"],
            "chars": b_chars,
            "est_sec": b_est_sec,
        }
        if b["t_start"] is not None and b["t_end"] is not None:
            planned = b["t_end"] - b["t_start"]
            entry["planned_sec"] = planned
            entry["delta_sec"] = round(b_est_sec - planned, 1)
            # 估時 vs 標記時長漂 >25% 且 >10s → warn
            if planned > 0 and abs(entry["delta_sec"]) > max(10, planned * 0.25):
                warnings.append(
                    "beat '%s' est %.0fs vs planned %ds (drift %.0fs)"
                    % (_ascii(b["title"]), b_est_sec, planned, entry["delta_sec"])
                )
        per_beat.append(entry)

    return {
        "chars": chars,
        "est_min": round(est_min, 2),
        "est_sec": round(est_min * 60.0, 1),
        "cpm": cpm,
        "per_beat": per_beat,
        "warnings": warnings,
    }


# ---------------------------------------------------------------- 2. hook

def check_hook(text: str) -> list:
    """R24 cold open：前兩段禁自介/打招呼；第一段需含結果性詞。

    回傳 violations list（空 = 過）。
    """
    violations = []
    paras = _speakable_paras(text)
    if not paras:
        return [{"rule": "hook.empty", "detail": "script has no content paragraphs"}]

    head = paras[:2]
    for i, p in enumerate(head):
        for label, rx in _BANNED_OPENERS:
            m = rx.search(p)
            if m:
                violations.append({
                    "rule": "hook.banned_opener",
                    "paragraph": i + 1,
                    "pattern": label,
                    "matched": m.group(0),
                })

    if not _RESULT_WORD_RE.search(paras[0]):
        violations.append({
            "rule": "hook.no_result_word",
            "paragraph": 1,
            "detail": "first paragraph lacks a number / result verb (R24 cold open)",
        })
    return violations


# ---------------------------------------------------------------- 3. structure

def _has_interrupt_signal(p: str) -> bool:
    return bool(_QUESTION_RE.search(p) or _DIGIT_RE.search(p) or _TWIST_RE.search(p))


def check_structure(text: str, cpm: int = CPM_DEFAULT) -> dict:
    """章節問句 / 結尾 CTA / interrupt 缺口。"""
    beats = parse_beats(text)
    paras = _split_paragraphs(text)

    # -- 長章需有問句或具體推進；不可逼創作者硬塞反問來過 gate。
    chapter_issues = []
    for b in beats:
        b_paras = _split_paragraphs(b["body"])
        has_progress = re.search(r"但|結果|所以|反而|真正|直接|接下來|再來|現在|可以看到|先.{0,18}再|從.{0,18}到", b["body"])
        if len(b_paras) >= 3 and not (_QUESTION_RE.search(b["body"]) or has_progress):
            chapter_issues.append({
                "rule": "structure.chapter_no_progress",
                "chapter": b["title"],
                "paragraphs": len(b_paras),
            })

    # -- 結尾段強制 outro：訂閱 CTA + 示範社群
    # 舞台註記（📺 end screen / 純括號指示）不是唸稿 → 跳過再取最後「可唸」段
    cta_issues = []
    speakable = _speakable_paras(text)
    tail = speakable[-1] if speakable else (paras[-1] if paras else "")
    if not _CTA_SUBSCRIBE_RE.search(tail):
        cta_issues.append({"rule": "structure.outro_no_subscribe_cta",
                           "detail": "last paragraph lacks subscribe CTA"})
    if not _CTA_COMMUNITY_RE.search(tail):
        cta_issues.append({"rule": "structure.outro_no_community",
                           "detail": "last paragraph lacks community mention"})

    # -- 連續 >90s 估時無問句/數字/轉折詞 → interrupt 缺口（warn）
    gaps = []
    t = 0.0
    last_signal_t = 0.0
    for p in paras:
        dur = _count_chars(p) / float(cpm) * 60.0 if cpm else 0.0
        t_end = t + dur
        if _has_interrupt_signal(p):
            # 訊號視為出現在段落中點
            last_signal_t = t + dur / 2.0
        elif t_end - last_signal_t > _INTERRUPT_GAP_SEC:
            gaps.append({
                "rule": "structure.interrupt_gap",
                "from_sec": round(last_signal_t, 1),
                "to_sec": round(t_end, 1),
                "gap_sec": round(t_end - last_signal_t, 1),
            })
            last_signal_t = t_end  # 重置，避免同一缺口重複報
        t = t_end

    return {
        "chapters": len(beats),
        "paragraphs": len(paras),
        "chapter_issues": chapter_issues,
        "cta_issues": cta_issues,
        "interrupt_gaps": gaps,
        "ok": not chapter_issues and not cta_issues,
    }


# ---------------------------------------------------------------- 3.5 M110 language

def check_audience_language(text: str) -> list:
    """M110 觀眾語言：旁白裡的行話掃描（per beat）。

    fail 級：HARD_BAN 出現 / NEED_PAIR 同 beat 無白話同伴詞。
    warn 級：不在任何表上的英文 token（人工判級後入表）。
    Title-case 專有名詞（Midjourney/Discord…）跳過 unknown warn，
    但 HARD_BAN / NEED_PAIR 仍然照抓（case-insensitive）。
    """
    out = []
    for b in parse_beats(text):
        speak = _strip_markup(b["body"])
        low = speak.lower()
        seen = set()
        for tok in _LATIN_TOKEN_RE.findall(speak):
            if len(tok) < 2:
                continue
            t = tok.lower().strip(".-")
            if not t or t in seen:
                continue
            seen.add(t)
            if t in HARD_BAN:
                out.append({"rule": "lang.hard_ban", "level": "fail",
                            "beat": b["title"], "term": tok})
            elif t in SUBSTITUTE:
                out.append({"rule": "lang.use_chinese", "level": "fail",
                            "beat": b["title"], "term": tok,
                            "hint": "creator says: " + SUBSTITUTE[t]})
            elif t in NEED_PAIR:
                comps = NEED_PAIR[t]
                if not any(c in low for c in comps):
                    out.append({"rule": "lang.jargon_unexplained", "level": "fail",
                                "beat": b["title"], "term": tok,
                                "hint": "same-beat plain companion needed: "
                                        + "/".join(comps)})
            elif t in SPOKEN_OK:
                continue
            elif tok[0].isupper() and any(c.islower() for c in tok[1:]):
                continue  # Title-case 專有名詞（產品名）不進 unknown warn
            else:
                out.append({"rule": "lang.unknown_term", "level": "warn",
                            "beat": b["title"], "term": tok,
                            "hint": "not in proven vocab; verify audience knows it"})
    return out


# ---------------------------------------------------------------- 3.6 M110 rhythm

def check_rhythm(text: str, cpm: int = CPM_DEFAULT) -> list:
    """M110 節奏（全 warn 級）：beat 過長 / 中段無動能 / 中段總結感 /
    hook 無 open loop / 長 beat 全長句沒短句打點。"""
    issues = []
    beats = parse_beats(text)
    n = len(beats)

    # hook open loop：前兩可唸段要有懸念訊號
    paras = _speakable_paras(text)
    hook_zone = " ".join(paras[:2])
    if hook_zone and not _CURIOSITY_RE.search(hook_zone):
        issues.append({"rule": "rhythm.hook_no_open_loop", "level": "warn",
                       "detail": "first 2 paragraphs lack a curiosity signal"})

    # and-then 密度：段首弱連接（然後/接著/再來/另外）>2/min = 流水帳
    est_min_total = _count_chars(text) / float(cpm) if cpm else 0.0
    if est_min_total >= 1.0:
        andthen = sum(1 for p in paras if _ANDTHEN_RE.match(p))
        rate = andthen / est_min_total
        if rate > _ANDTHEN_MAX_PER_MIN:
            issues.append({"rule": "rhythm.andthen_chain", "level": "warn",
                           "count": andthen, "per_min": round(rate, 1),
                           "detail": "weak connectors - rewrite as but/therefore chain"})

    for i, b in enumerate(beats):
        body = _strip_markup(b["body"]).strip()
        chars = _count_chars(b["body"])
        if not body or chars < 20:
            continue
        est_sec = chars / float(cpm) * 60.0 if cpm else 0.0

        if est_sec > _BEAT_MAX_SEC:
            issues.append({"rule": "rhythm.beat_too_long", "level": "warn",
                           "beat": b["title"], "est_sec": round(est_sec, 1),
                           "detail": "add payoff/visual event or split beat"})

        is_mid = 0 < i < n - 1
        if is_mid and chars >= 30 and not (
                _MOMENTUM_RE.search(body) or _QUESTION_RE.search(body)):
            issues.append({"rule": "rhythm.no_momentum", "level": "warn",
                           "beat": b["title"],
                           "detail": "no twist/momentum word and no question"})

        if i < n - 1:
            for p in _split_paragraphs(b["body"]):
                if _CLOSING_FEEL_RE.match(p.strip()):
                    issues.append({"rule": "rhythm.mid_closing_tone", "level": "warn",
                                   "beat": b["title"],
                                   "detail": "closing-feel opener mid-video"})
                    break

        if chars >= _LONGBEAT_MIN_CHARS:
            sents = [s for s in re.split(r"[。！？!?]", body) if _count_chars(s)]
            if sents and all(
                    _count_chars(s) > _PUNCH_MAX_CHARS for s in sents):
                issues.append({"rule": "rhythm.no_punch", "level": "warn",
                               "beat": b["title"],
                               "detail": "long beat, all long sentences - add a short punch line"})
    return issues


# ---------------------------------------------------------------- 4. schedule

def interrupt_schedule(text: str, cpm: int = CPM_DEFAULT) -> list:
    """30s 首發 + 每 75±15s 一發的建議表；re-hook 標在 40%/70%。

    回傳 [{t_est, type}]（秒，可直接 json.dump 給 build 對接）。
    """
    total = estimate_duration(text, cpm)["est_sec"]
    if total <= 0:
        return []

    rehook_ts = [round(total * f, 1) for f in _REHOOK_FRACS]
    sched = []
    t = float(_FIRST_INTERRUPT_SEC)
    first = True
    while t < total:
        typ = "first_interrupt" if first else "interrupt"
        # 落在 re-hook 位 ±jitter 內 → 升級成 re-hook
        for rt in list(rehook_ts):
            if abs(t - rt) <= _INTERRUPT_JITTER_SEC:
                typ = "re-hook"
                rehook_ts.remove(rt)
                break
        sched.append({"t_est": round(t, 1), "type": typ,
                      "jitter_sec": _INTERRUPT_JITTER_SEC})
        t += _INTERRUPT_PERIOD_SEC
        first = False

    # 沒被吸收的 re-hook 位補進表
    for rt in rehook_ts:
        if rt > _FIRST_INTERRUPT_SEC:
            sched.append({"t_est": rt, "type": "re-hook",
                          "jitter_sec": _INTERRUPT_JITTER_SEC})
    sched.sort(key=lambda x: x["t_est"])
    return sched


# ---------------------------------------------------------------- 5. gate

def gate(text: str, cpm: int = CPM_DEFAULT):
    """總閘門。fail 條件 = hook violation / 章節無問句 / outro CTA 缺 /
    M110 觀眾語言 fail（HARD_BAN / NEED_PAIR 無同伴詞）。

    interrupt 缺口、時長漂移、M110 節奏、unknown term = warning（不擋，但列出來）。
    回傳 (ok, report)。
    """
    dur = estimate_duration(text, cpm)
    hook = check_hook(text)
    struct = check_structure(text, cpm)
    lang = check_audience_language(text)
    rhythm = check_rhythm(text, cpm)
    sched = interrupt_schedule(text, cpm)

    lang_fails = [v for v in lang if v["level"] == "fail"]
    ok = (not hook) and struct["ok"] and not lang_fails
    report = {
        "ok": ok,
        "duration": dur,
        "hook_violations": hook,
        "structure": struct,
        "language": lang,
        "rhythm": rhythm,
        "interrupt_schedule": sched,
        "warnings": list(dur["warnings"]) + [
            "interrupt gap %.0fs-%.0fs (%.0fs silent stretch)"
            % (g["from_sec"], g["to_sec"], g["gap_sec"])
            for g in struct["interrupt_gaps"]
        ] + [
            "lang unknown term '%s' in beat %s" % (v["term"], _ascii(v["beat"]))
            for v in lang if v["level"] == "warn"
        ] + [
            "%s @ %s" % (r["rule"], _ascii(r.get("beat", "hook")))
            for r in rhythm
        ],
    }
    return ok, report


# ---------------------------------------------------------------- report io

def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")


def write_report(report: dict, path: str) -> str:
    """人可讀 report 存檔（UTF-8）；同名 .json 存機器版。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = []
    lines.append("SCRIPT GATE REPORT")
    lines.append("=" * 50)
    lines.append("verdict: %s" % ("PASS" if report["ok"] else "FAIL"))
    d = report["duration"]
    lines.append("")
    lines.append("[duration] chars=%d  est=%.2f min (%.0fs) @ cpm=%d"
                 % (d["chars"], d["est_min"], d["est_sec"], d["cpm"]))
    for b in d["per_beat"]:
        extra = ""
        if "planned_sec" in b:
            extra = "  planned=%ds delta=%+.0fs" % (b["planned_sec"], b["delta_sec"])
        lines.append("  - %s: %d chars ~%.0fs%s"
                     % (b["title"], b["chars"], b["est_sec"], extra))
    lines.append("")
    lines.append("[hook] violations=%d" % len(report["hook_violations"]))
    for v in report["hook_violations"]:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    s = report["structure"]
    lines.append("")
    lines.append("[structure] chapters=%d paragraphs=%d ok=%s"
                 % (s["chapters"], s["paragraphs"], s["ok"]))
    for v in s["chapter_issues"] + s["cta_issues"]:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    for g in s["interrupt_gaps"]:
        lines.append("  - WARN interrupt gap %.0fs-%.0fs" % (g["from_sec"], g["to_sec"]))
    lang = report.get("language", [])
    lines.append("")
    lines.append("[language M110] fails=%d warns=%d"
                 % (len([v for v in lang if v["level"] == "fail"]),
                    len([v for v in lang if v["level"] == "warn"])))
    for v in lang:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    rhythm = report.get("rhythm", [])
    lines.append("")
    lines.append("[rhythm M110] warns=%d" % len(rhythm))
    for v in rhythm:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    lines.append("")
    lines.append("[interrupt schedule] (30s first, then every 75+/-15s; re-hook @40%/70%)")
    for it in report["interrupt_schedule"]:
        lines.append("  - %6.1fs  %s" % (it["t_est"], it["type"]))
    lines.append("")
    if report["warnings"]:
        lines.append("[warnings]")
        for w in report["warnings"]:
            lines.append("  - %s" % w)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    jpath = os.path.splitext(path)[0] + ".json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------- self-test

def _clean_script_fixture():
    # PUBLIC_FIXTURE: invented narration used only for deterministic gate tests.
    clean = (
        "**[00:00-00:30 cold open]**\n\n"
        "這支示範影片曝光達到 12345，訂閱增加 67，"
        "我只用了 3 個小時就完成。\n\n"
        "你猜最關鍵的一步是什麼？\n\n"
        "**[00:30-02:00 method]**\n\n"
        "第一步是把腳本交給機械檢查，先估時長再看鉤子，"
        "最後掃一遍章節結構，確認每一章都有讓人停下來的理由。\n\n"
        "但是這裡有個陷阱，為什麼大家都忽略？"
        "因為多數人以為腳本寫完就等於準備好了，"
        "結果錄完音才發現開場拖了整整 40 秒還沒進重點。\n\n"
        "答案是留存曲線前 30 秒很重要，"
        "所以錄音之前就要把這些問題全部攔下來，"
        "而不是等剪輯的時候才回頭救火。\n\n"
        "**[02:00-02:30 outro]**\n\n"
        "覺得有用就訂閱，也歡迎來示範社群聊。\n"
    )
    return clean


def _selftest_gate_cases(check, clean):
    if __package__:
        from .script_gate_commands import _selftest_gate_cases as _implementation
    else:
        from script_gate_commands import _selftest_gate_cases as _implementation
    return _implementation(globals(), check, clean)

def _selftest_rhythm_cases(check, clean, paired):
    if __package__:
        from .script_gate_commands import _selftest_rhythm_cases as _implementation
    else:
        from script_gate_commands import _selftest_rhythm_cases as _implementation
    return _implementation(globals(), check, clean, paired)

def _selftest_duration_cases(check, clean, rep1):
    if __package__:
        from .script_gate_commands import _selftest_duration_cases as _implementation
    else:
        from script_gate_commands import _selftest_duration_cases as _implementation
    return _implementation(globals(), check, clean, rep1)


def _selftest_body(check):
    if __package__:
        from .script_gate_commands import _selftest_body as _implementation
    else:
        from script_gate_commands import _selftest_body as _implementation
    return _implementation(globals(), check)


def _selftest():
    if __package__:
        from .script_gate_commands import _selftest as _implementation
    else:
        from script_gate_commands import _selftest as _implementation
    return _implementation(globals())


if __name__ == "__main__":
    raise SystemExit(_selftest())
