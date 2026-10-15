"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _selftest_language_rejections(_module_globals, check):
    jargon = (
        "**[00:00-00:30 open]**\n\n"
        "我做了一個 pipeline，它會自己跑 QA，超過 9 成的錯都攔得下來。\n\n"
        "你想知道怎麼做到的嗎？\n\n"
        "**[00:30-01:00 outro]**\n\n"
        "訂閱一下，也來自由工坊。\n"
    )
    ok4, rep4 = _module_globals['gate'](jargon)
    check("jargon script fails gate", not ok4)
    lang_rules = {v["rule"] for v in rep4["language"] if v["level"] == "fail"}
    check("hard_ban 'pipeline' flagged", "lang.hard_ban" in lang_rules)
    check("unexplained 'QA' flagged", "lang.jargon_unexplained" in lang_rules)


def _selftest_gate_cases(_module_globals, check, clean):
    ok1, rep1 = _module_globals['gate'](clean)
    check("clean script passes gate", ok1)
    check("clean script: no hook violations", not rep1["hook_violations"])
    check("clean script: structure ok", rep1["structure"]["ok"])
    check("clean script: beats parsed = 3", rep1["duration"]["chars"] > 0
          and len(rep1["duration"]["per_beat"]) == 3)
    check("clean script: schedule starts at 30s",
          rep1["interrupt_schedule"] and rep1["interrupt_schedule"][0]["t_est"] == 30.0)

    walkthrough = (
        "**[00:00-00:20 open]**\n\n我用這批素材剪出一支影片！先看這個結果。\n\n"
        "**[00:20-01:00 body]**\n\n我先把素材排進來。\n\n"
        "可以看到時間軸現在有畫面。\n\n所以我直接調整這一刀。\n\n"
        "**[01:00-01:15 outro]**\n\n歡迎訂閱，也來自由工坊看看。\n"
    )
    ok_walk, rep_walk = _module_globals['gate'](walkthrough)
    check("first-person result verb and question-free walkthrough pass",
          ok_walk and not rep_walk["hook_violations"]
          and not rep_walk["structure"]["chapter_issues"])

    # -- 假腳本 2：自介開頭 → hook fail
    intro = (
        "大家好，我是Hao，今天要來聊剪片。\n\n"
        "歡迎回來我的頻道。\n\n"
        "這支影片會講三個重點，你準備好了嗎？\n\n"
        "記得訂閱，也來自由工坊。\n"
    )
    ok2, rep2 = _module_globals['gate'](intro)
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
    ok3, rep3 = _module_globals['gate'](noq)
    check("no-progress script fails gate", not ok3)
    check("no-progress chapter flagged",
          any(i["rule"] == "structure.chapter_no_progress"
              for i in rep3["structure"]["chapter_issues"]))
    check("missing outro CTA flagged", len(rep3["structure"]["cta_issues"]) == 2)

    # -- M110 language：HARD_BAN / NEED_PAIR 無同伴 → fail
    _selftest_language_rejections(_module_globals, check)

    # -- M110 language：QA 帶白話同伴 → 不 fail；Title-case 產品名不 warn
    paired = (
        "**[00:00-00:30 open]**\n\n"
        "我用 Midjourney 做了 100 張圖，剪完之後品管還是我，"
        "講白了我變成它的 QA。你猜哪一步最花時間？\n\n"
        "**[00:30-01:00 outro]**\n\n"
        "訂閱一下，也來自由工坊。\n"
    )
    ok5, rep5 = _module_globals['gate'](paired)
    check("paired QA passes gate", ok5)
    check("Midjourney not flagged unknown",
          not any(v["term"] == "Midjourney" for v in rep5["language"]))

    # -- M110 language：白名單外全大寫 token → unknown warn（不 fail）
    unk = paired.replace("Midjourney", "OBSX")
    ok6, rep6 = _module_globals['gate'](unk)
    check("unknown all-caps term warns but passes", ok6 and any(
        v["rule"] == "lang.unknown_term" for v in rep6["language"]))
    return rep1, paired

