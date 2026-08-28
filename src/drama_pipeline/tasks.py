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


def _entity_map(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for key in ("characters", "locations", "props")
        for item in pack.get(key, [])
        if isinstance(item, dict) and item.get("id")
    }


def _anchor_task(entity: dict[str, Any], kind: str, config: dict[str, Any]) -> dict[str, Any]:
    entity_id = entity["id"]
    description = entity.get("visual_anchor", "")
    if kind == "character":
        prompt = (
            f"Character identity sheet for {entity.get('name', entity_id)}. "
            f"Locked identity: {description}. Public identity: {entity.get('public_identity', '')}. "
            f"Performance signature: {entity.get('performance_anchor', '')}. "
            "Front, three-quarter, profile and full-body views; identical face, age, hair, body ratio, "
            "wardrobe and signature accessories; neutral studio background; no labels, logo or watermark."
        )
    else:
        prompt = (
            f"Locked {kind} reference sheet for {entity.get('name', entity_id)}. "
            f"Preserve exactly: {description}. Clear spatial/material reference, consistent lighting, "
            "no people unless specified, no labels, logo or watermark."
        )
    return {
        "id": f"anchor_{entity_id}",
        "kind": f"{kind}_anchor",
        "status": "pending",
        "priority": 10 if kind == "character" else 20,
        "depends_on": [],
        "attempts": 0,
        "max_attempts": int(config["max_retries"]) + 1,
        "expected_path": f"assets/anchors/{entity_id}.png",
        "accepted_extensions": [".png", ".jpg", ".jpeg", ".webp"],
        "qc_required": True,
        "payload": {
            "entity_id": entity_id,
            "media": "image",
            "aspect": "3:4" if kind == "character" else config["aspect"],
            "provider": config["provider"],
            "model": config["model"],
            "prompt": prompt,
            "reference_roles": [],
        },
        "result": None,
    }


def _dialogue_text(
    shot: dict[str, Any],
    entities: dict[str, dict[str, Any]],
    spoken_dialogue_language: str,
) -> str:
    rows = []
    for line in shot.get("dialogue", []):
        if not isinstance(line, dict):
            continue
        speaker = entities.get(line.get("speaker_id"), {}).get("name", line.get("speaker_id", ""))
        rows.append(
            f'{speaker} says exactly "{line.get("text", "")}" in {spoken_dialogue_language}; '
            f'mode: {line.get("delivery", "on_screen")}; performance: {line.get("performance", "natural restrained")}'
        )
    return "\n".join(rows) or "No dialogue; no lip speech."


