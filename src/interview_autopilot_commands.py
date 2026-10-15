"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations

def _selftest(_host) -> int:
    """只驗純函式（render/build_docs/包裝/日期/路徑），不寫任何 _planning 目錄。"""
    from interview_gate import selftest_runner   # 共用 PASS/FAIL 外殼（含 fallback）

    def body(check):
        prof = dict(_host['PROFILE_DEFAULTS'])            # 未填 profile 的情境（kit 預設）
        guest = dict(ep="00", name="小明", one_line="兩個月做出上架的 App",
                     achievements=[("下載 5,000", "來賓提供後台截圖")],
                     links=["https://example.com"], start_state="完全不會寫程式",
                     struggle="卡在上架審核", demo="用 AI 生成一個小工具",
                     audience="你的短文平台", screenshots_ok=["後台截圖 下載 5,000"])

        pk_unsigned = _host['_packaging_block']("00", guest["one_line"], guest["start_state"],
                                       "下載 5,000", guest["demo"], "示範主題")
        pk = _host['_packaging_block']("00", guest["one_line"], guest["start_state"],
                              "下載 5,000", guest["demo"], "示範主題",
                              compliance_ok=True)

        docs = _host['build_docs']("00", guest, "2026-01-01", "2026-01-08", pk, prof)
        _host['_check_interview_documents'](check, docs)

        inv = _host['build_invite']("00", "小明", "用 AI 做出一個 App", prof)
        check("invite renders 3 versions",
              all(v in inv for v in ("版本 A", "版本 B", "版本 C")) and "((" not in inv)
        check("invite embeds intake sheet", "來賓資訊表" in inv and "一句話怎麼說" in inv)
        check("invite has no hardcoded show identity",
              "{你的節目名}" in inv and "{你的頻道}" in inv)

        try:                                   # 少給欄位一定要擋（不准交出帶 (( )) 的檔）
            _host['render']("consent_form", EP="00")
            check("missing field blocked", False)
        except AssertionError:
            check("missing field blocked", True)

        if _host['gate_plan'] is None:
            print("[SKIP] plan_gate 不在 → 包裝先行未機械驗證（gate 相關 4 項未跑）")
        else:
            ok, rep = _host['gate_plan'](pk)
            check("packaging passes plan_gate (human-signed)", ok)
            check("packaging has >=8 pairs", rep["pairs"] >= 8)
            # 合規章只能人蓋：沒 --compliance-ok 一定要被 P4 擋（防機器自簽假綠）
            ok0, rep0 = _host['gate_plan'](pk_unsigned)
            check("unsigned compliance -> blocked by plan_gate P4",
                  (not ok0) and any("P4" in f for f in rep0["fails"]))
            check("unsigned text says pending-review, not passed",
                  "待複核" in pk_unsigned and "合規：通過" not in pk_unsigned)
            check("no loser combo warn (W2)",
                  not any(w.startswith("W2") for w in rep["warns"]))

        r, p = _host['_dates'](None, None)
        check("default dates: record +7 / publish +14",
              r == (_host['date'].today() + _host['timedelta'](days=7)).isoformat()
              and p == (_host['date'].today() + _host['timedelta'](days=14)).isoformat())
        r2, p2 = _host['_dates']("2026-03-01", None)
        check("explicit record shifts publish", (r2, p2) == ("2026-03-01", "2026-03-08"))

        check("_slug strips non-ascii", _host['_slug']("小 明/測*試 Ming") == "Ming")
        check("ep_dir ascii with latin name",
              _host['ep_dir']("07", "Ming").endswith("interview_EP07_Ming"))
        check("ep_dir stays ascii with cjk name",
              _host['ep_dir']("07", "小明").endswith("interview_EP07")
              and _host['ep_dir']("07", "小明").isascii())

        check("profile parser reads filled values",
              _host['_parse_profile']("SHOW_NAME: 我的節目\n## OUTRO_LINES\n```\n下次見\n```\n")
              == {"SHOW_NAME": "我的節目", "OUTRO_LINES": "下次見"})
        check("profile parser ignores blanks",
              _host['_parse_profile']("SHOW_NAME: ______\nCHANNEL: `____`\n") == {})

    return selftest_runner(body, width=56)


def main(_host):
    if "--selftest" in _host['sys'].argv:
        return _host['_selftest']()
    try:  # cp950 終端印到罕見符號不炸
        _host['sys'].stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = _host['argparse'].ArgumentParser(
        description="線上訪談節目一鍵流程（invite -> plan -> build）")
    ap.add_argument("cmd", choices=["invite", "plan", "build"])
    ap.add_argument("ep")
    ap.add_argument("--name", default="來賓")
    ap.add_argument("--hint", default="", help="你看到他做到什麼（會寫進邀約訊息）")
    ap.add_argument("--record", default=None, help="錄製日 YYYY-MM-DD（預設今天+7）")
    ap.add_argument("--publish", default=None, help="發布日 YYYY-MM-DD（預設錄製日+7）")
    ap.add_argument("--compliance-ok", action="store_true",
                    help="人工簽章：已跑過平台 AI 內容政策 checklist。"
                         "不給這個旗標 = plan_gate P4 擋下（程式不代簽）")
    a = ap.parse_args()
    try:
        if a.cmd == "invite":
            _host['invite'](a.ep, a.name, a.hint)
        elif a.cmd == "plan":
            _host['plan'](a.ep, a.record, a.publish, compliance_ok=a.compliance_ok)
        else:
            _host['build'](a.ep)
    except AssertionError as e:      # 閘門擋下 = 正常結果，不是 crash：印訊息就好
        print("\n[GATE FAIL] %s" % e)
        return 1
    return 0
