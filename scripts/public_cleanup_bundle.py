"""Pin the complete public Cleanup provider, including its self-test closure."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from public_sync_inventory import CLEANUP_HELPER_FILES
from public_sync_paths import _output_path_boundary_rule, _text_sha256, _write_utf8

BUNDLE_PATH = "tools/code-cleanup-helper/BUNDLE.json"
UPSTREAM = {"project": "claude-skill-code-cleanup", "tag": "v0.22.1",
            "commit": "7097840737035007989dd9fc564dcc65df5e23bb"}
# Filled from the current canonical export and independently compared with the
# named release. A changed provider requires an explicit new inventory/pin.
PUBLIC_EXPORT_SHA256 = "85bee14f241970ae40454ae31e6132643ced8413995377ae9890e7c76bbcdd83"


def _digest(values: dict) -> str:
    data = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canonical_policy(cleanup: Path):
    """Use the provider's own public selection and privacy policy before writes."""
    path = cleanup / "scripts/sync_safety.py"
    spec = importlib.util.spec_from_file_location("_canonical_cleanup_sync_policy", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cleanup publication policy unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads(module.read_bytes(cleanup / "audit.config.json"))
    return module, config


def validate_cleanup_source(cleanup: Path) -> dict:
    policy, config = _canonical_policy(cleanup)
    selected = policy.source_files(cleanup, config)
    expected = set(CLEANUP_HELPER_FILES) - {"audit.config.json"}
    if set(selected) != expected:
        raise ValueError("Cleanup bundle inventory differs from the current public export")
    for name in selected:
        policy.privacy_check(policy.read_bytes(cleanup / name), name, config)
    hashes = {name: _text_sha256(cleanup / name) for name in selected}
    if _digest(hashes) != PUBLIC_EXPORT_SHA256:
        raise ValueError("Cleanup canonical export changed; refresh the upstream release pin")
    return hashes


def copy_cleanup_source(cleanup: Path, name: str, destination: Path) -> None:
    policy, config = _canonical_policy(cleanup)
    data = policy.read_bytes(policy.safe_path(cleanup, name))
    policy.privacy_check(data, name, config)
    text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def write_cleanup_bundle(cleanup: Path, repository: Path, source_hashes: dict) -> None:
    if validate_cleanup_source(cleanup) != source_hashes:
        raise ValueError("Cleanup source changed during export")
    prefix = repository / "tools/code-cleanup-helper"
    hashes = {name: _text_sha256(prefix / name) for name in CLEANUP_HELPER_FILES}
    for name, digest in source_hashes.items():
        if hashes[name] != digest:
            raise ValueError("Cleanup public source was altered during export: " + name)
    payload = {"schema": "video-kit-bundled-cleanup/v1", "upstream": UPSTREAM,
               "sourceExportSha256": PUBLIC_EXPORT_SHA256,
               "hashSemantics": "UTF-8 text; BOM removed; newline normalized to LF",
               "files": hashes}
    (repository / BUNDLE_PATH).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def verify_cleanup_bundle(repository: Path) -> None:
    root = repository / "tools/code-cleanup-helper"
    payload = json.loads((repository / BUNDLE_PATH).read_text(encoding="utf-8-sig"))
    if (payload.get("schema") != "video-kit-bundled-cleanup/v1"
            or payload.get("upstream") != UPSTREAM
            or payload.get("sourceExportSha256") != PUBLIC_EXPORT_SHA256
            or set(payload.get("files", {})) != set(CLEANUP_HELPER_FILES)):
        raise ValueError("Cleanup bundle provenance mismatch")
    for name, digest in payload["files"].items():
        relative = "tools/code-cleanup-helper/" + name
        if _output_path_boundary_rule(repository, relative) is not None:
            raise ValueError("Cleanup bundle contains an unsafe file")
        if _text_sha256(root / name) != digest:
            raise ValueError("Cleanup bundle file changed: " + name)
    exported = {name: value for name, value in payload["files"].items()
                if name != "audit.config.json"}
    if _digest(exported) != PUBLIC_EXPORT_SHA256:
        raise ValueError("Cleanup bundle public export pin mismatch")
