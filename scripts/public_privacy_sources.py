#!/usr/bin/env python3
"""Creator-neutral public transforms for generated Python source modules."""
from __future__ import annotations

import ast
import re

from public_privacy_legacy import (
    PUBLIC_FIXTURE,
    _function,
    _generalize_identity,
    _generalize_project_ids,
    _lf,
    _replace_lines,
    _replace_function_docstring,
    _replace_module_docstring,
    _silent_vlog_checklists,
)


from public_privacy_review import (
    _module_doc,
    _sanitize_comments,
    _common,
    _replace_review_resolution,
    _replace_review_selftests,
    _autonomy_standard,
)


_DRIVE_ROOT_LITERAL = re.compile(r"^[A-Za-z]:[\\/]$")


def _contains_drive_root_literal(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and _DRIVE_ROOT_LITERAL.fullmatch(child.value) is not None
        for child in ast.walk(node)
    )


def _replace_design_drive_scan(text: str) -> str:
    """Replace a literal drive allowlist with a creator-neutral all-drive scan."""
    public = _lf(text)
    scope = _function(public, "validate_dna")
    candidates = [
        node
        for node in ast.walk(scope)
        if isinstance(node, ast.For) and _contains_drive_root_literal(node.iter)
    ]
    if not candidates:
        if _contains_drive_root_literal(scope):
            raise ValueError("public sanitizer could not isolate the design path scan")
        return public
    if len(candidates) != 1:
        raise ValueError("public sanitizer expected one design path scan")
    node = candidates[0]
    return _replace_lines(
        public,
        node.lineno,
        node.end_lineno or node.lineno,
        '''    private_tokens = ("codex-remote-" + "attachments",) + tuple(
        f"{chr(code)}:{chr(92)}" for code in range(ord("a"), ord("z") + 1)
    )
    for private_token in private_tokens:
        if private_token in serialized:
            errors.append("private path leaked into design DNA")''',
    )


def _replace_template_drive_scan(text: str) -> str:
    """Replace literal host drives in the template-plan privacy condition."""
    public = _lf(text)
    scope = _function(public, "score_template_plan")
    candidates = [
        node
        for node in ast.walk(scope)
        if isinstance(node, ast.If) and _contains_drive_root_literal(node.test)
    ]
    if not candidates:
        if _contains_drive_root_literal(scope):
            raise ValueError("public sanitizer could not isolate the template path scan")
        return public
    if len(candidates) != 1:
        raise ValueError("public sanitizer expected one template path scan")
    node = candidates[0]
    return _replace_lines(
        public,
        node.lineno,
        node.end_lineno or node.lineno,
        '''    drive_prefixes = tuple(
        f"{chr(code)}:{chr(92)}" for code in range(ord("a"), ord("z") + 1)
    )
    if any(token in raw for token in (private_attachment_marker, *drive_prefixes)):
        errors.append("private path leaked")''',
    )


def _design_system_v6(text: str) -> str:
    public = _common(text, _module_doc(
        "Redistributable design recipe compiler",
        "Compiles an anonymized public seed catalog into bounded visual recipes for multiple formats.",
    ))
    return _replace_design_drive_scan(public)


def _template_compiler(text: str) -> str:
    public = _common(text, _module_doc(
        "Reusable template-plan compiler",
        "Compiles reusable components into small, fatigue-aware plans without retaining source-media paths.",
    ))
    return _replace_template_drive_scan(public)


def _taste_model(text: str) -> str:
    public = _common(text, _module_doc(
        "Pairwise aesthetic preference model",
        "Stores reviewer-owned comparisons and explicit constraints without shipping a maintainer profile.",
    ))
    return _replace_function_docstring(
        public,
        "record_constraint",
        '    """Record an explicit reviewer constraint without inventing a pairwise comparison.\n\n'
        '    PUBLIC_FIXTURE: the caller supplies its own rule, score and evidence.\n'
        '    """',
    )


_LOCAL_INCIDENT_MARKER = re.compile(
    r"(?<![A-Za-z0-9])#0\d{2}(?:\s+v\d+[a-z]?)?(?![A-Za-z0-9])",
    re.I,
)


