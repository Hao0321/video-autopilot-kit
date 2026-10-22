# -*- coding: utf-8 -*-
"""Word-timed caption grouping (public distribution).

Caption timing comes from approved word timestamps while line breaks follow
punctuation, pauses and semantic constraints.  Project transcript excerpts,
maintainer correction history and private sign-off phrases are not documentation
fixtures in the public module.

PUBLIC_FIXTURE: caption regressions use synthetic narration only.
"""
import os, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

# 行尾懸掛字（斷在這些字後面 = 片語被腰斬，讀起來卡）→ 斷行點會避開
DANGLERS = set("的了也就才把去和跟在是有我你他很而且然後到個一二兩三")
# 行尾【硬】懸掛字（M108：情態/助動/介係/指示/共動 —— 收在這裡 = 謂語被腰斬，strict 斷點直接不合格）
TAIL_HARD = set("會要能想該讓被幫給從當像比把這靠用往向對跟開始變成")
# 行尾【硬】懸掛【詞】（M108：黏後動詞/謂語的副詞、共動片語 —— 收在行尾 = 缺後續）
TAIL_HARD_TOK = ("一直", "幾乎", "越來越", "慢慢", "剛剛", "正在", "不斷", "持續", "已經")
# 行首禁用的方向補語（M108：方向補語當行頭 = 上一行被腰斬）
DIR_COMPLEMENTS = ("下去", "起來", "出來", "回來", "進去", "下來", "上來", "過去", "過來")
# 行首懸掛字（下一行用這些字開頭 = 上一行被腰斬）→ 不在這些字前斷
HEAD_DANGLERS = set("了的地得個們嗎呢吧啦")
# 連接詞 token 不掛行尾（「…結論所以」這種）
TAIL_DANGLER_TOKENS = {"所以", "而且", "然後", "但是", "因為", "就是", "甚至", "如果", "但"}
# 子句開頭詞（M108：斷在這些詞【前面】= 順著語意換氣）→ best_break 加分
CLAUSE_HEADS = ("因為", "所以", "但是", "然後", "接著", "結果", "其實", "而且", "如果",
                "就是", "甚至", "另外", "再來", "最後", "這種", "這個", "這些", "那種",
                "真正", "開始", "第一", "第二", "第三", "演算法", "為什麼",
                "好啦", "好了", "掰掰")   # M108b：語段 pivot（片尾收尾語多在句首）
# 子句標點（M108：whisper 有給逗號/句號 = 它偵測到的子句邊界，是最強斷句訊號，
_SENT_PUNCT = "。！？!?"          # 句末 → 短行也斷
_CLAUSE_PUNCT = "，、；：,;…"     # 子句 → 夠長才斷
NEVER_SPLIT = {"完整", "下去", "抽卡", "觀念", "作為", "交流", "半成", "成品", "上架", "禮拜",
               "實驗", "訂閱", "引擎", "程度", "結論", "推測", "期待", "教學", "社群", "立繪",
               "美術", "戰鬥", "遊戲", "挑戰", "分享", "留言", "影片", "東西", "部分", "方向",
               "地方", "時候", "小時", "功能", "簡單", "震撼", "誤會", "藍圖", "程式", "工具",
               "角色", "老實", "實說", "打開", "開過", "自己", "大概", "大堆", "什麼",
               "數據", "資料", "流量", "觸及", "互動", "瀏覽", "收益", "演算", "算法",
               "規則", "公式", "貼文", "追蹤", "陌生", "營利", "邏輯", "平台", "收穫",
               "運氣", "細節", "連結", "廣告", "收入", "回報", "基礎", "開發", "創作",
               "一開", "件事", "這套", "模一", "鐵粉", "盈利",
               # M108：凡「不能收行尾」的黏後副詞，內部也不准被拆（否則被逼成 幾|乎 腰斬）
               "幾乎", "一直", "越來", "來越", "慢慢", "剛剛", "正在", "不斷", "持續", "已經"}

