# -*- coding: utf-8 -*-
"""Closed-world path and receipt integrity for release construction."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath


SYNC_RECEIPT_SCHEMA = "video-autopilot-public-sync-receipt/v3"
SYNC_RECEIPT_HASH_SEMANTICS = "sha256:utf8-bom-stripped:lf-normalized"
SYNC_RECEIPT_FIELDS = {
    "schema", "assurance", "canonical_inventory_sha256", "canonical_inventory",
    "output_hash_semantics", "output_count", "outputs", "public_owned",
    "public_destination_required_paths",
}
UPDATE_STATE_DIR = ".video-autopilot"


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe release path")
    return path.as_posix()


def canonical_portable_relative(value: object) -> str:
    """Require one portable spelling for a release-owned relative path."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("non-canonical release path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("non-canonical release path")
    normalized = _safe_relative(value)
    if normalized != value:
        raise ValueError("non-canonical release path")
    return normalized


def canonical_persisted_paths(value: object) -> list[str]:
    """Validate an untrusted persisted list of release-owned relative paths."""
    if not isinstance(value, list):
        raise RuntimeError("persisted path inventory is invalid")
    canonical: list[str] = []
    folded: set[str] = set()
    for raw in value:
        try:
            relative = canonical_portable_relative(raw)
        except (TypeError, ValueError):
            raise RuntimeError("persisted path inventory is invalid") from None
        key = relative.casefold()
        if key in folded:
            raise RuntimeError("persisted path inventory is invalid")
        folded.add(key)
        canonical.append(relative)
    return canonical


def canonical_persisted_hashes(value: object) -> dict[str, str]:
    """Validate persisted managed hashes without trusting their path keys."""
    if not isinstance(value, dict):
        raise RuntimeError("persisted hash inventory is invalid")
    canonical: dict[str, str] = {}
    folded: set[str] = set()
    for raw, digest in value.items():
        try:
            relative = canonical_portable_relative(raw)
        except (TypeError, ValueError):
            raise RuntimeError("persisted hash inventory is invalid") from None
        key = relative.casefold()
        if key in folded or not isinstance(digest, str) or not re.fullmatch(
            r"[0-9a-fA-F]{64}", digest
        ):
            raise RuntimeError("persisted hash inventory is invalid")
        folded.add(key)
        canonical[relative] = digest.lower()
    return canonical


def _is_link_or_reparse(path: Path) -> bool:
    """Return true for symlinks and Windows junction/reparse points."""
    try:
        metadata = path.lstat()
    except OSError:
        return False
    if path.is_symlink():
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def assert_safe_mutation_path(
    root: Path, path: Path, *, require_file: bool = False,
    allow_missing: bool = True,
) -> Path:
    """Reject mutation paths that escape ``root`` or traverse a link/reparse point.

    The leaf may not exist yet. Diagnostics intentionally contain only a path
    relative to the trusted root and never a resolved machine-local target.
    """
    lexical_root = Path(os.path.abspath(root))
    lexical_path = Path(os.path.abspath(path))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise RuntimeError("managed mutation path is outside its root") from exc
    label = relative.as_posix() or "."
    resolved_root = lexical_root.resolve(strict=False)
    cursor = lexical_root
    for part in relative.parts:
        cursor = cursor / part
        try:
            cursor.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise RuntimeError("managed mutation path is unreadable: " + label) from exc
        if _is_link_or_reparse(cursor):
            raise RuntimeError(
                "managed mutation path uses link/reparse point: " + label
            )
        try:
            cursor.resolve(strict=True).relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RuntimeError(
                "managed mutation path is unresolvable or outside root: " + label
            ) from exc
    if require_file:
        try:
            metadata = lexical_path.lstat()
        except FileNotFoundError:
            if not allow_missing:
                raise RuntimeError("managed mutation file is missing: " + label) from None
        except OSError as exc:
            raise RuntimeError("managed mutation path is unreadable: " + label) from exc
        else:
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError("managed mutation path is not a regular file: " + label)
    return lexical_path


def validated_install_state(
    state: object, expected_version: object = None
) -> tuple[list[str], dict[str, str]]:
    if not isinstance(state, dict):
        raise RuntimeError("install state is invalid")
    if "managed_files" not in state or "managed_hashes" not in state:
        raise RuntimeError("install state managed inventory is missing")
    managed = canonical_persisted_paths(state.get("managed_files", []))
    hashes = canonical_persisted_hashes(state.get("managed_hashes", {}))
    if set(managed) != set(hashes):
        raise RuntimeError("install state managed inventory is inconsistent")
    if expected_version is not None and state.get("version") != expected_version:
        raise RuntimeError("install state version is inconsistent")
    return managed, hashes


