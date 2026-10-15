"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from typing import NamedTuple


class InstallPlan(NamedTuple):
    """Read-only assessment used by the subsequent mutation transaction."""
    current: object
    migration: object
    is_compatible: bool
    protected: list
    managed: list
    state_dir: object
    previous_state_path: object
    has_previous_state: bool
    previous_managed: list


def _assess_install(_host, install_root, stage, index, auto):
    manifest = _host['read_json'](stage / "release-manifest.json")
    if manifest["version"] != index["version"]:
        raise RuntimeError("manifest/index version mismatch")
    current = _host['detect_current_version'](install_root)
    current_tuple, target_tuple = _host['version_tuple'](current), _host['version_tuple'](index["version"])
    if current_tuple and target_tuple and target_tuple < current_tuple:
        return {"status": "CURRENT", "current": current, "latest": index["version"]}
    if current_tuple and target_tuple and target_tuple == current_tuple:
        target_state = {
            "managed_hashes": {
                _host['_canonical_portable_relative'](row["path"]): row["sha256"]
                for row in index["files"]
            }
        }
        target_drift = _host['locally_modified_managed_files'](install_root, target_state)
        if not target_drift:
            return {"status": "CURRENT", "current": current, "latest": index["version"]}
        if auto:
            return {
                "status": "CONFIRM_REQUIRED", "current": current,
                "latest": index["version"],
                "reason": "same-version managed files require explicit repair",
                "modified": target_drift,
            }
    migration = _host['declared_migration'](current, index["version"], manifest)
    is_compatible = _host['compatible_upgrade'](current, manifest)
    if auto and (not is_compatible or not migration or not migration.get("automatic")):
        return {
            "status": "CONFIRM_REQUIRED",
            "current": current or "unversioned",
            "latest": index["version"],
            "reason": "release is outside the declared automatic-migration window",
        }
    protected = manifest["protected_globs"]
    managed = [_host['_canonical_portable_relative'](row["path"]) for row in index["files"]]
    bad = [relative for relative in managed if _host['_matches'](relative, protected)]
    if bad:
        raise RuntimeError("release attempts to manage protected paths: " + ", ".join(bad))
    state_dir = install_root / _host['STATE_DIR']
    previous_state_path = state_dir / "install-state.json"
    has_previous_state = previous_state_path.is_file()
    previous_state = _host['read_json'](previous_state_path) if has_previous_state else {}
    previous_managed, previous_hashes = _host['_validated_install_state'](previous_state) if has_previous_state else ([], {})
    legacy_nonempty = (
        not has_previous_state
        and install_root.exists()
        and any(install_root.iterdir())
    )
    if auto and legacy_nonempty:
        return {
            "status": "CONFIRM_REQUIRED",
            "current": current or "unversioned",
            "latest": index["version"],
            "reason": "one explicit bootstrap is required before automatic updates can own legacy files",
        }
    modified = _host['locally_modified_managed_files'](
        install_root, {"managed_hashes": previous_hashes}
    )
    if auto and modified:
        return {
            "status": "CONFIRM_REQUIRED",
            "current": current or "unversioned",
            "latest": index["version"],
            "reason": "locally modified managed files would be replaced",
            "modified": modified,
        }
    return InstallPlan(current, migration, is_compatible, protected, managed, state_dir, previous_state_path, has_previous_state, previous_managed)


def _apply_release_payload(_host, backup_root, install_root, plan, record, stage):
    for relative in plan.managed:
        source = stage / relative
        target = install_root / relative
        _host['_assert_contained_release_path'](stage, source, require_file=True)
        if target.exists() and not target.is_file():
            raise RuntimeError("managed file conflicts with directory: " + relative)
        if target.is_file() or target.is_symlink():
            _host['_backup_file'](install_root, target, backup_root, relative)
            record["replaced"].append(relative)
        else:
            record["created"].append(relative)
        _host['atomic_json'](backup_root / "transaction.json", record)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_target = target.with_name(target.name + ".update-tmp")
        _host['shutil'].copy2(source, temporary_target)
        _host['os'].replace(temporary_target, target)
    stale = sorted(set(plan.previous_managed) - set(plan.managed))
    for relative in stale:
        if _host['_matches'](relative, plan.protected):
            continue
        target = install_root / relative
        if target.is_file() or target.is_symlink():
            _host['_backup_file'](install_root, target, backup_root, relative)
            record["removed"].append(relative)
            _host['atomic_json'](backup_root / "transaction.json", record)
            target.unlink()


