#!/usr/bin/env python3
"""Synchronize redistributable Video Autopilot sources into the public kit.

The canonical workspace may contain user media, analytics, generated previews,
private preferences and machine paths. This deterministic synchronizer uses a
closed-world inventory, text-only copies, and privacy preflight transforms.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath

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
from public_sync_paths import _path_entry_metadata, _is_link_or_reparse, _is_contained_path, _resolve_entry, _safe_relative_output_path, _output_path_boundary_rule, _output_path_boundary_violations, _boundary_error, _assert_sync_output_boundaries, _write_utf8, _text_sha256, OUTPUT_HASH_SEMANTICS
from public_sync_receipts import _write_sync_receipt, _receipt_schema_errors, _verify_sync_receipt
from public_cleanup_bundle import (
    BUNDLE_PATH, copy_cleanup_source, validate_cleanup_source,
    verify_cleanup_bundle, write_cleanup_bundle,
)



# No complete canonical-to-public workflow transform is registered. These
# adapters implement a media-only public controller and must not be overwritten
# by the private original-source controller, including in an empty staging tree.
PUBLIC_WORKFLOW_ADAPTERS = ('engine_continuity.py', 'workflow_contract.py', 'workflow_state.py', 'workflow_receipts.py', 'workflow_material_receipts.py', 'workflow_transport.py', 'workflow_audit_binding.py', 'workflow_context_chain.py', 'workflow_render_retry.py', 'workflow_binding_fixture.py', 'workflow_primitives.py', 'workflow_contract_source.py', 'workflow_receipt_store.py', 'public_workflow_sources.py', 'workflow_contract.json')


def _workflow_adapter_text(path: Path) -> str:
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400
            or not 0 < before.st_size <= 1024 * 1024):
        raise ValueError("Public workflow derivation requires a bounded regular source: " + path.name)
    def identity(info):
        return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size,
                getattr(info, "st_file_attributes", 0) & 0x400)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if identity(before) != identity(opened):
            raise ValueError("Public workflow source path/handle changed: " + path.name)
        data = stream.read(1024 * 1024 + 1)
        after_handle, after_path = os.fstat(stream.fileno()), path.lstat()
        if (len(data) != before.st_size or identity(opened) != identity(after_handle)
                or identity(before) != identity(after_path)
                or (opened.st_mtime_ns, opened.st_ctime_ns) != (after_handle.st_mtime_ns, after_handle.st_ctime_ns)
                or (before.st_mtime_ns, before.st_ctime_ns) != (after_path.st_mtime_ns, after_path.st_ctime_ns)):
            raise ValueError("Public workflow source changed during read: " + path.name)
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def _assert_public_workflow_derivation(canonical: Path, distribution_source: Path) -> None:
    from public_workflow_distribution import validate_adapters
    validate_adapters(canonical, distribution_source, _workflow_adapter_text)






















def _transform(text: str, name: str = "") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in REPLACEMENTS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in MODULE_REPLACEMENTS.get(name, ()):
        text = pattern.sub(replacement, text)
    if name == "project_paths.py":
        required = (
            'MANIFEST_NAME = MANIFEST_NAMES[0]', '"release-manifest.json"',
            'for name in MANIFEST_NAMES',
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


def _assert_public_design_bridge_contract(text: str) -> None:
    """Reject an old public compiler surface before regenerating owned outputs.

    This is a source-contract preflight; executable policy behavior is covered by
    compiler tests and the consuming application's strict envelope validation.
    It reads the original public source and never imports the canonical bridge.
    """
    tree = ast.parse(text)
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    compiler = functions.get("compile_brief")
    strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    source_files = next((node.value for node in tree.body if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "SOURCE_FILES" for target in node.targets)), None)
    dependencies = ast.literal_eval(source_files) if source_files is not None else ()
    keys = {key.value for node in ast.walk(compiler) if isinstance(node, ast.Dict) for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)} if compiler else set()
    if (compiler is None or "review_policy" not in {arg.arg for arg in compiler.args.kwonlyargs}
            or "--review-policy-json" not in strings or "review_policy.py" not in dependencies
            or not {"reviewPolicy", "reviewPolicySha256"}.issubset(keys)):
        raise ValueError("public design compiler lacks the current creator policy envelope contract")

    def is_expression(node, expression):
        # Assignment targets have Store contexts; the same parsed expression
        # has Load contexts. Compare their structure without that distinction.
        observed = ast.dump(node, include_attributes=False).replace("ctx=Store()", "ctx=Load()")
        return observed == ast.dump(
            ast.parse(expression, mode="eval").body, include_attributes=False)

    imported = any(isinstance(node, ast.ImportFrom) and node.module == "native_graphic_direction"
                   and any(name.name == "normalize_native_graphic_direction" and name.asname is None
                           for name in node.names) for node in compiler.body)
    loops = [node for node in compiler.body if isinstance(node, ast.For)
             and is_expression(node.target, "beat") and is_expression(node.iter, 'request["beats"]')]
    consumed = False
    for loop in loops:
        # This deliberately recognizes the real producer, not a string, unused
        # helper import, or direction preserved only in request metadata.
        if len(loop.body) != 4:
            continue
        normalized, recipe, attach, append = loop.body
        consumed = (
            isinstance(normalized, ast.Assign) and len(normalized.targets) == 1
            and is_expression(normalized.targets[0], "direction")
            and is_expression(normalized.value,
                              'normalize_native_graphic_direction(beat["nativeTemplateDirection"], '
                              'format=request["format"]) if "nativeTemplateDirection" in beat else None')
            and isinstance(recipe, ast.Assign) and len(recipe.targets) == 1
            and is_expression(recipe.targets[0], "recipe") and isinstance(recipe.value, ast.Call)
            and is_expression(recipe.value.func, "compile_recipe")
            and isinstance(attach, ast.If) and is_expression(attach.test, "direction is not None")
            and not attach.orelse and len(attach.body) == 1
            and isinstance(attach.body[0], ast.Assign) and len(attach.body[0].targets) == 1
            and is_expression(attach.body[0].targets[0], 'recipe["nativeTemplateDirection"]')
            and is_expression(attach.body[0].value, "direction")
            and isinstance(append, ast.Expr)
            and is_expression(append.value, 'recipes.append({"beatId": beat["id"], "recipe": recipe})')
        )
        if consumed:
            break
    returned = any(isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
                   and any(isinstance(key, ast.Constant) and key.value == "recipes"
                           and is_expression(value, "recipes")
                           for key, value in zip(node.value.keys, node.value.values))
                   for node in compiler.body)
    if "native_graphic_direction.py" not in dependencies or not imported or not consumed or not returned:
        raise ValueError("public design compiler lacks actual native graphic direction recipe consumption")


def _assert_public_native_direction_helper(text: str) -> None:
    """Require the public-owned normalizer instead of a stale fixture module."""
    tree = ast.parse(text)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    normalizer = functions.get("normalize_native_graphic_direction")
    if (normalizer is None or [arg.arg for arg in normalizer.args.args] != ["raw"]
            or [arg.arg for arg in normalizer.args.kwonlyargs] != ["format"]
            or not {"_closed_object", "_relative_luminance", "_contrast_ratio"} <= set(functions)):
        raise ValueError("public-owned native graphic direction helper contract is missing")


def _copy_public_owned(distribution_source: Path, repository: Path) -> list[str]:
    """Copy public-kit-owned text with deterministic LF bytes.

    The release archive normalizes text payloads to LF.  Normalizing here too
    keeps the committed sync receipt valid after Git checkout/archive filters
    on Windows and makes the receipt portable across supported platforms.
    """
    generated_mirrors = {
        "codex-skill/video-autopilot/design_runtime/src/aesthetic_score.py": "src/aesthetic_score.py",
        "codex-skill/video-autopilot/design_runtime/src/design_system_v6.py": "src/design_system_v6.py",
        "codex-skill/video-autopilot/design_runtime/knowledge/runtime/aesthetic_standard.json": "knowledge/runtime/aesthetic_standard.json",
        "codex-skill/video-autopilot/design_runtime/knowledge/runtime/design_reference_dna.json": "knowledge/runtime/design_reference_dna.json",
    }
    helper = distribution_source / "codex-skill/video-autopilot/native_graphic_direction.py"
    _assert_public_native_direction_helper(helper.read_text(encoding="utf-8-sig"))
    prepared: list[tuple[str, str]] = []
    for relative in PUBLIC_OWNED_PATHS:
        generated = repository / generated_mirrors[relative] if relative in generated_mirrors else None
        source = generated if generated is not None and generated.is_file() else distribution_source / relative
        if not source.is_file():
            raise FileNotFoundError("public-kit-owned source missing: " + relative)
        source_root = repository if source == generated else distribution_source
        source_relative = source.relative_to(source_root).as_posix()
        boundary = _output_path_boundary_rule(source_root, source_relative)
        if boundary is not None:
            raise ValueError("unsafe public-kit-owned input: " + relative)
        text = _workflow_adapter_text(source)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if relative == "codex-skill/video-autopilot/editkin_design_bridge.py":
            _assert_public_design_bridge_contract(text)
        hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
        if hits:
            raise ValueError(f"privacy token in public-kit-owned source {source}: {hits}")
        prepared.append((relative, text))
    for relative, text in prepared:
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_utf8(destination, text)
    return [relative for relative, _text in prepared]


def _self_test_public_owned_lf() -> None:
    """In-place public-owned sync must remove CRLF before receipt hashing."""
    with tempfile.TemporaryDirectory(prefix="video-autopilot-public-owned-lf-") as temp:
        root = Path(temp)
        distribution = Path(__file__).resolve().parents[1]
        real_compilers = {"codex-skill/video-autopilot/editkin_design_bridge.py",
                          "codex-skill/video-autopilot/native_graphic_direction.py"}
        for relative in PUBLIC_OWNED_PATHS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = (distribution / relative).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n") \
                if relative in real_compilers else b"# fixture\r\nvalue = 1\r\n"
            target.write_bytes(payload)
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
    expected.update(Path(name).name for name in PUBLIC_OWNED_PATHS
                    if Path(name).parent.as_posix() == "codex-skill/video-autopilot/references")
    actual = {
        path.relative_to(reference_root).as_posix()
        for path in reference_root.rglob("*.md")
        if path.is_file()
    }
    return sorted(actual - expected)








def _self_test_receipt_schema(repository: Path) -> None:
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
    outputs = {name: "0" * 64 for name in sync_expected_output_paths()}
    payload = {
        "schema": "video-autopilot-public-sync-receipt/v3",
        "assurance": "Detects stale or accidental drift; not an external signature.",
        "canonical_inventory": inventory,
        "canonical_inventory_sha256": hashlib.sha256(json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "output_hash_semantics": OUTPUT_HASH_SEMANTICS, "output_count": len(outputs), "outputs": outputs,
        "public_owned": {name: outputs[name] for name in PUBLIC_OWNED_PATHS},
        "public_destination_required_paths": public_destination_required_paths(),
    }
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
    distribution_source = (
        distribution_source.resolve()
        if distribution_source is not None
        else Path(__file__).resolve().parents[1]
    )
    _assert_public_workflow_derivation(canonical, distribution_source)
    canonical_evidence = validate_canonical_inventory(canonical)
    cleanup = Path.home() / ".codex" / "skills" / "code-cleanup-helper"
    cleanup_sources = validate_cleanup_source(cleanup)
    # This must precede cleanup, mkdir, and every copy.  A malicious junction
    # must not turn even a nominally local cleanup/write into an external one.
    _assert_sync_output_boundaries(repository)
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
    for relative in CLEANUP_HELPER_FILES:
        destination = repository / "tools" / "code-cleanup-helper" / relative
        if relative == "audit.config.json":
            _copy_public_cleanup_config(cleanup / relative, destination)
        else:
            copy_cleanup_source(cleanup, relative, destination)
        copied.append(destination.relative_to(repository).as_posix())
    write_cleanup_bundle(cleanup, repository, cleanup_sources)
    copied.append(BUNDLE_PATH)
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




def _self_test_text_hash_portability() -> None:
    with tempfile.TemporaryDirectory(prefix="video-autopilot-text-hash-") as temp:
        root = Path(temp)
        lf, crlf, bom = root / "lf.txt", root / "crlf.txt", root / "bom.txt"
        changed = root / "changed.txt"
        lf.write_bytes("alpha\nbeta\n".encode("utf-8"))
        crlf.write_bytes("alpha\r\nbeta\r\n".encode("utf-8"))
        bom.write_bytes(b"\xef\xbb\xbf" + "alpha\rbeta\r".encode("utf-8"))
        changed.write_bytes("alpha\ngamma\n".encode("utf-8"))
        assert _text_sha256(lf) == _text_sha256(crlf) == _text_sha256(bom)
        assert _text_sha256(changed) != _text_sha256(lf)
    print("sync_canonical portable text-hash self-test GREEN")


def _self_test_try_symlink(
    link: Path, target: Path, *, directory: bool = False
) -> bool:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        return False
    return True


def _self_test_try_windows_junction(link: Path, target: Path) -> bool:
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
    metadata = _path_entry_metadata(link)
    assert metadata is not None and metadata is not False
    assert _is_link_or_reparse(link, metadata), "Windows junction not recognized"
    return True


def _self_test_output_path_boundaries() -> None:
    """Exercise safe files, aliases, external ancestors, and receipt verify."""
    import os
    import sys
    from contextlib import nullcontext
    from unittest.mock import patch

    import public_sync_paths as path_module
    import public_sync_receipts as receipt_module

    with tempfile.TemporaryDirectory(prefix="video-autopilot-sync-boundary-") as temp:
        root = Path(temp)
        repository, external = root / "repository", root / "external-private"
        repository.mkdir()
        external.mkdir()

        safe = repository / "src" / "safe.py"
        safe.parent.mkdir()
        safe.write_text("SAFE = True\n", encoding="utf-8")
        assert not _output_path_boundary_violations(repository, {"src/safe.py"})

        leaf_alias = repository / "src" / "alias.py"
        real_leaf_alias = _self_test_try_symlink(leaf_alias, safe)
        if not real_leaf_alias:
            # GitHub Windows runners can deny os.symlink.  Keep this security
            # branch deterministic by simulating only the no-follow metadata
            # classification, not by skipping the assertion.
            leaf_alias.write_text("SAFE = True\n", encoding="utf-8")
            real_alias_check = _is_link_or_reparse

            def fixture_alias_check(path: Path, metadata) -> bool:
                if path == leaf_alias:
                    return True
                return real_alias_check(path, metadata)

        def leaf_alias_context():
            if real_leaf_alias:
                return nullcontext()
            return patch.object(path_module, "_is_link_or_reparse", fixture_alias_check)

        with leaf_alias_context():
            leaf_rule = _output_path_boundary_rule(repository, "src/alias.py")
        assert leaf_rule == "output-alias"
        leaf_relative = "src/alias.py"
        _write_utf8(
            repository / SYNC_RECEIPT_PATH,
            json.dumps({"outputs": {leaf_relative: "0" * 64}}) + "\n",
        )
        with (
            leaf_alias_context(),
            patch.object(receipt_module, "sync_expected_output_paths", return_value={leaf_relative}),
            patch.object(receipt_module, "_receipt_schema_errors", return_value=[]),
        ):
            leaf_verify_errors = _verify_sync_receipt(repository)
        assert any("output-alias" in error for error in leaf_verify_errors)

        inside_target = repository / "inside-target"
        inside_target.mkdir()
        (inside_target / "probe.py").write_text("SAFE = True\n", encoding="utf-8")
        inside_alias = repository / "inside-alias"
        real_inside_alias = _self_test_try_symlink(
            inside_alias, inside_target, directory=True
        )
        if not real_inside_alias:
            inside_alias.mkdir()
            (inside_alias / "probe.py").write_text("SAFE = True\n", encoding="utf-8")
            baseline_alias_check = _is_link_or_reparse

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
            inside_rule = _output_path_boundary_rule(
                repository, "inside-alias/probe.py"
            )
        assert inside_rule == "ancestor-alias"

        outside_target = external / "managed"
        outside_target.mkdir()
        (outside_target / "probe.py").write_text("PRIVATE = True\n", encoding="utf-8")
        outside_alias = repository / "outside-alias"
        if os.name == "nt":
            real_outside_alias = _self_test_try_windows_junction(
                outside_alias, outside_target
            )
            outside_fixture = (
                "windows-junction" if real_outside_alias else "simulated-alias"
            )
        else:
            real_outside_alias = _self_test_try_symlink(
                outside_alias, outside_target, directory=True
            )
            outside_fixture = "posix-symlink" if real_outside_alias else "simulated-alias"
        if real_outside_alias:
            resolver_context = nullcontext()
        else:
            # Non-NTFS Windows CI or a policy that blocks all aliases still
            # exercises the containment decision rather than skipping it.
            outside_alias.mkdir()
            real_resolver = _resolve_entry

            def fixture_resolver(path: Path, *, strict: bool) -> Path:
                if path == outside_alias:
                    return outside_target.resolve(strict=strict)
                return real_resolver(path, strict=strict)

            resolver_context = patch.object(
                path_module, "_resolve_entry", side_effect=fixture_resolver
            )
        relative = "outside-alias/probe.py"
        with resolver_context:
            outside_rule = _output_path_boundary_rule(repository, relative)
            expected_outside_rule = (
                "ancestor-alias" if real_outside_alias else "ancestor-escape"
            )
            assert outside_rule == expected_outside_rule
            public_error = _boundary_error(relative, outside_rule)
            assert str(outside_target.resolve()) not in public_error

            # Apply preflight and receipt verification must reject the alias
            # before cleanup, hashing, or a downstream validator. Patch only
            # inventory size so this fixture stays focused and deterministic.
            receipt = {"outputs": {relative: "0" * 64}}
            _write_utf8(repository / SYNC_RECEIPT_PATH, json.dumps(receipt) + "\n")
            with patch.object(
                receipt_module, "sync_expected_output_paths", return_value={relative}
            ), patch.object(
                path_module, "sync_expected_output_paths", return_value={relative}
            ):
                try:
                    _assert_sync_output_boundaries(repository)
                except ValueError as exc:
                    assert expected_outside_rule in str(exc)
                    assert str(outside_target.resolve()) not in str(exc)
                else:
                    raise AssertionError("sync apply preflight followed external alias")
                with patch.object(receipt_module, "_receipt_schema_errors", return_value=[]):
                    verify_errors = _verify_sync_receipt(repository)
            assert any(expected_outside_rule in error for error in verify_errors)
            assert str(outside_target.resolve()) not in "; ".join(verify_errors)
    print(f"sync_canonical output-boundary self-test GREEN ({outside_fixture})")


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
    parser.add_argument("--check", "--dry-run", dest="check", action="store_true", help="report drift without writing the target repository")
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
        _self_test_text_hash_portability()
        _self_test_output_path_boundaries()
        self_test_public_renderers(repository)
        self_test_public_inventory(repository)
        _self_test_receipt_schema(repository)
        return 0
    if args.verify_receipt:
        errors = _verify_sync_receipt(repository)
        if not errors:
            try:
                verify_cleanup_bundle(repository)
            except (OSError, ValueError, UnicodeError) as exc:
                errors.append(str(exc))
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
    _assert_public_workflow_derivation(canonical, distribution_source or Path(__file__).resolve().parents[1])
    if args.check:
        with tempfile.TemporaryDirectory(prefix="video-autopilot-sync-") as temp:
            staged = Path(temp) / "repository"
            expected = sync(canonical, staged, distribution_source)
            boundary_violations = _output_path_boundary_violations(
                repository, expected
            )
            drift = [
                name for name in expected
                if name not in boundary_violations
                and (
                    not (repository / name).is_file()
                    or _text_sha256(staged / name) != _text_sha256(repository / name)
                )
            ]
            drift[:0] = [
                _boundary_error(relative, rule)
                for relative, rule in sorted(boundary_violations.items())
            ]
        if boundary_violations:
            # Avoid reference scans and manifest validation on a tree already
            # proven to contain an escaping alias.
            print("SYNC DRIFT: " + ", ".join(drift[:30]))
            return 1
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
