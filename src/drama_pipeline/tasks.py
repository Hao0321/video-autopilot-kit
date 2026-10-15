"""Generation queue compilation, retries, and deterministic mock execution."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .media_contract_bridge import (
    EXECUTION_MODE,
    canonical_manifest_records,
    lint_bound_receipt,
    load_canonical_bundle,
    load_task_job,
    task_payload_from_job,
    validate_locked_queue,
)
from .store import ProjectStore, sha256_file, utc_now


if __package__:
    from .task_prompts import (
        _entity_map,
        _anchor_task,
        _dialogue_text,
        _reference_lines,
        _shot_prompt,
        _shot_task,
        _compile_mock_queue,
    )
else:
    from task_prompts import (
        _entity_map,
        _anchor_task,
        _dialogue_text,
        _reference_lines,
        _shot_prompt,
        _shot_task,
        _compile_mock_queue,
    )


def _compile_locked_queue(store: ProjectStore) -> dict[str, Any]:
    config = store.config()
    store.set_stage("compile", "running", "validating canonical Media Job bundle")
    try:
        bundle = load_canonical_bundle(store)
    except Exception as exc:
        store.set_stage("compile", "failed", str(exc))
        raise
    tasks: list[dict[str, Any]] = []
    previous_task_id: str | None = None
    for item in bundle:
        job = item["job"]
        job_id = job["job_id"]
        task_id = f"locked_{job_id}"
        task = {
            "id": task_id,
            "job_id": job_id,
            "job_path": store.relative(item["path"]),
            "job_sha256": item["canonical_sha256"],
            "kind": "locked_media_job",
            "status": "pending",
            "priority": 101 + len(tasks),
            "depends_on": [previous_task_id] if previous_task_id else [],
            "attempts": 0,
            "max_attempts": int(job["retry_policy"]["max_attempts"]),
            "expected_path": job["outputs"]["video_path"],
            "accepted_extensions": [".mp4", ".mov", ".mkv", ".webm"],
            "qc_required": True,
            "payload": task_payload_from_job(store, item),
            "result": None,
        }
        tasks.append(task)
        previous_task_id = task_id

    manifests = canonical_manifest_records(store)
    source_ids = list(
        dict.fromkeys(item["job"]["source"]["source_id"] for item in bundle)
    )
    queue = {
        "schema_version": 1,
        "project_id": config["project_id"],
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "execution_mode": EXECUTION_MODE,
        "manifests": manifests,
        "source_ids": source_ids,
        "story_locked": True,
        "may_rewrite_story": False,
        "tasks": tasks,
    }
    store.save_queue(queue)
    store.set_stage("compile", "complete", f"{len(tasks)} locked Media Job segment(s)")
    store.set_stage("generate", "ready", "canonical Media Job queue ready")
    return queue


def compile_queue(store: ProjectStore) -> dict[str, Any]:
    """Compile mock fixtures or the project-local canonical Media Job bundle."""

    if store.config().get("provider") == "mock":
        return _compile_mock_queue(store)
    return _compile_locked_queue(store)


def _task_index(queue: dict[str, Any], task_id: str) -> tuple[int, dict[str, Any]]:
    for index, task in enumerate(queue.get("tasks", [])):
        if task.get("id") == task_id:
            return index, task
    raise KeyError(f"Unknown task: {task_id}")


def ready_tasks(queue: dict[str, Any]) -> list[dict[str, Any]]:
    completed = {item["id"] for item in queue.get("tasks", []) if item.get("status") == "complete"}
    return [
        item
        for item in queue.get("tasks", [])
        if item.get("status") == "pending" and set(item.get("depends_on", [])) <= completed
    ]


def next_task(store: ProjectStore) -> dict[str, Any] | None:
    queue = store.queue()
    if store.config().get("provider") != "mock" and queue.get("execution_mode") != EXECUTION_MODE:
        raise RuntimeError(
            "real short-drama generation refuses legacy/free-text queues; "
            "compile the project media-jobs/manifest.json bundle"
        )
    if queue.get("execution_mode") == EXECUTION_MODE:
        validate_locked_queue(store, queue)
    rows = ready_tasks(queue)
    task = rows[0] if rows else None
    if task and task.get("kind") == "locked_media_job":
        load_task_job(store, task)
    return task


def claim_task(store: ProjectStore, task_id: str) -> dict[str, Any]:
    queue = store.queue()
    if store.config().get("provider") != "mock":
        validate_locked_queue(store, queue)
    _index, task = _task_index(queue, task_id)
    if task["status"] not in {"pending", "running"}:
        raise ValueError(f"Task {task_id} cannot be claimed from {task['status']}")
    if task.get("kind") == "locked_media_job":
        load_task_job(store, task)
    elif store.config().get("provider") != "mock":
        raise ValueError("legacy generation tasks are mock-only")
    task["status"] = "running"
    task["started_at"] = utc_now()
    store.save_queue(queue)
    store.log("task_claimed", {"task_id": task_id})
    return task


def _probe_video(path: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise FileNotFoundError("ffprobe is required")
    command = [
        executable,
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,width,height",
        "-of", "json",
        str(path),
    ]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if run.returncode:
        raise ValueError(f"ffprobe failed for {path}: {run.stderr.strip()}")
    data = json.loads(run.stdout)
    duration = float(data.get("format", {}).get("duration") or 0)
    videos = [row for row in data.get("streams", []) if row.get("codec_type") == "video"]
    if not videos or duration <= 0.2:
        raise ValueError(f"Invalid or empty video: {path}")
    return {"duration": duration, "width": videos[0].get("width"), "height": videos[0].get("height")}


def _validate_output(task: dict[str, Any], source: Path) -> dict[str, Any]:
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError(f"Output file is missing or empty: {source}")
    suffix = source.suffix.lower()
    if suffix not in task["accepted_extensions"]:
        raise ValueError(f"Unsupported output extension for {task['id']}: {suffix}")
    if task["kind"] in {"shot_video", "locked_media_job"}:
        return _probe_video(source)
    try:
        with Image.open(source) as image:
            image.verify()
        return {"image_verified": True}
    except Exception as exc:
        raise ValueError(f"Invalid image {source}: {exc}") from exc


if __package__:
    from .task_artifacts import (
        _preflight_artifact,
        _copy_artifact_once,
        _complete_locked_task,
    )
else:
    from task_artifacts import (
        _preflight_artifact,
        _copy_artifact_once,
        _complete_locked_task,
    )


def complete_task(
    store: ProjectStore,
    task_id: str,
    source: Path,
    *,
    qc_passed: bool,
    receipt_path: Path | None = None,
    artifact_root: Path | None = None,
    provider: str = "browser",
    note: str = "",
    cost: float | None = None,
    mock: bool = False,
) -> dict[str, Any]:
    queue = store.queue()
    if store.config().get("provider") != "mock":
        validate_locked_queue(store, queue)
    _index, task = _task_index(queue, task_id)
    if task["status"] not in {"pending", "running"}:
        raise ValueError(f"Task {task_id} cannot complete from {task['status']}")
    completed_ids = {
        item.get("id") for item in queue.get("tasks", []) if item.get("status") == "complete"
    }
    missing_dependencies = set(task.get("depends_on", [])) - completed_ids
    if missing_dependencies:
        raise ValueError(
            f"Task {task_id} has incomplete dependencies: {sorted(missing_dependencies)}"
        )
    source = source.expanduser().resolve()
    probe = _validate_output(task, source)
    if task.get("kind") == "locked_media_job":
        if mock:
            raise ValueError("canonical locked_media_job tasks cannot use the mock completion path")
        return _complete_locked_task(
            store,
            queue,
            task,
            source,
            probe,
            receipt_path,
            artifact_root,
            qc_passed=qc_passed,
            note=note,
            cost=cost,
        )
    if not mock:
        raise ValueError("legacy anchor/shot tasks are mock-only; real runs require locked_media_job")

    preferred = store.artifact(task["expected_path"])
    destination = preferred.with_suffix(source.suffix.lower())
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source != destination:
        shutil.copy2(source, destination)
    task["expected_path"] = store.relative(destination)
    task["status"] = "complete"
    task["result"] = {
        "file": str(destination),
        "provider": provider,
        "qc_passed": bool(qc_passed or mock),
        "mock": mock,
        "note": note,
        "cost": cost,
        "probe": probe,
        "completed_at": utc_now(),
    }
    store.save_queue(queue)
    store.log("task_completed", {"task_id": task_id, "result": task["result"]})
    return task


def fail_task(store: ProjectStore, task_id: str, reason: str) -> dict[str, Any]:
    queue = store.queue()
    if store.config().get("provider") != "mock":
        validate_locked_queue(store, queue)
    _index, task = _task_index(queue, task_id)
    if task["status"] == "complete":
        raise ValueError(f"Completed task cannot be failed: {task_id}")
    task["attempts"] = int(task.get("attempts", 0)) + 1
    task["last_error"] = reason
    task["status"] = "pending" if task["attempts"] < task["max_attempts"] else "blocked"
    store.save_queue(queue)
    store.log(
        "task_failed",
        {"task_id": task_id, "reason": reason, "status": task["status"], "attempts": task["attempts"]},
    )
    if task["status"] == "blocked":
        store.set_stage("generate", "failed", f"task blocked: {task_id}: {reason}")
    return task


def _resolution(config: dict[str, Any]) -> tuple[int, int]:
    raw = str(config.get("resolution", "1080x1920")).lower().split("x")
    return int(raw[0]), int(raw[1])


def _mock_image(path: Path, label: str, size: tuple[int, int]) -> None:
    width, height = size
    image = Image.new("RGB", (width, height), (30, 42, 58))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, width - 20, height - 20), outline=(233, 190, 80), width=4)
    draw.text((40, max(40, height // 2 - 10)), label[:48], fill=(245, 245, 245))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _mock_video(path: Path, label: str, duration: float, size: tuple[int, int], work_dir: Path) -> None:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise FileNotFoundError("ffmpeg is required")
    frame = work_dir / f"{path.stem}_mock.png"
    _mock_image(frame, label, size)
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable, "-y", "-loop", "1", "-i", str(frame),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", f"{duration:.3f}", "-r", "30",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if run.returncode:
        raise RuntimeError(f"mock ffmpeg failed: {run.stderr[-1000:]}")


def execute_mock_task(store: ProjectStore, task: dict[str, Any]) -> dict[str, Any]:
    claim_task(store, task["id"])
    config = store.config()
    width, height = _resolution(config)
    # Keep mock self-tests cheap while preserving the requested aspect.
    scale = min(1.0, 640 / max(width, height))
    size = (max(2, int(width * scale) // 2 * 2), max(2, int(height * scale) // 2 * 2))
    output = store.artifact(task["expected_path"])
    if task["kind"] == "shot_video":
        _mock_video(output, task["id"], float(task["payload"]["duration"]), size, store.work_dir)
    else:
        _mock_image(output, task["id"], size)
    return complete_task(store, task["id"], output, qc_passed=True, provider="mock", mock=True)


def drain_mock(store: ProjectStore) -> dict[str, int]:
    store.set_stage("generate", "running", "mock executor")
    while True:
        task = next_task(store)
        if task is None:
            break
        execute_mock_task(store, task)
    summary = queue_summary(store.queue())
    if summary.get("blocked") or summary.get("pending") or summary.get("running"):
        store.set_stage("generate", "failed", f"incomplete mock queue: {summary}")
    else:
        store.set_stage("generate", "complete", f"{summary.get('complete', 0)} tasks")
    return summary


def queue_summary(queue: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in queue.get("tasks", []):
        status = task.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def task_for_shot(queue: dict[str, Any], shot_id: str) -> dict[str, Any] | None:
    return next(
        (
            task
            for task in queue.get("tasks", [])
            if task.get("kind") == "shot_video" and task.get("payload", {}).get("shot_id") == shot_id
        ),
        None,
    )