# 常見 whisper 誤聽 →正字（專案可再傳入自己的 fixes 疊加）
#   （「Cloud」「Code」被斷到兩行，r"Cloud\s*Code" 兩行都 match 不到 → CRIT 出貨）。
BASE_FIXES = [
    (r"Cloud\s*Code", "Claude Code"), (r"cloud\s*code", "Claude Code"), (r"老口", "Claude Code"),
    (r"每速圖", "美術圖"), (r"美速圖", "美術圖"), (r"立會", "立繪"),
    (r"安慮", "Unreal"), (r"安路", "Unreal"), (r"論和", "任何"), (r"遮行", "這行"),
    (r"熟寫", "手寫"), (r"游戏", "遊戲"), (r"寫勾", "寫 code"), (r"寫購", "寫 code"),
    (r"Apple\s*Store", "App Store"), (r"AppleStore", "App Store"),
    (r"\bC\s*ode\b", "Code"), (r"G\s*P\s*T", "GPT"), (r"U\s*I", "UI"),
    (r"字幕by\S*", ""), (r"字幕組\S*", ""),   # whisper 訓練資料殘留的字幕組 credit 幻覺
]


def apply_fixes_to_words(words, fixes=None):
    """字級修正（M105 核心防線）：在【斷行前】對整個 beat 的連續文字跑 regex，
    match 到的字區間合併成一個修正後的 word（start=首字 start、end=末字 end）。
    這樣誤聽跨 word（Cloud|Code）或跨未來斷行位置都修得到、拆不散。空替換 = 刪除（幻覺字串）。"""
    allf = list(BASE_FIXES) + list(fixes or [])
    ws = [(s, e, t) for s, e, t in words]
    for pat, rep in allf:
        search_from = 0          # 已處理到的字符位置（防冪等 pattern 如 GPT→GPT 無限迴圈）
        for _guard in range(200):
            joined = "".join(t for _, _, t in ws)
            cidx = [wi for wi, (_, _, t) in enumerate(ws) for _ in t]
            m = re.search(pat, joined[search_from:])
            if not m or not cidx:
                break
            a = search_from + m.start()
            b = max(a, search_from + m.end() - 1)
            if a >= len(cidx):
                break
            w1, w2 = cidx[a], cidx[min(b, len(cidx) - 1)]
            merged_txt = "".join(t for _, _, t in ws[w1:w2 + 1])
            new_txt = re.sub(pat, rep, merged_txt, count=1)
            if new_txt == merged_txt:            # 已是正字（冪等）→ 跳過這個 match 繼續往後找
                search_from = a + max(1, m.end() - m.start())
                continue
            repl = [] if not new_txt.strip() else [(ws[w1][0], ws[w2][1], new_txt)]
            ws = ws[:w1] + repl + ws[w2 + 1:]
            # 下一輪從被替換區之後找起（替換文字長度可能不同 → 用 w1 前綴長 + 新字長）
            search_from = len("".join(t for _, _, t in ws[:w1])) + len(new_txt)
    return ws


def transcribe_words(wav, model_size="small", language="zh", model=None):
    """單檔 → [(start,end,word),...]（faster_whisper word_timestamps）。可傳入共用 model 免重載。"""
    from faster_whisper import WhisperModel
    m = model or WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), language=language, vad_filter=True, word_timestamps=True)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append((round(w.start, 3), round(w.end, 3), w.word))
    return out


def _cjklen(s):
    return len(re.sub(r"\s", "", s))


def fix_text(t, fixes=None):
    """套誤聽修正 + 清空格/標點（M68 白字乾淨版）。時間不動，只動文字。"""
    t = t.strip()
    for pat, rep in (list(BASE_FIXES) + list(fixes or [])):
        t = re.sub(pat, rep, t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"([一-鿿])\s+([一-鿿])", r"\1\2", t)
    t = re.sub(r"\s*([，。、！？：；,!?])\s*", "", t)
    return t.strip()


