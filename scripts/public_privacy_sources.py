#!/usr/bin/env python3
"""Creator-neutral public transforms for generated Python source modules."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from public_privacy_fixtures import (
    DEMO_TOP_COUNTERFEIT,
    DEMO_TOP_LEFT,
    DEMO_TOP_RIGHT,
    PUBLIC_LONGFORM_FORMAT_CARD,
    PUBLIC_MEDIA_CAPTION_SYNC_FIXTURE,
    PUBLIC_PUBLISHING_COPY_SELFTEST,
    PUBLIC_SHORTS_CLAIM_CLASSES,
    PUBLIC_SHORTS_READING_FIXTURE,
    PUBLIC_SHORTS_RISKY_CLAIM,
)
from public_privacy_syntax import (
    _append_module_docstring_note,
    _replace_function,
    _subn_once,
    _tree,
)
from public_sync_inventory import PUBLIC_OWNED_PATHS, REFERENCE_FILES
from public_privacy_legacy import (
    _function,
    _generalize_identity,
    _generalize_project_ids,
    _lf,
    _replace_lines,
    _replace_function_docstring,
    _replace_module_docstring,
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


def _design_system_v6(text: str) -> str:
    public = _common(text, _module_doc(
        "Redistributable design recipe compiler",
        "Compiles an anonymized public seed catalog into bounded visual recipes for multiple formats.",
    ))
    return _replace_design_drive_scan(public)


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
    return _subn_once(
        r"(?ms)^[ \t]*with _tf\.NamedTemporaryFile\('w', suffix='\.ass'.*?(?=^[ \t]*assert _char_overlap\(\"\", )",
        PUBLIC_MEDIA_CAPTION_SYNC_FIXTURE, public, "caption-sync narration fixture",
    )


def _shipped_reference_names() -> frozenset:
    names = {Path(name).name for name in REFERENCE_FILES}
    names.update(Path(path).name for path in PUBLIC_OWNED_PATHS
                 if path.startswith("codex-skill/video-autopilot/references/"))
    return frozenset(names)


def _top_assignment(public: str, name: str) -> ast.Assign:
    for node in _tree(public).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return node
    raise ValueError(f"public sanitizer expected assignment {name!r}")


def _route_target(value: str, shipped: frozenset) -> bool:
    return "/" not in value and "\\" not in value and value in shipped


def _filter_reference_routes(public: str, shipped: frozenset) -> str:
    node = _top_assignment(public, "REFERENCE_ROUTES")
    if not isinstance(node.value, ast.Dict):
        raise ValueError("public sanitizer expected REFERENCE_ROUTES to be a dict")
    rows = []
    for key, value in zip(node.value.keys, node.value.values):
        names = [element.value for element in getattr(value, "elts", ())
                 if isinstance(element, ast.Constant) and isinstance(element.value, str)]
        kept = [name for name in names if _route_target(name, shipped)]
        if not isinstance(key, ast.Constant) or not kept:
            raise ValueError("public sanitizer cannot keep a shipped route for every format")
        rendered = ", ".join(json.dumps(name, ensure_ascii=False) for name in kept)
        rows.append(f"    {json.dumps(key.value)}: ({rendered}{',' if len(kept) == 1 else ''}),")
    replacement = "REFERENCE_ROUTES = {\n" + "\n".join(rows) + "\n}"
    return _replace_lines(public, node.lineno, node.end_lineno or node.lineno, replacement)


def _filter_topic_routes(public: str, shipped: frozenset) -> str:
    node = _top_assignment(public, "TOPIC_ROUTES")
    if not isinstance(node.value, ast.Tuple):
        raise ValueError("public sanitizer expected TOPIC_ROUTES to be a tuple")
    lines = public.splitlines(keepends=True)
    dropped = []
    for row in node.value.elts:
        target = row.elts[-1] if isinstance(row, ast.Tuple) and row.elts else None
        if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
            raise ValueError("public sanitizer expected (pattern, reference) topic routes")
        if _route_target(target.value, shipped):
            continue
        head = lines[row.lineno - 1].encode("utf-8")[:row.col_offset]
        tail = lines[row.end_lineno - 1].encode("utf-8")[row.end_col_offset:]
        if head.strip() or tail.strip() not in (b",", b""):
            raise ValueError("public sanitizer expected one topic route per source line block")
        dropped.append(row)
    for row in sorted(dropped, key=lambda item: item.lineno, reverse=True):
        del lines[row.lineno - 1:row.end_lineno]
    return "".join(lines)


def _context_router(text: str) -> str:
    """Route only to shipped references; drop maintainer-only routes and templates."""
    shipped = _shipped_reference_names()
    public = _append_module_docstring_note(
        _lf(text), "PUBLIC_FIXTURE: routes target only references shipped with this kit.")
    public = _subn_once(
        r'(?m)^(\s*"longform": )"16:9；[^"\n]*"(,?)$',
        lambda match: match.group(1) + json.dumps(PUBLIC_LONGFORM_FORMAT_CARD, ensure_ascii=False) + match.group(2),
        public, "longform format card",
    )
    public = _filter_topic_routes(_filter_reference_routes(public, shipped), shipped)
    public = re.sub(
        r'REFS / "([^"/\\]+\.md)"',
        lambda match: match.group(0) if match.group(1) in shipped else 'REFS / "craft-index.md"',
        public,
    )
    leftovers = sorted({
        node.value for node in ast.walk(_tree(public))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.endswith(".md") and "*" not in node.value
        and not _route_target(node.value, shipped)
    })
    if leftovers:
        raise ValueError(f"public context router still routes to {len(leftovers)} non-shipped references")
    return _generalize_project_ids(_generalize_identity(public))


def _battle_name_map(public: str, functions: tuple) -> dict:
    """Map fixture tops to fictional names by authenticity, in source order."""
    rows = []
    for name in functions:
        for node in ast.walk(_function(public, name)):
            if not isinstance(node, ast.Dict):
                continue
            fields = {key.value: value.value for key, value in zip(node.keys, node.values)
                      if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)}
            if {"name", "authenticity"} <= set(fields):
                rows.append((node.lineno, node.col_offset, fields["name"], fields["authenticity"]))
    pools = {"official": [DEMO_TOP_LEFT, DEMO_TOP_RIGHT], "counterfeit": [DEMO_TOP_COUNTERFEIT]}
    mapping: dict = {}
    for _line, _column, top, authenticity in sorted(rows):
        if top in mapping or top in (DEMO_TOP_LEFT, DEMO_TOP_RIGHT, DEMO_TOP_COUNTERFEIT):
            continue
        pool = pools.get(authenticity)
        if not pool:
            raise ValueError("public sanitizer has no fictional top left for a battle fixture")
        mapping[top] = pool.pop(0)
    if not mapping:
        raise ValueError("public sanitizer expected battle fixture tops")
    return mapping


def _replace_values(public: str, mapping: dict, label: str) -> str:
    for old, new in sorted(mapping.items(), key=lambda item: -len(item[0])):
        public = public.replace(old, new)
    if any(old in public for old in mapping):
        raise ValueError(f"public sanitizer left a {label} fixture value")
    return public


def _caption_literal(call: ast.AST, index: int) -> ast.Constant:
    caps = next((keyword.value for keyword in getattr(call, "keywords", ())
                 if keyword.arg == "caps_by_seg"), None)
    try:
        literal = caps.elts[index].elts[1].elts[0].elts[0]
    except (AttributeError, IndexError):
        raise ValueError("public sanitizer expected a caps_by_seg caption fixture") from None
    if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
        raise ValueError("public sanitizer expected a literal caption fixture")
    return literal


def _local_call(public: str, function: str, name: str) -> ast.AST:
    for node in ast.walk(_function(public, function)):
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return node.value
    raise ValueError(f"public sanitizer expected {function}.{name}")


def _shorts_gate_commands(text: str) -> str:
    """Replace place, claim and battle fixtures copied from published Shorts."""
    public = _lf(text)
    public = _replace_values(
        public, _battle_name_map(public, ("_battle_test_fixture", "_selftest_battle_rules")), "battle")
    semantic = _function(public, "_selftest_semantic_rules")
    risky = _caption_literal(_local_call(public, "_selftest_semantic_rules", "risky"), 2).value
    evidence = next((node for node in ast.walk(semantic) if isinstance(node, ast.Dict)
                     and [getattr(key, "value", None) for key in node.keys] == [risky]), None)
    classes = next((node.iter for node in ast.walk(semantic) if isinstance(node, ast.For)
                    and isinstance(node.target, ast.Name) and node.target.id == "cls_txt"), None)
    reading = _caption_literal(_local_call(public, "_selftest_reading_rules", "toolong"), 1).value
    if (evidence is None or not isinstance(evidence.values[0], ast.Constant)
            or not isinstance(classes, ast.Tuple)
            or len(classes.elts) != len(PUBLIC_SHORTS_CLAIM_CLASSES)):
        raise ValueError("public sanitizer expected the S-P claim fixtures")
    claim_segment = ast.get_source_segment(public, classes)
    mapping = {
        risky: PUBLIC_SHORTS_RISKY_CLAIM[0],
        evidence.values[0].value: PUBLIC_SHORTS_RISKY_CLAIM[1],
        reading: PUBLIC_SHORTS_READING_FIXTURE,
    }
    public = public.replace(claim_segment, "(" + ", ".join(
        json.dumps(value, ensure_ascii=False) for value in PUBLIC_SHORTS_CLAIM_CLASSES) + ")")
    public = _replace_values(public, mapping, "claim")
    return _append_module_docstring_note(
        public, "PUBLIC_FIXTURE: places, claims and battle tops in these fixtures are fictional.")


def _beyblade_x_rules(text: str) -> str:
    public = _replace_values(_lf(text), _battle_name_map(_lf(text), ("selftest",)), "battle")
    return _append_module_docstring_note(
        public, "PUBLIC_FIXTURE: self-test matchups use fictional tops.")


def _quality_corpus_source(text: str) -> str:
    public = _subn_once(
        r'narrative_similarity\("正版 ([^"\s]+) 決戰", "正版 \1 結果"\)',
        f'narrative_similarity("正版 {DEMO_TOP_RIGHT} 決戰", "正版 {DEMO_TOP_RIGHT} 結果")',
        text, "battle narrative similarity fixture",
    )
    return _append_module_docstring_note(
        public, "PUBLIC_FIXTURE: regression fixtures name fictional subjects.")


def _publishing_copy(text: str) -> str:
    public = _replace_function(_lf(text), "selftest", PUBLIC_PUBLISHING_COPY_SELFTEST)
    return _append_module_docstring_note(
        public, "PUBLIC_FIXTURE: self-test titles use fictional tops, not published titles.")


def _publish_hub_layout(text: str) -> str:
    public = _subn_once(
        r'(assert not VERSION_LIKE\.search\(")[^"\n]*("\))',
        lambda match: match.group(1) + f"S901_{DEMO_TOP_LEFT}對決{DEMO_TOP_RIGHT}" + match.group(2),
        text, "versioned-name negative fixture",
    )
    return _append_module_docstring_note(
        public, "PUBLIC_FIXTURE: package-name fixtures are fictional.")


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


SANITIZERS = {
    'src/longform_maker/shorts_battle_contract.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/review_http_selftest.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/review_daemon.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable workflow component; public fixtures carry no creator data or live proof.")),
    'src/autonomy_plan_repairs.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/storage_audit.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/publish_hub_registry.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/review_process.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/review_readiness.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/script_parsing.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/script_report.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/longform_maker/shorts_caption_validation.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/drama_pipeline/task_prompts.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    'src/drama_pipeline/task_artifacts.py': lambda text: _common(text, _module_doc("Public workflow component", "Configurable source-only workflow implementation; no creator data or live capability proof.")),
    "src/autonomy_standard.py": _autonomy_standard,
    "src/publish_hub_cli.py": _publish_hub_cli,
    "src/design_system_v6.py": _design_system_v6,
    "src/taste_model.py": _taste_model,
    "src/media_delivery_qa.py": _media_delivery_qa,
    "src/delivery_timing_checks.py": _delivery_timing_checks,
    "src/longform_maker/pace_gate.py": _pace_gate,
    "src/context_router.py": _context_router,
    "src/longform_maker/shorts_gate_commands.py": _shorts_gate_commands,
    "src/beyblade_x_rules.py": _beyblade_x_rules,
    "src/quality_corpus.py": _quality_corpus_source,
    "src/publishing_copy.py": _publishing_copy,
    "src/publish_hub_layout.py": _publish_hub_layout,
}