def apply_release_archive(_host, archive: Path, install_root: Path, expected_hash: Optional[str] = None, auto: bool = False) -> dict:
    archive = archive.resolve()
    install_root = _host['_resolve_mutation_root'](install_root)
    _host['_assert_safe_mutation_path'](install_root, install_root / _host['STATE_DIR'])
    _host['_assert_safe_mutation_path'](install_root, install_root / _host['STATE_DIR'] / "install-state.json", require_file=True)
    _host['_assert_safe_mutation_path'](install_root, install_root / "release-manifest.json", require_file=True)
    index = _host['verify_archive'](archive, expected_hash)
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-update-") as temporary:
        stage = _host['Path'](temporary) / "release"
        staged_index = _host['stage_verified_archive'](archive, stage, expected_hash)
        if staged_index != index:
            raise RuntimeError("archive changed between validation and staging")
        plan = _assess_install(_host, install_root, stage, index, auto)
        if isinstance(plan, dict):
            return plan
        transaction = _host['_new_transaction_id']()
        backup_root = plan.state_dir / "backups" / transaction
        record = {
            "schema_version": 1,
            "transaction": transaction,
            "started_at": _host['utc_now'](),
            "from_version": plan.current or "unversioned",
            "to_version": index["version"],
            "migration": plan.migration["id"] if plan.migration else "explicit-unmanaged-upgrade",
            "replaced": [],
            "created": [],
            "removed": [],
            "had_previous_state": plan.has_previous_state,
            "status": "PENDING",
        }
        _host['_preflight_apply_paths'](
            install_root, plan.managed, plan.previous_managed, backup_root
        )
        backup_root.mkdir(parents=True, exist_ok=False)
        if plan.has_previous_state:
            _host['shutil'].copy2(plan.previous_state_path, backup_root / "previous-install-state.json")
        _host['atomic_json'](backup_root / "transaction.json", record)
        try:
            _apply_release_payload(_host, backup_root, install_root, plan, record, stage)
            state = {
                "schema_version": 1,
                "project_id": "video-autopilot-kit",
                "version": index["version"],
                "installed_at": _host['utc_now'](),
                "managed_files": plan.managed,
                "managed_hashes": {
                    relative: _host['sha256_path'](install_root / relative) for relative in plan.managed
                },
                "last_transaction": transaction,
                "last_migration": record["migration"],
                "auto_update_compatible": plan.is_compatible,
            }
            _host['atomic_json'](plan.previous_state_path, state)
            record["status"] = "COMMITTED"
            record["finished_at"] = _host['utc_now']()
            _host['atomic_json'](backup_root / "transaction.json", record)
        except Exception:
            _host['_rollback_record'](install_root, record, backup_root)
            _host['_restore_previous_state'](install_root, backup_root)
            record["status"] = "ROLLED_BACK"
            record["finished_at"] = _host['utc_now']()
            _host['atomic_json'](backup_root / "transaction.json", record)
            raise
    return {
        "status": "UPDATED",
        "from": plan.current or "unversioned",
        "to": index["version"],
        "managed_files": len(plan.managed),
        "transaction": transaction,
        "backup": str(backup_root),
        "migration": record["migration"],
    }


