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


def _module_doc(title: str, purpose: str) -> str:
    return f'''"""{title} (public distribution).

{purpose}

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""'''


def _sanitize_comments(text: str) -> str:
    lines: list[str] = []
    for line in _lf(text).splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            sensitive_context = re.search(
                r"(?:creator|demo_longform|示範長片|實測|審片|評分|回測|淘汰|踩過|抓到)",
                line,
                re.I,
            )
            dated = re.search(r"20\d{2}[-/.]\d{2}[-/.]\d{2}", line)
            measured = re.search(r"(?:\d+(?:\.\d+)?%|\d+\s*/\s*\d+|AVP|CTR|cuts/min)", line, re.I)
            if sensitive_context and (dated or measured):
                indent = line[:len(line) - len(stripped)]
                line = indent + "# PUBLIC_FIXTURE: starter defaults require creator-owned calibration evidence."
            elif sensitive_context and dated:
                line = re.sub(r"20\d{2}[-/.]\d{2}[-/.]\d{2}", "public calibration", line)
        lines.append(line)
    return "\n".join(lines) + "\n"


def _common(text: str, doc: str) -> str:
    public = _replace_module_docstring(_lf(text), doc)
    public = _generalize_project_ids(_generalize_identity(public))
    return _sanitize_comments(public)


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


_VOICE_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-voice\b", re.I)
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def _is_voice_profile_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    segments = [segment for segment in normalized.split("/") if segment]
    has_voice_segment = any(re.search(r"voice", segment, re.I) for segment in segments)
    is_user_path = (
        _WINDOWS_ABSOLUTE.match(value) is not None
        or normalized.startswith("~/")
        or any(segment.lower() in {"skills", "references"} for segment in segments)
    )
    return has_voice_segment and is_user_path


def _cleanup_changelog(text: str) -> str:
    """Generalize legacy voice-profile discovery history without retaining its values."""
    public = _lf(text)

    def replace_code_span(match: re.Match[str]) -> str:
        value = match.group(1)
        if _is_voice_profile_path(value):
            return "`<user-skill-root>/creator-voice/profile.md`"
        return match.group(0)

    public = re.sub(r"`([^`\r\n]+)`", replace_code_span, public)

    def replace_skill_discovery(match: re.Match[str]) -> str:
        line = match.group(0)
        if "<user-skill-root>/creator-voice/profile.md" not in line:
            return line
        if re.search(r"session", line, re.I):
            return (
                "- `SKILL.md` Session discovery loads only the explicitly configured "
                "`<user-skill-root>/creator-voice/profile.md`; public builds do not probe host-local paths"
            )
        return (
            "- `SKILL.md` creator-voice discovery uses "
            "`<user-skill-root>/creator-voice/profile.md`; legacy project adapters remain local-only"
        )

    public = re.sub(r"(?m)^- `SKILL\.md`[^\r\n]*$", replace_skill_discovery, public)
    public = _VOICE_IDENTIFIER.sub("creator-voice", public)
    public = re.sub(
        r"(?m)^- Audit report output[^\r\n]*creator-voice[^\r\n]*$",
        "- Audit report output may use the active creator voice profile while preserving the report contract",
        public,
    )
    public = re.sub(
        r"(?m)^- [^\r\n]*safety\s*>\s*creator-voice\s*>\s*generic default\s*$",
        "- Precedence remains: audit rules and safety > active creator voice profile > generic default",
        public,
    )
    public = re.sub(
        r"(?m)^- creator-voice[^\r\n]*(?:user-level skill|<user-skill-root>)[^\r\n]*$",
        "- Creator voice profiles are configurable user-level inputs, never repository-bound public data",
        public,
    )
    if PUBLIC_FIXTURE not in public:
        first_newline = public.find("\n")
        marker = (
            "\n\n<!-- PUBLIC_FIXTURE: maintainer paths and profile identities are generalized. -->"
        )
        public = public + marker + "\n" if first_newline < 0 else public[:first_newline] + marker + public[first_newline:]
    if re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", public):
        raise ValueError("public cleanup changelog retained an absolute drive path")
    return public


def _audio_chain(text: str) -> str:
    return _common(text, _module_doc(
        "Reusable long-form audio chain",
        "Provides voice processing, room tone, music construction, ducking and final mix helpers.",
    ))


def _media_delivery_qa(text: str) -> str:
    public = _common(text, _module_doc(
        "Media delivery quality assurance",
        "Checks the rendered artifact for technical, audio, caption, freeze, flash and coverage failures.",
    ))
    public = _replace_function_docstring(
        public,
        "classify_flash",
        '    """Separate clustered or micro flashes from isolated transition fades.\n\n'
        '    PUBLIC_FIXTURE: thresholds are configurable starter values and carry no\n'
        '    private project result or dated review evidence.\n'
        '    """',
    )
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


