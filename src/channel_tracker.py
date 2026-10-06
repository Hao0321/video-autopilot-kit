# -*- coding: utf-8 -*-
"""Channel publishing state machine (public distribution).

The JSON state stores D2/D7/D28 scheduling and pending actions.  It does not
ship a maintainer state file or maintainer analytics.  Examples in this module
are synthetic and exist only to exercise the public API.

PUBLIC_FIXTURE: channel metrics examples are synthetic.
"""
from __future__ import annotations

import argparse
import sys
import json
import math
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import date, timedelta

_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(os.path.dirname(_DIR), "data", "channel_state.json")
SNAP_WINDOWS = {"D2": 2, "D7": 7, "D28": 28}

# Captures outside [due, due + tolerance] days are stored but excluded from baselines.
CAPTURE_TOLERANCE_DAYS = {"D2": 1, "D7": 2, "D28": 4}
FORMATS = ("shorts", "longform", "live")
LOCK_STALE_SECONDS = 60.0


# ---------------------------------------------------------------- io

def load_state(path: str = STATE_PATH) -> dict:
    """Read a state file; a missing file raises OSError, a broken one ValueError."""
    try:
        with open(path, encoding="utf-8") as f:
            st = json.load(f)
    except ValueError as exc:
        raise ValueError("STATE_CORRUPT: %s is not valid JSON (%s)" % (path, exc)) from exc
    if not isinstance(st, dict) or not all(
            isinstance(st.setdefault(key, []), list) for key in ("videos", "pending_actions")):
        raise ValueError("STATE_CORRUPT: %s is not a channel state object" % path)
    return st


def save_state(st: dict, path: str = STATE_PATH) -> None:
    atomic_write_json(path, st, indent=1)