def rollback(_host, install_root: Path, transaction: Optional[str] = None) -> dict:
    install_root = _host['_resolve_mutation_root'](install_root)
    state_dir = install_root / _host['STATE_DIR']
    backups = state_dir / "backups"
    _host['_assert_safe_mutation_path'](install_root, state_dir)
    _host['_assert_safe_mutation_path'](install_root, backups)
    if transaction is not None:
        selected = _host['_assert_transaction_id'](transaction)
        backup_root = backups / selected
        _host['_assert_safe_mutation_path'](install_root, backup_root)
        candidates = [backup_root] if backup_root.is_dir() else []
    else:
        candidates = []
        if backups.is_dir():
            for path in backups.iterdir():
                _host['_assert_safe_mutation_path'](install_root, path)
                if path.is_dir():
                    _host['_assert_transaction_id'](path.name)
                    candidates.append(path)
        candidates.sort()
    if not candidates:
        raise RuntimeError("no update backup is available")
    backup_root = candidates[-1]
    transaction = _host['_assert_transaction_id'](backup_root.name)
    transaction_path = backup_root / "transaction.json"
    _host['_assert_safe_mutation_path'](install_root, transaction_path, require_file=True, allow_missing=False)
    record = _host['_validated_transaction_record'](_host['read_json'](transaction_path), transaction)
    if record.get("status") not in {"COMMITTED", "PENDING"}:
        raise RuntimeError("transaction cannot be rolled back in its current state")
    _host['_preflight_rollback_paths'](install_root, record, backup_root)
    state_path = state_dir / "install-state.json"
    has_current_state = state_path.is_file()
    current_state = _host['read_json'](state_path) if has_current_state else {}
    if has_current_state: _host['_validated_install_state'](current_state)
    previous_state_path = backup_root / "previous-install-state.json"
    has_previous_state = previous_state_path.is_file()
    previous_state = _host['read_json'](previous_state_path) if has_previous_state else {}
    _host['_validated_transaction_record'](record, transaction, current_state_present=has_current_state, previous_state_present=has_previous_state)
    if has_previous_state: _host['_validated_install_state'](previous_state, record.get("from_version"))
    _host['_rollback_record'](install_root, record, backup_root)
    _host['_restore_previous_state'](install_root, backup_root)
    state = dict(previous_state)
    if state:
        state.update(
            {
                "version": record["from_version"],
                "rolled_back_at": _host['utc_now'](),
                "rolled_back_transaction": record["transaction"],
            }
        )
        _host['atomic_json'](state_path, state)
    record["status"] = "MANUALLY_ROLLED_BACK"
    record["finished_at"] = _host['utc_now']()
    _host['atomic_json'](backup_root / "transaction.json", record)
    return {"status": "ROLLED_BACK", "to": record["from_version"], "transaction": record["transaction"]}


def sync_codex_skill(_host, repo_root: Path, destination: Path, adopt: bool = False) -> dict:
    repo_root = repo_root.resolve(strict=True)
    manifest_path = repo_root / "release-manifest.json"
    _host['_assert_contained_release_path'](repo_root, manifest_path, require_file=True)
    manifest = _host['read_json'](manifest_path)
    source = repo_root / _host['_canonical_portable_relative'](manifest["codex_skill"]["source"])
    _host['_assert_contained_release_path'](repo_root, source)
    destination = _host['_resolve_mutation_root'](destination)
    marker = destination / ".video-autopilot-skill.json"
    _host['_assert_safe_mutation_path'](destination, marker, require_file=True)
    _host['_assert_safe_mutation_path'](destination, marker.with_name(marker.name + ".tmp"), require_file=True)
    has_marker = marker.is_file()
    if destination.exists() and not has_marker and not adopt:
        return {
            "status": "ADOPT_REQUIRED",
            "destination": str(destination),
            "reason": "existing skill is not managed by video-autopilot-kit",
        }
    marker_state = _host['read_json'](marker) if has_marker else {}
    previous_managed, previous_hashes = _host['_validated_install_state'](marker_state) if has_marker else ([], {})
    modified = _host['locally_modified_managed_files'](
        destination, {"managed_hashes": previous_hashes}
    )
    if modified and not adopt:
        return {
            "status": "CONFIRM_REQUIRED",
            "destination": str(destination),
            "reason": "locally modified managed Skill files would be replaced",
            "modified": modified,
        }
    sources = _host['_collect_skill_sources'](
        repo_root, source, manifest["codex_skill"].get("materialize_from", {})
    )
    managed = [relative for relative, _path in sources]
    stale = sorted(set(previous_managed) - set(managed))
    for relative in sorted(set(managed) | set(previous_managed)):
        target = destination / relative
        _host['_assert_safe_mutation_path'](destination, target, require_file=True)
        if target.exists() and not target.is_file():
            raise RuntimeError("managed Skill file conflicts with directory: " + relative)
        if relative in managed:
            _host['_assert_safe_mutation_path'](
                destination, target.with_name(target.name + ".skill-tmp"), require_file=True
            )
    destination.mkdir(parents=True, exist_ok=True)
    for relative, path in sources:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".skill-tmp")
        _host['shutil'].copy2(path, temporary)
        _host['os'].replace(temporary, target)
    for relative in stale:
        target = destination / relative
        if target.is_file():
            target.unlink()
    _host['atomic_json'](
        marker,
        {
            "schema_version": 1,
            "managed_by": "video-autopilot-kit",
            "repo_root": str(repo_root.resolve()),
            "version": manifest["version"],
            "managed_files": managed,
            "managed_hashes": {
                relative: _host['sha256_path'](destination / relative) for relative in managed
            },
            "synced_at": _host['utc_now'](),
        },
    )
    return {"status": "SYNCED", "destination": str(destination), "managed_files": len(managed)}
