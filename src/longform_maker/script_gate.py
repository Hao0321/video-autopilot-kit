# -*- coding: utf-8 -*-
"""script_gate.py — 腳本機械檢查（錄音前攔）· fill-in-your-own-data

⚙️ **觀眾語言的四層詞表預設是空的**，因為它只能從「你自己的逐字稿」審計出來
（別人的白名單帶著別人的題材、市場與語感，照抄比不檢查更糟）。
建表流程 → `templates/style_profile.template.md` §5；骨架檔 →
`templates/audience_vocab.example.json`；填好後 `load_vocab("你的.json")`。
COMMUNITY_WORD 同樣是 FILL-IN。

輸入 = 旁白腳本純文字。beats 用 **[mm:ss-mm:ss 標題]** 或 markdown 段落。

API:
    load_vocab(path_or_dict)         -> {層: 筆數}             # 載入你自己的詞表
    reset_vocab() / vocab_is_empty()
    estimate_duration(text, cpm=260) -> {chars, est_min, est_sec, per_beat, warnings}
    check_hook(text)                 -> [violations]           # R24 cold open
    check_structure(text)            -> report dict            # 問句/CTA/interrupt 缺口
    check_audience_language(text)    -> [violations]           # M110 觀眾語言（fail 級）
    check_rhythm(text, cpm)          -> [issues]               # M110 節奏（warn 級）
    interrupt_schedule(text, cpm)    -> [{t_est, type}]        # 給 build 對接（json-able）
    gate(text, cpm=260)              -> (ok, report)           # 總閘門

規則來源：R24 cold open / M95 死空檔 / 強制 outro（訂閱+社群 CTA，可配置）/
M110 腳本三支柱（語氣＝你的 voice profile／觀眾語言＝路人 0.5 秒懂／節奏＝一直看下去）
— 語氣歸 voice profile 工具（`templates/style_profile.template.md`），本檔機械化後兩柱；
擋不了的人工 craft（hook 三件套／loop 開關／payoff 密度…）→
`knowledge/script-retention-craft.md`。
cp950 安全：print 只 ASCII；檔案 I/O 一律 encoding="utf-8"。
self-test 外殼（PASS/FAIL 印法 + exit code）→ gate_core.py；規則本體留在本檔。
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

CPM_DEFAULT = 260          # 中文旁白 chars/min（中文口播常見區間 240-280，請用自己舊片校準）
CPM_OK_RANGE = (240, 280)

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
    r"|做到|衝到|賺到|開啟|突破|翻倍|翻了|漲到|掉到|省下|成長|破紀錄|拿下"
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
COMMUNITY_WORD = "社群"   # FILL-IN：你的社群名（Discord 群名等）；空字串=跳過社群 CTA 檢查

_INTERRUPT_GAP_SEC = 90        # 連續無 interrupt 訊號上限
_FIRST_INTERRUPT_SEC = 30      # 30s 首發
_INTERRUPT_PERIOD_SEC = 75     # 之後每 75±15s 一發
_INTERRUPT_JITTER_SEC = 15
_REHOOK_FRACS = (0.25, 0.50, 0.75)   # re-hook 位（2026-07 研究收斂：25/50/75%，
                                     #  中段 50% 那發 8min+ 影片不可省）

# ---------------- M110 觀眾語言（旁白層的「路人 0.5 秒懂」鐵則）
#
# 【四層表預設是空的，這是刻意的】
# 行話分級只有一種正確做法：**從你自己的逐字稿審計出來**。別人的白名單帶著別人的
# 題材（他的觀眾聽過的詞 ≠ 你的觀眾聽過的詞）、別人的市場（有些平台名只在特定地區
# 通用）、別人的語感。照抄別人的表 = 用別人的觀眾檢查你的稿子，比不檢查更糟——
# 它會放行你觀眾聽不懂的詞，又擋掉你觀眾早就熟的詞，而你還會信任它。
#
# 四層定義：
#   SPOKEN_OK  = 你舊稿實際講過、且影片留存正常 → 可直接講（不報 warn）
#   SUBSTITUTE = 你本來就有中文說法的英文詞 → 講英文 = fail（同時掉 voice 與觀眾語言）
#   NEED_PAIR  = 可以講，但【同一個 beat】要有白話同伴詞（先白話後術語 / 術語即解）
#   HARD_BAN   = 內部工程詞，旁白永遠不出現 = fail
#
# 怎麼建（一次 30-60 分鐘，之後只增補）→ `templates/style_profile.template.md` §5
# 骨架檔 → `templates/audience_vocab.example.json`（複製成你自己的再填）
# 填好後：`load_vocab("你的 audience_vocab.json")`
#
# 四表全空時：不掃詞，只回一條 lang.no_vocab warn（提醒你還沒建表），gate 照樣能過
# ——先讓流程跑起來，再慢慢把表養大。新詞的正常生命週期：
# lang.unknown_term warn → 人工判級 → 入表。
# **判級標準不是「我的同溫層懂不懂」，是「我樣本裡講過沒有 + 路人 0.5 秒懂不懂」。**
SPOKEN_OK: set = set()
SUBSTITUTE: dict = {}
NEED_PAIR: dict = {}
HARD_BAN: list = []

# self-test / 文件示範用的最小表（**不是**建議值，只為示範四層各自怎麼作用）。
_DEMO_VOCAB = {
    "spoken_ok": ["ai", "app", "ok"],
    "substitute": {"prompt": "提示詞"},
    "need_pair": {"qa": ["品管", "驗收", "檢查", "抓錯"]},
    "hard_ban": ["pipeline", "regex", "endpoint"],
}

_LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]*")
_KIT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXAMPLE_VOCAB = os.path.join(_KIT_ROOT, "templates", "audience_vocab.example.json")


def load_vocab(src) -> dict:
    """載入你自己的四層詞表。src = JSON 檔路徑 或 dict。回傳各層筆數。

    JSON 格式見 `templates/audience_vocab.example.json`：
        {"spoken_ok": [...], "substitute": {...}, "need_pair": {...}, "hard_ban": [...]}
    底線開頭的 key 一律忽略（可以在 JSON 裡寫給自己看的註解）。
    比對一律轉小寫；重複呼叫 = **整組取代**，不是累加。
    """
    global SPOKEN_OK, SUBSTITUTE, NEED_PAIR, HARD_BAN
    if isinstance(src, str):
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = dict(src or {})
    data = {k: v for k, v in data.items() if not str(k).startswith("_")}
    SPOKEN_OK = {str(w).lower() for w in (data.get("spoken_ok") or [])}
    SUBSTITUTE = {str(k).lower(): v for k, v in (data.get("substitute") or {}).items()}
    NEED_PAIR = {str(k).lower(): list(v)
                 for k, v in (data.get("need_pair") or {}).items()}
    HARD_BAN = [str(w).lower() for w in (data.get("hard_ban") or [])]
    return {"spoken_ok": len(SPOKEN_OK), "substitute": len(SUBSTITUTE),
            "need_pair": len(NEED_PAIR), "hard_ban": len(HARD_BAN)}


def reset_vocab() -> dict:
    """清空四層表（回到「還沒建表」狀態）。"""
    return load_vocab({})


def vocab_is_empty() -> bool:
    """四層表全空 = 還沒做逐字稿審計。"""
    return not (SPOKEN_OK or SUBSTITUTE or NEED_PAIR or HARD_BAN)

# ---------------- M110 節奏（讓人一直看下去；warn 級 craft 檢查）
# momentum：每個中段 beat 至少一個轉折/動能詞或問句（含你自己的招牌動能詞）
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
                               # （門檻刻意放寬到 160：長句連珠砲本身可以是招牌語感，
                               #   這條只想抓真的一路不換氣的段落。你的語感更短促就調小。）

_DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")


# ---------------------------------------------------------------- parsing

def _strip_markup(s: str) -> str:
    """去 markdown 記號，留純旁白字。

    blockquote 行（> 開頭）＝檔頭註記／給自己看的對帳筆記，不是旁白 → 整行剔除
    （否則 gate 會把註記裡的行話、代號、BGM 備忘當旁白掃，時長也跟著灌水）。"""
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

    # -- 每章（>=3 段落塊）至少 1 問句
    chapter_issues = []
    for b in beats:
        b_paras = _split_paragraphs(b["body"])
        if len(b_paras) >= 3 and not _QUESTION_RE.search(b["body"]):
            chapter_issues.append({
                "rule": "structure.chapter_no_question",
                "chapter": b["title"],
                "paragraphs": len(b_paras),
            })

    # -- 結尾段強制 outro：訂閱 CTA + 測試社群
    # 舞台註記（📺 end screen / 純括號指示）不是唸稿 → 跳過再取最後「可唸」段
    cta_issues = []
    speakable = _speakable_paras(text)
    tail = speakable[-1] if speakable else (paras[-1] if paras else "")
    if not _CTA_SUBSCRIBE_RE.search(tail):
        cta_issues.append({"rule": "structure.outro_no_subscribe_cta",
                           "detail": "last paragraph lacks subscribe CTA"})
    if COMMUNITY_WORD and COMMUNITY_WORD not in tail:
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

    fail 級：HARD_BAN 出現 / SUBSTITUTE 有中文說法卻講英文 / NEED_PAIR 同 beat 無白話同伴詞。
    warn 級：不在任何表上的英文 token（人工判級後入表）。
    Title-case 專有名詞（產品名）跳過 unknown warn，
    但 HARD_BAN / NEED_PAIR 仍然照抓（case-insensitive）。

    四層表全空（還沒做逐字稿審計）→ 不掃詞，只回一條 lang.no_vocab warn。
    """
    if vocab_is_empty():
        return [{"rule": "lang.no_vocab", "level": "warn", "beat": "(all)", "term": "",
                 "hint": "audience vocab is empty - build yours from your own "
                         "transcripts (templates/audience_vocab.example.json), "
                         "then call load_vocab(path)"}]

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
                            "hint": "say instead: " + SUBSTITUTE[t]})
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
    """30s 首發 + 每 75±15s 一發的建議表；re-hook 標在 25%/50%/75%。

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
            ("lang vocab not configured - see load_vocab() / "
             "templates/audience_vocab.example.json"
             if v["rule"] == "lang.no_vocab" else
             "lang unknown term '%s' in beat %s" % (v["term"], _ascii(v["beat"])))
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
    lines.append("[interrupt schedule] (30s first, then every 75+/-15s; re-hook @25/50/75%)")
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

def _selftest_body(check):
    # -- 詞表預設空：不掃詞，只提醒你還沒建表（gate 不因此擋稿）
    reset_vocab()
    check("vocab starts empty (fill-in-your-own)", vocab_is_empty())
    empty_lang = check_audience_language(
        "**[00:00-00:30 open]**\n\n我做了一個 pipeline 跑 QA，還寫了 prompt。\n")
    check("empty vocab: no term scanning, single no_vocab warn",
          len(empty_lang) == 1 and empty_lang[0]["rule"] == "lang.no_vocab"
          and empty_lang[0]["level"] == "warn")

    # -- 隨 kit 出貨的骨架檔要能被 load_vocab 讀（schema 漂移防呆）
    if os.path.isfile(_EXAMPLE_VOCAB):
        counts_ex = load_vocab(_EXAMPLE_VOCAB)
        check("shipped example vocab parses",
              set(counts_ex) == {"spoken_ok", "substitute", "need_pair", "hard_ban"})
        check("shipped example vocab ships blank (nothing borrowed)",
              vocab_is_empty())
    else:                                        # 單檔複製走的情境
        check("shipped example vocab parses (skipped: file not next to module)", True)

    # -- 載入示範表（真實使用請 load_vocab 你自己審計出來的 JSON）
    counts = load_vocab(_DEMO_VOCAB)
    check("load_vocab populates four layers",
          counts == {"spoken_ok": 3, "substitute": 1, "need_pair": 1, "hard_ban": 3})
    check("vocab_is_empty false after load", not vocab_is_empty())
    vpath = os.path.join(_DEMO_DIR, "audience_vocab.json")
    os.makedirs(_DEMO_DIR, exist_ok=True)
    with open(vpath, "w", encoding="utf-8") as f:
        json.dump(dict(_DEMO_VOCAB, _note="demo only"), f, ensure_ascii=False, indent=2)
    check("load_vocab reads json path and ignores _ keys",
          load_vocab(vpath) == counts)

    # -- 假腳本 1：乾淨過關（cold open 有數字結果、每章有問句、outro 齊全）
    # ⚠️ 以下數字全是虛構的整數佔位值，只為觸發 hook 的「結果性訊號」規則。
    #    不要把任何真實頻道的後台讀數寫進 fixture（會變成公開的私有數據）。
    clean = (
        "**[00:00-00:30 cold open]**\n\n"
        "這支影片曝光衝到 10000，訂閱 +100，"
        "我只用了 3 個小時就做到。\n\n"
        "你猜最關鍵的一步是什麼？\n\n"
        "**[00:30-02:00 method]**\n\n"
        "第一步是把腳本交給機械檢查，先估時長再看鉤子，"
        "最後掃一遍章節結構，確認每一章都有讓人停下來的理由。\n\n"
        "但是這裡有個陷阱，為什麼大家都忽略？"
        "因為多數人以為腳本寫完就等於準備好了，"
        "結果錄完音才發現開場拖了整整 40 秒還沒進重點。\n\n"
        "答案是留存曲線前 30 秒決定 80% 的命運，"
        "所以錄音之前就要把這些問題全部攔下來，"
        "而不是等剪輯的時候才回頭救火。\n\n"
        "**[02:00-02:30 outro]**\n\n"
        "覺得有用就訂閱，也歡迎來測試社群聊。\n"
    )
    ok1, rep1 = gate(clean)
    check("clean script passes gate", ok1)
    check("clean script: no hook violations", not rep1["hook_violations"])
    check("clean script: structure ok", rep1["structure"]["ok"])
    check("clean script: beats parsed = 3", rep1["duration"]["chars"] > 0
          and len(rep1["duration"]["per_beat"]) == 3)
    check("clean script: schedule starts at 30s",
          rep1["interrupt_schedule"] and rep1["interrupt_schedule"][0]["t_est"] == 30.0)

    # -- 假腳本 2：自介開頭 → hook fail
    intro = (
        "大家好，我是小明，今天要來聊剪片。\n\n"
        "歡迎回來我的頻道。\n\n"
        "這支影片會講三個重點，你準備好了嗎？\n\n"
        "記得訂閱，也來測試社群。\n"
    )
    ok2, rep2 = gate(intro)
    check("self-intro script fails gate", not ok2)
    rules2 = {v["rule"] for v in rep2["hook_violations"]}
    check("self-intro flagged banned_opener", "hook.banned_opener" in rules2)
    check("self-intro flagged no_result_word", "hook.no_result_word" in rules2)

    # -- 假腳本 3：無問句章節 + 缺 outro → structure fail
    noq = (
        "**[00:00-00:20 open]**\n\n"
        "我用 7 天做到了 10 倍流量。\n\n"
        "**[00:20-02:00 body]**\n\n"
        "第一段內容都在這裡。\n\n"
        "第二段內容繼續。\n\n"
        "第三段內容收尾，完全沒有問句。\n"
    )
    ok3, rep3 = gate(noq)
    check("no-question script fails gate", not ok3)
    check("no-question chapter flagged",
          any(i["rule"] == "structure.chapter_no_question"
              for i in rep3["structure"]["chapter_issues"]))
    check("missing outro CTA flagged", len(rep3["structure"]["cta_issues"]) == 2)

    # -- M110 language：HARD_BAN / NEED_PAIR 無同伴 → fail
    jargon = (
        "**[00:00-00:30 open]**\n\n"
        "我做了一個 pipeline，它會自己跑 QA，超過 9 成的錯都攔得下來。\n\n"
        "你想知道怎麼做到的嗎？\n\n"
        "**[00:30-01:00 outro]**\n\n"
        "訂閱一下，也來測試社群。\n"
    )
    ok4, rep4 = gate(jargon)
    check("jargon script fails gate", not ok4)
    lang_rules = {v["rule"] for v in rep4["language"] if v["level"] == "fail"}
    check("hard_ban 'pipeline' flagged", "lang.hard_ban" in lang_rules)
    check("unexplained 'QA' flagged", "lang.jargon_unexplained" in lang_rules)

    # -- M110 language：QA 帶白話同伴 → 不 fail；Title-case 產品名不 warn
    paired = (
        "**[00:00-00:30 open]**\n\n"
        "我用 Midjourney 做了 100 張圖，剪完之後品管還是我，"
        "講白了我變成它的 QA。你猜哪一步最花時間？\n\n"
        "**[00:30-01:00 outro]**\n\n"
        "訂閱一下，也來測試社群。\n"
    )
    ok5, rep5 = gate(paired)
    check("paired QA passes gate", ok5)
    check("Midjourney not flagged unknown",
          not any(v["term"] == "Midjourney" for v in rep5["language"]))

    # -- M110 language：白名單外全大寫 token → unknown warn（不 fail）
    unk = paired.replace("Midjourney", "OBSX")
    ok6, rep6 = gate(unk)
    check("unknown all-caps term warns but passes", ok6 and any(
        v["rule"] == "lang.unknown_term" for v in rep6["language"]))

    # -- M110 rhythm：超長 beat 全長句 → beat_too_long + no_punch warn
    drone = "這一段的內容會一直往下講而且完全沒有停下來的意思也沒有任何短句" * 8
    rhy = (
        "**[00:00-00:20 open]**\n\n我 3 天做到了 10 倍流量，你信嗎？\n\n"
        "**[00:20-03:00 body]**\n\n" + drone + "。\n\n"
        "**[03:00-03:20 outro]**\n\n訂閱，也來測試社群。\n"
    )
    r_iss = {i["rule"] for i in check_rhythm(rhy)}
    check("overlong beat flagged", "rhythm.beat_too_long" in r_iss)
    check("all-long-sentence beat flagged no_punch", "rhythm.no_punch" in r_iss)
    check("droning mid-beat flagged no_momentum", "rhythm.no_momentum" in r_iss)

    # -- M110 rhythm：中段總結感 + hook 無懸念
    flathook = (
        "**[00:00-00:20 open]**\n\n我做了 3 個工具。\n\n"
        "**[00:20-01:00 body]**\n\n總而言之這些工具都很好用，但是我最推第一個。\n\n"
        "**[01:00-01:20 outro]**\n\n訂閱，也來測試社群。\n"
    )
    r2 = {i["rule"] for i in check_rhythm(flathook)}
    check("mid closing tone flagged", "rhythm.mid_closing_tone" in r2)
    check("flat hook flagged no_open_loop", "rhythm.hook_no_open_loop" in r2)

    # -- M110 rhythm：乾淨腳本 0 節奏 warn（clean fixture 校準）
    check("clean script has no rhythm issues", not check_rhythm(clean))

    # -- M110 SUBSTITUTE：prompt 有原生中文詞「提示詞」→ 用英文 fail
    subst = paired.replace("做了 100 張圖", "寫了 3 個 prompt 做了 100 張圖")
    ok8, rep8 = gate(subst)
    check("english 'prompt' fails (use_chinese)", not ok8 and any(
        v["rule"] == "lang.use_chinese" and v["term"] == "prompt"
        for v in rep8["language"]))

    # -- M110 and-then 密度：段首弱連接流水帳 → warn
    at_paras = "\n\n".join(
        "然後我們再做一件事情把畫面調整好接著往下走，"
        "再把聲音的部分也順一次調整到大家聽起來舒服的程度，調完就存檔"
        for _ in range(9))
    at_script = ("我 3 天賺到 10 萬，你信嗎？\n\n" + at_paras +
                 "\n\n訂閱，也來測試社群。\n")
    check("and-then chain flagged", any(
        i["rule"] == "rhythm.andthen_chain" for i in check_rhythm(at_script)))

    # -- blockquote 註記不算旁白（給自己看的對帳注釋含行話也不觸發）
    noted = ("> gate note: regex pipeline endpoint (memo to self)\n\n" + paired)
    ok7, rep7 = gate(noted)
    check("blockquote notes excluded from gate", ok7)
    check("blockquote terms not scanned",
          not any(v["term"] in ("regex", "pipeline", "endpoint")
                  for v in rep7["language"]))
    check("blockquote chars not counted",
          estimate_duration(noted)["chars"] == estimate_duration(paired)["chars"])

    # -- estimate_duration 邊界：cpm 出區間 warn
    d = estimate_duration(clean, cpm=200)
    check("cpm=200 triggers warning", any("cpm=200" in w for w in d["warnings"]))

    # -- interrupt gap：長篇無訊號段落 → gap warn
    filler = "這是一段沒有任何訊號的內容填充" * 30
    gap_script = (
        "我賺到了 100 萬。\n\n" + filler + "。\n\n"
        "訂閱加測試社群。\n"
    )
    s_gap = check_structure(gap_script)
    check("90s+ dead stretch flagged as interrupt gap", len(s_gap["interrupt_gaps"]) >= 1)

    # -- schedule 含 re-hook（用夠長的腳本）
    long_txt = ("這裡是內容。" * 400)
    sched = interrupt_schedule(long_txt)
    check("long script schedule has re-hook",
          any(it["type"] == "re-hook" for it in sched))
    check("schedule is json-serializable", bool(json.dumps(sched)))

    # -- demo：乾淨腳本 report 存 _demo/
    demo_path = os.path.join(_DEMO_DIR, "script_report.txt")
    write_report(rep1, demo_path)
    check("demo report written", os.path.isfile(demo_path)
          and os.path.getsize(demo_path) > 200)
    check("demo report json written",
          os.path.isfile(os.path.join(_DEMO_DIR, "script_report.json")))

    reset_vocab()          # 別把示範表留在 module 狀態裡


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=50, list_fails=True)


if __name__ == "__main__":
    raise SystemExit(_selftest())
