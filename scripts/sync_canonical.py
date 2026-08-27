#!/usr/bin/env python3
"""Synchronize redistributable Video Autopilot sources into the public kit.

The canonical workspace may contain user media, analytics, generated previews,
private preferences and machine paths. This deterministic synchronizer uses a
closed-world inventory, text-only copies, and privacy preflight transforms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from public_privacy_sanitizer import (
    PUBLIC_FIXTURE,
    SANITIZERS,
    assert_public_text_safe,
    contains_private_identity,
    generalize_private_identity,
    sanitize_public_text,
)
from public_skill_skeleton import render_public_skill
from public_sync_inventory import (
    CLEANUP_HELPER_FILES,
    DRAMA_MODULES,
    KNOWLEDGE_FILES,
    LONGFORM_MODULES,
    PRIVATE_PUBLIC_FILES,
    PUBLIC_OWNED_PATHS,
    PUBLIC_AUDIT_EXCLUDES,
    REFERENCE_FILES,
    ROOT_MODULES,
    SANITIZED_KNOWLEDGE_FILES,
    SILENT_VLOG_MODULES,
    SYNC_RECEIPT_PATH,
    WORKFLOW_SKILL_FILES,
    canonical_receipt_shape_errors,
    public_destination_required_paths,
    self_test_public_inventory,
    sync_expected_output_paths,
    validate_canonical_inventory,
    validate_public_destination,
)
from public_sync_renderers import (
    render_public_broll,
    render_public_editorial_templates,
    self_test_public_renderers,
)
from public_sync_support import (
    PUBLIC_KNOWLEDGE_SANITIZERS,
    _assert_public_knowledge_safe,
    _copy_public_autopilot_config,
    _copy_public_cleanup_config,
    _copy_public_knowledge_json,
    _copy_public_knowledge_state,
    _genericize_creator_labels,
    _public_planes,
    _public_required_paths,
    _public_src_path,
    _remove_private_public_files,
    _sanitize_aesthetic_standard,
    _sanitize_color_grading_profiles,
    _sanitize_design_reference_dna,
    _sanitize_thumbnail_standard,
    _self_test_public_privacy,
    _unexpected_private_public_files,
    _write_public_manifest,
)
from public_sync_transforms import MODULE_REPLACEMENTS, PRIVACY_PATTERNS, REPLACEMENTS


def _write_utf8(path: Path, text: str) -> None:
    """Write deterministic LF text on every supported Python version."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _transform(text: str, name: str = "") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in REPLACEMENTS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in MODULE_REPLACEMENTS.get(name, ()):
        text = pattern.sub(replacement, text)
    if name == "project_paths.py":
        required = (
            'MANIFEST_NAME = MANIFEST_NAMES[0]',
            'for name in MANIFEST_NAMES',
            '"release-manifest.json"',
        )
        missing = [token for token in required if token not in text]
        if missing:
            raise ValueError(
                "project_paths public transform lost manifest compatibility: "
                + ", ".join(missing)
            )
    if name == "architecture_gate.py" and (
        "str(HERE.parent)" not in text or "cwd=HERE.parent" not in text
    ):
        raise ValueError("architecture gate public transform lost repository-root scope")
    if name == "delivery.py" and "from .. import publish_hub" not in text:
        raise ValueError(
            "long-form delivery public transform lost package-relative control-plane edge"
        )
    if name == "publish_hub_cli.py":
        required = (
            'withdraw.add_argument("--actor", default="creator")',
            'description="Video Autopilot publishing hub"',
        )
        if any(token not in text for token in required):
            raise ValueError("publishing CLI public transform lost creator-neutral defaults")
    return text


