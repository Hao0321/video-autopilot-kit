# -*- coding: utf-8 -*-
"""Pairwise aesthetic preference model (public distribution).

Stores reviewer-owned comparisons and explicit constraints without shipping a maintainer profile.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import json
import math
import os
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from channel_tracker import atomic_write_json, state_lock


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT.parent / "data" / "taste_model.json"
K = 24.0
# One-sided 95% Wilson bound: a feature is preferred (avoided) only when the lower
# (upper) bound of its decisive win rate clears 0.5 after the minimum vote count.
PREFERENCE_Z = 1.645


def load_state(path: str | Path = STATE_PATH) -> dict:
    target = Path(path)
    if not target.is_file():
        return {"schema_version": 1, "min_comparisons_for_preference": 5, "feature_ratings": {}, "comparisons": [], "summary": {}}
    return json.loads(target.read_text(encoding="utf-8"))


def save_state(state: dict, path: str | Path = STATE_PATH) -> None:
    atomic_write_json(path, state, indent=2)


def _side(row: dict, key: str) -> dict:
    side = row.get(key)
    return side if isinstance(side, dict) else {}


def _media(side: dict) -> str:
    return os.path.normcase(os.path.normpath(str(side.get("path", ""))))


def _comparison_key(row: dict) -> tuple:
    """Same context and same media pair (in either order) is one comparison."""
    paths = sorted(_media(_side(row, key)) for key in ("a", "b"))
    return str(row.get("context", "general")), tuple(paths)


def add_comparison(state: dict, a: dict, b: dict, context: str = "general") -> dict:
    required = {"label", "path", "features"}
    if not required.issubset(a) or not required.issubset(b):
        raise ValueError("each candidate needs label, path and features")
    row = {"id": uuid.uuid4().hex[:12], "context": context, "a": a, "b": b,
           "winner": None, "created_at": datetime.now(timezone.utc).isoformat()}
    key = _comparison_key(row)
    if key[1][0] == key[1][1]:
        raise ValueError("a comparison needs two different media paths")
    existing = next((x for x in state.get("comparisons", [])
                     if isinstance(x, dict) and _comparison_key(x) == key), None)
    if existing is not None:
        if _media(_side(existing, "a")) != _media(a):
            raise ValueError("comparison %s already holds this pair with sides swapped"
                             % existing.get("id"))
        return existing  # idempotent: an identical pair can only ever be voted once
    state.setdefault("comparisons", []).append(row)
    return row


def _rating(ratings: dict, feature: str) -> dict:
    return ratings.setdefault(feature, {"rating": 1000.0, "wins": 0, "losses": 0,
                                        "votes": 0, "ties": 0, "comparisons": 0})


def _features(row: dict, key: str) -> set:
    features = _side(row, key).get("features")
    return {str(x) for x in features} if isinstance(features, list) else set()


def _exclusive_features(row: dict) -> tuple[set, set]:
    """Features shown on only one side; a feature on both sides carries no contrast."""
    a, b = _features(row, "a"), _features(row, "b")
    return a - b, b - a


def _apply_vote(ratings: dict, winners: set, losers: set) -> None:
    """One decisive vote: each exclusive feature counts once; K is split over |A|*|B| pairs."""
    scale = K / (len(winners) * len(losers)) if winners and losers else 0.0
    delta: dict = defaultdict(float)
    for wf in winners:
        for lf in losers:
            gap = (_rating(ratings, lf)["rating"] - _rating(ratings, wf)["rating"]) / 400.0
            change = scale * (1.0 - 1.0 / (1.0 + 10.0 ** gap))
            delta[wf] += change
            delta[lf] -= change
    for feature, outcome in [(f, "wins") for f in winners] + [(f, "losses") for f in losers]:
        row = _rating(ratings, feature)
        row["rating"] += delta[feature]
        row[outcome] += 1
        row["votes"] += 1
        row["comparisons"] += 1


def _replay(state: dict) -> tuple[dict, int]:
    """Rebuild feature ratings from the vote log; ties never count as votes."""
    ratings: dict = {}
    seen, duplicates = set(), 0
    voted = [x for x in state.get("comparisons", [])
             if isinstance(x, dict) and x.get("winner") in ("a", "b", "tie")]
    for row in sorted(voted, key=lambda x: str(x.get("voted_at") or "")):
        key = _comparison_key(row)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        a_only, b_only = _exclusive_features(row)
        if row["winner"] == "tie":
            for feature in a_only | b_only:
                _rating(ratings, feature)["ties"] += 1
                _rating(ratings, feature)["comparisons"] += 1
        else:
            winners, losers = (a_only, b_only) if row["winner"] == "a" else (b_only, a_only)
            _apply_vote(ratings, winners, losers)
    return ratings, duplicates


def _wilson(wins: int, n: int, z: float = PREFERENCE_Z) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    p = wins / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - spread) / (1 + z * z / n), (centre + spread) / (1 + z * z / n)


def vote(state: dict, comparison_id: str, winner: str) -> dict:
    if winner not in {"a", "b", "tie"}: raise ValueError("winner must be a, b or tie")
    row = next((x for x in state.get("comparisons", []) if x.get("id") == comparison_id), None)
    if not row: raise KeyError("comparison not found")
    if row.get("winner") is not None: raise RuntimeError("comparison already voted")
    row["winner"] = winner; row["voted_at"] = datetime.now(timezone.utc).isoformat()
    summarize(state)
    return row


def record_constraint(state: dict, constraint_id: str, *, scope: str, rule: str,
                      score: float, kind: str, evidence: str) -> dict:
    """Record an explicit reviewer constraint without inventing a pairwise comparison.

    PUBLIC_FIXTURE: the caller supplies its own rule, score and evidence.
    """
    if not constraint_id.strip() or not rule.strip() or not evidence.strip():
        raise ValueError("constraint id, rule and evidence are required")
    if kind not in {"requirement", "rejection"}:
        raise ValueError("constraint kind must be requirement or rejection")
    if not 0 <= float(score) <= 100:
        raise ValueError("constraint score must be between 0 and 100")
    rows = state.setdefault("explicit_constraints", [])
    row = next((item for item in rows if item.get("id") == constraint_id), None)
    now = datetime.now(timezone.utc).isoformat()
    if row is None:
        row = {"id": constraint_id, "created_at": now, "support": 0}
        rows.append(row)
    row.update(scope=scope, rule=rule, score=float(score), kind=kind,
               evidence=evidence, updated_at=now, support=int(row.get("support", 0)) + 1)
    summarize(state)
    return row


def summarize(state: dict) -> dict:
    """Preferred/avoided needs the minimum distinct decisive votes AND a confident margin."""
    threshold = max(1, int(state.get("min_comparisons_for_preference", 5)))
    ratings, duplicates = _replay(state)
    logged = set()
    for row in state.get("comparisons", []):
        if isinstance(row, dict):
            logged |= _features(row, "a") | _features(row, "b")
    previous = state.get("feature_ratings")
    # The vote log owns every logged feature; rows outside it are kept but never eligible.
    kept = {k: v for k, v in previous.items() if k not in logged} if isinstance(previous, dict) else {}
    state["feature_ratings"] = {**kept, **ratings}
    preferred, avoided, undecided = [], [], []
    for name, row in ratings.items():
        if row["votes"] < threshold:
            continue
        low, high = _wilson(row["wins"], row["votes"])
        entry = {"feature": name, "rating": round(row["rating"], 2), "n": row["votes"],
                 "wins": row["wins"], "losses": row["losses"],
                 "win_rate_bounds": [round(low, 3), round(high, 3)]}
        (preferred if low > 0.5 else avoided if high < 0.5 else undecided).append(entry)
    preferred.sort(key=lambda item: (-item["rating"], item["feature"]))
    avoided.sort(key=lambda item: (item["rating"], item["feature"]))
    undecided.sort(key=lambda item: (-item["n"], item["feature"]))
    voted = sum(isinstance(x, dict) and x.get("winner") is not None for x in state.get("comparisons", []))
    state["summary"] = {
        "status": ("LEARNED_PREFERENCES" if preferred or avoided
                   else "NO_CLEAR_PREFERENCE" if undecided else "NEEDS_COMPARISONS"),
        "voted_pairs": voted,
        "ignored_duplicate_votes": duplicates,
        "min_votes": threshold, "confidence_z": PREFERENCE_Z,
        "top_preferences": preferred[:8],
        "avoid_preferences": avoided[:5],
        "no_clear_preference": undecided[:8],
        "hard_constraints": [
            {key: row.get(key) for key in ("id", "scope", "rule", "score", "kind", "support")}
            for row in state.get("explicit_constraints", [])
        ],
    }
    return state["summary"]


def build_review(state: dict, output: str | Path) -> Path:
    pending = [x for x in state.get("comparisons", []) if x.get("winner") is None]
    cards = []
    for row in pending:
        sides = []
        for key in ("a", "b"):
            item = row[key]; path = Path(item["path"]).resolve(); suffix = path.suffix.lower()
            media = (f"<video controls src='{path.as_uri()}'></video>" if suffix in {'.mp4','.mov','.webm'}
                     else f"<img src='{path.as_uri()}'>")
            sides.append(f"<section><h3>{key.upper()} · {html.escape(item['label'])}</h3>{media}<p>{html.escape(', '.join(item['features']))}</p></section>")
        cards.append(f"<article><h2>{row['id']} · {html.escape(row['context'])}</h2><div class='pair'>{''.join(sides)}</div><p>投票指令：<code>python taste_model.py vote {row['id']} a|b|tie</code></p></article>")
    doc = "<!doctype html><meta charset='utf-8'><style>body{font-family:system-ui;background:#101116;color:#f6f6f2;margin:24px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}img,video{width:100%;max-height:65vh;object-fit:contain;background:#000}article{border-bottom:1px solid #555;padding-bottom:28px}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>creator Taste Pairwise Lab</h1>" + ("".join(cards) or "<p>目前沒有待比較項目。</p>")
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(doc, encoding="utf-8"); return out


def _fresh_state() -> dict:
    return {"schema_version": 1, "min_comparisons_for_preference": 5, "feature_ratings": {}, "comparisons": [], "summary": {}}


def _vote_pair(state: dict, a_features: list, b_features: list, winner: str, tag: str) -> dict:
    row = add_comparison(state, {"label": "A", "path": "a-%s.png" % tag, "features": a_features},
                         {"label": "B", "path": "b-%s.png" % tag, "features": b_features})
    return vote(state, row["id"], winner)


def _selftest_vote_rules() -> None:
    s = _fresh_state()
    _vote_pair(s, ["neon_glow"], ["f1", "f2", "f3", "f4", "f5"], "a", "one")
    glow = s["feature_ratings"]["neon_glow"]
    assert s["summary"]["status"] == "NEEDS_COMPARISONS" and not s["summary"]["top_preferences"]
    assert glow["votes"] == 1 and abs(glow["rating"] - (1000 + K / 2)) < 1e-9, "K split over 1x5 pairs"
    s = _fresh_state()
    for i in range(5):
        _vote_pair(s, ["x"], ["y"], "tie", "tie%d" % i)
    assert s["summary"]["status"] == "NEEDS_COMPARISONS" and s["feature_ratings"]["x"]["votes"] == 0
    for order in ("ababab", "bababa"):
        s = _fresh_state()
        for i, winner in enumerate(order):
            _vote_pair(s, ["x"], ["y"], winner, "split%d" % i)
        summary = s["summary"]
        assert summary["status"] == "NO_CLEAR_PREFERENCE", order
        assert not summary["top_preferences"] and not summary["avoid_preferences"], order
    s = _fresh_state()
    _vote_pair(s, ["x", "shared"], ["y", "shared"], "a", "shared")
    assert "shared" not in s["feature_ratings"], "a feature on both sides is not rated"
    s = _fresh_state()
    first = _vote_pair(s, ["x"], ["y"], "a", "same")
    again = add_comparison(s, {"label": "A", "path": "a-same.png", "features": ["x"]},
                           {"label": "B", "path": "b-same.png", "features": ["y"]})
    assert again["id"] == first["id"] and len(s["comparisons"]) == 1
    try: vote(s, again["id"], "a"); raise AssertionError("re-added identical pair voted twice")
    except RuntimeError: pass
    try:
        add_comparison(s, {"label": "B", "path": "b-same.png", "features": ["y"]},
                       {"label": "A", "path": "a-same.png", "features": ["x"]})
        raise AssertionError("swapped duplicate accepted")
    except ValueError: pass
    s["comparisons"] += [dict(first, id="dup%d" % i) for i in range(4)]  # legacy duplicate rows
    assert summarize(s)["ignored_duplicate_votes"] == 4 and s["feature_ratings"]["x"]["votes"] == 1


def _selftest_legacy_state() -> None:
    state = _fresh_state()
    row = add_comparison(state, {"label": "A", "path": "a.png", "features": ["neon_glow", "shared"]},
                         {"label": "B", "path": "b.png", "features": ["f1", "shared"]})
    row["winner"] = "a"  # voted by an older build that cached inflated pair counts
    state["feature_ratings"] = {"neon_glow": {"rating": 1056.0, "comparisons": 5},
                                "shared": {"rating": 1000.4, "comparisons": 2},
                                "imported_only": {"rating": 1200.0, "comparisons": 9}}
    summary, ratings = summarize(state), state["feature_ratings"]
    assert summary["status"] == "NEEDS_COMPARISONS" and not summary["top_preferences"]
    assert ratings["neon_glow"]["votes"] == 1 and "shared" not in ratings
    assert ratings["imported_only"] == {"rating": 1200.0, "comparisons": 9}, "kept, never eligible"


def _selftest_concurrency() -> None:
    import threading
    with tempfile.TemporaryDirectory(prefix="taste-lock-test-") as td:
        path, errors = Path(td) / "taste_model.json", []

        def locked(i: int) -> None:
            for j in range(10):
                with state_lock(path):
                    st = load_state(path)
                    st["comparisons"].append({"id": "%d-%d" % (i, j), "pad": "x" * 2000})
                    save_state(st, path)

        def unlocked(i: int) -> None:
            for _ in range(10):
                try:
                    save_state({"comparisons": [], "pad": "y" * 3000 * (i + 1)}, path)
                except OSError as exc:  # Windows may refuse a concurrent replace
                    errors.append(exc)

        for target in (locked, unlocked):
            threads = [threading.Thread(target=target, args=(i,)) for i in range(4)]
            for t in threads: t.start()
            for t in threads: t.join()
            if target is locked:
                assert len(load_state(path)["comparisons"]) == 40, "locked writers lose no update"
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
        assert sorted(p.name for p in Path(td).iterdir()) == ["taste_model.json"], "no temp leftovers"
        assert not errors or os.name == "nt", errors


def _selftest() -> None:
    state = _fresh_state()
    for i in range(5):
        a = {"label": "A", "path": "a%d.png" % i, "features": ["bright_editorial", "strong_hierarchy"]}
        b = {"label": "B", "path": "b%d.png" % i, "features": ["generic_grid", "weak_hierarchy"]}
        row = add_comparison(state, a, b, "shorts"); vote(state, row["id"], "a")
    constraint = record_constraint(
        state, "icon-flat", scope="icon", rule="icons stay flat and monochrome",
        score=100, kind="requirement", evidence="explicit fixture",
    )
    assert constraint["support"] == 1 and state["summary"]["hard_constraints"]
    assert state["summary"]["status"] == "LEARNED_PREFERENCES"
    assert state["summary"]["top_preferences"][0]["rating"] > 1000
    assert {x["feature"] for x in state["summary"]["avoid_preferences"]} == {"generic_grid", "weak_hierarchy"}
    try: vote(state, row["id"], "a"); raise AssertionError("duplicate vote accepted")
    except RuntimeError: pass
    _selftest_vote_rules()
    _selftest_legacy_state()
    _selftest_concurrency()
    with tempfile.TemporaryDirectory(prefix="hao-taste-test-") as td:
        save_state(state, Path(td) / "state.json")
    print("taste_model self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    add = sub.add_parser("add"); add.add_argument("a_json"); add.add_argument("b_json"); add.add_argument("--context", default="general")
    vo = sub.add_parser("vote"); vo.add_argument("id"); vo.add_argument("winner", choices=("a","b","tie"))
    constraint = sub.add_parser("constraint")
    constraint.add_argument("--id", required=True); constraint.add_argument("--scope", required=True)
    constraint.add_argument("--rule", required=True); constraint.add_argument("--score", type=float, required=True)
    constraint.add_argument("--kind", choices=("requirement", "rejection"), required=True)
    constraint.add_argument("--evidence", required=True)
    rv = sub.add_parser("review"); rv.add_argument("output")
    sub.add_parser("summary")
    args = ap.parse_args(argv)
    if args.cmd == "selftest": _selftest(); return 0
    writes = args.cmd in {"add", "vote", "constraint"}
    with (state_lock(STATE_PATH) if writes else contextlib.nullcontext()):  # read-modify-write
        state = load_state()
        if args.cmd == "add": result = add_comparison(state, json.loads(args.a_json), json.loads(args.b_json), args.context); save_state(state)
        elif args.cmd == "vote": result = vote(state, args.id, args.winner); save_state(state)
        elif args.cmd == "constraint":
            result = record_constraint(state, args.id, scope=args.scope, rule=args.rule,
                                       score=args.score, kind=args.kind, evidence=args.evidence)
            save_state(state)
        elif args.cmd == "review": result = {"output": str(build_review(state, args.output))}
        else: result = summarize(state)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
