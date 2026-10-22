"""Synthetic public fixture blocks used by the per-output privacy sanitizers.

Every value here is invented demo data: places, products, prices, metrics and
narration are fictional.  The sanitizers splice these blocks over canonical
fixtures that were derived from a maintainer's own projects; this module never
stores the private values it replaces.
"""
from __future__ import annotations


# Fictional battle tops (caption lengths match the gate fixtures they replace).
DEMO_TOP_LEFT = "示範紅"
DEMO_TOP_RIGHT = "示範藍陀螺"
DEMO_TOP_COUNTERFEIT = "示範金陀螺"

PUBLIC_LONGFORM_FORMAT_CARD = (
    "16:9；以已驗證的長片模板為基準：創作者連續口白、概念全幅 Motion、真操作／證據、"
    "半透明黑底白字幕與低 BGM；節奏依題材。"
)


PUBLIC_WORD_CAPTIONS_SELFTEST = r'''if __name__ == "__main__":
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
        shutil.rmtree(work, ignore_errors=True)'''


PUBLIC_MEDIA_CAPTION_SYNC_FIXTURE = r'''    with _tf.NamedTemporaryFile('w', suffix='.ass', delete=False, encoding='utf-8') as _f:
        _f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                 "Dialogue: 0,0:00:01.00,0:00:03.50,Cap,,0,0,0,,{\\fad(90,60)}這是一段示範字幕\n"
                 "Dialogue: 0,0:00:03.60,0:00:06.00,Cap,,0,0,0,,完全沒有真實旁白\n")
        _assp = _f.name
    _evs = _parse_ass_events(_assp)
    assert len(_evs) == 2 and _evs[0][0] == 1.0 and _evs[0][2] == "這是一段示範字幕", "_parse_ass_events 解析錯"
    os.remove(_assp)
    # PUBLIC_FIXTURE: caption-sync overlap fixtures are synthetic wording.
    assert _char_overlap("這是,一段示範的字幕", "這是一段示範字幕") >= 0.9, "同句 overlap 該高"
    assert _char_overlap("完全不相干的內容啦", "請先檢查 Claude Code") < 0.5, "異句 overlap 該低"
'''


PUBLIC_PUBLISHING_COPY_SELFTEST = '''def selftest() -> None:
    # PUBLIC_FIXTURE: fictional tops; routing relies on the generic franchise alias.
    official = build_publish_copy(
        {"name": "demo_battle", "niche": "toy", "what": "戰鬥陀螺 示範紅對決示範藍陀螺"},
        {"yt_title": "示範紅 VS 示範藍陀螺", "text": "這一局誰先出界？"},
        today=date(2026, 8, 11),
    )
    assert official["topic_key"] == "beyblade_x" and not official["issues"]
    wrong = build_publish_copy(
        {"niche": "toy", "what": "戰鬥陀螺 正版示範紅對決正版示範藍陀螺"},
        {"yt_title": "正版示範紅 VS 正版示範藍陀螺", "text": "實測"},
        today=date(2026, 8, 11),
    )
    assert wrong["issues"]
    counterfeit = build_publish_copy(
        {"niche": "toy", "what": "戰鬥陀螺 示範藍陀螺對決盜版示範金陀螺"},
        {"yt_title": "示範藍陀螺 VS 盜版示範金陀螺", "text": "這一局實測"},
        today=date(2026, 8, 11),
    )
    assert counterfeit["release_ready"]
    print("publishing_copy self-test GREEN")'''


PUBLIC_SHORTS_SPEC_EXAMPLE = '''spec 結構（一支 Short；PUBLIC_FIXTURE 合成範例）:
    {
      "name": "demo_bakery",
      "place": "示範市 示範烘焙",         # 開場識別大字（必填）
      "what":  "示範甜點店",             # 一句這是什麼（必填）
      "addr":  "📍 示範烘焙｜示範市示範路 1 號",   # 地址常駐條（必填）
      "segs":  [(clip, in_sec, dur), ...],
      "caps_by_seg": [(seg_idx, [(text, color)], kind), ...],
      "bgm_folder": "示範配樂",
    }
'''


