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
    self_test_public_renderers,
)
from public_sync_support import (
    PUBLIC_KNOWLEDGE_SANITIZERS,
    _assert_public_knowledge_safe,
    _copy_public_autopilot_config,
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
    if "scripts/hao_autopilot.py" in text:
        # The maintainer wrapper is not distributed; map each citation to a
        # public entry point in MODULE_REPLACEMENTS instead of publishing it.
        raise ValueError(f"private wrapper command survived public transforms in {source.name}")
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
    from public_sync_selftest import _self_test_public_owned_lf as implementation
    return implementation(globals())


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
    from public_sync_selftest import _self_test_receipt_schema as implementation
    return implementation(globals(), repository)


def _copy_canonical_groups(canonical, copied, repository):
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
            elif name == "state.json" and source_root.name == "knowledge":
                _copy_public_knowledge_state(source_root / name, destination)
            elif name in SANITIZED_KNOWLEDGE_FILES and source_root.name == "knowledge":
                _copy_public_knowledge_json(source_root / name, destination)
            else:
                relative = destination.relative_to(repository).as_posix()
                _copy_text(source_root / name, destination, relative)
            copied.append(destination.relative_to(repository).as_posix())


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
    # This must precede cleanup, mkdir, and every copy.  A malicious junction
    # must not turn even a nominally local cleanup/write into an external one.
    _assert_sync_output_boundaries(repository)
    _remove_private_public_files(repository)
    copied: list[str] = []
    _copy_canonical_groups(canonical, copied, repository)
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
    _write_public_manifest(repository)
    copied.append("AUTOPILOT_MANIFEST.json")
    copied.extend(_copy_public_owned(distribution_source, repository))
    validate_public_destination(repository, distribution_source / "release-manifest.json")
    _write_sync_receipt(canonical_evidence, repository, copied)
    copied.append(SYNC_RECEIPT_PATH)
    return copied


def _self_test_text_hash_portability() -> None:
    from public_sync_selftest import _self_test_text_hash_portability as implementation
    return implementation(globals())


def _self_test_try_symlink(
    link: Path, target: Path, *, directory: bool = False
) -> bool:
    from public_sync_selftest import _self_test_try_symlink as implementation
    return implementation(globals(), link, target, directory=directory)


def _self_test_try_windows_junction(link: Path, target: Path) -> bool:
    from public_sync_selftest import _self_test_try_windows_junction as implementation
    return implementation(globals(), link, target)


def _self_test_output_path_boundaries() -> None:
    from public_sync_selftest import _self_test_output_path_boundaries as implementation
    return implementation(globals())


def _self_test_reserved_public_marker() -> None:
    from public_sync_selftest import _self_test_reserved_public_marker as implementation
    return implementation(globals())


def _parse_sync_arguments():
    from public_sync_cli import _parse_sync_arguments as implementation
    return implementation(globals())


def main() -> int:
    from public_sync_cli import main as implementation
    return implementation(globals())


if __name__ == "__main__":
    raise SystemExit(main())