def _silent_vlog_checklists_public(text: str) -> str:
    source = _lf(text)
    if PUBLIC_FIXTURE not in source:
        source = _silent_vlog_checklists(source)
    public = _common(source, _module_doc(
        "Reusable pre-build checklists",
        "Defines configurable preparation questions, defaults and verification steps by content type.",
    ))
    public, count = re.subn(
        r'(?m)^(\s*"screen_rec_clean"\s*:\s*True,\s*)#.*$',
        r'\1# PUBLIC_FIXTURE: clean imported screen recordings before editing.',
        public,
        count=1,
    )
    if count != 1:
        raise ValueError("public sanitizer expected the screen-recording checklist comment")
    return _LOCAL_INCIDENT_MARKER.sub("PUBLIC_FIXTURE incident", public)


from public_privacy_cleanup import (
    _VOICE_IDENTIFIER,
    _WINDOWS_ABSOLUTE,
    _is_voice_profile_path,
    _cleanup_changelog,
)


def _audio_chain(text: str) -> str:
    return _common(text, _module_doc(
        "Reusable long-form audio chain",
        "Provides voice processing, room tone, music construction, ducking and final mix helpers.",
    ))


def _public_flash_classifier(public: str) -> str:
    return _replace_function_docstring(
        public,
        "classify_flash",
        '    """Separate clustered or micro flashes from isolated transition fades.\n\n'
        '    PUBLIC_FIXTURE: thresholds are configurable starter values and carry no\n'
        '    private project result or dated review evidence.\n'
        '    """',
    )


def _delivery_timing_checks(text: str) -> str:
    public = _common(text, _module_doc(
        "Timing, audio and caption checks",
        "Checks measured media timings without retaining private production results.",
    ))
    return _public_flash_classifier(public)


def _media_delivery_qa(text: str) -> str:
    public = _common(text, _module_doc(
        "Media delivery quality assurance",
        "Checks the rendered artifact for technical, audio, caption, freeze, flash and coverage failures.",
    ))
    timing_aliases = {alias.name for node in ast.parse(public).body
                      if isinstance(node, ast.ImportFrom) and node.module == "delivery_timing_checks"
                      for alias in node.names}
    if "classify_flash" not in timing_aliases:
        raise ValueError("Media QA must import its registered timing-check implementation")
    public = _replace_function_docstring(
        public,
        "check_bgm_coverage",
        '    """Measure rendered audio during narration gaps and near the tail.\n\n'
        '    PUBLIC_FIXTURE: a window below ``floor_db`` is treated as a potential\n'
        '    coverage hole; calibrate against creator-owned approved media.\n'
        '    """',
    )
    public = re.sub(
        r"(?m)(wins\.append\([^\n]+\))\s*#.*$",
        r"\1  # PUBLIC_FIXTURE: always sample a near-tail window.",
        public,
        count=1,
    )
    return public


def _publish_hub_cli(text: str) -> str:
    public = _common(text, _module_doc(
        "Publishing hub command-line adapter",
        "Routes creator-owned publishing state changes without performing a public upload.",
    ))
    scope = _function(public, "selftest")
    return _replace_lines(
        public,
        scope.lineno,
        scope.end_lineno or scope.lineno,
        '''def selftest(module: ModuleType | None = None) -> None:
    import tempfile
    from pathlib import Path

    hub = _hub(module)
    assert hub._slug('a:b/c*', fallback="x") == "a_b_c"
    assert hub.READY.parent == hub.HUB and hub.PUBLISHED.parent == hub.HUB
    assert hub.HUB.name == "_PUBLISH_HUB"
    root_entry = hub._root_entry_text()
    assert "(videos/" not in root_entry
    assert 'publish_hub.py" sync' in root_entry
    assert 'publish_hub.py" open' in root_entry
    parsed = _parser().parse_args(["mark-published", "S001"])
    assert parsed.platform == "reported_by_creator"
    contract_selftest()
    assert hub._withdrawn_ids() >= set()

    with tempfile.TemporaryDirectory(prefix="publish-hub-metadata-") as temporary:
        root = Path(temporary)
        owner = sys.modules[hub.mark_published.__module__]
        root_owner = sys.modules[hub._relative.__module__]
        original_root = root_owner.ROOT
        originals = {name: getattr(owner, name) for name in (
            "ROOT", "READY", "PUBLISHED", "HUB_AUDIT",
            "_content_manifests", "rebuild_index",
        )}
        try:
            owner.ROOT = root
            root_owner.ROOT = root
            owner.READY = root / "hub" / "READY"
            owner.PUBLISHED = root / "hub" / "PUBLISHED"
            owner.HUB_AUDIT = root / "hub" / "_AUDIT"
            package = owner.READY / "shorts" / "review" / "S001"
            package.mkdir(parents=True)
            video = package / "current.mp4"
            video.write_bytes(b"synthetic-published-metadata-fixture")
            manifest = package / "publish.json"
            manifest.write_text(json.dumps({
                "content_id": "S001", "format": "shorts", "status": "review",
                "video": video.name, "sha256": hub._sha256(video),
            }), encoding="utf-8")
            owner._content_manifests = lambda _content_id: [manifest]
            owner.rebuild_index = lambda: {"status": "GREEN"}
            result = hub.mark_published("S001")
            published = json.loads((owner.PUBLISHED / "shorts" / "published" /
                                    "S001" / "publish.json").read_text(encoding="utf-8"))
            metadata = published["published"]
            assert result["published"] == metadata
            assert metadata["platform"] == "reported_by_creator"
            assert metadata["video_id"] is None and metadata["url"] is None
            assert metadata["reported_on"] and metadata["note"]
        finally:
            root_owner.ROOT = original_root
            for name, value in originals.items():
                setattr(owner, name, value)
    print("publish_hub self-test GREEN")''',
    )