def _selftest_rhythm_cases(_module_globals, check, clean, paired):
    # -- M110 rhythm：超長 beat 全長句 → beat_too_long + no_punch warn
    drone = "這一段的內容會一直往下講而且完全沒有停下來的意思也沒有任何短句" * 8
    rhy = (
        "**[00:00-00:20 open]**\n\n我 3 天做到了 10 倍流量，你信嗎？\n\n"
        "**[00:20-03:00 body]**\n\n" + drone + "。\n\n"
        "**[03:00-03:20 outro]**\n\n訂閱，也來自由工坊。\n"
    )
    r_iss = {i["rule"] for i in _module_globals['check_rhythm'](rhy)}
    check("overlong beat flagged", "rhythm.beat_too_long" in r_iss)
    check("all-long-sentence beat flagged no_punch", "rhythm.no_punch" in r_iss)
    check("droning mid-beat flagged no_momentum", "rhythm.no_momentum" in r_iss)

    # -- M110 rhythm：中段總結感 + hook 無懸念
    flathook = (
        "**[00:00-00:20 open]**\n\n我做了 3 個工具。\n\n"
        "**[00:20-01:00 body]**\n\n總而言之這些工具都很好用，但是我最推第一個。\n\n"
        "**[01:00-01:20 outro]**\n\n訂閱，也來自由工坊。\n"
    )
    r2 = {i["rule"] for i in _module_globals['check_rhythm'](flathook)}
    check("mid closing tone flagged", "rhythm.mid_closing_tone" in r2)
    check("flat hook flagged no_open_loop", "rhythm.hook_no_open_loop" in r2)

    # -- M110 rhythm：乾淨腳本 0 節奏 warn（clean fixture 校準）
    check("clean script has no rhythm issues", not _module_globals['check_rhythm'](clean))

    # -- M110 SUBSTITUTE：prompt 有原生中文詞「提示詞」→ 用英文 fail
    subst = paired.replace("做了 100 張圖", "寫了 3 個 prompt 做了 100 張圖")
    ok8, rep8 = _module_globals['gate'](subst)
    check("english 'prompt' fails (use_chinese)", not ok8 and any(
        v["rule"] == "lang.use_chinese" and v["term"] == "prompt"
        for v in rep8["language"]))

    # -- M110 and-then 密度：段首弱連接流水帳 → warn
    at_paras = "\n\n".join(
        "然後我們再做一件事情把畫面調整好接著往下走，"
        "再把聲音的部分也順一次調整到大家聽起來舒服的程度，調完就存檔"
        for _ in range(9))
    at_script = ("我 3 天賺到 10 萬，你信嗎？\n\n" + at_paras +
                 "\n\n訂閱，也來自由工坊。\n")
    check("and-then chain flagged", any(
        i["rule"] == "rhythm.andthen_chain" for i in _module_globals['check_rhythm'](at_script)))

    # -- blockquote 註記不算旁白（M10 對帳注釋含行話也不觸發）
    noted = ("> script_gate PASS note: fork assert pipeline M79\n\n" + paired)
    ok7, rep7 = _module_globals['gate'](noted)
    check("blockquote notes excluded from gate", ok7)
    check("blockquote terms not scanned",
          not any(v["term"] in ("fork", "assert", "pipeline")
                  for v in rep7["language"]))
    check("blockquote chars not counted",
          _module_globals['estimate_duration'](noted)["chars"] == _module_globals['estimate_duration'](paired)["chars"])

def _selftest_duration_cases(_module_globals, check, clean, rep1):
    # -- estimate_duration 邊界：cpm 出區間 warn
    d = _module_globals['estimate_duration'](clean, cpm=200)
    check("cpm=200 triggers warning", any("cpm=200" in w for w in d["warnings"]))

    # -- interrupt gap：長篇無訊號段落 → gap warn
    filler = "這是一段沒有任何訊號的內容填充" * 30
    gap_script = (
        "我賺到了 100 萬。\n\n" + filler + "。\n\n"
        "訂閱加自由工坊。\n"
    )
    s_gap = _module_globals['check_structure'](gap_script)
    check("90s+ dead stretch flagged as interrupt gap", len(s_gap["interrupt_gaps"]) >= 1)

    # -- schedule 含 re-hook（用夠長的腳本）
    long_txt = ("這裡是內容。" * 400)
    sched = _module_globals['interrupt_schedule'](long_txt)
    check("long script schedule has re-hook",
          any(it["type"] == "re-hook" for it in sched))
    check("schedule is json-serializable", bool(_module_globals['json'].dumps(sched)))

    # -- demo：乾淨腳本 report 存 _demo/
    demo_path = _module_globals['os'].path.join(_module_globals['_DEMO_DIR'], "script_report.txt")
    _module_globals['write_report'](rep1, demo_path)
    check("demo report written", _module_globals['os'].path.isfile(demo_path)
          and _module_globals['os'].path.getsize(demo_path) > 200)
    check("demo report json written",
          _module_globals['os'].path.isfile(_module_globals['os'].path.join(_module_globals['_DEMO_DIR'], "script_report.json")))

def _selftest_body(_module_globals, check):
    clean = _module_globals['_clean_script_fixture']()
    rep1, paired = _module_globals['_selftest_gate_cases'](check, clean)
    _module_globals['_selftest_rhythm_cases'](check, clean, paired)
    _module_globals['_selftest_duration_cases'](check, clean, rep1)

def _selftest(_module_globals):
    return _module_globals['selftest_runner'](_module_globals['_selftest_body'], width=50, list_fails=True)
