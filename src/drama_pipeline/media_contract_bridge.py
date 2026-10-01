"""Fail-closed bridge to ai-short-drama's canonical Media Job contract.

The schemas and semantic linter stay owned by ``ai-short-drama``.  This module
loads that implementation directly, validates a closed-world bundle, and makes
sure queue snapshots and completed results still point at the exact same jobs.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .planner import locate_short_drama_skill
from .store import ProjectStore, is_within, sha256_file


CONTRACT_VERSION = "1.0"
MEDIA_JOB_DIR = "media-jobs"
EXECUTION_MODE = "locked_media_jobs"
_CONTRACT: Any | None = None


def _contract_module() -> Any:
    global _CONTRACT
    if _CONTRACT is not None:
        return _CONTRACT
    source = locate_short_drama_skill() / "scripts" / "media_contract_lint.py"
    if not source.is_file():
        raise RuntimeError(f"ai-short-drama media contract linter is unavailable: {source}")
    name = "_hao_ai_short_drama_media_contract_lint"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load media contract linter: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    _CONTRACT = module
    return module


def self_test_contract_location() -> None:
    """Exercise portable Skill discovery and fail-closed missing-linter handling."""
    global _CONTRACT
    previous = os.environ.get("AI_SHORT_DRAMA_SKILL")
    try:
        with tempfile.TemporaryDirectory(prefix="media-contract-location-") as raw:
            root = Path(raw)
            good = root / "good-skill"
            scripts = good / "scripts"
            scripts.mkdir(parents=True)
            (good / "SKILL.md").write_text(
                "---\nname: ai-short-drama\n---\n", encoding="utf-8"
            )
            (scripts / "media_contract_lint.py").write_text(
                'LOCATION_PROBE = "GREEN"\n', encoding="utf-8"
            )
            os.environ["AI_SHORT_DRAMA_SKILL"] = str(good)
            _CONTRACT = None
            module = _contract_module()
            if getattr(module, "LOCATION_PROBE", None) != "GREEN":
                raise AssertionError("media contract linter override was not loaded")

            missing = root / "missing-linter-skill"
            missing.mkdir()
            (missing / "SKILL.md").write_text(
                "---\nname: ai-short-drama\n---\n", encoding="utf-8"
            )
            os.environ["AI_SHORT_DRAMA_SKILL"] = str(missing)
            _CONTRACT = None
            try:
                _contract_module()
            except RuntimeError as exc:
                if "media contract linter is unavailable" not in str(exc):
                    raise
            else:
                raise AssertionError("missing media contract linter was accepted")
    finally:
        _CONTRACT = None
        if previous is None:
            os.environ.pop("AI_SHORT_DRAMA_SKILL", None)
        else:
            os.environ["AI_SHORT_DRAMA_SKILL"] = previous


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _contract_errors(report: Any) -> str:
    return "; ".join(f"{item.path}: {item.message}" for item in report.errors)


def _safe_manifest_file(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).name != raw or not raw.endswith(".json"):
        raise ValueError(f"manifest job file must be one plain .json filename: {raw!r}")
    path = (root / raw).resolve()
    if not is_within(path, root):
        raise ValueError(f"manifest job file escapes media-jobs: {raw!r}")
    return path


def _pack_episode_ids(store: ProjectStore) -> list[str]:
    episodes = store.pack().get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("production_pack.json must contain at least one episode")
    ids: list[str] = []
    for item in episodes:
        episode_id = item.get("id") if isinstance(item, dict) else None
        if (
            not isinstance(episode_id, str)
            or not episode_id
            or Path(episode_id).name != episode_id
            or episode_id in ids
        ):
            raise ValueError(f"production pack contains an unsafe or duplicate episode id: {episode_id!r}")
        ids.append(episode_id)
    return ids


def _manifest_specs(store: ProjectStore) -> list[tuple[str, Path]]:
    """Resolve the canonical one-manifest-per-episode layout.

    A one-episode project may keep the original ``media-jobs/manifest.json``
    layout. Multi-episode projects must use
    ``media-jobs/<episode-id>/manifest.json`` for every pack episode.
    """

    root = (store.root / MEDIA_JOB_DIR).resolve()
    episode_ids = _pack_episode_ids(store)
    flat_manifest = root / "manifest.json"
    if flat_manifest.is_file():
        if len(episode_ids) != 1:
            raise ValueError(
                "multi-episode projects require one canonical manifest at "
                "media-jobs/<episode-id>/manifest.json for every episode"
            )
        return [(episode_ids[0], flat_manifest)]

    specs = [(episode_id, root / episode_id / "manifest.json") for episode_id in episode_ids]
    missing = [str(path) for _episode_id, path in specs if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "real short-drama runs require canonical media-jobs manifest(s); missing: "
            + ", ".join(missing)
        )
    return specs


def canonical_manifest_records(store: ProjectStore) -> list[dict[str, str]]:
    return [
        {
            "episode_id": episode_id,
            "path": store.relative(path),
            "sha256": sha256_file(path),
        }
        for episode_id, path in _manifest_specs(store)
    ]


def _load_episode_manifest(
    store: ProjectStore,
    expected_episode_id: str,
    manifest_path: Path,
    *,
    pack_hash: str,
    seen_job_ids: set[str],
    seen_source_ids: set[str],
    seen_output_paths: set[str],
) -> tuple[list[dict[str, Any]], set[Path]]:
    media_root = (store.root / MEDIA_JOB_DIR).resolve()
    root = manifest_path.parent.resolve()
    if not is_within(manifest_path.resolve(), media_root):
        raise ValueError("media-job manifest must be a real project-local file")
    manifest = _read_json(manifest_path, "media-job manifest")
    if set(manifest) != {"contract_version", "source_id", "jobs"}:
        raise ValueError("media-job manifest must contain only contract_version, source_id, and jobs")
    if manifest.get("contract_version") != CONTRACT_VERSION:
        raise ValueError(f"unsupported media-job manifest contract: {manifest.get('contract_version')!r}")
    source_id = manifest.get("source_id")
    entries = manifest.get("jobs")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("media-job manifest source_id must be non-empty")
    if not isinstance(entries, list) or not entries:
        raise ValueError("media-job manifest jobs must be a non-empty array")

    expected_paths = {manifest_path.resolve()}
    seen_files: set[str] = set()
    jobs: list[dict[str, Any]] = []
    contract = _contract_module()
    shared_source: dict[str, Any] | None = None
    expected_start = 0.0
    source_duration: float | None = None

    for position, raw in enumerate(entries, start=1):
        if not isinstance(raw, dict) or set(raw) != {"job_id", "file", "canonical_sha256"}:
            raise ValueError(f"manifest.jobs[{position - 1}] has an invalid shape")
        job_id = raw.get("job_id")
        filename = raw.get("file")
        expected_hash = raw.get("canonical_sha256")
        if not isinstance(job_id, str) or not job_id or job_id in seen_job_ids:
            raise ValueError(f"manifest contains an invalid or duplicate job_id: {job_id!r}")
        path = _safe_manifest_file(root, filename)
        if filename in seen_files:
            raise ValueError(f"manifest contains duplicate job file: {filename}")
        if not path.is_file():
            raise FileNotFoundError(f"manifest job file is missing: {path}")
        expected_paths.add(path)
        seen_files.add(filename)
        seen_job_ids.add(job_id)

        job = _read_json(path, "media job")
        report = contract.lint_job(job)
        if report.errors:
            raise ValueError(f"invalid canonical media job {filename}: {_contract_errors(report)}")
        actual_hash = contract.canonical_sha256(job)
        if expected_hash != actual_hash:
            raise ValueError(f"manifest hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}")
        if job.get("job_id") != job_id:
            raise ValueError(f"manifest job_id does not match {filename}")
        for output_key in ("video_path", "receipt_path"):
            output_path = str(job.get("outputs", {}).get(output_key, ""))
            collision_key = Path(output_path).as_posix().casefold()
            if collision_key in seen_output_paths:
                raise ValueError(
                    f"canonical media jobs reuse an output path: {output_path}"
                )
            seen_output_paths.add(collision_key)
        source = job.get("source", {})
        if source.get("source_id") != source_id:
            raise ValueError(f"source_id mismatch in {filename}")
        if source.get("episode_id") != expected_episode_id:
            raise ValueError(
                f"{filename} belongs to {source.get('episode_id')!r}, expected {expected_episode_id!r}"
            )
        if source.get("production_pack_sha256") != pack_hash:
            raise ValueError(f"{filename} does not bind the current locked production_pack.json")
        if shared_source is None:
            shared_source = source
        elif source != shared_source:
            raise ValueError("all media jobs in one manifest must share the exact source object")

        segment = job.get("segment", {})
        if segment.get("index") != position or segment.get("count") != len(entries):
            raise ValueError("manifest jobs must be in complete one-based segment order")
        if segment.get("segment_id") != f"seg_{position:03d}":
            raise ValueError("segment_id must match manifest order")
        start = float(segment.get("source_start_seconds", -1))
        end = float(segment.get("source_end_seconds", -1))
        duration = float(segment.get("duration_seconds", -1))
        if abs(start - expected_start) > contract.EPSILON or abs((end - start) - duration) > contract.EPSILON:
            raise ValueError("media-job segment ranges must be contiguous and match duration_seconds")
        expected_start = end
        current_source_duration = float(segment.get("source_duration_seconds", -1))
        if source_duration is None:
            source_duration = current_source_duration
        elif abs(current_source_duration - source_duration) > contract.EPSILON:
            raise ValueError("all media jobs must share source_duration_seconds")
        jobs.append(
            {
                "job": job,
                "path": path,
                "manifest_path": manifest_path.resolve(),
                "canonical_sha256": actual_hash,
            }
        )

    if source_duration is None or abs(expected_start - source_duration) > contract.EPSILON:
        raise ValueError("media-job segments do not cover the locked source duration")
    if source_id in seen_source_ids:
        raise ValueError(f"duplicate source_id across episode manifests: {source_id}")
    seen_source_ids.add(source_id)
    return jobs, expected_paths


def load_canonical_bundle(store: ProjectStore) -> list[dict[str, Any]]:
    """Load every project episode as one ordered, closed-world Media Job bundle."""

    media_root = (store.root / MEDIA_JOB_DIR).resolve()
    specs = _manifest_specs(store)
    contract = _contract_module()
    pack_hash = contract.canonical_sha256(store.pack())
    seen_job_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    seen_output_paths: set[str] = set()
    expected_json: set[Path] = set()
    jobs: list[dict[str, Any]] = []
    for episode_id, manifest_path in specs:
        episode_jobs, episode_paths = _load_episode_manifest(
            store,
            episode_id,
            manifest_path,
            pack_hash=pack_hash,
            seen_job_ids=seen_job_ids,
            seen_source_ids=seen_source_ids,
            seen_output_paths=seen_output_paths,
        )
        jobs.extend(episode_jobs)
        expected_json.update(episode_paths)

    actual_json = {
        path.resolve()
        for path in media_root.rglob("*.json")
        if path.is_file()
    }
    if actual_json != expected_json:
        extra = sorted(path.as_posix() for path in actual_json - expected_json)
        missing = sorted(path.as_posix() for path in expected_json - actual_json)
        raise ValueError(f"media-jobs is not closed-world; extra={extra}, missing={missing}")
    return jobs


def task_payload_from_job(store: ProjectStore, item: dict[str, Any]) -> dict[str, Any]:
    """Create a queue payload containing only exact job fields, never a rewritten prompt."""

    job = item["job"]
    target = job["generation_target"]
    return {
        "execution_contract": "ai-short-drama.media-job/1.0",
        "episode_id": job["source"]["episode_id"],
        "order": job["segment"]["index"],
        "media": "video",
        "job_path": store.relative(item["path"]),
        "job_sha256": item["canonical_sha256"],
        "provider": target["provider"],
        "entrypoint": target["entrypoint"],
        "model": target["model_id"],
        "languages": job["languages"],
        "asset_bindings": job["asset_bindings"],
        "segment": job["segment"],
        "shots": job["shots"],
        "duration": job["segment"]["duration_seconds"],
        "story_locked": True,
        "may_rewrite_story": False,
    }


def validate_locked_queue(store: ProjectStore, queue: dict[str, Any]) -> list[dict[str, Any]]:
    """Prove ordering, dependencies, paths, hashes, and payloads still match the bundle."""

    if queue.get("execution_mode") != EXECUTION_MODE:
        raise ValueError("real generation requires a locked_media_jobs queue")
    bundle = load_canonical_bundle(store)
    manifests = canonical_manifest_records(store)
    if queue.get("manifests") != manifests:
        raise ValueError("canonical media-job manifest set changed after queue compilation; recompile")
    tasks = queue.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(bundle):
        raise ValueError("locked queue must contain exactly one task per manifest job")
    previous_id: str | None = None
    for position, (task, item) in enumerate(zip(tasks, bundle), start=1):
        if not isinstance(task, dict):
            raise ValueError(f"queue.tasks[{position - 1}] must be an object")
        job = item["job"]
        task_id = f"locked_{job['job_id']}"
        expected_fields = {
            "id": task_id,
            "job_id": job["job_id"],
            "job_path": store.relative(item["path"]),
            "job_sha256": item["canonical_sha256"],
            "kind": "locked_media_job",
            "priority": 100 + position,
            "depends_on": [previous_id] if previous_id else [],
            "max_attempts": int(job["retry_policy"]["max_attempts"]),
            "expected_path": job["outputs"]["video_path"],
            "accepted_extensions": [".mp4", ".mov", ".mkv", ".webm"],
            "qc_required": True,
            "payload": task_payload_from_job(store, item),
        }
        required_task_keys = set(expected_fields) | {"status", "attempts", "result"}
        optional_task_keys = {"started_at", "last_error"}
        missing_task_keys = required_task_keys - set(task)
        extra_task_keys = set(task) - required_task_keys - optional_task_keys
        if missing_task_keys or extra_task_keys:
            raise ValueError(
                f"queue task {task_id} has invalid keys; "
                f"missing={sorted(missing_task_keys)}, extra={sorted(extra_task_keys)}"
            )
        for key, expected in expected_fields.items():
            if task.get(key) != expected:
                raise ValueError(f"queue task {task_id} drifted from canonical field {key}")
        if task.get("status") not in {"pending", "running", "complete", "blocked"}:
            raise ValueError(f"queue task {task_id} has an invalid status")
        attempts = task.get("attempts")
        if (
            not isinstance(attempts, int)
            or isinstance(attempts, bool)
            or attempts < 0
            or attempts > int(job["retry_policy"]["max_attempts"])
        ):
            raise ValueError(f"queue task {task_id} has invalid attempts")
        if task.get("status") == "complete":
            verify_completed_locked_task(store, task)
        elif task.get("result") is not None:
            raise ValueError(f"incomplete queue task {task_id} cannot carry a result")
        previous_id = task_id
    source_ids = list(
        dict.fromkeys(item["job"]["source"]["source_id"] for item in bundle)
    )
    if queue.get("source_ids") != source_ids:
        raise ValueError("queue source_ids drifted from canonical manifests")
    if queue.get("story_locked") is not True or queue.get("may_rewrite_story") is not False:
        raise ValueError("queue story lock is invalid")
    return bundle


def load_task_job(store: ProjectStore, task: dict[str, Any]) -> dict[str, Any]:
    """Revalidate the bundle and prove a queue task is an exact job snapshot."""

    if task.get("kind") != "locked_media_job":
        raise ValueError("task is not a canonical locked_media_job")
    payload = task.get("payload")
    if not isinstance(payload, dict) or "prompt" in payload:
        raise ValueError("locked_media_job payload is invalid or contains a rewritten prompt")
    rows = load_canonical_bundle(store)
    matches = [row for row in rows if row["job"].get("job_id") == task.get("job_id")]
    if len(matches) != 1:
        raise ValueError(f"queue task does not identify exactly one manifest job: {task.get('job_id')!r}")
    item = matches[0]
    expected_payload = task_payload_from_job(store, item)
    if payload != expected_payload:
        raise ValueError(f"queue task payload drifted from canonical job: {task.get('id')}")
    if task.get("job_sha256") != item["canonical_sha256"]:
        raise ValueError(f"queue task hash drifted from canonical job: {task.get('id')}")
    if task.get("job_path") != expected_payload["job_path"]:
        raise ValueError(f"queue task path drifted from canonical job: {task.get('id')}")
    return item["job"]


def lint_bound_receipt(
    job: dict[str, Any],
    receipt: dict[str, Any],
    *,
    artifact_root: str | Path | None = None,
) -> None:
    report = _contract_module().lint_receipt(
        receipt,
        job,
        artifact_root=artifact_root,
    )
    if report.errors:
        raise ValueError(f"media receipt failed canonical contract: {_contract_errors(report)}")
    if receipt.get("status") != "succeeded":
        raise ValueError("only a succeeded canonical receipt can complete a locked media task")


def verify_completed_locked_task(store: ProjectStore, task: dict[str, Any]) -> dict[str, Any]:
    """Recheck immutable evidence before the editor consumes a completed segment."""

    job = load_task_job(store, task)
    result = task.get("result")
    if task.get("status") != "complete" or not isinstance(result, dict):
        raise RuntimeError(f"locked media segment is incomplete: {task.get('id')}")
    video = Path(str(result.get("file", ""))).resolve()
    receipt_path = Path(str(result.get("receipt_file", ""))).resolve()
    prompt_path = Path(str(result.get("prompt_file", ""))).resolve()
    for path, label in ((video, "video"), (receipt_path, "receipt"), (prompt_path, "prompt")):
        if not path.is_file() or not is_within(path, store.root):
            raise RuntimeError(f"completed {label} evidence is missing or outside the project: {path}")
    if sha256_file(video) != result.get("video_sha256"):
        raise RuntimeError(f"completed video evidence changed after receipt: {video}")
    if sha256_file(receipt_path) != result.get("receipt_sha256"):
        raise RuntimeError(f"completed receipt evidence changed after persistence: {receipt_path}")
    if sha256_file(prompt_path) != result.get("prompt_sha256"):
        raise RuntimeError(f"completed prompt evidence changed after persistence: {prompt_path}")
    receipt = _read_json(receipt_path, "persisted media receipt")
    lint_bound_receipt(job, receipt, artifact_root=store.root)
    video_output = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "video"),
        None,
    )
    if not isinstance(video_output, dict) or video_output.get("sha256") != sha256_file(video):
        raise RuntimeError("persisted receipt video hash no longer matches the completed segment")
    if prompt_path.read_text(encoding="utf-8") != receipt.get("prompt"):
        raise RuntimeError("persisted prompt evidence no longer matches the canonical receipt")
    return job