def _motion_asset_pack(text: str) -> str:
    return _common(text, _module_doc(
        "Reusable motion asset pack",
        "Builds editable functional motion templates while preserving semantic and deprecation gates.",
    ))


def _pace_gate(text: str) -> str:
    public = _common(text, _module_doc(
        "Configurable pacing gate",
        "Evaluates shot duration, density, variation, transition load and jitter against a selected profile.",
    ))
    public = re.sub(
        r"；creator 參考片 \d+(?:\.\d+)?-\d+(?:\.\d+)?",
        "；PUBLIC_FIXTURE starter profile",
        public,
    )
    public = re.sub(
        r'"creator 關掉別人影片的四個點之一是[^"\n]*"',
        '"PUBLIC_FIXTURE starter policy: excessive transition density reduces clarity"',
        public,
    )
    public = re.sub(
        r'"creator [^"\n]*[『「][^"\n]*[』」]）"',
        '"PUBLIC_FIXTURE: jitter effects are blocked by the generic starter policy.）"',
        public,
    )
    public = re.sub(
        r'check\("creator-calibrated \d+(?:\.\d+)? cuts/min passes"',
        'check("PUBLIC_FIXTURE starter pace passes"',
        public,
    )
    return public


def _screen_clean(text: str) -> str:
    public = _common(text, _module_doc(
        "Screen-recording privacy cleaner",
        "Trims capture boundaries and applies fail-closed privacy checks before a recording becomes selectable.",
    ))
    return re.sub(
        r"(?m)^(MIN_TAIL_TRIM\s*=\s*[^#\n]+)#.*$",
        r"\1# PUBLIC_FIXTURE generic stop-capture safety floor",
        public,
    )


def _grade_gate(text: str) -> str:
    public = _common(text, _module_doc(
        "Configurable color-consistency gate",
        "Measures within-class consistency, clipping and adjacent-shot jumps without treating structural cards as footage.",
    ))
    public = re.sub(
        r"(?ms)^#\s*⚠️\s*數值由 `grade_calibrate\.py`.*?^#\s*$",
        "# PUBLIC_FIXTURE: profile thresholds are starter values; calibrate with creator-owned approved media.\n#\n",
        public,
        count=1,
    )
    public = re.sub(
        r"(?ms)^#\s*🚨.*?^#\s*量的是.*?$",
        "# PUBLIC_FIXTURE: group frames by content class before measuring within-class consistency.\n"
        "# Structural cards, dark frames and bright UI are not one homogeneous grade sample.",
        public,
        count=1,
    )
    public = re.sub(
        r"(?ms)^#\s*⚠️\s*\*\*已知限制.*?^#\s*真正會出錯的情況:.*?$",
        "# PUBLIC_FIXTURE known limitation: saturation is only a proxy for content class.\n"
        "# Mixed low-saturation footage and UI may require an additional luminance/source dimension.",
        public,
        count=1,
    )
    return public