def assert_transaction_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:\d{8}T\d{6}Z|\d{8}T\d{12}Z-[0-9a-f]{12})", value
    ):
        raise RuntimeError("rollback transaction identifier is invalid")
    return value


def validated_transaction_record(
    record: object, transaction: str, *, current_state_present: bool | None = None,
    previous_state_present: bool | None = None,
) -> dict:
    if not isinstance(record, dict) or record.get("transaction") != transaction:
        raise RuntimeError("rollback transaction record is invalid")
    validated = dict(record)
    inventories = {
        name: canonical_persisted_paths(record.get(name, []))
        for name in ("created", "replaced", "removed")
    }
    combined = [relative for values in inventories.values() for relative in values]
    if len(combined) != len({relative.casefold() for relative in combined}):
        raise RuntimeError("rollback transaction record is invalid")
    expected_previous = record.get("had_previous_state")
    if expected_previous is not None and not isinstance(expected_previous, bool):
        raise RuntimeError("rollback transaction record is invalid")
    if previous_state_present is not None and expected_previous is not None and (
        previous_state_present != expected_previous
    ):
        raise RuntimeError("rollback previous-state presence is inconsistent")
    if current_state_present is not None and not current_state_present and (
        record.get("status") == "COMMITTED" or expected_previous is True
    ):
        raise RuntimeError("rollback current-state presence is inconsistent")
    validated.update(inventories)
    return validated


