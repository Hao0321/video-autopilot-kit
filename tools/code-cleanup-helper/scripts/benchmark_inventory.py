#!/usr/bin/env python3
"""Compare inventory algorithms on one owned excluded-tree fixture, not whole audits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
from audit_core import TEXT_EXTENSIONS, collect_files, deep_merge, DEFAULT_CONFIG, is_excluded


def legacy_inventory(root: Path, config: dict) -> list[Path]:
    """The prior rglob algorithm retained as a benchmark oracle, never a runtime path."""
    files = []
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            path.resolve().relative_to(resolved_root)
        except ValueError:
            continue
        relative = path.relative_to(root).as_posix()
        if not is_excluded(relative, config["exclude"]):
            files.append(path)
    return sorted(files)


def benchmark() -> dict:
    config = deep_merge(DEFAULT_CONFIG, {"exclude": ["**/node_modules/**", "dist/**"]})
    with tempfile.TemporaryDirectory(prefix="cleanup-inventory-bench-") as raw:
        root = Path(raw)
        for folder, count in [("src", 160), ("node_modules", 3200), ("dist", 1600)]:
            for index in range(count):
                path = root / folder / str(index // 80) / f"file{index}.py"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"value = 1\n")
        expected = legacy_inventory(root, config)
        assert collect_files(root, config) == expected
        samples = {"legacy": [], "pruned": []}
        for round_id in range(9):
            order = [("legacy", legacy_inventory), ("pruned", collect_files)]
            for name, function in order if round_id % 2 == 0 else reversed(order):
                started = time.perf_counter_ns()
                actual = function(root, config)
                elapsed = (time.perf_counter_ns() - started) / 1e6
                assert actual == expected, "included-file parity changed during measurement"
                samples[name].append(round(elapsed, 3))
        legacy, candidate = (statistics.median(samples[k]) for k in ("legacy", "pruned"))
        identity = "\n".join(p.relative_to(root).as_posix() for p in expected)
        return {"schema_version": 1, "status": "PASS" if candidate < legacy else "INCONCLUSIVE",
                "scope": "owned 4960-file warm-cache inventory fixture only; excludes 4800 files",
                "included_files": len(expected), "included_set_sha256": hashlib.sha256(identity.encode()).hexdigest(),
                "interleaved_rounds": 9, "samples_ms": samples,
                "median_ms": {"legacy": legacy, "pruned": candidate},
                "speedup": round(legacy / candidate, 3),
                "environment": {"python": platform.python_version(), "platform": platform.platform()},
                "implementation_sha256": hashlib.sha256(Path(__file__).with_name("audit_core.py").read_bytes()).hexdigest(),
                "limitations": "Not a claim about whole-audit latency, cold caches, or other file distributions"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = benchmark()
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.buffer.write(payload.encode("utf-8"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
