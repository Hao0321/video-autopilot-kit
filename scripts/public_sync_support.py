"""Knowledge, Cleanup-config, manifest, and fixture helpers for public sync."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from public_privacy_sanitizer import (
    contains_private_identity,
    generalize_private_identity,
)
from public_sync_inventory import (
    CLEANUP_HELPER_FILES,
    PRIVATE_PUBLIC_FILES,
    PUBLIC_AUDIT_EXCLUDES,
    SYNC_RECEIPT_PATH,
    public_destination_required_paths,
)
from public_sync_transforms import PRIVACY_PATTERNS


def _write_utf8(path: Path, text: str) -> None:
    """Write deterministic LF text on every supported Python version."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _copy_public_knowledge_state(source: Path, destination: Path) -> None:
    """Publish an empty writable state schema, never maintainer history."""
    if not source.is_file():
        raise FileNotFoundError(source)
    private = json.loads(source.read_text(encoding="utf-8-sig"))
    payload = {
        "schema_version": private.get("schema_version", 2),
        "revision": 0,
        "promotion_policy": private.get("promotion_policy", {}),
        "records": [],
        "privacy_contract": (
            "Empty public ledger; creator scopes, triggers, timestamps, review "
            "quotes, project identities, analytics and outcomes are excluded."
        ),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in generalized knowledge state {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _genericize_creator_labels(value):
    """Replace maintainer identity labels without changing JSON shape."""
    if isinstance(value, dict):
        return {key: _genericize_creator_labels(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_genericize_creator_labels(item) for item in value]
    if isinstance(value, str):
        value = generalize_private_identity(value)
    return value


def _sanitize_aesthetic_standard(payload: dict) -> dict:
    payload = _genericize_creator_labels(payload)
    payload["standard_id"] = "public-aesthetic-standard"
    basis = payload.setdefault("reference_basis", {})
    basis.pop("private_reference_count", None)
    basis["dna_file"] = "knowledge/runtime/design_reference_dna.json"
    basis["method"] = (
        "Redistributable abstract composition, typography, colour, image-integration, "
        "material and motion rules; no creator profile or review evidence is included."
    )
    principles = payload.get("principles") or {}
    for key in (
        "nonreal_editorial_is_limited_to_travel_food_and_cafe",
        "japanese_lifestyle_calm_is_the_default_nonreal_direction",
    ):
        principles.pop(key, None)
    for grammar in (payload.get("presentation_grammars") or {}).values():
        if isinstance(grammar, dict) and "status" in grammar:
            grammar["status"] = "public_default"
    routes = payload.get("domain_routes") or {}
    generic_routes = {
        "food": ("food_hero", ["japanese_lifestyle_calm", "travel_scrapbook"]),
        "cafe": ("food_hero", ["luminous_organic", "japanese_lifestyle_calm"]),
        "travel": ("travel_scrapbook", ["japanese_lifestyle_calm", "cobalt_editorial"]),
    }
    for domain, (primary, support) in generic_routes.items():
        if isinstance(routes.get(domain), dict):
            routes[domain]["primary"] = primary
            routes[domain]["support"] = support
    return payload


def _sanitize_design_reference_dna(payload: dict) -> dict:
    payload = _genericize_creator_labels(payload)
    payload["system_id"] = "public-design-reference-dna"
    payload["privacy"] = (
        "Redistributable abstract design seeds only; creator preferences, source "
        "attachments, paths, dates and review outcomes are excluded."
    )
    payload.pop("preference_overrides", None)
    source_rows = payload.get("references") or []
    selected: list[dict] = []
    selected_indexes: set[int] = set()
    seen_families: set[str] = set()
    for index, row in enumerate(source_rows):
        family = str(row.get("family") or "")
        if family and family not in seen_families:
            selected.append(dict(row))
            selected_indexes.add(index)
            seen_families.add(family)
    for index, row in enumerate(source_rows):
        if (index not in selected_indexes and
                row.get("learning_scope") in {"layout_only", "art_direction"}):
            selected.append(dict(row))
            selected_indexes.add(index)
    for index, row in enumerate(selected, 1):
        row["id"] = f"public-seed-{index:03d}"
    payload["references"] = selected
    payload["reference_count"] = len(selected)
    payload["catalog_role"] = "redistributable_generic_seed_set"
    return payload


def _sanitize_color_grading_profiles(payload: dict) -> dict:
    payload = _genericize_creator_labels(payload)
    payload["standard_id"] = "public-visual-master-color"
    for profile in (payload.get("profiles") or {}).values():
        if isinstance(profile, dict):
            profile.pop("human_validation", None)
    return payload


def _sanitize_thumbnail_standard(payload: dict) -> dict:
    payload = _genericize_creator_labels(payload)
    payload["standard_id"] = "public-thumbnail-algorithm-score"
    niche = (payload.get("dimensions") or {}).get("niche_differentiation")
    if isinstance(niche, dict):
        niche["question"] = "放進同題材影片牆時，是否仍能辨認這個頻道與本片的獨特承諾？"
        niche["improvement"] = "保留目前頻道已設定的品牌語彙與真實主體，移除泛用介面拼貼。"
    return payload


PUBLIC_KNOWLEDGE_SANITIZERS = {
    "aesthetic_standard.json": _sanitize_aesthetic_standard,
    "design_reference_dna.json": _sanitize_design_reference_dna,
    "color_grading_profiles.json": _sanitize_color_grading_profiles,
    "thumbnail_algorithm_standard.json": _sanitize_thumbnail_standard,
}


def _assert_public_knowledge_safe(name: str, payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    forbidden = {
        "private_reference_count": "private source count",
        '"preference_overrides"': "creator preference profile",
        '"human_validation"': "private validation outcome",
        '"reviewed_by"': "reviewer identity",
        '"reviewed_at"': "private review date",
        "positive_user_reference_": "dated user preference status",
    }
    hits = [label for token, label in forbidden.items() if token in text]
    if contains_private_identity(text):
        hits.append("maintainer identity label")
    if name == "design_reference_dna.json":
        rows = payload.get("references") or []
        if payload.get("reference_count") != len(rows):
            hits.append("reference count does not match public seed rows")
        if any(not str(row.get("id", "")).startswith("public-seed-") for row in rows):
            hits.append("private reference identifiers survived")
    if hits:
        raise ValueError(f"private knowledge metadata in {name}: {', '.join(hits)}")


def _copy_public_knowledge_json(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    sanitizer = PUBLIC_KNOWLEDGE_SANITIZERS[source.name]
    public = sanitizer(payload)
    _assert_public_knowledge_safe(source.name, public)
    text = json.dumps(public, ensure_ascii=False, indent=2) + "\n"
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in sanitized knowledge {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _copy_public_cleanup_config(source: Path, destination: Path) -> None:
    """Copy Cleanup defaults without publishing maintainer privacy tokens."""
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    sync_config = payload.get("sync")
    if isinstance(sync_config, dict):
        sync_config.pop("privacy", None)
    payload["privacy"] = {"tokens": [], "allow": []}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in sanitized Cleanup config {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _public_src_path(value: str) -> str:
    """Map a canonical runtime path to its public ``src`` location."""
    normalized = value.replace("\\", "/")
    return normalized if normalized.startswith("src/") else "src/" + normalized


def _copy_public_autopilot_config(source: Path, destination: Path) -> None:
    """Translate canonical Cleanup paths to the public package topology."""
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    exclude = payload.setdefault("exclude", [])
    if not isinstance(exclude, list):
        raise ValueError("canonical Cleanup exclude must be a list")
    payload["exclude"] = list(dict.fromkeys([*exclude, *PUBLIC_AUDIT_EXCLUDES]))
    architecture = payload.get("architecture")
    if not isinstance(architecture, dict):
        raise ValueError("canonical Cleanup architecture config is required")
    for layer in architecture.get("layers", []):
        layer["patterns"] = [_public_src_path(item) for item in layer.get("patterns", [])]
    for key in ("forbidden_dependencies", "required_dependencies"):
        for rule in architecture.get(key, []):
            rule["source"] = _public_src_path(rule["source"])
            rule["target"] = _public_src_path(rule["target"])
    for rule in architecture.get("ignore_edges", []):
        if isinstance(rule, dict):
            rule["source"] = _public_src_path(rule["source"])
            rule["target"] = _public_src_path(rule["target"])
    for key in ("function_exceptions", "module_hotspot_exceptions"):
        for rule in architecture.get(key, []):
            rule["path"] = _public_src_path(rule["path"])
    if any(item not in payload["exclude"] for item in PUBLIC_AUDIT_EXCLUDES):
        raise ValueError("public Cleanup packaging exclusions are incomplete")
    configured_paths: list[str] = []
    for layer in architecture.get("layers", []):
        configured_paths.extend(layer.get("patterns", []))
    for key in ("forbidden_dependencies", "required_dependencies", "ignore_edges"):
        for rule in architecture.get(key, []):
            if isinstance(rule, dict):
                configured_paths.extend((rule["source"], rule["target"]))
    for key in ("function_exceptions", "module_hotspot_exceptions"):
        configured_paths.extend(rule["path"] for rule in architecture.get(key, []))
    invalid_paths = sorted(path for path in configured_paths if not path.startswith("src/"))
    if invalid_paths:
        raise ValueError("public Cleanup runtime paths lack src/ prefix: " + ", ".join(invalid_paths))
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in public Cleanup config {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_utf8(destination, text)


def _public_required_paths() -> list[str]:
    required = [
        "release-manifest.json", SYNC_RECEIPT_PATH, "scripts/public_privacy_gate.py",
        "scripts/public_privacy_legacy.py", "scripts/public_privacy_profiles.py",
        "scripts/public_privacy_references.py", "scripts/public_privacy_sanitizer.py",
        "scripts/public_privacy_sources.py", "scripts/public_skill_skeleton.py",
        "scripts/public_sync_inventory.py", "scripts/public_sync_renderers.py", "scripts/public_sync_support.py",
        "scripts/public_sync_transforms.py", "scripts/sync_canonical.py",
        "src/project_paths.py", "src/context_router.py",
        "src/workflow_contract.py", "src/workflow_state.py", "src/workflow_receipts.py", "src/workflow_material_receipts.py", "src/workflow_transport.py", "src/workflow_contract.json",
        "src/broll_qa.py", "src/media_delivery_qa.py", "src/delivery_media_ops.py",
        "src/asset_registry.py", "src/visual_director.py", "src/visual_master.py", "src/battle_plan_components.py",
        "src/tracked_graphics.py", "src/tracked_graphics_presentation.py", "src/tracked_graphics_render.py", "src/tracked_graphics_validation.py",
        "src/roto_matte.py", "src/parallax_transition.py", "src/filter_primitives.py", "src/filter_renderers.py", "src/filter_runtime.py", "src/filter_materials.py", "src/imagegen_asset_gateway.py", "src/visual_style_router.py",
        "src/composition_runtime.py", "src/browser_seek_runtime.py", "src/component_scene_runtime.py", "src/vector_scene_runtime.py",
        "src/quality_95.py", "src/publish_contract.py", "src/publish_hub.py", "src/publish_hub_cli.py", "src/publish_hub_layout.py",
        "src/release_integrity.py", "src/release_manager.py", "src/release_manager_selftest.py", "src/startup_update.py", "src/workspace_migrator.py", "src/storage_lifecycle.py", "src/system_health.py", "src/project_quality_95.py", "src/autonomy_standard.py",
        "src/longform_maker/delivery.py", "src/longform_maker/shorts_gate_validation.py", "src/design_system_v6.py", "src/template_compiler.py", "src/mediastorm_craft.py",
        "src/editorial_parity_benchmark.py", "src/ten_million_editorial.py", "src/mrbeast_editing_system.py", "src/mrbeast_source_map.py", "src/three_d_system.py",
        "src/architecture_gate.py", "src/asset_workshop.py", "src/vfx_keyer.py", "src/beyblade_x_rules.py", "knowledge/runtime/beyblade_x_rules.json",
        "knowledge/production-safety-principles.md", "audit.config.json", "src/asset_usage.py", "src/asset_index_migration.py",
        "knowledge/runtime/design_reference_dna.json", "knowledge/runtime/mediastorm_craft_benchmark.json", "knowledge/runtime/mrbeast_effect_source_map.json",
        "knowledge/runtime/filter_library.json", "knowledge/runtime/filter_materials.json", "knowledge/runtime/imagegen_asset_policy.json", "docs/AUTOPILOT_ARCHITECTURE_V6.md",
        "codex-skill/video-autopilot/SKILL.md", "codex-skill/video-autopilot/workflow_contract.py", "codex-skill/video-autopilot/workflow_state.py",
        "codex-skill/video-autopilot/workflow_receipts.py", "codex-skill/video-autopilot/workflow_material_receipts.py", "codex-skill/video-autopilot/workflow_transport.py",
        "codex-skill/video-autopilot/workflow_contract.json", "codex-skill/video-autopilot/agents/openai.yaml",
        "codex-skill/video-autopilot/references/open-source-release-and-upgrade.md", "codex-skill/video-autopilot/references/template-compiler-v2.md",
        "codex-skill/video-autopilot/references/mediastorm-craft-system.md", "codex-skill/video-autopilot/references/ten-million-editorial-system.md",
        "codex-skill/video-autopilot/references/asset-workshop.md", "codex-skill/video-autopilot/references/unattended-autonomy-standard.md",
        "codex-skill/video-autopilot/references/beyblade-x-finish-judging.md", "codex-skill/video-autopilot/references/programmatic-motion-runtime.md",
        "codex-skill/video-autopilot/references/filter-library.md", "codex-skill/video-autopilot/references/editorial-intelligence-contract.md",
        "codex-skill/video-autopilot/references/model-and-context-adaptation.md", "codex-skill/video-autopilot/references/editkin-workflow-execution.md",
        "codex-skill/video-autopilot/references/editkin-plugin-automation.md", "codex-skill/video-autopilot/references/editkin-mobile-device-binding.md",
    ]
    required.extend(f"tools/code-cleanup-helper/{relative}" for relative in CLEANUP_HELPER_FILES)
    required.extend(public_destination_required_paths())
    return list(dict.fromkeys(required))


def _public_planes() -> dict[str, list[str]]:
    return {
        "control": ["AUTOPILOT_MANIFEST.json", "audit.config.json", "src/architecture_gate.py", "src/editorial_parity_benchmark.py", "src/project_kernel.py", "src/workflow_contract.py", "src/workflow_state.py", "src/workflow_receipts.py", "src/workflow_material_receipts.py", "src/workflow_transport.py", "src/workflow_contract.json", "src/system_health.py", "src/autonomy_standard.py", "src/release_integrity.py", "src/publish_contract.py", "src/publish_hub.py", "src/publish_hub_cli.py", "src/publish_hub_layout.py"],
        "decision": ["src/context_router.py", "src/knowledge_lifecycle.py", "src/quality_95.py", "src/autonomy_standard.py", "src/visual_master.py"],
        "design": ["src/design_system_v6.py", "src/template_compiler.py", "src/mediastorm_craft.py", "src/mrbeast_editing_system.py", "src/mrbeast_source_map.py", "src/ten_million_editorial.py", "src/three_d_system.py", "src/visual_director.py", "src/visual_style_router.py", "src/tracked_graphics.py", "src/tracked_graphics_presentation.py", "src/tracked_graphics_render.py", "src/tracked_graphics_validation.py", "src/roto_matte.py", "src/parallax_transition.py", "src/composition_runtime.py", "src/filter_runtime.py", "src/filter_renderers.py", "src/filter_primitives.py", "src/filter_materials.py", "src/browser_seek_runtime.py", "src/component_scene_runtime.py", "src/vector_scene_runtime.py", "src/battle_plan_components.py", "knowledge/runtime/design_reference_dna.json", "knowledge/runtime/mediastorm_craft_benchmark.json", "knowledge/runtime/mrbeast_effect_source_map.json", "knowledge/runtime/filter_library.json", "knowledge/runtime/filter_materials.json"],
        "asset": ["src/asset_usage.py", "src/asset_index_migration.py", "src/asset_catalog.py", "src/asset_selection.py", "src/asset_registry.py", "src/asset_memory.py", "src/asset_license_governance.py", "src/motion_asset_pack.py", "src/imagegen_asset_gateway.py", "knowledge/runtime/imagegen_asset_policy.json"],
        "execution": ["src/longform_maker", "src/shorts_autopilot.py", "src/tracked_graphics.py", "src/tracked_graphics_presentation.py", "src/tracked_graphics_render.py", "src/tracked_graphics_validation.py", "src/roto_matte.py", "src/parallax_transition.py", "src/composition_runtime.py", "src/filter_runtime.py", "src/filter_renderers.py", "src/filter_primitives.py", "src/browser_seek_runtime.py", "src/component_scene_runtime.py", "src/vector_scene_runtime.py", "src/battle_plan_components.py", "src/drama_autopilot.py", "src/broll_qa.py", "src/media_delivery_qa.py", "src/delivery_media_ops.py"],
        "evidence": ["knowledge/runtime/state.json", "knowledge/runtime/quality_corpus.json", "knowledge/runtime/filter_library.json", "knowledge/runtime/filter_materials.json", "knowledge/runtime/imagegen_asset_policy.json", "data"],
    }


def _write_public_manifest(repository: Path) -> None:
    payload = {
        "schema_version": 2, "project_id": "video-autopilot-kit",
        "architecture_version": "7.0", "public_distribution": True,
        "roots": {"skills": "codex-skill", "assets": "assets", "videos": "videos", "community": "community", "scripts": "scripts"},
        "planes": _public_planes(), "required_paths": _public_required_paths(),
        "skills": [{"id": "video-autopilot", "source": "codex-skill/video-autopilot", "destination": "video-autopilot", "include": ["SKILL.md", "workflow_contract.json", "*.py", "agents/*.yaml", "references/*.md"]},
                   {"id": "code-cleanup-helper", "source": "tools/code-cleanup-helper", "destination": "code-cleanup-helper", "include": ["SKILL.md", "CHANGELOG.md", "audit.config.json", "audit.config.example.json", "scripts/*.py", "references/*.md", "agents/*.yaml"]}],
        "budgets": {
            "context_tokens": {"default": 900, "plan": 900, "build": 800, "audit": 1000, "learn": 1100, "outcome": 650},
            "storage_gb": {"videos_warning": 12, "videos_max": 20, "assets_warning": 5, "assets_max": 8},
            "source_lines": {"python_warning": 500, "python_severe": 1000, "markdown_warning": 400, "markdown_severe": 800, "function_warning": 50, "function_severe": 100},
            "knowledge_lines": {"knowledge/runtime/state.json": {"warning": 1400, "rotate": 1800, "policy": "compact-supported-rules; archive local evidence under data/"}},
        },
        "audit": {
            "source_roots": ["src", "scripts", "codex-skill/video-autopilot"],
            "ignore_globs": ["**/__pycache__/**", "**/_runtime/**", "**/_demo/**"],
            "absolute_path_allowlist": ["src/project_paths.py", "src/project_kernel.py", "scripts/sync_canonical.py"],
            "large_file_allowlist": {
                "codex-skill/video-autopilot/references/editing-craft-fundamentals.md": "on-demand reference chapter; never loaded into default context",
                "codex-skill/video-autopilot/references/editing-master-techniques.md": "on-demand technique catalog",
                "codex-skill/video-autopilot/references/competitor-vertical-teardown-2026.md": "evidence-backed teardown kept cohesive for traceability",
            },
            "long_function_allowlist": {
                "src/silent_vlog_maker/verify.py:run_verify_steps": "ordered verification transaction with one failure ledger",
                "src/release_manager.py:apply_release_archive": "fail-closed upgrade transaction; backup, replacement, rollback and state commit share one boundary",
                "src/shorts_autopilot.py:scan": "compatibility orchestration adapter; its underlying analyzers are independently tested",
                "src/silent_vlog_maker/audit.py:audit_raw_files": "ordered media audit adapter around probe and frame evidence",
                "src/longform_maker/word_captions.py:group_words": "single timing and segmentation algorithm with tightly coupled invariants",
                "src/silent_vlog_maker/audit_report.py:write_markdown_report": "linear report serializer over one immutable audit result",
            },
        },
        "privacy_contract": "No user media, profiles, credentials, analytics, or local outcomes.",
    }
    path = repository / "AUTOPILOT_MANIFEST.json"
    _write_utf8(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _self_test_public_privacy() -> None:
    """Negative fixtures for private state, preferences and review outcomes."""
    with tempfile.TemporaryDirectory(prefix="video-autopilot-privacy-test-") as temp:
        root = Path(temp)
        private_state = {
            "schema_version": 2, "revision": 91,
            "updated_at": "2030-01-02T03:04:05+00:00",
            "promotion_policy": {"minimum_support": 3},
            "records": [{"id": "K-private-fixture", "fingerprint": "private123", "scope": "creator-only", "triggers": ["private-shop-name", "private-dislike-quote"], "rule": "PRIVATE-CONTENT-001 was rejected by the maintainer.", "pinned": True, "created_at": "2030-01-01T00:00:00+00:00", "updated_at": "2030-01-02T03:04:05+00:00"}],
        }
        source, destination = root / "state.json", root / "public-state.json"
        source.write_text(json.dumps(private_state), encoding="utf-8")
        _copy_public_knowledge_state(source, destination)
        public_state = json.loads(destination.read_text(encoding="utf-8"))
        serialized = json.dumps(public_state, ensure_ascii=False)
        assert public_state["records"] == [] and public_state["revision"] == 0
        for token in ("creator-only", "private-shop-name", "PRIVATE-CONTENT-001", "2030-"):
            assert token not in serialized
        aesthetic = _sanitize_aesthetic_standard({"standard_id": "private-standard-fixture", "reference_basis": {"private_reference_count": 19, "shared_dna": []}, "principles": {"japanese_lifestyle_calm_is_the_default_nonreal_direction": True}, "presentation_grammars": {"demo": {"status": "positive_user_reference_2030-01-02"}}})
        _assert_public_knowledge_safe("aesthetic_standard.json", aesthetic)
        assert "private_reference_count" not in aesthetic["reference_basis"]
        assert aesthetic["presentation_grammars"]["demo"]["status"] == "public_default"
        design = _sanitize_design_reference_dna({"system_id": "private-system-fixture", "preference_overrides": {"effective_date": "2030-01-02", "approved_by": "private-reviewer"}, "references": [{"id": "private-1", "family": "family-a", "composition": "a"}, {"id": "private-2", "family": "family-a", "composition": "b"}, {"id": "private-3", "family": "family-a", "learning_scope": "layout_only", "composition": "layout"}]})
        _assert_public_knowledge_safe("design_reference_dna.json", design)
        assert "preference_overrides" not in design and design["reference_count"] == 2
        assert all(row["id"].startswith("public-seed-") for row in design["references"])
        color = _sanitize_color_grading_profiles({"standard_id": "private-color-fixture", "working_contract": {"order": ["run grade gate and private review"]}, "profiles": {"demo": {"params": {}, "human_validation": {"content_id": "PRIVATE-CONTENT-001", "reviewed_by": "private-reviewer", "reviewed_at": "2030-01-02", "before_score": 1, "after_score": 5}}}})
        _assert_public_knowledge_safe("color_grading_profiles.json", color)
        assert "human_validation" not in color["profiles"]["demo"]
        stale = root / "knowledge" / "meta-lessons.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("private history", encoding="utf-8")
        assert _unexpected_private_public_files(root) == ["knowledge/meta-lessons.md"]
        _remove_private_public_files(root)
        assert not stale.exists()
    print("sync_canonical public privacy self-test GREEN")


def _unexpected_private_public_files(repository: Path) -> list[str]:
    return [relative for relative in PRIVATE_PUBLIC_FILES if (repository / relative).is_file()]


def _remove_private_public_files(repository: Path) -> None:
    for relative in PRIVATE_PUBLIC_FILES:
        target = repository / relative
        if target.is_file():
            target.unlink()
