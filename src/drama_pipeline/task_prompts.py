"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from .store import ProjectStore, utc_now


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