def resolve_mutation_root(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    resolved_parent = absolute.parent.resolve()
    canonical = resolved_parent / absolute.name
    assert_safe_mutation_path(resolved_parent, canonical)
    return canonical.resolve()


def preflight_apply_paths(
    install_root: Path,
    managed: list[str],
    previous_managed: list[str],
    backup_root: Path,
) -> None:
    state_dir = install_root / UPDATE_STATE_DIR
    for path in [state_dir, state_dir / "backups", backup_root, backup_root / "files"]:
        assert_safe_mutation_path(install_root, path)
    for path in [
        state_dir / "install-state.json", state_dir / "install-state.json.tmp",
        backup_root / "previous-install-state.json", backup_root / "transaction.json",
        backup_root / "transaction.json.tmp",
    ]:
        assert_safe_mutation_path(install_root, path, require_file=True)
    managed_set = set(managed)
    for relative in sorted(managed_set | set(previous_managed)):
        target = install_root / relative
        assert_safe_mutation_path(install_root, target, require_file=True)
        assert_safe_mutation_path(
            install_root, backup_root / "files" / relative, require_file=True
        )
        if relative in managed_set:
            assert_safe_mutation_path(
                install_root, target.with_name(target.name + ".update-tmp"),
                require_file=True,
            )


def preflight_rollback_paths(
    install_root: Path, record: dict, backup_root: Path
) -> None:
    state_dir = install_root / UPDATE_STATE_DIR
    for path in [state_dir, state_dir / "backups", backup_root, backup_root / "files"]:
        assert_safe_mutation_path(install_root, path)
    for path in [
        state_dir / "install-state.json", state_dir / "install-state.json.tmp",
        backup_root / "previous-install-state.json", backup_root / "transaction.json.tmp",
    ]:
        assert_safe_mutation_path(install_root, path, require_file=True)
    assert_safe_mutation_path(
        install_root, backup_root / "transaction.json",
        require_file=True, allow_missing=False,
    )
    restored = set(record["replaced"]) | set(record["removed"])
    for relative in sorted(set(record["created"]) | restored):
        target = install_root / relative
        assert_safe_mutation_path(install_root, target, require_file=True)
        assert_safe_mutation_path(
            install_root, target.with_name(target.name + ".update-tmp"),
            require_file=True,
        )
        if relative in restored:
            assert_safe_mutation_path(
                install_root, backup_root / "files" / relative,
                require_file=True, allow_missing=False,
            )
            assert_safe_mutation_path(
                install_root, target.with_name(target.name + ".rollback-tmp"),
                require_file=True,
            )


def assert_contained_release_path(
    root: Path, path: Path, *, require_file: bool = False
) -> Path:
    """Reject links, reparse points and paths resolving outside ``root``."""
    resolved_root = root.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("release path is outside root") from exc
    label = relative.as_posix()
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if _is_link_or_reparse(cursor):
            raise RuntimeError("release path uses link/reparse point: " + label)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(
            "release path is unresolvable or outside root: " + label
        ) from exc
    if require_file and not resolved.is_file():
        raise RuntimeError("release path is not a regular file: " + label)
    return resolved


def load_sync_inventory_contract(root: Path) -> dict:
    """Load the release-owned closed-world inventory without trusting receipt keys."""
    inventory_path = root / "scripts" / "public_sync_inventory.py"
    assert_contained_release_path(root, inventory_path, require_file=True)
    try:
        spec = importlib.util.spec_from_file_location(
            "_video_autopilot_release_sync_inventory", inventory_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("module loader unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected_outputs = frozenset(module.sync_expected_output_paths())
        required_paths = module.public_destination_required_paths()
        public_owned = frozenset(module.PUBLIC_OWNED_PATHS)
        shape_validator = module.canonical_receipt_shape_errors
    except Exception as exc:
        raise RuntimeError(
            "release sync inventory contract is unavailable: " + type(exc).__name__
        ) from None
    try:
        canonical_outputs = all(
            canonical_portable_relative(relative) == relative
            for relative in expected_outputs
        )
    except (TypeError, ValueError):
        canonical_outputs = False
    if not expected_outputs or not canonical_outputs:
        raise RuntimeError("release sync inventory contract is invalid")
    return {
        "expected_outputs": expected_outputs,
        "required_paths": required_paths,
        "public_owned": public_owned,
        "shape_validator": shape_validator,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def staged_sync_receipt_errors(stage: Path, contract: dict) -> list[str]:
    """Bind the complete receipt schema to exact canonical bytes entering the ZIP."""
    errors: list[str] = []
    receipt_path = stage / "sync-receipt.json"
    try:
        assert_contained_release_path(stage, receipt_path, require_file=True)
        receipt = _read_json(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        return ["staged sync receipt is unavailable or invalid: %s" % type(exc).__name__]
    if not isinstance(receipt, dict):
        return ["staged sync receipt root must be an object"]
    if set(receipt) != SYNC_RECEIPT_FIELDS:
        errors.append("staged sync receipt field set mismatch")
    if receipt.get("schema") != SYNC_RECEIPT_SCHEMA:
        errors.append("staged sync receipt schema mismatch")
    if receipt.get("output_hash_semantics") != SYNC_RECEIPT_HASH_SEMANTICS:
        errors.append("staged sync receipt hash semantics mismatch")
    assurance = receipt.get("assurance")
    if not isinstance(assurance, str) or "stale or accidental" not in assurance or (
        "not an external signature" not in assurance
    ):
        errors.append("staged sync receipt assurance boundary missing")
    inventory = receipt.get("canonical_inventory")
    errors.extend("staged " + error for error in contract["shape_validator"](inventory))
    if isinstance(inventory, dict):
        encoded = json.dumps(
            inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != receipt.get(
            "canonical_inventory_sha256"
        ):
            errors.append("staged sync receipt canonical inventory hash mismatch")
    if receipt.get("public_destination_required_paths") != contract["required_paths"]:
        errors.append("staged sync receipt public destination schema drift")
    outputs = receipt.get("outputs")
    if not isinstance(outputs, dict):
        return errors + ["staged sync receipt outputs missing"]
    expected_outputs = contract["expected_outputs"]
    if set(outputs) != expected_outputs:
        errors.append("staged sync receipt output key set mismatch")
    if receipt.get("output_count") != len(expected_outputs) or len(outputs) != len(
        expected_outputs
    ):
        errors.append("staged sync receipt output_count mismatch")
    folded_paths: dict[str, str] = {}
    for raw_relative in outputs:
        try:
            relative = canonical_portable_relative(raw_relative)
        except (TypeError, ValueError):
            errors.append("staged sync receipt contains non-canonical output path")
            continue
        folded = relative.casefold()
        if folded in folded_paths and folded_paths[folded] != relative:
            errors.append("staged sync receipt contains case-folding path collision")
        folded_paths[folded] = relative
    public_owned = receipt.get("public_owned")
    if not isinstance(public_owned, dict) or set(public_owned) != contract["public_owned"]:
        errors.append("staged sync receipt public-owned inventory mismatch")
    else:
        for relative in sorted(contract["public_owned"]):
            if public_owned.get(relative) != outputs.get(relative):
                errors.append("staged sync receipt public-owned hash mismatch: " + relative)
    for relative in sorted(expected_outputs):
        expected = outputs.get(relative)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            errors.append("staged sync receipt contains invalid output hash: " + relative)
            continue
        target = stage / relative
        try:
            assert_contained_release_path(stage, target, require_file=True)
        except RuntimeError:
            errors.append("staged sync receipt output missing or unsafe: " + relative)
            continue
        if _sha256_path(target) != expected:
            errors.append("staged sync receipt payload mismatch: " + relative)
    return errors
