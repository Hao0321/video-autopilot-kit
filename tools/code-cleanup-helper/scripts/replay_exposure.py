#!/usr/bin/env python3
"""Isolated owned-fixture replay with current code identity, never a target audit."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import platform
import sys

# -I deliberately removes the script directory as well as user/PYTHONPATH imports.
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROVIDER_FILES = ("replay_exposure.py", "exposure_regression.py", "exposure_formats_regression.py",
                  "exposure_scope_regression.py", "check_release_exposure.py", "exposure_formats.py", "sync_safety.py")


def code_identity() -> dict:
    rows = []
    for path in sorted(SCRIPTS / name for name in PROVIDER_FILES):
        with path.open("rb") as handle:
            data = handle.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("fixture replay source exceeds bounds")
        rows.append({"path": "scripts/" + path.name, "sha256": hashlib.sha256(data).hexdigest()})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"sha256": digest, "files": rows}


IMPORT_IDENTITY = code_identity()
import exposure_regression
import exposure_formats_regression
import exposure_scope_regression
import check_release_exposure
import exposure_formats
import sync_safety


def replay() -> dict:
    before = IMPORT_IDENTITY
    modules = (exposure_regression, exposure_formats_regression, exposure_scope_regression,
               check_release_exposure, exposure_formats, sync_safety)
    if any(Path(module.__file__).resolve().parent != SCRIPTS for module in modules):
        raise ValueError("fixture replay imported a different provider")
    if code_identity() != before:
        raise ValueError("fixture replay code changed during imports")
    result = exposure_regression.run_self_test()
    formats = exposure_formats_regression.run_self_test()
    exposure_scope_regression.run_self_test()
    if code_identity() != before:
        raise ValueError("fixture replay code changed during measurement")
    return {"schemaVersion": 1, "status": "PASS", "replay": result,
            "supplemental": formats, "codeIdentity": before,
            "environment": {"pythonVersion": platform.python_version(),
                            "executableSha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                            "scope": "interpreter executable identity; full OS/runtime libraries not attested"},
            "scope": "owned calibration only; does not inspect a user's product"}


def main() -> int:
    try:
        report = replay()
    except (AssertionError, OSError, ValueError) as exc:
        report = {"status": "BLOCK", "error": type(exc).__name__}
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
