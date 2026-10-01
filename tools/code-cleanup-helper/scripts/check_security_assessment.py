#!/usr/bin/env python3
"""Validate a closed-world security-assessment receipt without running scanners."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from security_assessment_evaluator import evaluate, input_error_report
from security_assessment_selftest import run_self_test
from security_assessment_shared import MAX_RECEIPT_BYTES, read_bytes_bounded, safe_path
from security_assessment_v2_common import parse_json_object


def _emit(report: dict[str, object], output_format: str) -> int:
    if output_format == "json":
        print(json.dumps(report, ensure_ascii=False))
    else:
        coverage = report["coverage"]
        assert isinstance(coverage, dict)
        print(f"{report['status']}: planned={coverage['plannedTasks']} open={coverage['openFindings']}")
        findings = report["findings"]
        assert isinstance(findings, list)
        for finding in findings:
            assert isinstance(finding, dict)
            print(f"[{finding['status']}] {finding['code']}: {finding['message']}")
    return 0 if report["status"] == "GREEN" else 3 if report["status"] == "NOT_CHECKED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?")
    parser.add_argument("--receipt")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("security assessment self-test passed")
        return 0
    if not args.target or not args.receipt:
        parser.error("target and --receipt are required unless --self-test is used")
    root = Path(args.target).resolve()
    receipt_path, error = safe_path(root, args.receipt)
    if error or receipt_path is None or not receipt_path.is_file() or receipt_path.is_symlink():
        return _emit(input_error_report("receipt-path"), args.format)
    try:
        raw, _identity = read_bytes_bounded(receipt_path, max_bytes=MAX_RECEIPT_BYTES)
        document = parse_json_object(raw)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, RecursionError):
        return _emit(input_error_report("receipt-invalid"), args.format)
    report = evaluate(document, root)
    return _emit(report, args.format)


if __name__ == "__main__":
    raise SystemExit(main())
