# -*- coding: utf-8 -*-
"""channel_tracker.py — 頻道經營狀態機（懶人自動化中樞，2026-07-24 R4 落地）

單一真理來源 = 同目錄 channel_state.json：
  - videos[]：每支已發布影片的 D2/D7/D28 快照排程與完成狀態（playbook 站6 SOP）
  - pending_actions[]：待辦（owner=hao|claude），到期追蹤

用法：
  python channel_tracker.py                # 今日報告（ASCII-safe console）
  python channel_tracker.py --date 2026-07-29   # 模擬某日
  python channel_tracker.py --selftest

API（session 內 import 用）：
  load_state() / save_state(st)
  due_report(st, today) -> {"due":[...], "upcoming":[...], "actions_hao":[...], "actions_claude":[...]}
  mark_snapshot(st, video_name, window, done_on)   # window in {"D2","D7","D28"}
  add_video(st, name, video_id, published, line)   # 自動排 D2/D7/D28
  add_action(st, owner, item, due=None) / close_action(st, keyword)

規則：快照數據本體寫進 video_log.md（本檔只管「到期了沒」）；跨片對比只准同窗（playbook §1）。
cp950 安全：console 只印 ASCII + 中文（無 emoji）；I/O 一律 utf-8。
"""
from __future__ import annotations

import argparse
import sys
import json
import os
from datetime import date, timedelta

_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(_DIR, "channel_state.json")
SNAP_WINDOWS = {"D2": 2, "D7": 7, "D28": 28}


# ---------------------------------------------------------------- io

