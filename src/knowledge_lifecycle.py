# -*- coding: utf-8 -*-
"""Bounded, conflict-aware learning memory for video-autopilot.

Raw feedback remains evidence.  Only deduplicated and sufficiently supported
rules are promoted into the tiny runtime card consumed by context_router.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE = SKILL_ROOT.parent / "knowledge" / "runtime" / "state.json"
DEFAULT_VIDEO_LOG = SKILL_ROOT.parent / "data" / "video_log.md"
DEFAULT_VIDEO_ARCHIVE = SKILL_ROOT.parent / "data" / "video_log_archive.md"


LEDGER_ENV = "VIDEO_AUTOPILOT_KNOWLEDGE_STATE"
SOURCE_KEY_LIMIT = 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_ledger_path() -> Path:
    """Return where learned rules are written.

    A release-managed kit (``release-manifest.json`` beside the code root)
    ships ``DEFAULT_STATE`` as a seed that updates may replace, so learning
    goes to the protected ``data/`` folder instead.  Other layouts keep
    learning in ``DEFAULT_STATE``.  ``VIDEO_AUTOPILOT_KNOWLEDGE_STATE``
    overrides both.
    """
    explicit = os.environ.get(LEDGER_ENV, "").strip()
    if explicit:
        return Path(explicit).expanduser()
    kit_root = SKILL_ROOT.parent
    if (kit_root / "release-manifest.json").is_file():
        return kit_root / "data" / "knowledge_state.json"
    return Path(DEFAULT_STATE)


def _resolve_state(state_path: str | os.PathLike | None) -> Path:
    """Explicit paths win; otherwise read the ledger, migrating a learned seed once."""
    if state_path is not None:
        return Path(state_path)
    ledger, seed = default_ledger_path(), Path(DEFAULT_STATE)
    if ledger.is_file() or ledger == seed or not seed.is_file():
        return ledger
    seeded = load_state(seed)
    if not seeded["records"]:
        return seed
    # Rules learned before the ledger moved must not vanish when an update
    # replaces the managed seed: copy them into protected data first.
    _atomic_write(ledger, seeded)
    return ledger


def estimate_tokens(value) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", text))
    return cjk + math.ceil(max(0, len(text) - cjk) / 4)


def load_state(path: str | os.PathLike = DEFAULT_STATE) -> dict:
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2 or not isinstance(data.get("records"), list):
        raise ValueError(f"Invalid knowledge state: {target}")
    return data


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".knowledge-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".knowledge-text-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _fingerprint(scope: str, rule: str) -> str:
    return hashlib.sha256(f"{_normalize(scope)}|{_normalize(rule)}".encode("utf-8")).hexdigest()[:12]


def _scope_values(values: list[str] | None) -> list[str]:
    normalized = {str(value).strip().lower() for value in (values or ["*"]) if str(value).strip()}
    return ["*"] if normalized & {"*", "all"} else sorted(normalized)


def _source_key(source: str | None, evidence: str) -> str:
    """One observation = one source (a video/version id); else its evidence text."""
    basis = _normalize(source) if source and str(source).strip() else _normalize(evidence)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def _count_source(record: dict, key: str) -> None:
    """Support counts distinct observations, so a retried review cannot promote a rule."""
    if "sources" not in record:
        # Legacy rows: keep their support, and treat their evidence as already seen.
        record["sources"] = [_source_key(None, item) for item in record.get("evidence", [])]
    if key in record["sources"]:
        return
    record["sources"] = (record["sources"] + [key])[-SOURCE_KEY_LIMIT:]
    record["support"] = int(record.get("support", 0)) + 1


def _resolve_supersede(state: dict, record: dict, old_id: str) -> None:
    other = next((row for row in state["records"] if row.get("id") == old_id), None)
    if not other:
        raise ValueError(f"Unknown superseded rule: {old_id}")
    if other["id"] == record["id"]:
        raise ValueError("a rule cannot supersede itself")
    other["pinned"] = False
    other["pinned_explicit"] = False
    other["superseded_by"] = record["id"]
    # Superseding is the human resolution of a conflict between the two rules.
    record["contradictions"] = [item for item in record.get("contradictions", []) if item != other["id"]]
    other["contradictions"] = [item for item in other.get("contradictions", []) if item != record["id"]]
    record.setdefault("supersedes", [])
    if other["id"] not in record["supersedes"]:
        record["supersedes"].append(other["id"])


def record_feedback(
    rule: str,
    evidence: str,
    *,
    scope: str = "project",
    formats: list[str] | None = None,
    domains: list[str] | None = None,
    triggers: list[str] | None = None,
    kind: str = "soft",
    contradicts: str | None = None,
    supersedes: str | None = None,
    pin: bool = False,
    source: str | None = None,
    state_path: str | os.PathLike | None = None,
) -> dict:
    """Record one observation of a rule.

    ``source`` identifies the observed video/version (for example
    ``content_id@sha12``); repeats of the same source never add support.
    ``pin`` is an explicit creator instruction and survives later
    observations until the rule is contradicted or superseded.
    """
    if not str(rule).strip() or not str(evidence).strip():
        raise ValueError("rule and evidence are required")
    if kind not in {"hard", "soft"}:
        raise ValueError("kind must be hard or soft")
    if contradicts and supersedes:
        raise ValueError("use either contradicts or supersedes, not both")
    state = load_state(_resolve_state(state_path))
    path = Path(state_path) if state_path is not None else default_ledger_path()
    fingerprint = _fingerprint(scope, rule)
    record = next((row for row in state["records"] if row.get("fingerprint") == fingerprint), None)
    created = record is None
    if created:
        record = {
            "id": f"K-{fingerprint}",
            "fingerprint": fingerprint,
            "scope": scope,
            "formats": _scope_values(formats),
            "domains": _scope_values(domains),
            "triggers": [],
            "kind": kind,
            "rule": str(rule).strip(),
            "support": 0,
            "evidence": [],
            "contradictions": [],
            "pinned": False,
            "created_at": _now(),
        }
        state["records"].append(record)
    _count_source(record, _source_key(source, evidence))
    record["formats"] = _scope_values(record.get("formats"))
    record["domains"] = _scope_values(record.get("domains"))
    if triggers is not None:
        record["triggers"] = sorted({
            _normalize(value) for value in [*(record.get("triggers") or []), *triggers]
            if _normalize(value)
        })
    else:
        record.setdefault("triggers", [])
    record["updated_at"] = _now()
    if evidence not in record["evidence"]:
        record["evidence"] = (record["evidence"] + [str(evidence).strip()])[-5:]
    if contradicts:
        other = next((row for row in state["records"] if row.get("id") == contradicts), None)
        if not other:
            raise ValueError(f"Unknown contradicted rule: {contradicts}")
        if other["id"] not in record["contradictions"]:
            record["contradictions"].append(other["id"])
        other.setdefault("contradictions", [])
        if record["id"] not in other["contradictions"]:
            other["contradictions"].append(record["id"])
        other["pinned"] = False
        other["pinned_explicit"] = False
    if supersedes:
        _resolve_supersede(state, record, supersedes)
    minimum = int(state.get("promotion_policy", {}).get("minimum_support", 3))
    record["pinned_explicit"] = bool(pin or record.get("pinned_explicit"))
    record["pinned"] = not record.get("contradictions") and bool(
        record["pinned_explicit"] or record["support"] >= minimum
    )
    state["records"] = sorted(state["records"], key=lambda row: row["id"])
    state["revision"] = int(state.get("revision", 0)) + 1
    state["updated_at"] = _now()
    _atomic_write(path, state)
    return {"created": created, "record": record, "revision": state["revision"]}


def select_rules(
    mode: str = "build",
    format: str = "shorts",
    domain: str = "general",
    topic: str = "",
    *,
    limit: int = 6,
    state_path: str | os.PathLike | None = None,
) -> list[dict]:
    state = load_state(_resolve_state(state_path))
    topic_normalized = _normalize(topic)
    candidates = []
    for record in state["records"]:
        if not record.get("pinned") or record.get("contradictions") or record.get("superseded_by"):
            continue
        formats = record.get("formats", ["*"])
        domains = record.get("domains", ["*"])
        format_wildcard = bool({"*", "all"} & set(formats))
        domain_wildcard = bool({"*", "all"} & set(domains))
        if not format_wildcard and format not in formats:
            continue
        if not domain_wildcard and domain not in domains:
            continue
        score = int(record.get("support", 0))
        score += 5 if format in formats else 0
        score += 5 if domain in domains else 0
        score += 3 if record.get("kind") == "hard" else 0
        trigger_hits = sum(1 for trigger in record.get("triggers", [])
                           if trigger and trigger in topic_normalized)
        score += trigger_hits * 12
        specificity = int(format in formats) + int(domain in domains) + min(2, trigger_hits) * 2
        scoped_memory = int(str(record.get("scope", "project")) != "project")
        candidates.append((specificity, scoped_memory, score, record))
    # 任務精確記憶先於全域 core；否則 support=99 的 core 永遠佔滿小卡，
    # 使用者剛教的新片型規則即使 pinned 也永遠載不到，表面「記住」實際仍忘記。
    candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]["id"]))
    return [
        {
            "id": record["id"],
            "kind": record["kind"],
            "rule": record["rule"],
            "support": record["support"],
        }
        for _specificity, _scoped, _score, record in candidates[: max(1, int(limit))]
    ]


def build_digest(state_path: str | os.PathLike | None = None) -> dict:
    state = load_state(_resolve_state(state_path))
    pinned = [row for row in state["records"]
              if row.get("pinned") and not row.get("contradictions") and not row.get("superseded_by")]
    conflicts = [row for row in state["records"] if row.get("contradictions")]
    # Runtime packets never inject every pinned rule; select_rules() routes at
    # most ``runtime_rule_limit`` cards for the current format/domain/topic.
    # Audit the worst possible packet (the longest N cards), not the whole
    # historical pinned set, otherwise learning more topics creates a false RED
    # even though no prompt can receive that many rules.
    limit = max(1, int(state.get("promotion_policy", {}).get("runtime_rule_limit", 6)))
    budget_rows = sorted(pinned, key=lambda row: len(str(row.get("rule", ""))), reverse=True)[:limit]
    digest = {
        # Runtime only needs the rule text. IDs, evidence and lifecycle metadata
        # remain in state.json and are loaded only for audit/review. Keeping them
        # out of every edit packet prevents memory growth from becoming a token tax.
        "rules": "\n".join(row["rule"] for row in budget_rows),
        "budget_basis": "worst_case_longest_%d_of_%d_active_pinned" % (limit, len(pinned)),
    }
    if conflicts:
        digest["conflicts"] = [row["id"] for row in conflicts]
    # Budget the text actually injected into an edit prompt. The wrapper is
    # diagnostic output only and is not copied into the runtime context.
    digest["estimated_tokens"] = estimate_tokens(digest["rules"])
    return digest


def audit(state_path: str | os.PathLike | None = None) -> dict:
    state = load_state(_resolve_state(state_path))
    ids = [row["id"] for row in state["records"]]
    fingerprints = [row["fingerprint"] for row in state["records"]]
    conflicts = [row["id"] for row in state["records"] if row.get("contradictions")]
    digest = build_digest(state_path)
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate knowledge ids")
    if len(fingerprints) != len(set(fingerprints)):
        errors.append("duplicate knowledge fingerprints")
    known = set(ids)
    for row in state["records"]:
        superseded_by = row.get("superseded_by")
        if superseded_by and superseded_by not in known:
            errors.append(f"unknown superseded_by reference: {row['id']}")
        if superseded_by and row.get("pinned"):
            errors.append(f"superseded rule remains pinned: {row['id']}")
        for old_id in row.get("supersedes", []):
            if old_id not in known:
                errors.append(f"unknown supersedes reference: {row['id']}")
    if digest["estimated_tokens"] > 900:
        errors.append("runtime knowledge digest exceeds 900 tokens")
    return {
        "status": "GREEN" if not errors else "RED",
        "records": len(ids),
        "pinned": sum(
            1 for row in state["records"]
            if row.get("pinned") and not row.get("contradictions") and not row.get("superseded_by")
        ),
        "conflicts": conflicts,
        "estimated_digest_tokens": digest["estimated_tokens"],
        "errors": errors,
    }


def rotate_numbered_video_log(
    source_path: str | os.PathLike = DEFAULT_VIDEO_LOG,
    archive_path: str | os.PathLike = DEFAULT_VIDEO_ARCHIVE,
    *,
    apply: bool = False,
) -> dict:
    """Archive whole legacy ``## #NNN`` records without losing a byte of evidence.

    The active log keeps its preface, template and newer named outcome sections.  The
    archive is written first and tagged with a digest, making retries non-destructive.
    """
    source = Path(source_path)
    archive = Path(archive_path)
    text = source.read_text(encoding="utf-8")
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    numbered = [part for part in parts if re.match(r"^## #\d+\b", part)]
    kept = [part for part in parts if not re.match(r"^## #\d+\b", part)]
    archived_text = "".join(numbered).strip()
    digest = hashlib.sha256(archived_text.encode("utf-8")).hexdigest()[:16] if archived_text else None
    before_lines = len(text.splitlines())
    after_text = "".join(kept).rstrip() + "\n"
    result = {
        "mode": "apply" if apply else "dry-run",
        "source": str(source),
        "archive": str(archive),
        "sections": len(numbered),
        "digest": digest,
        "before_lines": before_lines,
        "after_lines": len(after_text.splitlines()),
        "archived_lines": len(archived_text.splitlines()),
        "changed": bool(numbered),
    }
    if not apply or not numbered:
        return result

    prior = archive.read_text(encoding="utf-8") if archive.is_file() else "# Video Log Archive\n"
    marker = f"<!-- rotation:{digest} -->"
    if marker not in prior:
        stamp = datetime.now(timezone.utc).date().isoformat()
        addition = (
            f"\n\n---\n\n# Production records rotated {stamp}\n\n"
            f"{marker}\n\n{archived_text}\n"
        )
        _atomic_write_text(archive, prior.rstrip() + addition)
    _atomic_write_text(source, after_text)
    return result


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="knowledge-") as temp:
        path = Path(temp) / "state.json"
        path.write_text(json.dumps({
            "schema_version": 2,
            "revision": 0,
            "promotion_policy": {"minimum_support": 3},
            "records": [],
        }, ensure_ascii=False), encoding="utf-8")
        for i in range(3):
            result = record_feedback("同一規則", f"evidence-{i}", state_path=path)
        assert result["record"]["pinned"] is True
        assert len(load_state(path)["records"]) == 1
        assert select_rules(state_path=path)[0]["rule"] == "同一規則"
        scoped = record_feedback(
            "Shorts 新字幕規則", "Hao 明確指定", scope="caption", formats=["shorts"],
            domains=["all"], pin=True, state_path=path,
        )
        assert scoped["record"]["domains"] == ["*"]
        revised = record_feedback(
            "Shorts 字幕修正版", "Hao 更正舊規則", scope="caption", formats=["shorts"],
            domains=["all"], triggers=["mrbeast", "字幕"], kind="hard", pin=True,
            supersedes=scoped["record"]["id"],
            state_path=path,
        )
        revised_state = load_state(path)
        old = next(row for row in revised_state["records"] if row["id"] == scoped["record"]["id"])
        assert old["pinned"] is False and old["superseded_by"] == revised["record"]["id"]
        state = load_state(path)
        state["records"].append({
            "id": "K-core-test", "fingerprint": "coretest", "scope": "project",
            "formats": ["*"], "domains": ["*"], "kind": "hard",
            "rule": "全域高 support", "support": 99, "evidence": ["core"],
            "contradictions": [], "pinned": True,
        })
        _atomic_write(path, state)
        selected = select_rules("build", "shorts", "ai", "MrBeast 字幕", limit=2, state_path=path)
        assert selected[0]["rule"] == "Shorts 字幕修正版", "revised scoped memory must beat old and global core"
        assert audit(path)["status"] == "GREEN"
        log = Path(temp) / "video_log.md"
        archive = Path(temp) / "video_log_archive.md"
        log.write_text("# Log\n\n## #001 — old\nold evidence\n\n## Current\nkeep\n", encoding="utf-8")
        preview = rotate_numbered_video_log(log, archive)
        assert preview["sections"] == 1 and "old evidence" in log.read_text(encoding="utf-8")
        applied = rotate_numbered_video_log(log, archive, apply=True)
        assert applied["changed"] and "old evidence" not in log.read_text(encoding="utf-8")
        assert "old evidence" in archive.read_text(encoding="utf-8")
        assert rotate_numbered_video_log(log, archive, apply=True)["sections"] == 0
        _self_test_memory_guards(Path(temp))
        _self_test_ledger_location(Path(temp))
    print("knowledge_lifecycle self-test GREEN")


def _empty_state(path: Path, records: list | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": 2, "revision": 0,
        "promotion_policy": {"minimum_support": 3}, "records": records or [],
    }, ensure_ascii=False), encoding="utf-8")
    return path


def _self_test_memory_guards(temp: Path) -> None:
    path = _empty_state(temp / "guards.json")
    for _ in range(3):
        retried = record_feedback("同一支片的意見", "cut-1 @ 3.0s", state_path=path)
    assert retried["record"]["support"] == 1 and not retried["record"]["pinned"], \
        "a retried review of one cut must not promote a rule"
    for note in ("first wording", "second wording", "third wording"):
        same_video = record_feedback("同一來源", note, source="video-a@abc123", state_path=path)
    assert same_video["record"]["support"] == 1 and not same_video["record"]["pinned"]
    for video in ("video-a@1", "video-b@2", "video-c@3"):
        repeated = record_feedback("三支片都出現", "note", source=video, state_path=path)
    assert repeated["record"]["support"] == 3 and repeated["record"]["pinned"]
    hard = record_feedback("安全硬規則", "creator instruction", kind="hard", pin=True, state_path=path)
    again = record_feedback("安全硬規則", "seen once more", kind="hard", state_path=path)
    assert again["record"]["pinned"] and again["record"]["pinned_explicit"], \
        "more evidence must not demote an explicit pin"
    rival = record_feedback("相反規則", "creator note", pin=True, contradicts=hard["record"]["id"],
                            state_path=path)
    blocked = {row["id"] for row in select_rules(format="shorts", limit=10, state_path=path)}
    assert hard["record"]["id"] not in blocked and rival["record"]["id"] not in blocked
    record_feedback("相反規則", "creator resolved it", supersedes=hard["record"]["id"], state_path=path)
    resolved = {row["id"] for row in select_rules(format="shorts", limit=10, state_path=path)}
    assert rival["record"]["id"] in resolved and hard["record"]["id"] not in resolved, \
        "superseding must resolve the conflict it settles"
    assert audit(path)["status"] == "GREEN"


def _self_test_ledger_location(temp: Path) -> None:
    global SKILL_ROOT, DEFAULT_STATE
    kit = temp / "kit"
    (kit / "src").mkdir(parents=True)
    (kit / "release-manifest.json").write_text("{}", encoding="utf-8")
    learned = {"id": "K-legacy", "fingerprint": "legacy", "scope": "project", "formats": ["*"],
               "domains": ["*"], "kind": "soft", "rule": "舊規則", "support": 3,
               "evidence": ["a", "b", "c"], "contradictions": [], "pinned": True}
    seed = _empty_state(kit / "knowledge" / "runtime" / "state.json", [learned])
    saved = SKILL_ROOT, DEFAULT_STATE, os.environ.pop(LEDGER_ENV, None)
    SKILL_ROOT, DEFAULT_STATE = kit / "src", seed
    try:
        ledger = kit / "data" / "knowledge_state.json"
        assert default_ledger_path() == ledger
        assert [row["rule"] for row in select_rules(format="longform")] == ["舊規則"]
        assert ledger.is_file(), "rules learned in the managed seed must migrate to data/"
        _empty_state(seed)  # an update replaces the seed with the empty public ledger
        record_feedback("新規則", "after update")
        rules = {row["rule"] for row in load_state(ledger)["records"]}
        assert rules == {"舊規則", "新規則"} and not load_state(seed)["records"]
        os.environ[LEDGER_ENV] = str(temp / "override.json")
        assert default_ledger_path() == temp / "override.json"
    finally:
        SKILL_ROOT, DEFAULT_STATE = saved[0], saved[1]
        os.environ.pop(LEDGER_ENV, None)
        if saved[2] is not None:
            os.environ[LEDGER_ENV] = saved[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded learning memory")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("audit")
    subs.add_parser("digest")
    rec = subs.add_parser("record")
    rec.add_argument("--rule", required=True)
    rec.add_argument("--evidence", required=True)
    rec.add_argument("--scope", default="project")
    rec.add_argument("--format", action="append", dest="formats")
    rec.add_argument("--domain", action="append", dest="domains")
    rec.add_argument("--trigger", action="append", dest="triggers")
    rec.add_argument("--kind", choices=("hard", "soft"), default="soft")
    rec.add_argument("--contradicts", default=None)
    rec.add_argument("--supersedes", default=None)
    rec.add_argument("--pin", action="store_true")
    rec.add_argument("--source", default=None,
                     help="observed video/version id; repeats of one source never add support")
    rotate = subs.add_parser("rotate-video-log")
    rotate.add_argument("--apply", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "record":
        result = record_feedback(
            args.rule,
            args.evidence,
            scope=args.scope,
            formats=args.formats,
            domains=args.domains,
            triggers=args.triggers,
            kind=args.kind,
            contradicts=args.contradicts,
            supersedes=args.supersedes,
            pin=args.pin,
            source=args.source,
        )
    elif args.command == "rotate-video-log":
        result = rotate_numbered_video_log(apply=args.apply)
    elif args.command == "digest":
        result = build_digest()
    else:
        result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "audit":
        print("KNOWLEDGE " + result["status"])
        return 0 if result["status"] == "GREEN" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
