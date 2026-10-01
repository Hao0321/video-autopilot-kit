#!/usr/bin/env python3
"""Run configured private/public sync checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from audit_core import audit_sync, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.target.resolve()
    config, _ = load_config(root, args.config)
    findings = audit_sync(root, config)
    for item in findings:
        location = f" {item.path}" if item.path else ""
        print(f"{item.status} {item.code}{location} — {item.message}")
    if any(item.status == "FAIL" for item in findings):
        return 1
    return 3 if any(item.status == "NOT_CHECKED" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
