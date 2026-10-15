"""Path-free fixture reporting and owned directory-alias controls."""
from __future__ import annotations
import os
import subprocess
import traceback
from pathlib import Path
from typing import Callable, TypeVar

_StageResult = TypeVar("_StageResult")

def _runtime_category(exc: RuntimeError) -> str:
    message = str(exc)
    if message.startswith("release validation failed:"):
        return "release-validation"
    if message.startswith("release sync-receipt parity failed:"):
        return "sync-receipt-parity"
    if message.startswith("archive verification failed:"):
        return "archive-verification"
    return "runtime"

def _run_stage(label: str, action: Callable[[], _StageResult]) -> _StageResult:
    """Emit path-free progress while preserving the original failure type."""
    print(f"release_manager self-test START: {label}", flush=True)
    try:
        result = action()
    except Exception as exc:
        category = (
            _runtime_category(exc) if isinstance(exc, RuntimeError)
            else type(exc).__name__
        )
        # Report only a public fixture line number, never exception text or a
        # temporary path that could contain a copied capability or secret.
        fixture_frames = [frame for frame in traceback.extract_tb(exc.__traceback__)
                          if Path(frame.filename).name in {"release_manager_selftest.py", "release_mutation_selftest.py"}]
        site = f" line {fixture_frames[-1].lineno}" if fixture_frames else ""
        print(
            f"release_manager self-test RED: {label} ({category}{site})",
            flush=True,
        )
        raise
    print(f"release_manager self-test GREEN: {label}", flush=True)
    return result

def _directory_alias(link: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
    else:
        link.symlink_to(target, target_is_directory=True)

def _remove_directory_alias(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()
