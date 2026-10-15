"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations
from pathlib import Path

def _self_test_public_owned_lf(_host) -> None:
    """In-place public-owned sync must remove CRLF before receipt hashing."""
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-public-owned-lf-") as temp:
        root = _host['Path'](temp)
        distribution = _host['Path'](_host['__file__']).resolve().parents[1]
        real_compilers = {"codex-skill/video-autopilot/editkin_design_bridge.py",
                          "codex-skill/video-autopilot/native_graphic_direction.py"}
        for relative in _host['PUBLIC_OWNED_PATHS']:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = (distribution / relative).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n") \
                if relative in real_compilers else b"# fixture\r\nvalue = 1\r\n"
            target.write_bytes(payload)
        copied = _host['_copy_public_owned'](root, root)
        assert copied == list(_host['PUBLIC_OWNED_PATHS'])
        assert all(b"\r" not in (root / relative).read_bytes() for relative in copied)
    print("sync_canonical public-owned LF self-test GREEN")


def _self_test_receipt_schema(_host, repository: Path) -> None:
    import copy
    from public_sync_inventory import canonical_receipt_expected_shape, CANONICAL_PUBLIC_OWNED_PINS

    # Schema controls use synthetic in-memory hashes, never rewrite a working
    # tree receipt to make a changed source set look synchronized. Actual
    # committed-byte provenance remains the separate --verify-receipt gate.
    inventory = {}
    for label, shape in canonical_receipt_expected_shape().items():
        inventory[label] = {
            key: {name: "0" * 64 for name in shape[key]}
            for key in ("derived", "special", "public_owned_analogue")
        }
        inventory[label].update({key: shape[key] for key in ("private_count", "private_control_count")})
    inventory["root"]["public_owned_analogue"].update(CANONICAL_PUBLIC_OWNED_PINS["root"])
    outputs = {name: "0" * 64 for name in _host['sync_expected_output_paths']()}
    payload = {
        "schema": "video-autopilot-public-sync-receipt/v3",
        "assurance": "Detects stale or accidental drift; not an external signature.",
        "canonical_inventory": inventory,
        "canonical_inventory_sha256": _host['hashlib'].sha256(_host['json'].dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "output_hash_semantics": _host['OUTPUT_HASH_SEMANTICS'], "output_count": len(outputs), "outputs": outputs,
        "public_owned": {name: outputs[name] for name in _host['PUBLIC_OWNED_PATHS']},
        "public_destination_required_paths": _host['public_destination_required_paths'](),
    }
    assert not _host['_receipt_schema_errors'](payload)
    missing_output = copy.deepcopy(payload)
    missing_output["outputs"].pop(next(iter(missing_output["outputs"])))
    missing_output["output_count"] -= 1
    assert "sync receipt output key set mismatch" in _host['_receipt_schema_errors'](missing_output)
    extra_output = copy.deepcopy(payload)
    extra_output["outputs"]["src/extra_dir/extra.py"] = "0" * 64
    extra_output["output_count"] += 1
    assert "sync receipt output key set mismatch" in _host['_receipt_schema_errors'](extra_output)
    empty_inventory = copy.deepcopy(payload)
    empty_inventory["canonical_inventory"] = {}
    normalized = _host['json'].dumps({}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    empty_inventory["canonical_inventory_sha256"] = _host['hashlib'].sha256(normalized).hexdigest()
    assert _host['canonical_receipt_shape_errors']({})
    assert _host['_receipt_schema_errors'](empty_inventory)
    print("sync receipt schema negative fixtures GREEN")


def _self_test_text_hash_portability(_host) -> None:
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-text-hash-") as temp:
        root = _host['Path'](temp)
        lf, crlf, bom = root / "lf.txt", root / "crlf.txt", root / "bom.txt"
        changed = root / "changed.txt"
        lf.write_bytes("alpha\nbeta\n".encode("utf-8"))
        crlf.write_bytes("alpha\r\nbeta\r\n".encode("utf-8"))
        bom.write_bytes(b"\xef\xbb\xbf" + "alpha\rbeta\r".encode("utf-8"))
        changed.write_bytes("alpha\ngamma\n".encode("utf-8"))
        assert _host['_text_sha256'](lf) == _host['_text_sha256'](crlf) == _host['_text_sha256'](bom)
        assert _host['_text_sha256'](changed) != _host['_text_sha256'](lf)
    print("sync_canonical portable text-hash self-test GREEN")


def _self_test_try_symlink(_host,
    link: Path, target: Path, *, directory: bool = False
) -> bool:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        return False
    return True


def _self_test_try_windows_junction(_host, link: Path, target: Path) -> bool:
    import os
    import subprocess

    if os.name != "nt":
        return False
    try:
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    metadata = _host['_path_entry_metadata'](link)
    assert metadata is not None and metadata is not False
    assert _host['_is_link_or_reparse'](link, metadata), "Windows junction not recognized"
    return True


def _self_test_external_alias(_host, external, nullcontext, os, patch, path_module, receipt_module, repository):
    outside_target = external / "managed"
    outside_target.mkdir()
    (outside_target / "probe.py").write_text("PRIVATE = True\n", encoding="utf-8")
    outside_alias = repository / "outside-alias"
    if os.name == "nt":
        real_outside_alias = _host['_self_test_try_windows_junction'](
            outside_alias, outside_target
        )
        outside_fixture = (
            "windows-junction" if real_outside_alias else "simulated-alias"
        )
    else:
        real_outside_alias = _host['_self_test_try_symlink'](
            outside_alias, outside_target, directory=True
        )
        outside_fixture = "posix-symlink" if real_outside_alias else "simulated-alias"
    if real_outside_alias:
        resolver_context = nullcontext()
    else:
        # Non-NTFS Windows CI or a policy that blocks all aliases still
        # exercises the containment decision rather than skipping it.
        outside_alias.mkdir()
        real_resolver = _host['_resolve_entry']

        def fixture_resolver(path: Path, *, strict: bool) -> Path:
            if path == outside_alias:
                return outside_target.resolve(strict=strict)
            return real_resolver(path, strict=strict)

        resolver_context = patch.object(
            path_module, "_resolve_entry", side_effect=fixture_resolver
        )
    relative = "outside-alias/probe.py"
    with resolver_context:
        outside_rule = _host['_output_path_boundary_rule'](repository, relative)
        expected_outside_rule = (
            "ancestor-alias" if real_outside_alias else "ancestor-escape"
        )
        assert outside_rule == expected_outside_rule
        public_error = _host['_boundary_error'](relative, outside_rule)
        assert str(outside_target.resolve()) not in public_error

        # Apply preflight and receipt verification must reject the alias
        # before cleanup, hashing, or a downstream validator. Patch only
        # inventory size so this fixture stays focused and deterministic.
        receipt = {"outputs": {relative: "0" * 64}}
        _host['_write_utf8'](repository / _host['SYNC_RECEIPT_PATH'], _host['json'].dumps(receipt) + "\n")
        with patch.object(
            receipt_module, "sync_expected_output_paths", return_value={relative}
        ), patch.object(
            path_module, "sync_expected_output_paths", return_value={relative}
        ):
            try:
                _host['_assert_sync_output_boundaries'](repository)
            except ValueError as exc:
                assert expected_outside_rule in str(exc)
                assert str(outside_target.resolve()) not in str(exc)
            else:
                raise AssertionError("sync apply preflight followed external alias")
            with patch.object(receipt_module, "_receipt_schema_errors", return_value=[]):
                verify_errors = _host['_verify_sync_receipt'](repository)
        assert any(expected_outside_rule in error for error in verify_errors)
        assert str(outside_target.resolve()) not in "; ".join(verify_errors)
    return outside_fixture


def _self_test_output_leaf_alias(_host, nullcontext, patch, path_module, receipt_module, repository, safe):
    leaf_alias = repository / "src" / "alias.py"
    real_leaf_alias = _host['_self_test_try_symlink'](leaf_alias, safe)
    if not real_leaf_alias:
        # GitHub Windows runners can deny os.symlink.  Keep this security
        # branch deterministic by simulating only the no-follow metadata
        # classification, not by skipping the assertion.
        leaf_alias.write_text("SAFE = True\n", encoding="utf-8")
        real_alias_check = _host['_is_link_or_reparse']

        def fixture_alias_check(path: Path, metadata) -> bool:
            if path == leaf_alias:
                return True
            return real_alias_check(path, metadata)

    def leaf_alias_context():
        if real_leaf_alias:
            return nullcontext()
        return patch.object(path_module, "_is_link_or_reparse", fixture_alias_check)

    with leaf_alias_context():
        leaf_rule = _host['_output_path_boundary_rule'](repository, "src/alias.py")
    assert leaf_rule == "output-alias"
    leaf_relative = "src/alias.py"
    _host['_write_utf8'](
        repository / _host['SYNC_RECEIPT_PATH'],
        _host['json'].dumps({"outputs": {leaf_relative: "0" * 64}}) + "\n",
    )
    with (
        leaf_alias_context(),
        patch.object(receipt_module, "sync_expected_output_paths", return_value={leaf_relative}),
        patch.object(receipt_module, "_receipt_schema_errors", return_value=[]),
    ):
        leaf_verify_errors = _host['_verify_sync_receipt'](repository)
    assert any("output-alias" in error for error in leaf_verify_errors)


def _self_test_output_path_boundaries(_host) -> None:
    """Exercise safe files, aliases, external ancestors, and receipt verify."""
    import os
    import sys
    from contextlib import nullcontext
    from unittest.mock import patch

    import public_sync_paths as path_module
    import public_sync_receipts as receipt_module

    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-sync-boundary-") as temp:
        root = _host['Path'](temp)
        repository, external = root / "repository", root / "external-private"
        repository.mkdir()
        external.mkdir()

        safe = repository / "src" / "safe.py"
        safe.parent.mkdir()
        safe.write_text("SAFE = True\n", encoding="utf-8")
        assert not _host['_output_path_boundary_violations'](repository, {"src/safe.py"})

        _self_test_output_leaf_alias(_host, nullcontext, patch, path_module, receipt_module, repository, safe)

        inside_target = repository / "inside-target"
        inside_target.mkdir()
        (inside_target / "probe.py").write_text("SAFE = True\n", encoding="utf-8")
        inside_alias = repository / "inside-alias"
        real_inside_alias = _host['_self_test_try_symlink'](
            inside_alias, inside_target, directory=True
        )
        if not real_inside_alias:
            inside_alias.mkdir()
            (inside_alias / "probe.py").write_text("SAFE = True\n", encoding="utf-8")
            baseline_alias_check = _host['_is_link_or_reparse']

            def fixture_inside_alias(path: Path, metadata) -> bool:
                if path == inside_alias:
                    return True
                return baseline_alias_check(path, metadata)

        inside_context = (
            nullcontext()
            if real_inside_alias
            else patch.object(path_module, "_is_link_or_reparse", fixture_inside_alias)
        )
        with inside_context:
            inside_rule = _host['_output_path_boundary_rule'](
                repository, "inside-alias/probe.py"
            )
        assert inside_rule == "ancestor-alias"

        outside_fixture = _self_test_external_alias(_host, external, nullcontext, os, patch, path_module, receipt_module, repository)
    print(f"sync_canonical output-boundary self-test GREEN ({outside_fixture})")


def _self_test_reserved_public_marker(_host) -> None:
    """Canonical inputs cannot impersonate already-sanitized public outputs."""
    managed_path = next(iter(_host['SANITIZERS']))
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-marker-test-") as temp:
        root = _host['Path'](temp)
        source = root / "canonical-input.txt"
        source.write_text(_host['PUBLIC_FIXTURE'] + "\n", encoding="utf-8")
        try:
            _host['_copy_text'](source, root / "public-output.txt", managed_path)
        except ValueError as exc:
            assert "reserved public privacy marker" in str(exc)
        else:
            raise AssertionError("reserved public marker bypassed canonical preflight")
    print("sync_canonical reserved-marker self-test GREEN")
