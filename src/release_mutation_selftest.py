"""Owned install/update/rollback mutation-boundary fixtures."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from types import ModuleType

if __package__:
    from .release_test_support import _directory_alias, _remove_directory_alias
else:
    from release_test_support import _directory_alias, _remove_directory_alias

def _self_test_interrupted_update(archive, base, digest, manager):
    pending_install = base / "pending-transaction-install"
    manager.apply_release_archive(archive, pending_install, digest, auto=False)
    pending_readme = pending_install / "README.md"
    pending_readme.write_text("pending rollback fixture\n", encoding="utf-8")
    pending_backups = pending_install / manager.STATE_DIR / "backups"
    before_pending = {path.name for path in pending_backups.iterdir()}
    original_replace = manager.os.replace

    def interrupt_after_readme_replace(source, destination):
        original_replace(source, destination)
        if (
            Path(destination).resolve() == pending_readme.resolve()
            and str(source).endswith(".update-tmp")
        ):
            raise KeyboardInterrupt("simulated process interruption")

    manager.os.replace = interrupt_after_readme_replace
    try:
        try:
            manager.apply_release_archive(archive, pending_install, digest, auto=False)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("interruption fixture did not stop the update")
    finally:
        manager.os.replace = original_replace
    pending_ids = {path.name for path in pending_backups.iterdir()} - before_pending
    assert len(pending_ids) == 1
    pending_id = pending_ids.pop()
    pending_record = manager.read_json(
        pending_backups / pending_id / "transaction.json"
    )
    assert pending_record["status"] == "PENDING"
    assert "README.md" in pending_record["replaced"], pending_record
    assert manager.rollback(pending_install, pending_id)["status"] == "ROLLED_BACK"
    assert pending_readme.read_text(encoding="utf-8") == "pending rollback fixture\n"


def _self_test_apply_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict, outside: Path, marker: Path
) -> None:
    _self_test_archive_staging_race(manager, base, built)
    archive, digest = Path(built["archive"]), built["sha256"]

    state_type_install = base / "state-type-install"
    state_type_path = state_type_install / manager.STATE_DIR / "install-state.json"
    state_type_path.mkdir(parents=True)
    state_type_readme = state_type_install / "README.md"
    state_type_readme.write_text("legacy unchanged\n", encoding="utf-8")
    try:
        manager.apply_release_archive(archive, state_type_install, digest, auto=False)
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
        assert str(outside) not in str(exc)
    else:
        raise AssertionError("updater treated an install-state directory as absent")
    assert state_type_readme.read_text(encoding="utf-8") == "legacy unchanged\n"
    assert not (state_type_install / manager.STATE_DIR / "backups").exists()

    install = base / "junction-install"
    install.mkdir()
    alias = install / "src"
    _directory_alias(alias, outside)
    try:
        try:
            manager.apply_release_archive(archive, install, digest, auto=False)
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "src/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("updater wrote through a managed directory alias")
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
        assert not (install / manager.STATE_DIR).exists()
    finally:
        _remove_directory_alias(alias)

    state_install = base / "state-traversal-install"
    first = manager.apply_release_archive(archive, state_install, digest, auto=False)
    state_path = state_install / manager.STATE_DIR / "install-state.json"
    state = manager.read_json(state_path)
    state["managed_files"].append("../../outside-state.txt")
    state["managed_hashes"]["../../outside-state.txt"] = "0" * 64
    manager.atomic_json(state_path, state)
    (state_install / "README.md").write_text("repair fixture\n", encoding="utf-8")
    backups = state_install / manager.STATE_DIR / "backups"
    before_backups = sorted(path.name for path in backups.iterdir())
    try:
        manager.apply_release_archive(archive, state_install, digest, auto=False)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-state" not in str(exc)
    else:
        raise AssertionError("updater trusted a traversal path from install state")
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert sorted(path.name for path in backups.iterdir()) == before_backups

    _self_test_interrupted_update(archive, base, digest, manager)
    assert first["status"] == "UPDATED"

def _self_test_rollback_missing_payload(archive, base, digest, manager):
    rollback_payload_install = base / "rollback-payload-install"
    manager.apply_release_archive(archive, rollback_payload_install, digest, auto=False)
    rollback_payload_readme = rollback_payload_install / "README.md"
    rollback_payload_readme.write_text("same-version repair fixture\n", encoding="utf-8")
    repair = manager.apply_release_archive(
        archive, rollback_payload_install, digest, auto=False
    )
    repair_backup = (
        rollback_payload_install / manager.STATE_DIR / "backups" / repair["transaction"]
    )
    missing_backup = repair_backup / "files" / "README.md"
    missing_payload = missing_backup.read_bytes()
    missing_backup.unlink()
    repaired_readme = rollback_payload_readme.read_bytes()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "managed mutation file is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating every backup source")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    missing_backup.write_bytes(missing_payload)

    previous_state_path = repair_backup / "previous-install-state.json"
    previous_state_path.unlink()
    previous_state_path.mkdir()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("rollback treated a previous-state directory as absent")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    previous_state_path.rmdir()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "previous-state presence is inconsistent" in str(exc)
    else:
        raise AssertionError("rollback accepted a missing declared previous state")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    manager.atomic_json(previous_state_path, {})
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating previous install state")
    assert rollback_payload_readme.read_bytes() == repaired_readme


def _self_test_rollback_state_paths(archive, base, digest, manager):
    rollback_state_install = base / "rollback-state-install"
    rollback_state_result = manager.apply_release_archive(
        archive, rollback_state_install, digest, auto=False
    )
    rollback_state_path = (
        rollback_state_install / manager.STATE_DIR / "install-state.json"
    )
    manager.atomic_json(rollback_state_path, {})
    rollback_state_readme = (rollback_state_install / "README.md").read_bytes()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating current install state")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme
    rollback_state_path.unlink()
    rollback_state_path.mkdir()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("rollback treated a current-state directory as absent")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme
    rollback_state_path.rmdir()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "current-state presence is inconsistent" in str(exc)
    else:
        raise AssertionError("rollback accepted a missing committed install state")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme


def _self_test_rollback_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict, outside: Path, marker: Path
) -> None:
    archive, digest = Path(built["archive"]), built["sha256"]
    rollback_install = base / "rollback-traversal-install"
    applied = manager.apply_release_archive(
        archive, rollback_install, digest, auto=False
    )
    transaction = applied["transaction"]
    record_path = (
        rollback_install / manager.STATE_DIR / "backups" / transaction
        / "transaction.json"
    )
    record = manager.read_json(record_path)
    record["created"].append("../../outside-rollback.txt")
    manager.atomic_json(record_path, record)
    installed_readme = (rollback_install / "README.md").read_bytes()
    try:
        manager.rollback(rollback_install, transaction)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-rollback" not in str(exc)
    else:
        raise AssertionError("rollback trusted a traversal path from transaction state")
    assert (rollback_install / "README.md").read_bytes() == installed_readme
    assert marker.read_text(encoding="utf-8") == "unchanged"

    rollback_alias_install = base / "rollback-junction-install"
    rollback_alias_result = manager.apply_release_archive(
        archive, rollback_alias_install, digest, auto=False
    )
    rollback_alias = rollback_alias_install / "src"
    shutil.rmtree(rollback_alias)
    _directory_alias(rollback_alias, outside)
    alias_readme = (rollback_alias_install / "README.md").read_bytes()
    try:
        try:
            manager.rollback(
                rollback_alias_install, rollback_alias_result["transaction"]
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "src/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("rollback mutated through a managed directory alias")
        assert (rollback_alias_install / "README.md").read_bytes() == alias_readme
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
    finally:
        _remove_directory_alias(rollback_alias)

    _self_test_rollback_state_paths(archive, base, digest, manager)

    _self_test_rollback_missing_payload(archive, base, digest, manager)

def _self_test_skill_mutation_boundaries(
    manager: ModuleType, base: Path, outside: Path, marker: Path
) -> None:
    skill = base / "junction-skill"
    skill.mkdir()
    skill_alias = skill / "references"
    _directory_alias(skill_alias, outside)
    try:
        try:
            manager.sync_codex_skill(manager.ROOT, skill, adopt=True)
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "references/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("Skill sync wrote through a managed directory alias")
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
        assert not (skill / ".video-autopilot-skill.json").exists()
    finally:
        _remove_directory_alias(skill_alias)

    marker_type_skill = base / "marker-type-skill"
    marker_type_skill.mkdir()
    marker_type = marker_type_skill / ".video-autopilot-skill.json"
    marker_type.mkdir()
    marker_keep = marker_type_skill / "keep.txt"
    marker_keep.write_text("unchanged", encoding="utf-8")
    try:
        manager.sync_codex_skill(manager.ROOT, marker_type_skill, adopt=True)
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("Skill sync treated a marker directory as absent")
    assert marker_keep.read_text(encoding="utf-8") == "unchanged"

    marker_skill = base / "marker-traversal-skill"
    assert manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)[
        "status"
    ] == "SYNCED"
    skill_state_path = marker_skill / ".video-autopilot-skill.json"
    skill_state = manager.read_json(skill_state_path)
    manager.atomic_json(skill_state_path, {})
    try:
        manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("Skill sync accepted a truncated marker")
    manager.atomic_json(skill_state_path, skill_state)
    skill_state["managed_files"].append("../../outside-skill.txt")
    skill_state["managed_hashes"]["../../outside-skill.txt"] = "0" * 64
    manager.atomic_json(skill_state_path, skill_state)
    try:
        manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-skill" not in str(exc)
    else:
        raise AssertionError("Skill sync trusted a traversal path from its marker")
    assert marker.read_text(encoding="utf-8") == "unchanged"

def _self_test_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict
) -> None:
    outside = base / "mutation-boundary-outside"
    outside.mkdir()
    marker = outside / "marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    _self_test_apply_mutation_boundaries(manager, base, built, outside, marker)
    _self_test_rollback_mutation_boundaries(manager, base, built, outside, marker)
    _self_test_skill_mutation_boundaries(manager, base, outside, marker)


def _self_test_archive_staging_race(manager, base, built):
    """A valid same-version archive swap cannot cross the validation barrier."""
    import hashlib
    import zipfile
    original = Path(built["archive"])
    changed = base / "staging-race-alternate.zip"
    with zipfile.ZipFile(original) as package:
        infos = package.infolist()
        payloads = {info.filename: package.read(info) for info in infos}
    index = json.loads(payloads["release-index.json"].decode("utf-8"))
    payloads["README.md"] = b"Changed source fixture after initial validation.\n"
    row = next(item for item in index["files"] if item["path"] == "README.md")
    row.update(size=len(payloads["README.md"]),
               sha256=hashlib.sha256(payloads["README.md"]).hexdigest())
    payloads["release-index.json"] = json.dumps(index).encode("utf-8")
    with zipfile.ZipFile(changed, "w", zipfile.ZIP_DEFLATED) as package:
        for info in infos:
            package.writestr(info, payloads[info.filename])
    assert manager.verify_archive(changed)["version"] == built["version"]
    race = base / "staging-race.zip"
    race.write_bytes(original.read_bytes())
    target = base / "staging-race-install"
    stage_archive = manager.stage_verified_archive

    def swap_before_stage(archive, stage, expected_hash):
        race.write_bytes(changed.read_bytes())
        return stage_archive(archive, stage, expected_hash)

    manager.stage_verified_archive = swap_before_stage
    try:
        try:
            manager.apply_release_archive(race, target, None, auto=False)
        except RuntimeError as exc:
            assert str(exc) == "archive changed between validation and staging"
        else:
            raise AssertionError("same-version archive swap crossed the staging barrier")
    finally:
        manager.stage_verified_archive = stage_archive
    assert not target.exists(), "archive swap mutated the installation"