def _shorts_autopilot(text: str) -> str:
    public = _common(text, _module_doc(
        "Short-form autopilot orchestration",
        "Routes scan, plan, build, QA and delivery around an explicit source folder and structured receipts.",
    ))
    public = re.sub(
        r'(?m)^\s*"\s*自動排的 hook.*續看率.*$',
        '                 "   Compare hook choices with creator-owned equal-window evidence; PUBLIC_FIXTURE ships no retention result.",',
        public,
    )
    public = re.sub(r"user:\s*creator\s*告知", "user: creator-provided evidence", public)
    public = re.sub(r"20\d{2}-\d{2}-\d{2}\s*creator\s*裁決", "PUBLIC_FIXTURE generic publication rule", public)
    return public


def _shorts_captions(text: str) -> str:
    public = _common(text, _module_doc(
        "Short-form caption styling",
        "Renders white-first readable captions with profile-selected emphasis levels and mechanical QA.",
    ))
    public = re.sub(r"僅 creator 點名", "only when the active profile selects it", public)
    public = re.sub(r"creator 點名才用", "active profile opt-in", public)
    public = re.sub(r"creator white-first", "white-first profile", public, flags=re.I)
    return public


def _screen_rec_cleaner(text: str) -> str:
    public = _common(text, _module_doc(
        "Screen-recording cleanup helpers",
        "Crops capture chrome, trims boundaries, normalizes media and optionally removes long silence.",
    ))
    public = re.sub(r"creator 錄旁白", "Narration recordings", public)
    return public


def _proof_stage(text: str) -> str:
    return _common(text, _module_doc(
        "Evidence presentation stage",
        "Presents approved screenshots and verified values without redrawing factual proof.",
    ))


def _video_handlers(text: str) -> str:
    return _common(text, _module_doc(
        "Reusable long-form beat handlers",
        "Provides clip, still, color, proof and concat helpers driven by a project plan.",
    ))


def _brand_templates(text: str) -> str:
    public = _common(text, _module_doc(
        "Reusable brand template engine",
        "Builds configurable cards, lower thirds, progress elements and deterministic test previews.",
    ))
    public = re.sub(
        r'bright_stat_card\("[^"]+",\s*"[-+]\d+(?:\.\d+)?%",\s*"[^"]+",\s*"ai"\)',
        'bright_stat_card("示範指標", "+12%", "PUBLIC_FIXTURE synthetic value", "ai")',
        public,
        count=1,
    )
    return public


SANITIZERS = {
    'src/longform_maker/shorts_battle_contract.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/review_http_selftest.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/shorts_delivery_commands.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/visual_director_commands.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/visual_plan_composition.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/visual_plan_validation.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/visual_programmatic_delivery.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/review_daemon.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/roto_frame_collection.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/shorts_planning.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/shorts_scan.py': _shorts_autopilot,
    'src/silent_vlog_maker/shorts_video_render.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/autonomy_plan_repairs.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/storage_audit.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/publish_hub_registry.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/review_process.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/review_readiness.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/brand_code_cards.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/brand_device_frames.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/script_parsing.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/script_report.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/shorts_caption_validation.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/silent_vlog_maker/shorts_ass.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/silent_vlog_maker/shorts_music_selection.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/silent_vlog_maker/shorts_visual_layers.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/drama_pipeline/task_prompts.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/drama_pipeline/task_artifacts.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    "src/autonomy_standard.py": _autonomy_standard,
    "src/publish_hub_cli.py": _publish_hub_cli,
    "src/design_system_v6.py": _design_system_v6,
    "src/silent_vlog_maker/checklists.py": _silent_vlog_checklists_public,
    "src/taste_model.py": _taste_model,
    "src/template_compiler.py": _template_compiler,
    "src/longform_maker/audio_chain.py": _audio_chain,
    "src/media_delivery_qa.py": _media_delivery_qa,
    "src/delivery_timing_checks.py": _delivery_timing_checks,
    "src/motion_asset_pack.py": _motion_asset_pack,
    "src/longform_maker/pace_gate.py": _pace_gate,
    "src/longform_maker/screen_clean.py": _screen_clean,
    "src/longform_maker/grade_gate.py": _grade_gate,
    "src/shorts_autopilot.py": _shorts_autopilot,
    "src/silent_vlog_maker/shorts_captions.py": _shorts_captions,
    "src/silent_vlog_maker/screen_rec_cleaner.py": _screen_rec_cleaner,
    "src/longform_maker/proof_stage.py": _proof_stage,
    "src/longform_maker/video_handlers.py": _video_handlers,
    "src/longform_maker/brand_templates.py": _brand_templates,
    "tools/code-cleanup-helper/CHANGELOG.md": _cleanup_changelog,
}
