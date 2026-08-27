"""Closed-world inventories for canonical-to-public synchronization.

Private canonical filenames and reasons live only in the canonical workspace's
control JSON.  Public source and receipts retain aggregate counts, so the
inventory fails closed without publishing dictionary-attackable name hashes.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from pathlib import Path


ROOT_MODULES = (
    "aesthetic_score.py", "architecture_gate.py", "art_direction.py", "asset_catalog.py",
    "asset_index_migration.py", "asset_license_governance.py", "asset_memory.py",
    "asset_registry.py", "asset_registry_shared.py", "asset_selection.py", "asset_workshop.py",
    "av_util.py", "vfx_keyer.py",
    "battle_plan_components.py", "broll_qa.py", "camera_transition_director.py", "caption_director.py", "challenge_hud.py",
    "channel_tracker.py", "color_calibration_lab.py", "context_router.py",
    "domain_broll_pack.py", "domain_taxonomy.py", "drama_autopilot.py", "beyblade_x_rules.py",
    "design_system_v6.py", "editorial_parity_benchmark.py", "editorial_templates.py", "knowledge_lifecycle.py", "motion_asset_pack.py",
    "mrbeast_editing_system.py", "mrbeast_source_map.py", "three_d_system.py",
    "motion_renderers.py", "outcome_learning.py", "project_kernel.py",
    "project_quality_95.py", "media_delivery_qa.py", "delivery_media_ops.py",
    "project_paths.py", "autonomy_standard.py", "publishing_copy.py", "publish_contract.py", "publish_hub.py",
    "publish_hub_cli.py", "publish_hub_layout.py", "publish_hub_ops.py", "quality_95.py", "quality_corpus.py",
    "remix_planner.py", "render_caption_showcase.py", "review_loop.py",
    "shorts_autopilot.py", "shorts_delivery.py", "skill_sync.py",
    "storage_lifecycle.py", "storage_optimizer.py", "asset_usage.py", "taste_model.py",
    "teardown.py", "thumbnail_algorithm_score.py", "tracked_graphics.py",
    "tracked_graphics_presentation.py", "tracked_graphics_render.py",
    "tracked_graphics_validation.py",
    "roto_matte.py", "parallax_transition.py", "composition_runtime.py",
    "filter_primitives.py", "filter_renderers.py", "filter_runtime.py", "filter_materials.py",
    "imagegen_asset_gateway.py",
    "browser_seek_runtime.py", "component_scene_runtime.py", "vector_scene_runtime.py",
    "template_compiler.py", "mediastorm_craft.py", "ten_million_editorial.py",
    "tracked_typography.py", "visual_director.py", "visual_master.py",
    "visual_style_router.py",
    "visual_plan_support.py", "visual_profiles.py",
    "workflow_contract.py", "workflow_state.py", "workflow_receipts.py", "workflow_material_receipts.py", "workflow_transport.py", "workflow_contract.json",
)

LONGFORM_MODULES = (
    "asset_forge.py", "audio_chain.py", "brand_templates.py", "color_workflow.py",
    "delivery.py",
    "emphasis_overlays.py", "fx_lib.py", "gate_core.py", "grade_calibrate.py",
    "grade_gate.py", "grade_lib.py", "music_engine.py", "pace_gate.py",
    "plan_gate.py", "proof_stage.py", "screen_clean.py", "script_gate.py",
    "shorts_gate.py", "shorts_gate_validation.py", "thumb_template.py", "transitions.py", "video_handlers.py",
    "word_captions.py", "LONGFORM_PIPELINE.md",
)

SILENT_VLOG_MODULES = (
    "__init__.py", "asset_scanner.py", "audit.py", "audit_report.py",
    "bright_card_e2e.py", "checklists.py", "constants.py", "content_routing.py",
    "effects.py", "frame_audit.py", "helpers.py", "pipeline.py",
    "quality_check.py", "quality_check_corpus.py", "routing.py", "scene_audit.py",
    "screen_rec_cleaner.py", "shorts_audio.py", "shorts_captions.py",
    "shorts_template.py", "shorts_vertical.py", "text_overlay.py", "verify.py",
    "voice_profiles.json",
)

DRAMA_MODULES = (
    "__init__.py", "editor.py", "planner.py", "schema_validation.py",
    "schema_validation_corpus.py", "store.py", "tasks.py",
)

KNOWLEDGE_FILES = (
    "aesthetic_standard.json", "asset_license_overrides.json",
    "asset_license_policy.json", "camera_color_profiles.json",
    "color_grading_profiles.json", "design_reference_dna.json", "design_trend_radar.json",
    "state.json",
    "publishing_copy_playbooks.json", "quality_corpus.json",
    "thumbnail_algorithm_standard.json", "topic_research_catalog.json", "beyblade_x_rules.json",
    "mediastorm_craft_benchmark.json", "mrbeast_effect_source_map.json",
    "filter_library.json", "filter_materials.json", "imagegen_asset_policy.json",
)

# These files may exist in the private workspace, but are never valid public
# artifacts. Keep this exact so check mode rejects a stale tracked copy.
PRIVATE_PUBLIC_FILES = (
    "knowledge/meta-lessons.md",
)

SANITIZED_KNOWLEDGE_FILES = {
    "aesthetic_standard.json",
    "color_grading_profiles.json",
    "design_reference_dna.json",
    "thumbnail_algorithm_standard.json",
}

REFERENCE_FILES = (
    "ai-evidence-canvas.md", "asset-intelligence-hub.md", "asset-workshop.md", "autopilot-modes.md",
    "benchmark-effect-parity.md", "bright-editorial-template-system.md",
    "calibration-learning-and-license.md",
    "camera-transition-and-value-visualization.md", "caption-art-direction.md",
    "cinematic-wave-and-domain-grammar-2026.md",
    "color-science-and-visual-master.md", "craft-index.md", "editorial-intelligence-contract.md",
    "editing-craft-fundamentals.md", "editing-master-techniques.md",
    "editing-techniques-2026.md", "editing-wave5-finecut-2026.md",
    "editing-wave6-2026.md", "genre-copy-grammar-2026.md",
    "genre-editing-craft-2026.md", "hao-aesthetic-standard.md",
    "knowledge-lifecycle.md", "motion-asset-library.md",
    "mrbeast-and-yingshi-benchmark.md", "mrbeast-production-source-map.md", "niche-editing-grammar.md",
    "niche-fonts-colors.md", "open-source-release-and-upgrade.md",
    "publish-hub-and-remix.md", "quality-95-system.md",
    "script-retention-2026.md", "shorts-mastery-2026.md",
    "shorts_reels_2026_best_practices.md", "storage-lifecycle.md",
    "thumbnail-algorithm-score.md", "token-budget-system.md",
    "tracked-typography-and-challenge-ledger.md",
    "design-reference-dna-v6.md", "three-d-and-subject-fx.md",
    "visual-art-direction-2026.md", "competitor-vertical-teardown-2026.md",
    "template-compiler-v2.md", "mediastorm-craft-system.md", "ten-million-editorial-system.md",
    "architecture-foundation-v6-3.md", "unattended-autonomy-standard.md", "beyblade-x-finish-judging.md",
    "programmatic-motion-runtime.md", "filter-library.md",
    "model-and-context-adaptation.md", "editkin-batch-workflow.md",
    "editkin-mobile-device-binding.md", "editkin-plugin-automation.md",
    "editkin-workflow-execution.md",
)

WORKFLOW_SKILL_FILES = (
    "workflow_contract.py", "workflow_state.py", "workflow_receipts.py", "workflow_material_receipts.py", "workflow_transport.py", "workflow_contract.json",
)

CLEANUP_HELPER_FILES = (
    "SKILL.md",
    "CHANGELOG.md",
    "audit.config.json",
    "audit.config.example.json",
    "agents/openai.yaml",
    "scripts/audit.py",
    "scripts/audit_core.py",
    "scripts/self_test.py",
    "scripts/check_links.py",
    "scripts/check_drift.py",
    "scripts/check_sync.py",
    "scripts/check_build_receipt.py",
    "scripts/check_audit_snapshot.py",
    "scripts/check_skill_revision.py",
    "scripts/sync_public.py",
    "references/mode-a.md",
    "references/mode-b.md",
    "references/config-and-report.md",
    "references/rd-integration.md",
    "references/capability-obligations.md",
    "references/build-receipt-audit.md",
    "references/security-and-release-hygiene.md",
    "references/cross-system-integration-audit.md",
    "references/model-context-contract-audit.md",
)

# Two deliberate packaging mirrors are excluded from whole-repository scoring:
# the workflow runtime is installed in src and the Codex Skill, while Cleanup
# Helper is bundled as an independently audited evaluator.
PUBLIC_AUDIT_EXCLUDES = (
    "codex-skill/video-autopilot/workflow_contract.py",
    "codex-skill/video-autopilot/workflow_material_receipts.py",
    "codex-skill/video-autopilot/workflow_receipts.py",
    "codex-skill/video-autopilot/workflow_state.py",
    "codex-skill/video-autopilot/workflow_transport.py",
    "tools/code-cleanup-helper/**",
)


SYNC_RECEIPT_PATH = "sync-receipt.json"

# Public-kit-owned files have no canonical source and are copied verbatim into
# fresh staging trees.  ``system_health.py`` is the sole analogue of a private
# canonical module; its canonical content is pinned below so a private change
# cannot be silently ignored by a false-green public sync.
PUBLIC_OWNED_PATHS = (
    "src/editorial_template_fallback.py",
    "src/interview_autopilot.py",
    "src/interview_gate.py",
    "src/platform_compat.py",
    "src/release_integrity.py",
    "src/release_manager.py",
    "src/release_manager_selftest.py",
    "src/startup_update.py",
    "src/system_health.py",
    "src/workspace_migrator.py",
    "src/longform_maker/__init__.py",
)

CANONICAL_PUBLIC_OWNED_PINS = {
    "root": {
        "system_health.py": "c0b428ac4944ea6995888966abf5b6e8f38ef9a9be36433e4d33c77bee919287",
    },
}

PRIVATE_CONTROL_FILE = "public-sync-private-inventory.json"
PRIVATE_CONTROL_SCHEMA = "video-autopilot-private-sync-inventory/v1"
CANONICAL_DIRECTORY_LABELS = (
    "root", "longform_maker", "silent_vlog_maker", "drama_pipeline",
    "knowledge", "agents", "references",
)

# Aggregate counts are not identifying.  They let a public receipt verifier
# validate exact schema shape without retaining filenames, reasons, or hashes.
PRIVATE_CANONICAL_COUNTS = {
    "root": 7,
    "longform_maker": 0,
    "silent_vlog_maker": 0,
    "drama_pipeline": 0,
    "knowledge": 3,
    "agents": 0,
    "references": 5,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_private_control(canonical: Path) -> dict[str, dict[str, str]]:
    path = canonical / PRIVATE_CONTROL_FILE
    if not path.is_file():
        raise ValueError("canonical private inventory control file is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("canonical private inventory control file is invalid") from exc
    if payload.get("schema") != PRIVATE_CONTROL_SCHEMA:
        raise ValueError("canonical private inventory control schema drifted")
    directories = payload.get("directories")
    if not isinstance(directories, dict) or set(directories) != set(CANONICAL_DIRECTORY_LABELS):
        raise ValueError("canonical private inventory directory shape drifted")
    result: dict[str, dict[str, str]] = {}
    for label in CANONICAL_DIRECTORY_LABELS:
        rows = directories[label]
        if not isinstance(rows, dict):
            raise ValueError(f"canonical private inventory class must be an object: {label}")
        if len(rows) != PRIVATE_CANONICAL_COUNTS[label]:
            raise ValueError(f"canonical private inventory count drifted: {label}")
        normalized: dict[str, str] = {}
        for name, reason in rows.items():
            if (not isinstance(name, str) or not name or Path(name).name != name
                    or name == PRIVATE_CONTROL_FILE):
                raise ValueError(f"canonical private inventory filename is invalid: {label}")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"canonical private inventory reason is missing: {label}")
            normalized[name] = reason.strip()
        result[label] = normalized
    return result


def _canonical_public_classes() -> dict[str, dict[str, tuple[str, ...] | dict[str, str]]]:
    """Return every allowed direct canonical filename exactly once."""
    return {
        "root": {
            "derived": ROOT_MODULES,
            "special": ("SKILL.md", "audit.config.json"),
            "public_owned": CANONICAL_PUBLIC_OWNED_PINS["root"],
        },
        "longform_maker": {"derived": LONGFORM_MODULES, "special": (), "public_owned": {}},
        "silent_vlog_maker": {"derived": SILENT_VLOG_MODULES, "special": (), "public_owned": {}},
        "drama_pipeline": {"derived": DRAMA_MODULES, "special": (), "public_owned": {}},
        "knowledge": {"derived": KNOWLEDGE_FILES, "special": (), "public_owned": {}},
        "agents": {"derived": ("openai.yaml",), "special": (), "public_owned": {}},
        "references": {"derived": REFERENCE_FILES, "special": (), "public_owned": {}},
    }


def validate_canonical_inventory(canonical: Path) -> dict[str, dict]:
    """Validate all managed direct canonical directories and return hash evidence."""
    errors: list[str] = []
    evidence: dict[str, dict] = {}
    classes = _canonical_public_classes()
    private_control = _load_private_control(canonical)
    for label, classified in classes.items():
        root = canonical if label == "root" else canonical / label
        if not root.is_dir():
            errors.append(f"missing canonical directory: {label}")
            continue
        derived_seq = tuple(classified["derived"])
        special_seq = tuple(classified["special"])
        owned_pins = dict(classified["public_owned"])
        private = set(private_control[label])
        derived, special, owned = set(derived_seq), set(special_seq), set(owned_pins)
        for class_name, sequence in (("derived", derived_seq), ("special", special_seq)):
            duplicates = sorted(name for name in set(sequence) if sequence.count(name) != 1)
            if duplicates:
                errors.append(f"duplicate {label} {class_name}: " + ", ".join(duplicates))
        overlaps = sorted((derived & special) | (derived & owned) | (special & owned))
        if overlaps:
            errors.append(f"overlapping public classes in {label}: " + ", ".join(overlaps))
        public_names = derived | special | owned
        private_overlap = sorted(public_names & private)
        if private_overlap:
            errors.append(f"public/private overlap in {label}: " + ", ".join(private_overlap))
        actual = {path.name: path for path in root.iterdir() if path.is_file()}
        control_names = {PRIVATE_CONTROL_FILE} if label == "root" else set()
        missing_public = sorted(public_names - set(actual))
        missing_private = sorted(private - set(actual))
        unknown = sorted(
            name for name in actual
            if name not in public_names and name not in private and name not in control_names
        )
        if missing_public:
            errors.append(f"required canonical files missing in {label}: " + ", ".join(missing_public))
        if missing_private:
            errors.append(f"private classifications missing in {label}")
        if label == "root" and PRIVATE_CONTROL_FILE not in actual:
            errors.append("canonical private inventory control file is missing from root")
        if unknown:
            errors.append(f"unclassified canonical file count in {label}: {len(unknown)}")
        for name, expected in owned_pins.items():
            path = actual.get(name)
            if path is not None and _sha256(path) != expected:
                errors.append(
                    f"canonical public-owned analogue changed in {label}/{name}; "
                    "review and update its explicit content pin"
                )
        evidence[label] = {
            "derived": {name: _sha256(actual[name]) for name in sorted(derived) if name in actual},
            "special": {name: _sha256(actual[name]) for name in sorted(special) if name in actual},
            "public_owned_analogue": {
                name: _sha256(actual[name]) for name in sorted(owned) if name in actual
            },
            "private_count": len(private),
            "private_control_count": 1 if label == "root" else 0,
        }
    if errors:
        raise ValueError("canonical direct-file inventory is not closed-world: " + "; ".join(errors))
    return evidence


def public_destination_direct_files() -> dict[str, frozenset[str]]:
    """Exact leaf-file sets grouped by their managed public directory."""
    public_src_owned = {
        Path(relative).name for relative in PUBLIC_OWNED_PATHS
        if Path(relative).parent.as_posix() == "src"
    }
    return {
        "src": frozenset((*ROOT_MODULES, *public_src_owned)),
        "src/longform_maker": frozenset((*LONGFORM_MODULES, "__init__.py")),
        "src/silent_vlog_maker": frozenset(SILENT_VLOG_MODULES),
        "src/drama_pipeline": frozenset(DRAMA_MODULES),
        "knowledge/runtime": frozenset(KNOWLEDGE_FILES),
        "codex-skill/video-autopilot": frozenset(("SKILL.md", *WORKFLOW_SKILL_FILES)),
        "codex-skill/video-autopilot/agents": frozenset(("openai.yaml",)),
        "codex-skill/video-autopilot/references": frozenset(REFERENCE_FILES),
    }


def public_destination_required_paths() -> list[str]:
    return sorted(
        f"{directory}/{name}"
        for directory, names in public_destination_direct_files().items()
        for name in sorted(names)
    )


def sync_expected_output_paths() -> frozenset[str]:
    """Return the exact non-recursive-receipt output key set for one sync."""
    return frozenset({
        *public_destination_required_paths(),
        *(f"tools/code-cleanup-helper/{relative}" for relative in CLEANUP_HELPER_FILES),
        "audit.config.json",
        "docs/AUTOPILOT_ARCHITECTURE_V6.md",
        "AUTOPILOT_MANIFEST.json",
    })


def canonical_receipt_expected_shape() -> dict[str, dict]:
    """Return public class/name expectations without any private filenames."""
    result: dict[str, dict] = {}
    for label, classified in _canonical_public_classes().items():
        result[label] = {
            "derived": tuple(sorted(classified["derived"])),
            "special": tuple(sorted(classified["special"])),
            "public_owned_analogue": tuple(sorted(classified["public_owned"])),
            "private_count": PRIVATE_CANONICAL_COUNTS[label],
            "private_control_count": 1 if label == "root" else 0,
        }
    return result


_SHA256_TEXT = re.compile(r"[0-9a-f]{64}")


def canonical_receipt_shape_errors(inventory) -> list[str]:
    """Validate exact public canonical evidence shape, classes, names, and hashes."""
    expected = canonical_receipt_expected_shape()
    if not isinstance(inventory, dict):
        return ["canonical inventory evidence missing"]
    errors: list[str] = []
    if set(inventory) != set(expected):
        errors.append("canonical inventory root set mismatch")
        return errors
    expected_classes = {
        "derived", "special", "public_owned_analogue",
        "private_count", "private_control_count",
    }
    for label, shape in expected.items():
        row = inventory.get(label)
        if not isinstance(row, dict) or set(row) != expected_classes:
            errors.append(f"canonical inventory class set mismatch: {label}")
            continue
        for class_name in ("derived", "special", "public_owned_analogue"):
            values = row.get(class_name)
            expected_names = set(shape[class_name])
            if not isinstance(values, dict) or set(values) != expected_names:
                errors.append(f"canonical inventory name set mismatch: {label}/{class_name}")
                continue
            if any(not isinstance(value, str) or not _SHA256_TEXT.fullmatch(value)
                   for value in values.values()):
                errors.append(f"canonical inventory hash invalid: {label}/{class_name}")
        if row.get("private_count") != shape["private_count"]:
            errors.append(f"canonical private aggregate count mismatch: {label}")
        if row.get("private_control_count") != shape["private_control_count"]:
            errors.append(f"canonical private-control aggregate mismatch: {label}")
        if label == "root" and isinstance(row.get("public_owned_analogue"), dict):
            for name, expected_hash in CANONICAL_PUBLIC_OWNED_PINS["root"].items():
                if row["public_owned_analogue"].get(name) != expected_hash:
                    errors.append("canonical public-owned analogue pin mismatch")
    return errors


def _matches(relative: str, patterns) -> bool:
    value = relative.replace("\\", "/").lstrip("./")
    for raw in patterns:
        pattern = str(raw).replace("\\", "/").lstrip("./")
        if pattern.endswith("/**") and (
            value == pattern[:-3].rstrip("/") or value.startswith(pattern[:-3])
        ):
            return True
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def validate_public_destination(repository: Path, release_manifest_path: Path | None = None) -> None:
    """Reject every unexpected release-selected file recursively under managed roots."""
    manifest_path = release_manifest_path or repository / "release-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("release manifest is required for public destination inventory")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("release manifest is invalid for public destination inventory") from exc
    includes = manifest.get("managed_include")
    excludes = manifest.get("exclude_globs")
    protected = manifest.get("protected_globs")
    if not all(isinstance(value, list) for value in (includes, excludes, protected)):
        raise ValueError("release manifest selection schema is incomplete")
    expected = set(public_destination_required_paths())
    errors: list[str] = []
    not_selected = sorted(
        relative for relative in expected
        if not _matches(relative, includes) or _matches(relative, excludes)
    )
    if not_selected:
        errors.append("managed public schema contains non-release paths")
    actual: set[str] = set()
    for managed_root in ("src", "knowledge/runtime", "codex-skill/video-autopilot"):
        root = repository / managed_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(repository).as_posix()
            if not _matches(relative, includes) or _matches(relative, excludes):
                continue
            if _matches(relative, protected):
                errors.append("protected path entered managed public destination")
            actual.add(relative)
    missing, extra = sorted(expected - actual), sorted(actual - expected)
    if missing:
        errors.append("missing managed public release files: " + ", ".join(missing[:20]))
    if extra:
        errors.append("unclassified managed public release files: " + ", ".join(extra[:20]))
    if errors:
        raise ValueError("public destination inventory is not closed-world: " + "; ".join(errors))


def self_test_public_inventory(repository: Path) -> None:
    """Negative fixtures for recursive destination and receipt schema closure."""
    import copy
    import tempfile

    expected_shape = canonical_receipt_expected_shape()
    valid = {
        label: {
            "derived": {name: "0" * 64 for name in shape["derived"]},
            "special": {name: "0" * 64 for name in shape["special"]},
            "public_owned_analogue": {
                name: CANONICAL_PUBLIC_OWNED_PINS["root"][name]
                for name in shape["public_owned_analogue"]
            },
            "private_count": shape["private_count"],
            "private_control_count": shape["private_control_count"],
        }
        for label, shape in expected_shape.items()
    }
    assert not canonical_receipt_shape_errors(valid)
    assert canonical_receipt_shape_errors({})
    missing_name = copy.deepcopy(valid)
    missing_name["root"]["derived"].pop(next(iter(missing_name["root"]["derived"])))
    assert canonical_receipt_shape_errors(missing_name)
    injected_private_class = copy.deepcopy(valid)
    injected_private_class["root"]["forbidden_private_inventory"] = {"opaque": 1}
    assert canonical_receipt_shape_errors(injected_private_class)
    manifest_path = repository / "release-manifest.json"
    with tempfile.TemporaryDirectory(prefix="video-autopilot-inventory-test-") as temp:
        staged = Path(temp)
        for relative in public_destination_required_paths():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        validate_public_destination(staged, manifest_path)
        extra = staged / "src" / "extra_dir" / "extra.py"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("unexpected = True\n", encoding="utf-8")
        try:
            validate_public_destination(staged, manifest_path)
        except ValueError as exc:
            assert "unclassified managed public release files" in str(exc)
        else:
            raise AssertionError("recursive public destination accepted an extra release file")
        extra.unlink()
        cache = staged / "src" / "__pycache__" / "ignored.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"generated cache fixture")
        validate_public_destination(staged, manifest_path)
    assert len(sync_expected_output_paths()) == 264
    print("public sync inventory negative fixtures GREEN")
