"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _self_test_sync(_module_globals, temp: Path) -> None:
    sync_workspace = _module_globals['Path'](temp) / "sync-workspace"
    source = sync_workspace / "canonical"
    destination = _module_globals['Path'](temp) / "installed"
    source.mkdir(parents=True)
    canonical = source / "note.txt"
    canonical.write_text("v1\n", encoding="utf-8")
    skill = {
        "id": "sync-probe",
        "source": "canonical",
        "destination": "sync-probe",
        "include": ["**/*.txt"],
    }

    # First copy: a missing destination is safe and establishes a baseline.
    first = _module_globals['_skill_sync_status'](sync_workspace, skill, destination)
    assert first["status"] == "MISSING"
    assert first["missing"] == ["note.txt"]
    applied = _module_globals['_skill_sync_apply'](sync_workspace, skill, destination)
    assert applied["status"] == "GREEN" and applied["copied"] == 1
    assert (destination / _module_globals['SYNC_MARKER_NAME']).is_file()

    # Idempotent sync writes no managed file and keeps destination extras.
    extra = destination / "local-only.txt"
    extra.write_text("keep me", encoding="utf-8")
    repeated = _module_globals['_skill_sync_apply'](sync_workspace, skill, destination)
    assert repeated["status"] == "GREEN" and repeated["copied"] == 0
    assert extra.read_text(encoding="utf-8") == "keep me"

    # Source-only movement from the managed baseline is safe to apply.
    canonical.write_text("v2\n", encoding="utf-8")
    source_only = _module_globals['_skill_sync_status'](sync_workspace, skill, destination)
    assert source_only["status"] == "DRIFT"
    assert source_only["drift"] == ["note.txt"]
    updated = _module_globals['_skill_sync_apply'](sync_workspace, skill, destination)
    assert updated["status"] == "GREEN" and updated["copied"] == 1

    # Destination-only work is protected and blocks the whole Skill write.
    installed = destination / "note.txt"
    installed.write_text("local edit\n", encoding="utf-8")
    destination_only = _module_globals['_skill_sync_status'](sync_workspace, skill, destination)
    assert destination_only["status"] == "CONFLICT"
    assert destination_only["conflict"] == ["note.txt"]
    blocked = _module_globals['_skill_sync_apply'](sync_workspace, skill, destination)
    assert blocked["status"] == "CONFLICT" and blocked["copied"] == 0
    assert installed.read_text(encoding="utf-8") == "local edit\n"

    # A simultaneous source change remains blocked until source is accepted.
    canonical.write_text("v3\n", encoding="utf-8")
    both_changed = _module_globals['_skill_sync_status'](sync_workspace, skill, destination)
    assert both_changed["status"] == "CONFLICT"
    assert both_changed["conflict"] == ["note.txt"]
    accepted = _module_globals['_skill_sync_apply'](
        sync_workspace, skill, destination, accept_source_conflicts=True
    )
    assert accepted["status"] == "GREEN" and accepted["copied"] == 1
    assert accepted["accepted_source_conflicts"] is True
    assert installed.read_text(encoding="utf-8") == "v3\n"
    assert extra.read_text(encoding="utf-8") == "keep me"

    # An exact pre-existing copy can bootstrap a missing marker without copy.
    bootstrap = _module_globals['Path'](temp) / "bootstrap"
    bootstrap.mkdir()
    _module_globals['shutil'].copy2(canonical, bootstrap / "note.txt")
    bootstrapped = _module_globals['_skill_sync_apply'](sync_workspace, skill, bootstrap)
    assert bootstrapped["status"] == "GREEN" and bootstrapped["copied"] == 0
    assert (bootstrap / _module_globals['SYNC_MARKER_NAME']).is_file()
    _self_test_canonical_guard(_module_globals, temp, sync_workspace)