def group_words(words, max_chars=15, hard_gap=0.42, soft_gap=0.28, soft_len=9, fixes=None,
                min_break_gap=0.06, overflow=3, punct_min=7, sent_min=4,
                force_break_after=None):
    """Convert word timing into caption lines.

    Apply fixes before grouping; prefer punctuation and verified pauses, avoid
    dangling particles and protected word splits, and honor caller-provided
    semantic ``force_break_after`` hints.  Line start/end always use the first
    and last word timing.  PUBLIC_FIXTURE examples are creator-neutral.
    """
    if __package__:
        from .caption_grouping import GroupingLimits, WordGrouping
    else:
        from caption_grouping import GroupingLimits, WordGrouping
    grammar = {
        'CLAUSE_HEADS': CLAUSE_HEADS,
        'DANGLERS': DANGLERS,
        'DIR_COMPLEMENTS': DIR_COMPLEMENTS,
        'HEAD_DANGLERS': HEAD_DANGLERS,
        'NEVER_SPLIT': NEVER_SPLIT,
        'TAIL_DANGLER_TOKENS': TAIL_DANGLER_TOKENS,
        'TAIL_HARD': TAIL_HARD,
        'TAIL_HARD_TOK': TAIL_HARD_TOK,
        '_CLAUSE_PUNCT': _CLAUSE_PUNCT,
        '_SENT_PUNCT': _SENT_PUNCT,
    }
    limits = GroupingLimits(max_chars=max_chars, hard_gap=hard_gap, soft_gap=soft_gap,
                            soft_len=soft_len, min_break_gap=min_break_gap, overflow=overflow,
                            punct_min=punct_min, sent_min=sent_min)
    grouping = WordGrouping(grammar, limits, fix_text, _cjklen, fixes)
    return grouping.group(apply_fixes_to_words(words, fixes), force_break_after)


def scan_line_quality(texts, max_cjk=18):
    """M108 交付 gate（機械化，之前是 phantom）：掃字幕行的 尾懸掛/頭懸掛/腰斬/超長。
    texts=list[str]（已去 ASS tag 的行文字，按時間序）。回 {'ok','bad','note'}。
    規則與 group_words 生成側同一組常數（TAIL_HARD/TAIL_HARD_TOK/DIR_COMPLEMENTS/NEVER_SPLIT/HEAD_DANGLERS）
    —— 生成側防、掃描側驗，手改 ASS / 外部字幕也攔得住。"""
    bad = []
    for i, t in enumerate(texts):
        t = (t or "").strip()
        if not t:
            continue
        if len(re.sub(r"[^一-鿿]", "", t)) > max_cjk:
            bad.append((i, "超長", t))
        if (t[-1] in TAIL_HARD or t.endswith(TAIL_HARD_TOK)
                or any(t.endswith(token) for token in TAIL_DANGLER_TOKENS)):
            bad.append((i, "尾懸掛", t))
        if t.startswith(DIR_COMPLEMENTS) or (t[0] in HEAD_DANGLERS and len(t) > 1):
            bad.append((i, "頭懸掛", t))
        if i + 1 < len(texts) and texts[i + 1]:
            pair = t[-1:] + texts[i + 1].strip()[:1]
            if pair in NEVER_SPLIT:
                bad.append((i, "腰斬:" + pair, t + "|" + texts[i + 1][:8]))
    return {"ok": not bad, "bad": bad,
            "note": ("clean %d lines" % len(texts)) if not bad else
                    ("%d bad: " % len(bad)) + "; ".join(f"L{i}[{k}]{v[:14]}" for i, k, v in bad[:6])}


if __package__:
    from .caption_timeline import to_master_events, _ts
else:
    from caption_timeline import to_master_events, _ts


# ─────────────────────────────────── 每句 ≤1 關鍵詞變重（white-first/M68 守則）
# 詞表順序 = 命中優先序（前面的先中）。專案可直接覆寫模組級 EMPHASIS_TERMS。
EMPHASIS_TERMS = [
    # 工具名
    "Claude", "ChatGPT", "ffmpeg", "GitHub", "Unreal", "CapCut", "AI",
    # 結論動詞/名詞類
    "爆款", "演算法", "開源", "營利", "收益", "觸及", "互動", "瀏覽", "規則", "公式",
]
# 金色 RGB(255,210,63) → ASS BGR=&H3FD2FF&；結尾 reset 回白（white-first：只重點上色）
EMPH_TAG = r"{\fscx112\fscy112\c&H3FD2FF&}"
EMPH_RESET = r"{\fscx100\fscy100\c&HFFFFFF&}"
# 阿拉伯數字+單位（12.3萬 / 12.5% / $12.34 / 12,345）＝關鍵詞，優先於詞表
_NUM_KEY_RE = re.compile(r"[0-9][0-9,\.]*(?:%|萬|億|美金)?|\$[0-9][0-9,\.]*")
_HAS_INLINE_TAG = re.compile(r"\{\\")   # 已含 inline ASS tag → 防重入