def atomic_write_json(path, payload, indent: int = 2) -> None:
    """Serialize first, then write a unique temp file beside *path*, fsync and replace."""
    text = json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"
    target = os.path.abspath(os.fspath(path))
    folder = os.path.dirname(target)
    os.makedirs(folder, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + os.path.basename(target) + ".",
                                suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _try_lock(lock: str) -> bool:
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except PermissionError:  # Windows reports a lock that is being deleted this way
        if os.name != "nt":
            raise
        return False
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write("%d %.3f\n" % (os.getpid(), time.time()))
    return True


def _lock_age(lock: str) -> float:
    try:
        return time.time() - os.path.getmtime(lock)
    except OSError:
        return 0.0


def _discard(lock: str) -> None:
    try:
        os.unlink(lock)
    except OSError:
        pass


@contextmanager
def state_lock(path=STATE_PATH, timeout: float = 10.0,
               stale_after: float = LOCK_STALE_SECONDS):
    """Exclusive ``<state>.lock`` file (O_CREAT|O_EXCL) around one read-modify-write.

    A lock older than *stale_after* seconds is treated as left behind by a
    crashed writer and removed; waiting longer than *timeout* raises TimeoutError.
    """
    lock = os.path.abspath(os.fspath(path)) + ".lock"
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    deadline = time.monotonic() + timeout
    while not _try_lock(lock):
        if _lock_age(lock) > stale_after:
            _discard(lock)
            continue
        if time.monotonic() >= deadline:
            raise TimeoutError("state lock busy: %s" % lock)
        time.sleep(0.02)
    try:
        yield lock
    finally:
        _discard(lock)


@contextmanager
def edit_state(path: str = STATE_PATH, timeout: float = 10.0):
    """Locked read-modify-write: yield the loaded state, save it atomically on success."""
    with state_lock(path, timeout=timeout):
        st = load_state(path)
        yield st
        save_state(st, path)


def _d(s: str) -> date:
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


# ---------------------------------------------------------------- core

def add_video(st: dict, name: str, video_id: str, published: str, line: str,
              machine: str = "", fmt: str | None = None) -> dict:
    pub = _d(published)
    if fmt is not None and fmt not in FORMATS:
        raise ValueError("format must be one of %s, got %r" % (FORMATS, fmt))
    vid = str(video_id or "").strip()
    for other in st["videos"]:
        if other.get("name") == name or (vid and str(other.get("video_id") or "").strip() == vid):
            raise ValueError("video %r / id %r is already tracked; update that entry instead"
                             % (name, vid))
    v = {
        "name": name, "video_id": video_id, "published": published,
        "line": line, "format": fmt, "machine": machine,
        "snapshots": {
            w: {"due": (pub + timedelta(days=n)).isoformat(), "done_on": None}
            for w, n in SNAP_WINDOWS.items()
        },
    }
    st["videos"].append(v)
    return v


PLATFORMS = ("yt", "ig", "fb")


def is_metric_number(value) -> bool:
    """Only finite int/float values are metrics; bool, text, NaN and inf are not."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def capture_timing(published, window: str, captured_on) -> str:
    """on_time | early | late | capture_date_unknown | publish_date_unknown."""
    try:
        due = _d(str(published)) + timedelta(days=SNAP_WINDOWS[window])
    except (KeyError, TypeError, ValueError):
        return "publish_date_unknown"
    try:
        captured = _d(str(captured_on))
    except (TypeError, ValueError):
        return "capture_date_unknown"
    if captured < due:
        return "early"
    if (captured - due).days > CAPTURE_TOLERANCE_DAYS[window]:
        return "late"
    return "on_time"


def record_metrics(st: dict, name: str, platform: str, window: str, **kv) -> dict:
    """Store only metrics explicitly supplied by the caller.

    Platforms can have different scales, so missing fields remain absent rather
    than being filled or inferred.  The numbers used by the self-test are
    illustrative fixtures, never copied channel analytics.
    """
    if platform not in PLATFORMS:
        raise AssertionError("platform must be one of %s, got %r" % (PLATFORMS, platform))
    # Keyword captured_on= is the date the values were read (default: today).
    captured_on = kv.pop("captured_on", None)
    if window not in SNAP_WINDOWS:
        raise ValueError("window must be one of %s, got %r" % (tuple(SNAP_WINDOWS), window))
    values = {k: val for k, val in kv.items() if val is not None}
    bad = sorted(k for k, val in values.items() if not is_metric_number(val))
    if bad:
        raise ValueError("metric values must be finite numbers, rejected: %s" % ", ".join(bad))
    captured = _d(str(captured_on)).isoformat() if captured_on else date.today().isoformat()
    for v in st["videos"]:
        if v["name"] == name:
            m = v.setdefault("metrics", {}).setdefault(platform, {})
            entry = m.setdefault(window, {})
            stamps = entry.pop("captured_on", None)
            stamps = stamps if isinstance(stamps, dict) else {}
            entry.update(values)  # merge: a later field never erases earlier ones
            stamps.update(dict.fromkeys(values, captured))
            entry["captured_on"] = stamps
            return entry
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
    by_owner: dict = {}
    for a in st["pending_actions"]:
        if a.get("done"):
            continue
        by_owner.setdefault(str(a.get("owner") or "unassigned"), []).append(a["item"])
        if a.get("due") and _d(a["due"]) <= today:
            due.append("[%s] %s（due %s）" % (a["owner"], a["item"], a["due"]))
    return {"due": due, "upcoming": upcoming, "actions_by_owner": by_owner}


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
    for owner, items in r["actions_by_owner"].items():
        lines.append("[待 %s %d]" % (owner, len(items)))
        lines += ["  - " + x for x in items]
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def _expect_error(check, name, error, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except error as exc:
        check(name, True)
        return exc
    check(name, False)
    return None


def _selftest_metrics(check) -> None:
    """Comparable-outcome inputs: identity, format, window, merge, value type, timing."""
    def day(n: int) -> str:
        return (date(2026, 7, 1) + timedelta(days=n)).isoformat()

    st = {"videos": [], "pending_actions": []}
    add_video(st, "a", "ID-A", day(0), "toy", fmt="shorts")
    add_video(st, "draft-1", "", day(0), "toy")
    add_video(st, "draft-2", "", day(0), "toy")
    check("format stored; omitted format stays unknown",
          st["videos"][0]["format"] == "shorts" and st["videos"][1]["format"] is None)
    _expect_error(check, "duplicate name rejected", ValueError,
                  add_video, st, "a", "ID-B", day(0), "toy")
    _expect_error(check, "duplicate video_id rejected", ValueError,
                  add_video, st, "b", " ID-A ", day(0), "toy")
    _expect_error(check, "unknown format rejected", ValueError,
                  add_video, st, "c", "ID-C", day(0), "toy", fmt="reel")
    _expect_error(check, "window label outside SNAP_WINDOWS rejected", ValueError,
                  record_metrics, st, "a", "yt", "d7", views=1)
    for bad in (True, "1.2k", float("nan"), float("inf")):
        _expect_error(check, "metric value %r rejected" % (bad,), ValueError,
                      record_metrics, st, "a", "yt", "D2", views=bad)
    check("rejected input leaves the state untouched", "metrics" not in st["videos"][0])
    record_metrics(st, "a", "yt", "D2", captured_on=day(2), views=1200, ctr_pct=6.1)
    record_metrics(st, "a", "yt", "D2", captured_on=day(3), retention_pct=44.0)
    entry = st["videos"][0]["metrics"]["yt"]["D2"]
    check("re-recording a window merges instead of erasing earlier fields",
          (entry["views"], entry["ctr_pct"], entry["retention_pct"]) == (1200, 6.1, 44.0))
    check("capture date stored per field",
          entry["captured_on"] == {"views": day(2), "ctr_pct": day(2), "retention_pct": day(3)})
    timing = [capture_timing(day(0), "D7", day(n)) for n in (6, 7, 9, 10)]
    check("capture timing: early / on time / tolerance edge / late",
          timing == ["early", "on_time", "on_time", "late"])
    check("undated capture or publish date is never on time",
          capture_timing(day(0), "D7", None) == "capture_date_unknown"
          and capture_timing("", "D7", day(7)) == "publish_date_unknown")


def _selftest_storage(check) -> None:
    """Atomic save, corrupt/missing state, owner grouping from arbitrary names."""
    with tempfile.TemporaryDirectory(prefix="channel-tracker-test-") as td:
        path = os.path.join(td, "channel_state.json")
        st = {"videos": [], "pending_actions": []}
        add_action(st, "me", "fixture: end card")
        add_action(st, "ai", "fixture: snapshot review")
        save_state(st, path)
        report = due_report(load_state(path), date(2026, 1, 2))
        check("actions grouped by whatever owner names appear",
              report["actions_by_owner"] == {"me": ["fixture: end card"],
                                             "ai": ["fixture: snapshot review"]})
        text = render_report(st, date(2026, 1, 2))
        check("report lists every owner", "[待 me 1]" in text and "[待 ai 1]" in text)
        with open(path, encoding="utf-8") as f:
            good = f.read()
        st["pending_actions"].append({"owner": "me", "item": object(), "due": None})
        _expect_error(check, "unserializable save raises", TypeError, save_state, st, path)
        with open(path, encoding="utf-8") as f:
            intact = f.read() == good
        check("failed save keeps the previous file and leaves no temp file",
              intact and os.listdir(td) == ["channel_state.json"])
        _expect_error(check, "missing state raises OSError", OSError,
                      load_state, os.path.join(td, "missing.json"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(good[: len(good) // 2])
        exc = _expect_error(check, "truncated state raises", ValueError, load_state, path)
        check("truncated state is reported as STATE_CORRUPT", str(exc).startswith("STATE_CORRUPT"))


def _selftest_locking(check) -> None:
    """Locked read-modify-write under concurrency, stale-lock reclaim, busy timeout."""
    import threading
    with tempfile.TemporaryDirectory(prefix="channel-tracker-lock-") as td:
        path = os.path.join(td, "channel_state.json")
        save_state({"videos": [], "pending_actions": []}, path)

        def worker(i: int) -> None:
            for j in range(5):
                with edit_state(path) as cur:
                    add_action(cur, "w%d" % i, "item %d-%d" % (i, j))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        check("locked read-modify-write keeps every concurrent update",
              len(load_state(path)["pending_actions"]) == 20)
        lock = path + ".lock"
        open(lock, "w").close()
        os.utime(lock, (0, time.time() - LOCK_STALE_SECONDS - 5))
        with state_lock(path, timeout=1.0):  # raises TimeoutError if never reclaimed
            pass
        check("stale lock left by a crashed writer is reclaimed", not os.path.exists(lock))
        open(lock, "w").close()

        def busy() -> None:
            with state_lock(path, timeout=0.1):
                pass

        _expect_error(check, "fresh foreign lock blocks with TimeoutError", TimeoutError, busy)
        check("busy lock is left for its owner", os.path.exists(lock))


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
    check("no-due action listed in owner list",
          r3["actions_by_owner"].get(st["pending_actions"][-1]["owner"]) == ["剪 Shorts"])
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
    _selftest_metrics(check)
    _selftest_storage(check)
    _selftest_locking(check)

    # 真實 state 檔存在且可讀可 roundtrip
    # PUBLIC_FIXTURE: no maintainer state file is inspected by public self-tests.
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
    try:
        state = load_state()
    except FileNotFoundError:
        raise SystemExit("STATE_MISSING: %s" % STATE_PATH)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print(render_report(state, today))