def _copy_text(source: Path, destination: Path, relative_path: str | None = None) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    original = source.read_text(encoding="utf-8-sig")
    if (relative_path is not None and relative_path in SANITIZERS and
            PUBLIC_FIXTURE in original):
        raise ValueError(
            f"reserved public privacy marker in canonical source: {source}"
        )
    text = _transform(original, source.name)
    if relative_path is not None:
        text = sanitize_public_text(relative_path, text)
        assert_public_text_safe(relative_path, text)
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _copy_public_skill(source: Path, destination: Path) -> None:
    """Render the public entrypoint without consuming the canonical body."""
    if not source.is_file():
        raise FileNotFoundError(source)
    text = render_public_skill(source.read_text(encoding="utf-8-sig"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _copy_rendered_source(source: Path, destination: Path, renderer) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    original = source.read_text(encoding="utf-8-sig")
    if PUBLIC_FIXTURE in original:
        raise ValueError(f"reserved public privacy marker in canonical source: {source}")
    text = renderer(original)
    relative = destination.as_posix()
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in rendered source {source}: {hits}")
    try:
        compile(text, relative, "exec")
    except SyntaxError as exc:
        raise ValueError(f"rendered public Python is invalid for {source}: {exc}") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _copy_public_owned(distribution_source: Path, repository: Path) -> list[str]:
    """Copy public-kit-owned text with deterministic LF bytes.

    The release archive normalizes text payloads to LF.  Normalizing here too
    keeps the committed sync receipt valid after Git checkout/archive filters
    on Windows and makes the receipt portable across supported platforms.
    """
    copied: list[str] = []
    for relative in PUBLIC_OWNED_PATHS:
        source, destination = distribution_source / relative, repository / relative
        if not source.is_file():
            raise FileNotFoundError(f"public-kit-owned source missing: {source}")
        text = source.read_text(encoding="utf-8-sig")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
        if hits:
            raise ValueError(f"privacy token in public-kit-owned source {source}: {hits}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_utf8(destination, text)
        copied.append(relative)
    return copied


def _self_test_public_owned_lf() -> None:
    """In-place public-owned sync must remove CRLF before receipt hashing."""
    with tempfile.TemporaryDirectory(prefix="video-autopilot-public-owned-lf-") as temp:
        root = Path(temp)
        for relative in PUBLIC_OWNED_PATHS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"# fixture\r\nvalue = 1\r\n")
        copied = _copy_public_owned(root, root)
        assert copied == list(PUBLIC_OWNED_PATHS)
        assert all(b"\r" not in (root / relative).read_bytes() for relative in copied)
    print("sync_canonical public-owned LF self-test GREEN")


def _unexpected_public_references(repository: Path) -> list[str]:
    """Return stale Markdown files in the fully managed public reference tree."""
    reference_root = repository / "codex-skill" / "video-autopilot" / "references"
    if not reference_root.is_dir():
        return []
    expected = {Path(name).as_posix() for name in REFERENCE_FILES}
    actual = {
        path.relative_to(reference_root).as_posix()
        for path in reference_root.rglob("*.md")
        if path.is_file()
    }
    return sorted(actual - expected)


def _write_sync_receipt(
    canonical_evidence: dict[str, dict],
    repository: Path,
    copied: list[str],
) -> None:
    expected_outputs = sync_expected_output_paths()
    if len(copied) != len(set(copied)):
        raise ValueError("sync generated duplicate output paths")
    if set(copied) != expected_outputs:
        missing = sorted(expected_outputs - set(copied))
        extra = sorted(set(copied) - expected_outputs)
        raise ValueError(
            "sync output schema drifted; missing=%s extra=%s"
            % (missing[:20], extra[:20])
        )
    output_names = sorted(copied)
    outputs = {name: _sha256(repository / name) for name in output_names}
    public_owned = {name: outputs[name] for name in PUBLIC_OWNED_PATHS}
    inventory_text = json.dumps(
        canonical_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    payload = {
        "schema": "video-autopilot-public-sync-receipt/v2",
        "assurance": (
            "Detects stale or accidental public-sync drift. This committed receipt is not "
            "an external signature against an attacker who can modify both code and receipt."
        ),
        "canonical_inventory_sha256": hashlib.sha256(inventory_text).hexdigest(),
        "canonical_inventory": canonical_evidence,
        "output_count": len(outputs),
        "outputs": outputs,
        "public_owned": public_owned,
        "public_destination_required_paths": public_destination_required_paths(),
    }
    target = repository / SYNC_RECEIPT_PATH
    _write_utf8(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _receipt_schema_errors(payload) -> list[str]:
    expected_keys = {
        "schema", "assurance", "canonical_inventory_sha256", "canonical_inventory",
        "output_count", "outputs", "public_owned", "public_destination_required_paths",
    }
    if not isinstance(payload, dict):
        return ["sync receipt root must be an object"]
    errors: list[str] = []
    if set(payload) != expected_keys:
        errors.append("sync receipt field set mismatch")
    if payload.get("schema") != "video-autopilot-public-sync-receipt/v2":
        errors.append("unexpected sync receipt schema")
    assurance = payload.get("assurance")
    if (not isinstance(assurance, str) or "stale or accidental" not in assurance
            or "not an external signature" not in assurance):
        errors.append("sync receipt assurance boundary missing")
    inventory = payload.get("canonical_inventory")
    errors.extend(canonical_receipt_shape_errors(inventory))
    if isinstance(inventory, dict):
        normalized = json.dumps(
            inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if hashlib.sha256(normalized).hexdigest() != payload.get("canonical_inventory_sha256"):
            errors.append("canonical inventory evidence hash mismatch")
    expected_outputs = sync_expected_output_paths()
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("sync receipt outputs missing")
    else:
        if set(outputs) != expected_outputs:
            errors.append("sync receipt output key set mismatch")
        if payload.get("output_count") != len(expected_outputs) or len(outputs) != len(expected_outputs):
            errors.append("sync receipt output_count mismatch")
        if any(not isinstance(value, str) or len(value) != 64
               or any(char not in "0123456789abcdef" for char in value)
               for value in outputs.values()):
            errors.append("sync receipt output hash invalid")
    expected_required = public_destination_required_paths()
    if payload.get("public_destination_required_paths") != expected_required:
        errors.append("sync receipt public destination schema drift")
    public_owned = payload.get("public_owned")
    if not isinstance(public_owned, dict) or set(public_owned) != set(PUBLIC_OWNED_PATHS):
        errors.append("sync receipt public-owned inventory mismatch")
    elif isinstance(outputs, dict):
        for relative in PUBLIC_OWNED_PATHS:
            if public_owned.get(relative) != outputs.get(relative):
                errors.append("sync receipt public-owned hash mismatch: " + relative)
    return errors


def _verify_sync_receipt(repository: Path) -> list[str]:
    target = repository / SYNC_RECEIPT_PATH
    if not target.is_file():
        return [f"missing {SYNC_RECEIPT_PATH}"]
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid {SYNC_RECEIPT_PATH}: {exc}"]
    errors = _receipt_schema_errors(payload)
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        return errors
    for relative in sorted(sync_expected_output_paths()):
        expected = outputs.get(relative)
        path = repository / relative
        if not path.is_file():
            errors.append("missing receipt output: " + relative)
        elif isinstance(expected, str) and _sha256(path) != expected:
            errors.append("receipt output hash mismatch: " + relative)
    manifest_path = repository / "release-manifest.json"
    if not manifest_path.is_file():
        manifest_path = Path(__file__).resolve().parents[1] / "release-manifest.json"
    try:
        validate_public_destination(repository, manifest_path)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def _self_test_receipt_schema(repository: Path) -> None:
    import copy

    payload = json.loads((repository / SYNC_RECEIPT_PATH).read_text(encoding="utf-8-sig"))
    assert not _receipt_schema_errors(payload)
    missing_output = copy.deepcopy(payload)
    missing_output["outputs"].pop(next(iter(missing_output["outputs"])))
    missing_output["output_count"] -= 1
    assert "sync receipt output key set mismatch" in _receipt_schema_errors(missing_output)
    extra_output = copy.deepcopy(payload)
    extra_output["outputs"]["src/extra_dir/extra.py"] = "0" * 64
    extra_output["output_count"] += 1
    assert "sync receipt output key set mismatch" in _receipt_schema_errors(extra_output)
    empty_inventory = copy.deepcopy(payload)
    empty_inventory["canonical_inventory"] = {}
    normalized = json.dumps({}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    empty_inventory["canonical_inventory_sha256"] = hashlib.sha256(normalized).hexdigest()
    assert canonical_receipt_shape_errors({})
    assert _receipt_schema_errors(empty_inventory)
    print("sync receipt schema negative fixtures GREEN")


def sync(
    canonical: Path,
    repository: Path,
    distribution_source: Path | None = None,
) -> list[str]:
    canonical_evidence = validate_canonical_inventory(canonical)
    distribution_source = (
        distribution_source.resolve()
        if distribution_source is not None
        else Path(__file__).resolve().parents[1]
    )
    _remove_private_public_files(repository)
    copied: list[str] = []
    groups = (
        (ROOT_MODULES, canonical, repository / "src"),
        (LONGFORM_MODULES, canonical / "longform_maker", repository / "src" / "longform_maker"),
        (SILENT_VLOG_MODULES, canonical / "silent_vlog_maker", repository / "src" / "silent_vlog_maker"),
        (DRAMA_MODULES, canonical / "drama_pipeline", repository / "src" / "drama_pipeline"),
        (KNOWLEDGE_FILES, canonical / "knowledge", repository / "knowledge" / "runtime"),
        (REFERENCE_FILES, canonical / "references", repository / "codex-skill" / "video-autopilot" / "references"),
    )
    for names, source_root, destination_root in groups:
        for name in names:
            destination = destination_root / name
            if name == "broll_qa.py" and source_root == canonical:
                _copy_rendered_source(source_root / name, destination, render_public_broll)
            elif name == "editorial_templates.py" and source_root == canonical:
                _copy_rendered_source(
                    source_root / name, destination, render_public_editorial_templates
                )
            elif name == "state.json" and source_root.name == "knowledge":
                _copy_public_knowledge_state(source_root / name, destination)
            elif name in SANITIZED_KNOWLEDGE_FILES and source_root.name == "knowledge":
                _copy_public_knowledge_json(source_root / name, destination)
            else:
                relative = destination.relative_to(repository).as_posix()
                _copy_text(source_root / name, destination, relative)
            copied.append(destination.relative_to(repository).as_posix())
    _copy_public_skill(
        canonical / "SKILL.md",
        repository / "codex-skill" / "video-autopilot" / "SKILL.md",
    )
    copied.append("codex-skill/video-autopilot/SKILL.md")
    for name in WORKFLOW_SKILL_FILES:
        destination = repository / "codex-skill" / "video-autopilot" / name
        _copy_text(
            canonical / name,
            destination,
            destination.relative_to(repository).as_posix(),
        )
        copied.append(destination.relative_to(repository).as_posix())
    _copy_text(
        canonical / "agents" / "openai.yaml",
        repository / "codex-skill" / "video-autopilot" / "agents" / "openai.yaml",
        "codex-skill/video-autopilot/agents/openai.yaml",
    )
    copied.append("codex-skill/video-autopilot/agents/openai.yaml")
    _copy_public_autopilot_config(
        canonical / "audit.config.json", repository / "audit.config.json"
    )
    copied.append("audit.config.json")
    cleanup = Path.home() / ".codex" / "skills" / "code-cleanup-helper"
    for relative in CLEANUP_HELPER_FILES:
        destination = repository / "tools" / "code-cleanup-helper" / relative
        if relative == "audit.config.json":
            _copy_public_cleanup_config(cleanup / relative, destination)
        else:
            _copy_text(
                cleanup / relative,
                destination,
                destination.relative_to(repository).as_posix(),
            )
        copied.append(destination.relative_to(repository).as_posix())
    _copy_text(
        distribution_source.parent / "AUTOPILOT_ARCHITECTURE_V6.md",
        repository / "docs" / "AUTOPILOT_ARCHITECTURE_V6.md",
        "docs/AUTOPILOT_ARCHITECTURE_V6.md",
    )
    copied.append("docs/AUTOPILOT_ARCHITECTURE_V6.md")
    _write_public_manifest(repository)
    copied.append("AUTOPILOT_MANIFEST.json")
    copied.extend(_copy_public_owned(distribution_source, repository))
    validate_public_destination(repository, distribution_source / "release-manifest.json")
    _write_sync_receipt(canonical_evidence, repository, copied)
    copied.append(SYNC_RECEIPT_PATH)
    return copied


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_test_reserved_public_marker() -> None:
    """Canonical inputs cannot impersonate already-sanitized public outputs."""
    managed_path = next(iter(SANITIZERS))
    with tempfile.TemporaryDirectory(prefix="video-autopilot-marker-test-") as temp:
        root = Path(temp)
        source = root / "canonical-input.txt"
        source.write_text(PUBLIC_FIXTURE + "\n", encoding="utf-8")
        try:
            _copy_text(source, root / "public-output.txt", managed_path)
        except ValueError as exc:
            assert "reserved public privacy marker" in str(exc)
        else:
            raise AssertionError("reserved public marker bypassed canonical preflight")
    print("sync_canonical reserved-marker self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path)
    parser.add_argument(
        "--repository", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--distribution-source", type=Path,
        help="public-kit source used to seed explicit public-owned files",
    )
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    parser.add_argument(
        "--verify-receipt", action="store_true",
        help="verify the committed public sync receipt without a private canonical tree",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="run public privacy negative fixtures"
    )
    args = parser.parse_args()
    repository = args.repository.resolve()
    if args.self_test:
        _self_test_public_privacy()
        _self_test_reserved_public_marker()
        _self_test_public_owned_lf()
        self_test_public_renderers(repository)
        self_test_public_inventory(repository)
        _self_test_receipt_schema(repository)
        return 0
    if args.verify_receipt:
        errors = _verify_sync_receipt(repository)
        if errors:
            print("SYNC RECEIPT RED: " + "; ".join(errors[:30]))
            return 1
        receipt = json.loads((repository / SYNC_RECEIPT_PATH).read_text(encoding="utf-8"))
        print(f"SYNC RECEIPT GREEN: {receipt['output_count']} hashed outputs")
        return 0
    if args.canonical is None:
        parser.error("--canonical is required unless --self-test or --verify-receipt is used")
    canonical = args.canonical.resolve()
    distribution_source = (
        args.distribution_source.resolve() if args.distribution_source else None
    )
    if args.check:
        with tempfile.TemporaryDirectory(prefix="video-autopilot-sync-") as temp:
            staged = Path(temp) / "repository"
            expected = sync(canonical, staged, distribution_source)
            drift = [
                name for name in expected
                if not (repository / name).is_file()
                or _sha256(staged / name) != _sha256(repository / name)
            ]
        stale_references = _unexpected_public_references(repository)
        private_files = _unexpected_private_public_files(repository)
        destination_errors: list[str] = []
        destination_manifest = repository / "release-manifest.json"
        if not destination_manifest.is_file():
            destination_manifest = (
                distribution_source or Path(__file__).resolve().parents[1]
            ) / "release-manifest.json"
        try:
            validate_public_destination(repository, destination_manifest)
        except ValueError as exc:
            destination_errors.append(str(exc))
        if drift or stale_references or private_files or destination_errors:
            details = list(drift[:30])
            details.extend("stale-reference:" + name for name in stale_references[:30])
            details.extend("private-public-file:" + name for name in private_files[:30])
            details.extend("destination:" + error for error in destination_errors)
            print("SYNC DRIFT: " + ", ".join(details))
            return 1
        print(f"SYNC GREEN: {len(expected)} redistributable text files")
        return 0
    copied = sync(canonical, repository, distribution_source)
    print(f"SYNC APPLIED: {len(copied)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