def _replace_review_resolution(text: str) -> str:
    """Replace a maintainer-specific actor allowlist with explicit public config."""
    public = _lf(text)
    scope = _function(public, "resolve_review")
    return _replace_lines(
        public,
        scope.lineno,
        scope.end_lineno or scope.lineno,
        '''REVIEW_ACTORS_ENV = "VIDEO_AUTOPILOT_REVIEW_ACTORS"


def _configured_review_actors() -> set[str]:
    """Return the explicitly configured review actors; an empty set fails closed."""
    raw = os.environ.get(REVIEW_ACTORS_ENV, "")
    return {value.strip().casefold() for value in raw.split(",") if value.strip()}


def resolve_review(queue_id: str, *, actor: str, decision: str,
                   queue_path: str | Path = DEFAULT_QUEUE) -> dict[str, Any]:
    actor_name = str(actor).strip()
    if not actor_name or actor_name.casefold() not in _configured_review_actors():
        raise PermissionError(
            f"Actor is not authorized to resolve the subjective review queue; "
            f"configure {REVIEW_ACTORS_ENV} with a comma-separated allowlist"
        )
    queue = Path(queue_path).resolve()
    with _QueueLock(queue):
        state = _read_json(queue, {"schema_version": 1, "items": []})
        item = next((row for row in state.get("items", []) if row.get("queue_id") == queue_id), None)
        if not item:
            raise KeyError(queue_id)
        item.update(state="RESOLVED", decision=str(decision), resolved_by=actor_name,
                    resolved_at=_now(), updated_at=_now())
        state["updated_at"] = _now()
        _atomic_json(queue, state)
    return item''',
    )


def _replace_review_selftests(text: str) -> str:
    """Make actor authorization behavior executable public contract evidence."""
    public = _lf(text).replace("HAO_REVIEW_REQUIRED", "CREATOR_REVIEW_REQUIRED")
    scope = _function(public, "_selftest_queue")
    return _replace_lines(
        public,
        scope.lineno,
        scope.end_lineno or scope.lineno,
        '''def _selftest_queue(root: Path, artifact: Path, qa: dict, assessed: dict) -> None:
    queue = root / "queue.json"
    first = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    again = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert first["action"] == "ENQUEUED" and again["action"] == "IDEMPOTENT"
    artifact.write_bytes(b"revision-two")
    changed = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                             autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert changed["item"]["revision"] == 2
    errors: list[str] = []
    def worker(identifier: str) -> None:
        try:
            media = root / f"{identifier}.mp4"; media.write_bytes(identifier.encode("utf-8"))
            enqueue_review(content_id=identifier, format="shorts", artifact=media,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))
    threads = [threading.Thread(target=worker, args=(f"S10{i}",)) for i in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert not errors and queue_summary(queue)["counts"]["OPEN"] == 5

    previous = os.environ.pop(REVIEW_ACTORS_ENV, None)
    try:
        try:
            resolve_review(changed["item"]["queue_id"], actor="creator",
                           decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an empty actor allowlist must fail closed")

        os.environ[REVIEW_ACTORS_ENV] = "  CREATOR  "
        resolved = resolve_review(changed["item"]["queue_id"], actor=" creator ",
                                  decision="approve", queue_path=queue)
        assert resolved["state"] == "RESOLVED" and resolved["resolved_by"] == "creator"

        second = next(row for row in queue_summary(queue)["active"]
                      if row["content_id"] != "S001")
        os.environ[REVIEW_ACTORS_ENV] = "reviewer, EDITOR"
        resolved_second = resolve_review(second["queue_id"], actor=" editor ",
                                         decision="approve", queue_path=queue)
        assert resolved_second["resolved_by"] == "editor"

        os.environ[REVIEW_ACTORS_ENV] = "creator,reviewer"
        try:
            resolve_review(next(row["queue_id"] for row in queue_summary(queue)["active"]),
                           actor="bot", decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an unconfigured bot must not resolve creator review")
    finally:
        if previous is None:
            os.environ.pop(REVIEW_ACTORS_ENV, None)
        else:
            os.environ[REVIEW_ACTORS_ENV] = previous''',
    )


def _autonomy_standard(text: str) -> str:
    public = _common(text, _module_doc(
        "Fail-closed unattended editing standard and central review queue",
        "Allows reversible unattended work while keeping subjective approval and publishing human-owned.",
    ))
    return _replace_review_selftests(_replace_review_resolution(public))


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
        originals = {name: getattr(hub, name) for name in (
            "ROOT", "READY", "PUBLISHED", "HUB_AUDIT",
            "_content_manifests", "rebuild_index",
        )}
        try:
            hub.ROOT = root
            hub.READY = root / "hub" / "READY"
            hub.PUBLISHED = root / "hub" / "PUBLISHED"
            hub.HUB_AUDIT = root / "hub" / "_AUDIT"
            package = hub.READY / "shorts" / "review" / "S001"
            package.mkdir(parents=True)
            video = package / "current.mp4"
            video.write_bytes(b"synthetic-published-metadata-fixture")
            manifest = package / "publish.json"
            manifest.write_text(json.dumps({
                "content_id": "S001", "format": "shorts", "status": "review",
                "video": video.name, "sha256": hub._sha256(video),
            }), encoding="utf-8")
            hub._content_manifests = lambda _content_id: [manifest]
            hub.rebuild_index = lambda: {"status": "GREEN"}
            result = hub.mark_published("S001")
            published = json.loads((hub.PUBLISHED / "shorts" / "published" /
                                    "S001" / "publish.json").read_text(encoding="utf-8"))
            metadata = published["published"]
            assert result["published"] == metadata
            assert metadata["platform"] == "reported_by_creator"
            assert metadata["video_id"] is None and metadata["url"] is None
            assert metadata["reported_on"] and metadata["note"]
        finally:
            for name, value in originals.items():
                setattr(hub, name, value)
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
    "src/autonomy_standard.py": _autonomy_standard,
    "src/publish_hub_cli.py": _publish_hub_cli,
    "src/design_system_v6.py": _design_system_v6,
    "src/silent_vlog_maker/checklists.py": _silent_vlog_checklists_public,
    "src/taste_model.py": _taste_model,
    "src/template_compiler.py": _template_compiler,
    "src/longform_maker/audio_chain.py": _audio_chain,
    "src/media_delivery_qa.py": _media_delivery_qa,
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
