"""Owned, isolated adapter fixtures; never replace production source pins."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil

from public_workflow_distribution import ADAPTER_FILES, PUBLIC_ONLY_MODULES
from public_sync_inventory import (
    CANONICAL_DIRECTORY_LABELS, PRIVATE_CONTROL_FILE, PRIVATE_CONTROL_SCHEMA, PUBLIC_OWNED_PATHS,
)


@contextmanager
def canonical_adapter_fixture(repository: Path, root: Path):
    """Bind synthetic source bytes once; later tampering must fail the real guard."""
    root.mkdir(parents=True, exist_ok=True)
    pins = {}
    for name in ADAPTER_FILES:
        if name not in PUBLIC_ONLY_MODULES:
            shutil.copyfile(repository / "src" / name, root / name)
            pins[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    control = {"schema": PRIVATE_CONTROL_SCHEMA,
               "directories": {label: {} for label in CANONICAL_DIRECTORY_LABELS},
               "reviewed_analogue_pins": pins, "private_text_patterns": [], "private_terms": []}
    (root / PRIVATE_CONTROL_FILE).write_text(json.dumps(control), encoding="utf-8")
    yield root


def public_distribution_fixture(repository: Path, root: Path):
    for name in ADAPTER_FILES:
        for prefix in ("src", "codex-skill/video-autopilot"):
            target = root / prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repository / prefix / name, target)
    shutil.copyfile(repository / "release-manifest.json", root / "release-manifest.json")
    return root


def owned_source_fixture(repository: Path, root: Path):
    for relative in PUBLIC_OWNED_PATHS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / relative, target)
    return root