def _reference_lines(entity_ids: list[str], entities: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    dependencies, lines = [], []
    for entity_id in entity_ids:
        if entity_id not in entities:
            continue
        dependencies.append(f"anchor_{entity_id}")
        entity = entities[entity_id]
        asset_name = entity.get("platform_asset_name", entity.get("name", entity_id))
        lines.append(
            f"@{asset_name} = {entity_id} identity/geometry only; preserve {entity.get('visual_anchor', '')}"
        )
    return dependencies, lines


def _shot_prompt(
    config: dict[str, Any],
    scene: dict[str, Any],
    shot: dict[str, Any],
    entities: dict[str, dict[str, Any]],
    languages: dict[str, str],
) -> tuple[str, list[str]]:
    entity_ids = list(dict.fromkeys([*scene.get("characters", []), *shot.get("entities", [])]))
    dependencies, references = _reference_lines(entity_ids, entities)
    duration = float(shot["duration_target"])
    dialogue = _dialogue_text(shot, entities, languages.get("spoken_dialogue", "unspecified"))
    prompt = f"""[MODEL GATE]
Provider: {config['provider']}
Model: use the exact visible Seedance model ID; do not assume unsupported 2.5 capabilities.
Duration / aspect: {duration:g}s / {config['aspect']}

[FORMAT]
{config['format']}, vertical {config['aspect']}, one generated shot, no unrequested transition.
Prompt language: {languages.get('prompt', 'unspecified')}.
Direction language: {languages.get('direction', 'unspecified')}.
Spoken dialogue: {languages.get('spoken_dialogue', 'unspecified')} only.
Voice: {languages.get('voice', 'unspecified')}. Subtitle target: {languages.get('subtitle', 'unspecified')}.

[REFERENCE MAP]
{chr(10).join(references) if references else 'No external identity reference.'}
Conflict precedence: identity > continuity locks > event > camera/style.

[LOCKS]
Scene state before: {scene['state_before']}
Continuity: {shot['continuity']}
Preserve all referenced identities, wardrobe, props and location topology.

[CAMERA / LOOK]
Frame intent: {shot['frame_intent']}
Camera: {shot['camera']}

[TIMELINE]
00:00–00:{duration:04.1f} — Main event: {shot['observable_action']}
Required end state: {shot['end_state']}

[AUDIO LEDGER]
{shot['audio']}
{dialogue}
Natural precise lip synchronization only for the named speaker.

[ACCEPTANCE CONTRACT]
Preserve: identity, wardrobe, spatial layout, prop ownership and event order.
Allow change only in the named action, camera move and described environmental response.
Exclude: {shot['negative']}; duplicate subject, face drift, extra limbs, unreadable text, logo, watermark, subtitles, scene reset.

[ENDING]
Reach and hold this state for the final 0.5s: {shot['end_state']}. No fade or generated outro.
"""
    return prompt, dependencies


def _shot_task(
    config: dict[str, Any],
    episode: dict[str, Any],
    scene: dict[str, Any],
    shot: dict[str, Any],
    entities: dict[str, dict[str, Any]],
    languages: dict[str, str],
    order: int,
) -> dict[str, Any]:
    prompt, dependencies = _shot_prompt(config, scene, shot, entities, languages)
    return {
        "id": f"video_{shot['id']}",
        "kind": "shot_video",
        "status": "pending",
        "priority": 100 + order,
        "depends_on": dependencies,
        "attempts": 0,
        "max_attempts": int(config["max_retries"]) + 1,
        "expected_path": f"assets/shots/{shot['id']}.mp4",
        "accepted_extensions": [".mp4", ".mov", ".mkv", ".webm"],
        "qc_required": True,
        "payload": {
            "episode_id": episode["id"],
            "scene_id": scene["id"],
            "shot_id": shot["id"],
            "order": order,
            "media": "video",
            "duration": shot["duration_target"],
            "aspect": config["aspect"],
            "provider": config["provider"],
            "model": config["model"],
            "story_locked": True,
            "may_rewrite_story": False,
            "languages": languages,
            "prompt": prompt,
            "dialogue": shot.get("dialogue", []),
            "end_state": shot["end_state"],
            "reference_task_ids": dependencies,
        },
        "result": None,
    }


def _compile_mock_queue(store: ProjectStore) -> dict[str, Any]:
    config, pack = store.config(), store.pack()
    store.set_stage("compile", "running", "compiling generation queue")
    entities = _entity_map(pack)
    languages = pack.get("languages", {})
    tasks = []
    for key, kind in (("characters", "character"), ("locations", "location"), ("props", "prop")):
        tasks.extend(_anchor_task(item, kind, config) for item in pack.get(key, []))

    order = 0
    for episode in pack.get("episodes", []):
        for scene in episode.get("scenes", []):
            for shot in scene.get("shots", []):
                order += 1
                tasks.append(_shot_task(config, episode, scene, shot, entities, languages, order))

    references = [Path(item) for item in config.get("references", []) if Path(item).is_file()]
    character_tasks = [item for item in tasks if item["kind"] == "character_anchor"]
    for source, task in zip(references, character_tasks):
        task["status"] = "complete"
        task["result"] = {
            "file": str(source.resolve()),
            "source": "user_reference",
            "qc_passed": True,
            "completed_at": utc_now(),
        }

    queue = {
        "schema_version": 1,
        "project_id": config["project_id"],
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "execution_mode": "mock_legacy",
        "story_locked": True,
        "may_rewrite_story": False,
        "tasks": sorted(tasks, key=lambda item: (item["priority"], item["id"])),
    }
    store.save_queue(queue)
    store.set_stage("compile", "complete", f"{len(tasks)} tasks")
    store.set_stage("generate", "ready", "queue ready")
    return queue


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


def _preflight_artifact(path: Path, source_hash: str) -> None:
    if path.exists() and (not path.is_file() or sha256_file(path) != source_hash):
        raise ValueError(f"refusing to overwrite different canonical artifact: {path}")


def _copy_artifact_once(source: Path, destination: Path, expected_hash: str) -> None:
    if source == destination:
        if sha256_file(source) != expected_hash:
            raise ValueError(f"canonical artifact changed during persistence: {source}")
        return
    if destination.exists():
        if not destination.is_file() or sha256_file(destination) != expected_hash:
            raise ValueError(f"refusing late overwrite of different canonical artifact: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, raw = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(raw)
    try:
        shutil.copy2(source, temporary)
        if sha256_file(temporary) != expected_hash:
            raise ValueError(f"canonical artifact changed during persistence: {source}")
        try:
            # Atomic no-clobber publish. Unlike os.replace(), a concurrently
            # created user file can never be overwritten.
            os.link(temporary, destination)
        except FileExistsError:
            if not destination.is_file() or sha256_file(destination) != expected_hash:
                raise ValueError(
                    f"refusing late overwrite of different canonical artifact: {destination}"
                )
    finally:
        if temporary.exists():
            temporary.unlink()


def _complete_locked_task(
    store: ProjectStore,
    queue: dict[str, Any],
    task: dict[str, Any],
    source: Path,
    probe: dict[str, Any],
    receipt_path: Path | None,
    artifact_root: Path | None,
    *,
    qc_passed: bool,
    note: str,
    cost: float | None,
) -> dict[str, Any]:
    if receipt_path is None:
        raise ValueError("real locked_media_job completion requires --receipt")
    if artifact_root is None:
        raise ValueError("real locked_media_job completion requires --artifact-root")
    if not qc_passed:
        raise ValueError("Visual/audio QC must pass before completing a real generation task")
    job = load_task_job(store, task)
    receipt_source = receipt_path.expanduser().resolve()
    if not receipt_source.is_file():
        raise FileNotFoundError(f"media receipt is missing: {receipt_source}")
    receipt_bytes = receipt_source.read_bytes()
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"media receipt is not valid UTF-8 JSON: {receipt_source}: {exc}") from exc
    if not isinstance(receipt, dict):
        raise ValueError("media receipt must be a JSON object")
    submitted_root = artifact_root.expanduser().resolve()
    if not submitted_root.is_dir():
        raise FileNotFoundError(f"artifact_root is missing or not a directory: {submitted_root}")
    lint_bound_receipt(job, receipt, artifact_root=submitted_root)

    actual_video_hash = sha256_file(source)
    video_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "video"),
        None,
    )
    if not isinstance(video_artifact, dict) or video_artifact.get("sha256") != actual_video_hash:
        raise ValueError("receipt video SHA-256 does not match the actual submitted source file")
    receipt_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "receipt"),
        None,
    )
    prompt_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "prompt"),
        None,
    )
    if not isinstance(receipt_artifact, dict) or not isinstance(prompt_artifact, dict):
        raise ValueError("succeeded canonical receipt requires receipt and prompt output metadata")

    source_artifacts: dict[str, tuple[dict[str, Any], Path]] = {}
    seen_uris: set[str] = set()
    for artifact in receipt.get("outputs", []):
        uri = str(artifact["uri"])
        if uri in seen_uris:
            raise ValueError(f"receipt output URIs must be unique: {uri}")
        seen_uris.add(uri)
        artifact_source = (submitted_root / uri).resolve()
        try:
            artifact_source.relative_to(submitted_root)
        except ValueError as exc:
            raise ValueError(f"receipt artifact escapes artifact_root: {uri}") from exc
        source_artifacts[artifact["kind"]] = (artifact, artifact_source)

    if source != source_artifacts["video"][1]:
        raise ValueError("submitted video must be the exact video artifact under --artifact-root")
    if receipt_source != source_artifacts["receipt"][1]:
        raise ValueError("--receipt must be the exact receipt artifact under --artifact-root")
    locked_duration = float(job["segment"]["duration_seconds"])
    actual_duration = float(probe.get("duration") or 0)
    if abs(actual_duration - locked_duration) > max(0.5, locked_duration * 0.04):
        raise ValueError(
            f"actual video duration {actual_duration:g}s does not match locked segment "
            f"duration {locked_duration:g}s"
        )

    persisted: dict[str, Path] = {
        kind: store.artifact(str(artifact["uri"]))
        for kind, (artifact, _source_path) in source_artifacts.items()
    }
    if len(set(persisted.values())) != len(persisted):
        raise ValueError("canonical receipt artifacts must use distinct project paths")
    artifact_records: list[dict[str, Any]] = []
    # Validate every destination before making any mutation, then copy all evidence.
    for kind, (artifact, artifact_source) in source_artifacts.items():
        digest = sha256_file(artifact_source)
        _preflight_artifact(persisted[kind], digest)
        artifact_records.append(
            {"kind": kind, "uri": artifact["uri"], "sha256": digest}
        )
    artifact_hashes = {item["kind"]: item["sha256"] for item in artifact_records}
    for kind, (_artifact, artifact_source) in source_artifacts.items():
        _copy_artifact_once(artifact_source, persisted[kind], artifact_hashes[kind])

    destination = persisted["video"]
    persisted_receipt = persisted["receipt"]
    persisted_prompt = persisted["prompt"]
    if sha256_file(destination) != actual_video_hash:
        raise RuntimeError("persisted video hash changed during copy")
    if persisted_receipt.read_bytes() != receipt_bytes:
        raise RuntimeError("persisted receipt bytes changed during copy")
    # This second pass binds the immutable receipt to the actual project artifacts
    # that the editor will consume, not merely the submitted/download directory.
    lint_bound_receipt(job, receipt, artifact_root=store.root)

    task["expected_path"] = store.relative(destination)
    task["status"] = "complete"
    task["result"] = {
        "file": str(destination),
        "video_sha256": actual_video_hash,
        "provider": receipt["provider"],
        "model_id": receipt["model_id"],
        "qc_passed": True,
        "mock": False,
        "note": note,
        "cost": cost,
        "probe": probe,
        "job_path": task["job_path"],
        "job_sha256": task["job_sha256"],
        "receipt_id": receipt["receipt_id"],
        "receipt_file": str(persisted_receipt),
        "receipt_sha256": sha256_file(persisted_receipt),
        "prompt_file": str(persisted_prompt),
        "prompt_sha256": sha256_file(persisted_prompt),
        "canonical_video_uri": video_artifact["uri"],
        "submitted_artifact_root": str(submitted_root),
        "verified_artifact_root": str(store.root),
        "artifacts": artifact_records,
        "language_verification": receipt["language_verification"],
        "completed_at": utc_now(),
    }
    store.save_queue(queue)
    store.log("locked_media_job_completed", {"task_id": task["id"], "result": task["result"]})
    return task


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