def _self_test_canonical_guard(_module_globals, temp: Path, sync_workspace: Path) -> None:
    # A codex-canonical Skill is never a copy target: another tree is refused before any write (even with
    # accept_source_conflicts), the canonical tree only re-records hashes, and a copy inside the workspace
    # is not accepted as the authority.
    import os as _os
    env_name = "VA_KERNEL_SELFTEST_CANONICAL"
    canonical_tree = _module_globals['Path'](temp) / "codex-canonical"
    stale_tree = _module_globals['Path'](temp) / "stale-copy"
    for tree, text in ((canonical_tree, "canonical\n"), (stale_tree, "stale\n")):
        tree.mkdir()
        (tree / "SKILL.md").write_text("---\nname: canon-probe\n---\n", encoding="utf-8")
        (tree / "note.txt").write_text(text, encoding="utf-8")
    canon_skill = {"id": "canon-probe", "destination": "canon-probe", "include": ["**/*.txt"],
                   "source_authority": {"kind": "codex-canonical", "environment": env_name}}
    saved = _os.environ.get(env_name)
    try:
        _os.environ[env_name] = str(stale_tree / "SKILL.md")
        refused = _module_globals['_skill_sync_apply'](
            sync_workspace, canon_skill, canonical_tree, accept_source_conflicts=True)
        assert refused["status"] == "REFUSED" and refused["copied"] == 0
        assert (canonical_tree / "note.txt").read_text(encoding="utf-8") == "canonical\n"
        assert not (canonical_tree / _module_globals['SYNC_MARKER_NAME']).exists()
        _os.environ[env_name] = str(canonical_tree / "SKILL.md")
        recorded = _module_globals['_skill_sync_apply'](sync_workspace, canon_skill, canonical_tree)
        assert recorded["status"] == "GREEN" and recorded["copied"] == 0
        assert (canonical_tree / _module_globals['SYNC_MARKER_NAME']).is_file()
        inside = sync_workspace / ".claude" / "skills" / "canon-probe"
        inside.mkdir(parents=True)
        (inside / "SKILL.md").write_text("---\nname: canon-probe\n---\n", encoding="utf-8")
        _os.environ[env_name] = str(inside / "SKILL.md")
        try:
            _module_globals['_skill_source'](sync_workspace, canon_skill)
        except ValueError:
            pass
        else:
            raise AssertionError("a workspace copy was accepted as the canonical Skill")
    finally:
        if saved is None:
            _os.environ.pop(env_name, None)
        else:
            _os.environ[env_name] = saved

def self_test(_module_globals) -> None:
    workspace, manifest = _module_globals['load_manifest']()
    assert manifest["architecture_version"] == "7.0"
    assert set(manifest["planes"]) == {
        "control", "decision", "design", "asset", "execution", "evidence"
    }
    assert (workspace / manifest["planes"]["control"][0]).is_file()
    assert _module_globals['inventory'](workspace)["roots"]["skills"]["files"] > 0
    with _module_globals['tempfile'].TemporaryDirectory(prefix="kernel-") as temp:
        probe = _module_globals['Path'](temp) / "x.txt"
        probe.write_text("ok", encoding="utf-8")
        assert _module_globals['_hash'](probe) == _module_globals['hashlib'].sha256(b"ok").hexdigest()
        alias = _module_globals['Path'](temp) / "x-alias.txt"
        _module_globals['os'].link(probe, alias)
        metrics = _module_globals['_directory_metrics'](_module_globals['Path'](temp))
        assert metrics["logical_bytes"] == 4
        assert metrics["physical_bytes"] == 2
        assert metrics["hardlink_saved_bytes"] == 2

        _module_globals['_self_test_sync'](_module_globals['Path'](temp))
    print("project_kernel self-test GREEN")

def main(_module_globals, argv: list[str] | None = None) -> int:
    parser = _module_globals['argparse'].ArgumentParser(description="Video Autopilot manifest control plane")
    subs = parser.add_subparsers(dest="command", required=True)
    doctor_cmd = subs.add_parser("doctor")
    doctor_cmd.add_argument("--quick", action="store_true")
    doctor_cmd.add_argument("--json", action="store_true")
    inv_cmd = subs.add_parser("inventory")
    inv_cmd.add_argument("--json", action="store_true")
    sync_cmd = subs.add_parser("sync")
    sync_cmd.add_argument("action", choices=("status", "apply", "record"), nargs="?", default="status")
    sync_cmd.add_argument("--skill", default=None)
    sync_cmd.add_argument(
        "--accept-source-conflicts",
        action="store_true",
        help="explicitly replace conflicted installed files with canonical source",
    )
    sync_cmd.add_argument("--json", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        _module_globals['self_test']()
        return 0
    if args.command == "doctor":
        result = _module_globals['doctor'](quick=args.quick)
        if args.json:
            print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2))
        else:
            _module_globals['_print_human'](result, "KERNEL")
        return 0 if result["status"] == "GREEN" else 1
    if args.command == "inventory":
        result = _module_globals['inventory']()
        print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2))
        return 0
    try:
        if args.action == "apply":
            result = _module_globals['sync_apply'](
                skill_id=args.skill,
                accept_source_conflicts=args.accept_source_conflicts,
            )
        elif args.action == "record":
            result = _module_globals['sync_record'](skill_id=args.skill)
        else:
            result = _module_globals['sync_status'](skill_id=args.skill)
    except ValueError as error:
        print(f"SYNC REFUSED {error}")
        return 2
    if args.json:
        print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2))
    else:
        _module_globals['_print_human'](result, "SYNC")
        for row in result["skills"]:
            print(f"[{row['status']}] {row['id']}: {row['matched']}/{row['declared_files']}")
    return 0 if result["status"] == "GREEN" else 1