def emphasize_line(text, terms=None, max_hits=1):
    """把該句「第一個命中的關鍵詞」包上金色放大 tag（每句最多 max_hits=1 個）。
    優先序：阿拉伯數字+單位 > 詞表順序。整句已含 inline ASS tag → 原樣返回（防重入）。
    含 \\N 的多行文字也視為一「句」，整句仍只變重 1 個詞。"""
    if not text or max_hits <= 0 or _HAS_INLINE_TAG.search(text):
        return text
    spans = []

    def _free(a, b):
        return all(b <= s or a >= e for s, e in spans)

    for m in _NUM_KEY_RE.finditer(text):          # ① 數字+單位優先
        if len(spans) >= max_hits:
            break
        if _free(m.start(), m.end()):
            spans.append((m.start(), m.end()))
    if len(spans) < max_hits:                     # ② 詞表順序=優先序
        for term in (EMPHASIS_TERMS if terms is None else terms):
            if len(spans) >= max_hits:
                break
            i = text.find(term)
            if i >= 0 and _free(i, i + len(term)):
                spans.append((i, i + len(term)))
    for a, b in sorted(spans, reverse=True):      # 右往左包，index 不位移
        text = text[:a] + EMPH_TAG + text[a:b] + EMPH_RESET + text[b:]
    return text


def chapter_card_tag():
    """章節卡 blur-in 前綴 tag（0.28s 從模糊全透明入場）。
    給呼叫端自行 prepend 到章節卡 Dialogue 文字前，build_ass 不自動加。"""
    return r"{\blur16\alpha&HFF&\t(0,280,\blur0\alpha&H00&)}"


ASS_HEAD = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            # M68：教學長片 = 白字 + 黑色半透明底框，不多色
            "Style: Cap,Microsoft JhengHei,82,&H00FFFFFF,&H4D000000,&H00000000,-1,0,0,0,100,100,0.5,0,3,16,0,2,200,200,96,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")




def build_ass(events, out_path, fade=(90, 60), emphasize=False):
    # 🔒 長片逐句字幕鐵則：一律全白統一字級(M68)。
    # 巨型數字／關鍵字改走 emphasis_overlays.py 的獨立上層，不污染逐句字幕。
    """events=[(s,e,text)] → M68 白字黑框 ASS。回傳寫入行數。
    emphasize 只保留為舊 caller 的顯式錯誤提示；True 會 raise，避免規則只停在註解。"""
    if emphasize:
        raise AssertionError(
            "longform spoken captions are clean-only; use emphasis_overlays.py for big text/numbers")
    ev = []
    for s, e, t in events:
        ev.append(f"Dialogue: 0,{_ts(s)},{_ts(e)},Cap,,0,0,0,,{{\\fad({fade[0]},{fade[1]})}}{t}")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(ASS_HEAD + "\n".join(ev) + "\n")
    return len(ev)


