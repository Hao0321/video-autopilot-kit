# -*- coding: utf-8 -*-
"""Versioned golden contracts and negative-regression cases for video quality.

The corpus stores observable failures, not vague style prompts.  A green test
therefore means known bad patterns stay blocked; it never claims that a machine
can decide whether a finished film is beautiful.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = ROOT.parent / "knowledge" / "runtime" / "quality_corpus.json"


def load_corpus(path: str | Path = DEFAULT_CORPUS) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_corpus(corpus: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    dimensions = corpus.get("dimensions") or {}
    if sum(dimensions.values()) != 100:
        errors.append("dimension weights must sum to 100")
    case_ids = [row.get("id") for key in ("golden_contracts", "negative_cases")
                for row in corpus.get(key, [])]
    if any(not value for value in case_ids):
        errors.append("every case requires an id")
    if len(case_ids) != len(set(case_ids)):
        errors.append("case ids must be unique")
    for row in corpus.get("negative_cases", []):
        if row.get("severity") not in {"BLOCK", "REVIEW"}:
            errors.append("invalid severity for %s" % row.get("id"))
        if not row.get("when"):
            errors.append("negative case %s has no conditions" % row.get("id"))
    return errors


def _matches(signals: dict[str, Any], conditions: dict[str, Any]) -> bool:
    return all(signals.get(key) == expected for key, expected in conditions.items())


def detect_negative(signals: dict[str, Any], corpus: dict[str, Any] | None = None) -> list[dict]:
    corpus = corpus or load_corpus()
    return [
        {"id": row["id"], "severity": row["severity"], "message": row["message"]}
        for row in corpus.get("negative_cases", [])
        if _matches(signals, row["when"])
    ]


def narrative_tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w\u3400-\u9fff]+", str(value or "").lower()))


def narrative_similarity(left: str, right: str) -> float:
    a, b = narrative_tokens(left), narrative_tokens(right)
    return len(a & b) / max(1, len(a | b))


def regression_report(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = corpus or load_corpus()
    errors = validate_corpus(corpus)
    rows: list[dict] = []
    for case in corpus.get("golden_contracts", []):
        hits = detect_negative(case.get("signals") or {}, corpus)
        rows.append({"id": case["id"], "expected": "PASS", "hits": hits})
        if any(hit["severity"] == "BLOCK" for hit in hits):
            errors.append("golden contract blocked: %s" % case["id"])
    for case in corpus.get("negative_cases", []):
        hits = detect_negative(case["when"], corpus)
        caught = any(hit["id"] == case["id"] for hit in hits)
        rows.append({"id": case["id"], "expected": case["severity"], "caught": caught})
        if not caught:
            errors.append("negative case escaped: %s" % case["id"])
    return {"status": "GREEN" if not errors else "RED", "errors": errors, "cases": rows}


def self_test() -> None:
    report = regression_report()
    assert report["status"] == "GREEN", report["errors"]
    assert narrative_similarity("正版 榮耀女武神 決戰", "正版 榮耀女武神 結果") > 0
    assert narrative_similarity("夜景 旅行", "陀螺 對戰") == 0
    print("quality corpus regression GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "regression", "selftest"], nargs="?", default="selftest")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    args = parser.parse_args(argv)
    corpus = load_corpus(args.corpus)
    if args.command == "validate":
        errors = validate_corpus(corpus)
        print(json.dumps({"status": "GREEN" if not errors else "RED", "errors": errors},
                         ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if args.command == "regression":
        report = regression_report(corpus)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "GREEN" else 1
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
