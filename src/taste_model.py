# -*- coding: utf-8 -*-
"""Pairwise aesthetic preference model (public distribution).

Stores reviewer-owned comparisons and explicit constraints without shipping a maintainer profile.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT.parent / "data" / "taste_model.json"
K = 24.0


def load_state(path: str | Path = STATE_PATH) -> dict:
    target = Path(path)
    if not target.is_file():
        return {"schema_version": 1, "min_comparisons_for_preference": 5, "feature_ratings": {}, "comparisons": [], "summary": {}}
    return json.loads(target.read_text(encoding="utf-8"))


def save_state(state: dict, path: str | Path = STATE_PATH) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    candidate = target.with_suffix(target.suffix + ".candidate")
    candidate.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(candidate, target)


def add_comparison(state: dict, a: dict, b: dict, context: str = "general") -> dict:
    required = {"label", "path", "features"}
    if not required.issubset(a) or not required.issubset(b):
        raise ValueError("each candidate needs label, path and features")
    row = {"id": uuid.uuid4().hex[:12], "context": context, "a": a, "b": b,
           "winner": None, "created_at": datetime.now(timezone.utc).isoformat()}
    state.setdefault("comparisons", []).append(row)
    return row


def _rating(state: dict, feature: str) -> dict:
    return state.setdefault("feature_ratings", {}).setdefault(feature, {"rating": 1000.0, "wins": 0, "losses": 0, "comparisons": 0})


def _update_pair(win: dict, lose: dict) -> None:
    expected = 1.0 / (1.0 + 10.0 ** ((lose["rating"] - win["rating"]) / 400.0))
    delta = K * (1.0 - expected)
    win["rating"] += delta; lose["rating"] -= delta
    win["wins"] += 1; lose["losses"] += 1
    win["comparisons"] += 1; lose["comparisons"] += 1


def vote(state: dict, comparison_id: str, winner: str) -> dict:
    if winner not in {"a", "b", "tie"}: raise ValueError("winner must be a, b or tie")
    row = next((x for x in state.get("comparisons", []) if x["id"] == comparison_id), None)
    if not row: raise KeyError("comparison not found")
    if row.get("winner") is not None: raise RuntimeError("comparison already voted")
    row["winner"] = winner; row["voted_at"] = datetime.now(timezone.utc).isoformat()
    a_features = [str(x) for x in row["a"].get("features", [])]
    b_features = [str(x) for x in row["b"].get("features", [])]
    if winner == "tie":
        for feature in set(a_features + b_features): _rating(state, feature)["comparisons"] += 1
    else:
        win_features, lose_features = (a_features, b_features) if winner == "a" else (b_features, a_features)
        for wf in win_features:
            for lf in lose_features:
                if wf != lf: _update_pair(_rating(state, wf), _rating(state, lf))
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
    threshold = int(state.get("min_comparisons_for_preference", 5))
    eligible = [(name, row) for name, row in state.get("feature_ratings", {}).items()
                if row.get("comparisons", 0) >= threshold]
    eligible.sort(key=lambda item: (-item[1]["rating"], item[0]))
    preferred = [(name, row) for name, row in eligible if row["rating"] > 1000.0]
    avoided = sorted(
        ((name, row) for name, row in eligible if row["rating"] < 1000.0),
        key=lambda item: (item[1]["rating"], item[0]),
    )
    voted = sum(x.get("winner") is not None for x in state.get("comparisons", []))
    state["summary"] = {
        "status": "LEARNED_PREFERENCES" if eligible else "NEEDS_COMPARISONS",
        "voted_pairs": voted,
        "top_preferences": [{"feature": name, "rating": round(row["rating"], 2), "n": row["comparisons"]} for name, row in preferred[:8]],
        "avoid_preferences": [{"feature": name, "rating": round(row["rating"], 2), "n": row["comparisons"]} for name, row in avoided[:5]],
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


def _selftest() -> None:
    state = {"schema_version": 1, "min_comparisons_for_preference": 2, "feature_ratings": {}, "comparisons": [], "summary": {}}
    a = {"label": "A", "path": "a.png", "features": ["bright_editorial", "strong_hierarchy"]}
    b = {"label": "B", "path": "b.png", "features": ["generic_grid", "weak_hierarchy"]}
    for _ in range(2):
        row = add_comparison(state, a, b, "shorts"); vote(state, row["id"], "a")
    constraint = record_constraint(
        state, "icon-flat", scope="icon", rule="icons stay flat and monochrome",
        score=100, kind="requirement", evidence="explicit fixture",
    )
    assert constraint["support"] == 1 and state["summary"]["hard_constraints"]
    assert state["summary"]["status"] == "LEARNED_PREFERENCES"
    assert state["summary"]["top_preferences"][0]["rating"] > 1000
    try: vote(state, row["id"], "a"); raise AssertionError("duplicate vote accepted")
    except RuntimeError: pass
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
