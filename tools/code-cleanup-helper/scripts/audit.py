#!/usr/bin/env python3
"""CLI entrypoint for a full cleanup/repo audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit_core import render_human, run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only, cross-platform code/skill audit.")
    parser.add_argument("target", type=Path)
    parser.add_argument("--mode", choices=("a", "b", "architecture", "all"), default="all")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--max-findings", type=int, default=30)
    parser.add_argument("--strict", action="store_true", help="Exit 1 when FAIL findings exist.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = run_audit(args.target, args.mode, args.config)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_human(report, args.max_findings))
    return 1 if args.strict and report["summary"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