PUBLIC_SHORTS_SP_COMMENT = '''# ── S-P 高風險宣稱 lint（PUBLIC_FIXTURE generic starter）
# 六類**機器抓得到**的高風險詞。規則不是禁用這些詞——
# 是「用了就要付得出證據」：SPEC["evidence"][字幕原文] = 怎麼驗過的
# （frame: 親抽哪格看到什麼 / sign: 哪張牌逐字讀 / web: 出處 / user: creator 告知）。
# 常見落差：數量被誇大、材質或顏色看錯、紀錄名稱漏掉限定詞。無佐證 = FAIL。
'''


PUBLIC_SHORTS_SQ_COMMENT = '''# ── S-Q 首幀技術品質（PUBLIC_FIXTURE generic starter）
# S-N（首幀內容強不強）仍是人工項——銳利度/對比分不出好壞內容。
# 但「同一格 vs 全素材池」的**相對**銳利度是另一回事：選到池裡最軟的格子＝技術面失分，
# 這抓得到。資料免費：scan 期的 _scan.json 已有每 0.5s 的 sharp/bright。warn 級——
# 內容判斷可以壓過技術分數，但 warn 會把更銳利的候選格印出來給人比對。
'''


# S-P: one risky caption plus its evidence note, then one caption per risk class
# (absolute quantity, count, material, dark colour, superlative, unlimited plan).
PUBLIC_SHORTS_RISKY_CLAIM = ("門口擠滿排隊人潮", "frame: IMG@1.4 數過 8 人")
PUBLIC_SHORTS_CLAIM_CLASSES = ("桌面全是大理石", "一碗裝兩種", "漆黑色湖面", "全台最長步道", "飲料無限暢飲")
# S-R: a 14-character caption that cannot be read in the 0.74 s fixture window.
PUBLIC_SHORTS_READING_FIXTURE = "示範湯麵店的手工麵條值得排隊"


PUBLIC_GENRE_FOUR_CUTS = '''## 通用四刀（所有類型先過這關）

1. **名詞要具體**：「小吃店」→ 招牌上讀得到的店名；「肉」→ 菜單上的品名（例：「示範麵館」「招牌炸雞」）。
   讀不到就問 creator，**不准用泛稱混過去**（M113）。
2. **每支片一個「為什麼要看完」**：hook 不是報地名，是丟一個沒解完的東西
   （「號稱在地人排隊名店」→ 看完才知道值不值得排）。
3. **砍清點、留 payoff**：一句只留最有感的那個細節，形容詞換動詞
   （「醬汁淋上去還在冒泡」留、「深淺兩種顏色」砍）。
4. **結尾給動作**：分享對象（「傳給那個一直說要一起去的朋友」）或下一步（「下次去海邊就停這裡」），
   不求讚。

PUBLIC_FIXTURE: examples are synthetic; no maintainer shop, dish or route is named.'''


PUBLIC_GENRE_AI = '''### 🤖 AI 教學（主線，SOP 完整）
- 語音/字卡沿用 creator 自己的 voice profile 與腳本 gate；Shorts＝長片切條
- hook＝可驗證戰績＋反差（「這個工具連跑 30 天，但它昨天抓到我 3 個錯」）；數字全走 M10'''


PUBLIC_GENRE_LANDING = '''## 落地位置
- 寫任何 Shorts 字幕/文案前：先讀本檔，再對照 creator 自己的文案 profile（一稿多平台）。
'''


PUBLIC_STORAGE_PROBLEM = '''## 問題定義

同一支影片改字幕、BGM 或字卡時，不應因為一次小修改就新增一支完整 1080p／4K 影片。
`v2／v3／FINAL／old／backup` 是人工命名，不是版本控制，也不是備份策略。

導入前先用下方 CLI 在自己的工作區做唯讀盤點，記錄各資料夾的檔案數、容量與
≥20 MB 完全重複檔的組數，作為之後比較的基準。PUBLIC_FIXTURE 不附維護者工作區的盤點數字。'''