# ──────────────────────────────────────────── self-test
if __name__ == "__main__":
    # PUBLIC_FIXTURE: every narration fixture below is synthetic demo wording.
    # 1) 斷行純函數：模擬「素材也／都放進去了」懸掛情境 —— 長度爆掉時要回溯避開「也」結尾
    w = []
    t = 0.0
    for ch, gap in [("你可以", .02), ("看到", .05), ("畫面", .02), ("可以", .02), ("切", .30),
                    ("教學", .02), ("會", .02), ("跳", .30), ("背景", .02), ("素材", .02),
                    ("也", .02), ("都", .02), ("放進去了", .8), ("後面", .02), ("繼續", .02)]:
        w.append((round(t, 2), round(t + 0.2, 2), ch)); t += 0.2 + gap
    lines = group_words(w, max_chars=10)
    joined = [x[2] for x in lines]
    assert not any(l.endswith(("也", "的", "去", "一")) for l in joined[:-1]), f"懸掛字沒避開: {joined}"
    assert all(_cjklen(l) <= 13 for l in joined), f"行太長: {joined}"
    # 行時間必須 = 真實字時間（首字 start）
    assert abs(lines[0][0] - w[0][0]) < 1e-6, "行 start 不是首字真實時間"

    # 2) 誤聽修正（行內）
    assert "Claude Code" in fix_text("這段交給 Cloud Code 處理C ode"), "FIX 沒套到"

    w2 = [(0.0, 0.3, "這段"), (0.3, 0.6, "交給"), (0.6, 0.9, "Cloud"), (0.9, 1.3, " Code"),
          (1.3, 1.6, "整理"), (1.6, 1.9, "成"), (1.9, 2.2, "Code"), (2.2, 2.5, "字幕檔"),
          (2.5, 2.8, "再來"), (2.8, 3.1, "用"), (3.1, 3.4, "GPT"), (3.4, 3.7, "檢查")]
    fixed = apply_fixes_to_words(w2)
    jt = "".join(t for _, _, t in fixed)
    assert "Claude Code" in jt and "Cloud" not in jt, f"字級修正失敗: {jt}"
    g2 = group_words(w2, max_chars=8)   # 強迫斷行 → Claude Code 必須完整留在同一行
    assert any("Claude Code" in l[2] for l in g2), f"Claude Code 被斷行拆散: {[l[2] for l in g2]}"
    assert not any(("Cloud" in l[2] and "Claude" not in l[2]) for l in g2), f"殘留 Cloud: {[l[2] for l in g2]}"

    # 2c) whisper 幻覺 credit 字串刪除
    w3 = [(0.0, 0.3, "App"), (0.3, 0.6, " Store"), (0.6, 0.9, "的"), (0.9, 1.2, "流程"),
          (1.2, 1.5, "字幕by"), (1.5, 1.8, "示範字幕組")]
    g3 = group_words(w3)
    assert all("字幕by" not in l[2] for l in g3), f"幻覺字串沒刪: {[l[2] for l in g3]}"

    # 2d) 連讀詞（gap≈0，如 教／學）不得成為斷點
    w4 = []
    tt = 0.0
    for ch, gap in [("你可以", .02), ("看到", .20), ("畫面", .02), ("可以切", .20),
                    ("教", .00), ("學", .02), ("會跳", .20), ("背景", .02), ("素材", .02), ("放進去了", .5)]:
        w4.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g4 = group_words(w4, max_chars=7)
    for l in g4:
        assert not l[2].endswith("教"), f"連讀詞被腰斬: {[x[2] for x in g4]}"

    w5 = []
    tt = 0.0
    for ch, gap in [("這段", .05), ("剪輯比", .03), ("預期的", .08), ("還要", .02), ("完", .00),
                    ("整", .02), ("的", .02), ("很多", .40), ("整理", .03), ("只花", .02),
                    ("了", .02), ("一個", .02), ("下午", .30)]:
        w5.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g5 = group_words(w5, max_chars=8)
    for li, l in enumerate(g5):
        assert not l[2].endswith("完"), f"完|整 被腰斬: {[x[2] for x in g5]}"
        if li > 0:
            assert not l[2].startswith("了"), f"行首掛「了」: {[x[2] for x in g5]}"
    w6 = []
    tt = 0.0
    for ch, gap in [("這只是", .03), ("目前", .02), ("測試的", .03), ("結論", .06), ("所以", .02),
                    ("各位", .02), ("先別", .03), ("誤會", .5)]:
        w6.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g6 = group_words(w6, max_chars=8)
    for l in g6[:-1]:
        assert not l[2].endswith("所以"), f"連接詞掛行尾: {[x[2] for x in g6]}"

    # 2f) M108 回歸 ①：token 自帶逗號 = 子句邊界（合成句「…完全想錯,真正影響…」）
    w7 = []
    tt = 0.0
    for ch, gap in [("如果", .02), ("你覺得", .03), ("片長", .02), ("越長越好", .03), ("那其實", .02),
                    ("完全", .00), ("想錯,", .05), ("真正", .02), ("影響", .02), ("留存", .02),
                    ("的關鍵", .02), ("在哪裡", .02), ("是節奏", .6)]:
        w7.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g7 = group_words(w7, max_chars=15)
    j7 = [l[2] for l in g7]
    assert any(l.endswith("想錯") for l in j7), f"M108 標點斷句沒生效: {j7}"
    assert any(l.startswith("真正") for l in j7), f"M108 子句頭沒對齊: {j7}"
    assert not any(("想錯" in l and "真正" in l) for l in j7), f"M108 逗號兩側被擠同行: {j7}"

    # 2g) M108 回歸 ②：情態/助動不收行尾（合成句「…你真正會」）
    w8 = []
    tt = 0.0
    for ch, gap in [("這套", .02), ("流程", .02), ("幫你", .03), ("省下", .02), ("時間", .02),
                    ("你", .02), ("真正", .02), ("會", .02), ("想要", .02), ("每天用", .5)]:
        w8.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g8 = group_words(w8, max_chars=12)
    for l in g8[:-1]:
        assert not l[2].endswith(("會", "要", "該", "開始")), f"M108 情態懸掛沒避開: {[x[2] for x in g8]}"

    # 2h) M108 回歸 ③：千分位/小數點豁免（「48.」「1,」後接數字不是子句邊界）
    w9 = [(0.0, 0.3, "費用"), (0.3, 0.6, "48."), (0.6, 0.9, "50"), (0.9, 1.2, "元"),
          (1.2, 1.5, "看起來"), (1.5, 1.8, "不多,"), (1.8, 2.1, "但這是"), (2.1, 2.4, "起點")]
    g9 = group_words(w9, max_chars=15, punct_min=4)
    for l in g9:
        assert not l[2].endswith("48"), f"M108 小數點被誤當子句邊界: {[x[2] for x in g9]}"
    assert any(l[2].endswith("不多") for l in g9), f"M108 子句逗號沒斷: {[x[2] for x in g9]}"

    # 2i) M108 回歸 ④：超長段（中途無 gap、結尾才停頓）flush 時必須被拆成 ≤max_chars+overflow
    w10 = []
    tt = 0.0
    for ch, gap in [("把", .02), ("所有的", .02), ("素材", .02), ("先按", .02), ("場景", .02),
                    ("分類", .02), ("再交給", .02), ("剪輯流程", .6)]:  # 尾端 0.6 大 gap = 整段一次 flush
        w10.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g10 = group_words(w10, max_chars=15, overflow=3)
    for l in g10:
        assert _cjklen(l[2]) <= 18, f"超長行沒被 flush 拆開: {[(_cjklen(x[2]), x[2]) for x in g10]}"
    assert len(g10) >= 2, f"19字段落應拆 ≥2 行: {[x[2] for x in g10]}"

    # 2j) M108 回歸 ⑤：共動 coverb（靠/用/往）+ 黏後副詞（一直/幾乎）不收行尾
    w11 = []
    tt = 0.0
    for ch, gap in [("新手", .02), ("只要", .02), ("照著", .02), ("步驟", .02), ("也能夠", .02),
                    ("靠", .02), ("這個", .02), ("流程", .02), ("完成", .02), ("第一支片", .5)]:
        w11.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g11 = group_words(w11, max_chars=12)
    for l in g11[:-1]:
        assert not l[2].endswith(("靠", "一直", "幾乎", "用")), f"M108 共動/副詞懸掛: {[x[2] for x in g11]}"
    # 黏後副詞不能收行尾、但也不准被拆成單字（幾|乎）
    w12 = [(0.0, .3, "效果"), (.3, .6, "跟"), (.6, .9, "原本"), (.9, 1.2, "設計"), (1.2, 1.5, "幾"),
           (1.5, 1.8, "乎"), (1.8, 2.1, "完全"), (2.1, 2.4, "相同"), (2.4, 3.0, "所以")]
    g12 = group_words(w12, max_chars=8)
    for a2, b2 in zip(g12, g12[1:]):
        assert not (a2[2].endswith("幾") and b2[2].startswith("乎")), f"幾乎被腰斬: {[x[2] for x in g12]}"

    # 2j2) M108b 黏句 hint：無標點連讀「社群／大家每週」必須在 hint 處斷
    w13 = []
    tt = 0.0
    for ch, gap in [("歡迎你", .02), ("加入", .02), ("示範", .02), ("社群", .02),
                    ("大家", .02), ("每週", .02), ("會在", .02), ("裡面", .02), ("交流", .5)]:
        w13.append((round(tt, 2), round(tt + 0.2, 2), ch)); tt += 0.2 + gap
    g13 = group_words(w13, max_chars=15, force_break_after=["示範社群"])
    j13 = [l[2] for l in g13]
    assert any(l.endswith("社群") for l in j13), f"M108b hint 沒斷: {j13}"
    assert not any(("社群" in l and "大家" in l) for l in j13), f"M108b 黏句仍在: {j13}"

    # 2k) M108 scan_line_quality gate：正例 clean、負例逐類抓到
    sq = scan_line_quality(["這是乾淨的一行", "第二行也沒問題"])
    assert sq["ok"], f"scan 誤報: {sq}"
    sq2 = scan_line_quality(["這套流程讓你之後真的會",          # 尾懸掛(會)
                             "下去之後再來看結果",              # 頭懸掛(下去)
                             "我希望新手也能直接套用這",        # 尾懸掛(這)
                             "套流程完成第一支片"])             # 上行尾+本行頭=這套 腰斬
    kinds = {k.split(":")[0] for _, k, _ in sq2["bad"]}
    assert not sq2["ok"] and {"尾懸掛", "頭懸掛", "腰斬"} <= kinds, f"scan 漏抓: {sq2}"
    sq3 = scan_line_quality(["超級長的一行字要被抓出來因為超過十八個中文字上限了"])
    assert not sq3["ok"] and sq3["bad"][0][1] == "超長", f"超長沒抓: {sq3}"

    # 3) master 轉換：SPEED 同步 (M103)
    off = {"b1": {"start": 10.0, "dur": 5.0}, "_speed": 1.06}
    evs = to_master_events({"b1": [(1.0, 2.0, "第一句"), (2.5, 3.5, "第二句")]}, off, {"b1": 0.5})
    assert abs(evs[0][0] - (10 + 0.5 / 1.06)) < 0.01, "master start /SP 錯"
    assert evs[0][1] <= evs[1][0], "行重疊"

    # 3b) emphasize_line regression（每句 ≤1 關鍵詞、數字優先、防重入）
    _G, _R = EMPH_TAG, EMPH_RESET
    ea = emphasize_line("我用 Claude 做了一個 AI")
    assert ea == "我用 " + _G + "Claude" + _R + " 做了一個 AI", "emphasize: only Claude wrapped + reset expected"
    assert ea.count(_G) == 1 and ea.count(_R) == 1, "emphasize: exactly 1 wrap"
    eb = emphasize_line("衝到 12.3萬 瀏覽")
    assert eb == "衝到 " + _G + "12.3萬" + _R + " 瀏覽", "emphasize: number-first priority failed"
    ec_in = r"已含 {\c&H3FD2FF&}上色{\c&HFFFFFF&} 的行"
    assert emphasize_line(ec_in) == ec_in, "emphasize: pre-tagged line must pass through unchanged"
    ed = emphasize_line("Claude 和 GitHub 都很強")
    assert ed.count(_G) == 1 and (_G + "Claude") in ed and (_G + "GitHub") not in ed, \
        "emphasize: max_hits=1 must wrap first term only"
    en = emphasize_line("用 GitHub 開源\\N演算法推薦")
    assert en.count(_G) == 1, "emphasize: line with \\N must still get only 1 wrap"
    assert emphasize_line("$12.34 收益") == _G + "$12.34" + _R + " 收益", "emphasize: $-amount failed"
    assert emphasize_line("12.5% 互動率").startswith(_G + "12.5%" + _R), "emphasize: percent failed"
    assert chapter_card_tag() == r"{\blur16\alpha&HFF&\t(0,280,\blur0\alpha&H00&)}", "chapter_card_tag mismatch"

    # 4) 真 ffmpeg 燒字（M97）
    import tempfile, shutil
    work = tempfile.mkdtemp(prefix="wordcap_selftest_")
    try:
        ass = os.path.join(work, "t.ass")
        n = build_ass([(0.2, 1.4, "測試字幕一"), (1.5, 2.6, "測試字幕二")], ass)
        assert n == 2
        src = os.path.join(work, "c.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=navy:s=640x360:r=30:d=3",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", src],
                       capture_output=True, encoding="utf-8", errors="replace")
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "c.mp4", "-vf", "ass=t.ass",
                            "-frames:v", "60", "-f", "null", "-"],
                           cwd=work, capture_output=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, "ASS 燒字失敗:" + (r.stderr or "")[-300:]
        # 4b) 長片逐句字幕禁止 emphasize；巨字／數字必須走獨立 overlay layer
        ass_e = os.path.join(work, "e.ass")
        try:
            build_ass([(0.2, 1.4, "我用 Claude 做工具")], ass_e, emphasize=True)
            raise AssertionError("longform emphasize=True should fail")
        except AssertionError as exc:
            assert "clean-only" in str(exc)
        with open(ass, encoding="utf-8") as fh:
            assert r"\c&H3FD2FF&" not in fh.read(), "build_ass default must stay tag-free"
        print("[word_captions selftest] OK — 斷行/懸掛迴避/FIX/SP轉換/長片字幕鎖/真ffmpeg燒字 全過")
    finally:
        shutil.rmtree(work, ignore_errors=True)
