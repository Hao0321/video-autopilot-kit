#!/usr/bin/env python3
"""Run only the local Markdown-link audit."""

from __future__ import annotations

import argparse
from pathlib import Path

from audit_core import audit_links, collect_files, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.target.resolve()
    config, _ = load_config(root, args.config)
    findings = audit_links(root, collect_files(root, config))
    for item in findings:
        location = f" {item.path}:{item.line}" if item.path else ""
        print(f"{item.status} {item.code}{location} — {item.message}")
    return 1 if any(item.status == "FAIL" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
