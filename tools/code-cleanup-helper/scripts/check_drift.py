#!/usr/bin/env python3
"""Run ID-range and configured fact-drift checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from audit_core import audit_assertions, audit_ids_and_ranges, collect_files, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.target.resolve()
    config, _ = load_config(root, args.config)
    files = collect_files(root, config)
    findings = [item for item in audit_ids_and_ranges(root, files, config) if item.dimension == 8]
    findings.extend(audit_assertions(root, files, config))
    for item in findings:
        location = f" {item.path}:{item.line}" if item.path else ""
        print(f"{item.status} {item.code}{location} — {item.message}")
    return 1 if any(item.status == "FAIL" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