def load_state(path: str = STATE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(st: dict, path: str = STATE_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def _d(s: str) -> date:
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


# ---------------------------------------------------------------- core

def add_video(st: dict, name: str, video_id: str, published: str, line: str,
              machine: str = "") -> dict:
    pub = _d(published)
    v = {
        "name": name, "video_id": video_id, "published": published,
        "line": line, "machine": machine,
        "snapshots": {
            w: {"due": (pub + timedelta(days=n)).isoformat(), "done_on": None}
            for w, n in SNAP_WINDOWS.items()
        },
    }
    st["videos"].append(v)
    return v


PLATFORMS = ("yt", "ig", "fb")


def record_metrics(st: dict, name: str, platform: str, window: str, **kv) -> dict:
    """記一支片在某平台某窗口的真實後台數字。

    為什麼要多平台（2026-08-02 三平台後台實測）：同一支片
    YT 1,735 / IG 219 / FB 7 —— **量級差兩個數量級**。只追 YT 會
    誤以為 IG/FB 沒數據，實際是有數據且數據在說「別花力氣在那」。

    只存看得到的欄位（M10）：沒截到的就不填，不補零、不推估。
    """
    if platform not in PLATFORMS:
        raise AssertionError("platform must be one of %s, got %r" % (PLATFORMS, platform))
    for v in st["videos"]:
        if v["name"] == name:
            m = v.setdefault("metrics", {}).setdefault(platform, {})
            m[window] = {k: val for k, val in kv.items() if val is not None}
            return m[window]
    raise AssertionError("video %r not in state -- add_video() first" % name)


def platform_table(st: dict, window: str = "D2") -> list:
    """跨平台對照表 [(name, {platform: views})]，用來看『力氣該花在哪』。"""
    rows = []
    for v in st["videos"]:
        mt = v.get("metrics") or {}
        got = {p: (mt.get(p, {}).get(window) or {}).get("views") for p in PLATFORMS}
        if any(x is not None for x in got.values()):
            rows.append((v["name"], got))
    return rows


def mark_snapshot(st: dict, video_name: str, window: str, done_on: str) -> bool:
    for v in st["videos"]:
        if v["name"] == video_name and window in v["snapshots"]:
            v["snapshots"][window]["done_on"] = done_on
            return True
    return False


def add_action(st: dict, owner: str, item: str, due: str = None) -> None:
    st["pending_actions"].append(
        {"owner": owner, "item": item, "due": due, "done": False})


def close_action(st: dict, keyword: str) -> int:
    n = 0
    for a in st["pending_actions"]:
        if not a.get("done") and keyword in a["item"]:
            a["done"] = True
            n += 1
    return n


def due_report(st: dict, today: date) -> dict:
    due, upcoming = [], []
    horizon = today + timedelta(days=7)
    for v in st["videos"]:
        for w, snap in sorted(v["snapshots"].items(),
                              key=lambda kv: SNAP_WINDOWS[kv[0]]):
            if snap["done_on"] or snap.get("waived"):
                continue
            dd = _d(snap["due"])
            entry = "%s %s 快照（due %s）" % (v["name"], w, snap["due"])
            if dd <= today:
                due.append(entry)
            elif dd <= horizon:
                upcoming.append(entry)
    for a in st["pending_actions"]:
        if a.get("done"):
            continue
        if a.get("due") and _d(a["due"]) <= today:
            due.append("[%s] %s（due %s）" % (a["owner"], a["item"], a["due"]))
    return {
        "due": due,
        "upcoming": upcoming,
        "actions_hao": [a["item"] for a in st["pending_actions"]
                        if not a.get("done") and a.get("owner") == "hao"],
        "actions_claude": [a["item"] for a in st["pending_actions"]
                           if not a.get("done") and a.get("owner") == "claude"],
    }


def render_report(st: dict, today: date) -> str:
    r = due_report(st, today)
    lines = ["=== 頻道經營巡檢 %s ===" % today.isoformat()]
    if r["due"]:
        lines.append("[DUE 今日到期 %d]" % len(r["due"]))
        lines += ["  - " + x for x in r["due"]]
    else:
        lines.append("[DUE] 今日無到期事項")
    if r["upcoming"]:
        lines.append("[UPCOMING 7 天內]")
        lines += ["  - " + x for x in r["upcoming"]]
    if r["actions_hao"]:
        lines.append("[待 owner %d]" % len(r["actions_hao"]))
        lines += ["  - " + x for x in r["actions_hao"]]
    if r["actions_claude"]:
        lines.append("[待 Claude %d]" % len(r["actions_claude"]))
        lines += ["  - " + x for x in r["actions_claude"]]
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def _selftest() -> int:
    fails = []

    def check(name, cond):
        print("[%s] %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            fails.append(name)

    st = {"videos": [], "pending_actions": []}
    add_video(st, "測試片", "abc123", "2026-07-01", "AI教學")
    check("add_video schedules 3 windows",
          set(st["videos"][0]["snapshots"]) == {"D2", "D7", "D28"})
    check("D7 due computed", st["videos"][0]["snapshots"]["D7"]["due"] == "2026-07-08")

    r = due_report(st, date(2026, 7, 8))
    check("D2+D7 due on day7", len(r["due"]) == 2)
    check("D28 upcoming not due", not any("D28" in x for x in r["due"]))

    mark_snapshot(st, "測試片", "D2", "2026-07-03")
    mark_snapshot(st, "測試片", "D7", "2026-07-08")
    r2 = due_report(st, date(2026, 7, 8))
    check("done snapshots drop out", len(r2["due"]) == 0)

    add_action(st, "hao", "錄旁白", due="2026-07-05")
    add_action(st, "claude", "剪 Shorts")
    r3 = due_report(st, date(2026, 7, 8))
    check("overdue action listed in due", any("錄旁白" in x for x in r3["due"]))
    check("no-due action listed in owner list", "剪 Shorts" in r3["actions_claude"])
    check("close_action works", close_action(st, "錄旁白") == 1)

    rep = render_report(st, date(2026, 7, 8))
    check("report renders", "頻道經營巡檢" in rep and "DUE" in rep)

    # 多平台 metrics（2026-08-02）—— 雙向都要測：能存、也要擋得住壞輸入
    record_metrics(st, "測試片", "yt", "D2", views=100, retention_pct=31.1)
    record_metrics(st, "測試片", "ig", "D2", views=10, saves=None)
    check("metrics stored per platform",
          st["videos"][0]["metrics"]["yt"]["D2"]["views"] == 100)
    check("None fields dropped, not stored as null",
          "saves" not in st["videos"][0]["metrics"]["ig"]["D2"])
    try:
        record_metrics(st, "測試片", "tiktok", "D2", views=1)
        bad_platform_rejected = False
    except AssertionError:
        bad_platform_rejected = True
    check("unknown platform raises (not silent)", bad_platform_rejected)
    try:
        record_metrics(st, "不存在的片", "yt", "D2", views=1)
        missing_video_rejected = False
    except AssertionError:
        missing_video_rejected = True
    check("unknown video raises (not silent)", missing_video_rejected)
    tbl = platform_table(st, "D2")
    check("platform_table pairs platforms",
          tbl and tbl[0][1]["yt"] == 100 and tbl[0][1]["ig"] == 10
          and tbl[0][1]["fb"] is None)

    # 真實 state 檔存在且可讀可 roundtrip
    if os.path.isfile(STATE_PATH):
        real = load_state()
        check("real state loads", "videos" in real and "pending_actions" in real)
        check("real state has longform03 D7",
              any(v["name"] == "長片03" and v["snapshots"]["D7"]["due"] == "2026-07-29"
                  for v in real["videos"]))
    print("-" * 50)
    if fails:
        print("SELFTEST RED: %d failed" % len(fails))
        return 1
    print("SELFTEST GREEN: all checks passed")
    return 0


if __name__ == "__main__":
    try:  # cp950 終端印 ≥/× 等符號不炸（M102 家族）
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    today = _d(args.date) if args.date else date.today()
    print(render_report(load_state(), today))
