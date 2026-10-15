"""Inventory scope and multilingual machine-output regressions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from audit_core import DEFAULT_CONFIG, collect_files, deep_merge, is_excluded, TEXT_EXTENSIONS


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-inventory-") as raw:
        root = Path(raw) / "project"
        paths = ["main.py", "src/index.ts", "src/one/node_modules/lib/a.js",
                 "node_modules/deep/module.js", "dist/output.js", "not_node_modules/keep.js",
                 "src/not-dist/keep.ts", "src/a/cache/hidden.py", "cache/visible.py",
                 "source.map", "src/readme.md", "src/image.png"]
        for name in paths:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        config = deep_merge(DEFAULT_CONFIG, {"exclude": ["**/node_modules/**", "dist/**", "src/*/cache/**"]})
        expected = sorted(path for path in root.rglob("*")
                          if path.is_file() and path.suffix in TEXT_EXTENSIONS
                          and not is_excluded(path.relative_to(root).as_posix(), config["exclude"]))
        scanned: list[Path] = []
        original = os.scandir

        def observe(path: str):
            scanned.append(Path(path))
            return original(path)

        with patch("os.scandir", side_effect=observe):
            actual = collect_files(root, config)
        assert actual == expected, "pruning changed included-file semantics"
        assert not any(p.name in {"node_modules", "dist"} for p in scanned), "excluded tree was enumerated"
        assert root / "not_node_modules/keep.js" in actual, "near-miss folder was pruned"
        assert root / "cache/visible.py" in actual, "scoped exclusion became global"

        unicode_root = root / "工程-Ω"
        unicode_root.mkdir()
        (unicode_root / "顯示.py").write_text("value = 1\n", encoding="utf-8")
        child = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).with_name("audit.py")),
             str(unicode_root), "--mode", "architecture", "--format", "json"],
            capture_output=True, check=False, timeout=30,
            env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252"},
        )
        assert child.returncode == 0, "machine JSON depends on console code page"
        report = json.loads(child.stdout.decode("utf-8", errors="strict"))
        assert report["inventory"][0]["path"] == "顯示.py", "Unicode path identity changed"


if __name__ == "__main__":
    run_self_test()
    print("Inventory and UTF-8 JSON regressions passed")
