"""
capcut_helpers.effects — Apply / swap CapCut 花字 effects on caption segments.

Pattern generalized from one-off bulk-restyle scripts written for a past travel vlog:
- Effect material lives in `materials.effects[]`
- Caption segment links to it via `extra_material_refs[]`
- DAY 1 pattern: refs = [anim1, effect_id, anim2, effect_id]
"""
import copy
import json
import os
import uuid as uuid_mod
from typing import Optional

from .paths import EFFECT_CACHE


def find_effect_material(draft: dict, effect_id: str) -> Optional[dict]:
    """Find a materials.effects entry by effect_id (CapCut's internal ID)."""
    effects = draft.get("materials", {}).get("effects", [])
    for e in effects:
        if e.get("effect_id") == effect_id:
            return e
    return None


def get_effect_cache_path(effect_id: str) -> Optional[str]:
    """Resolve disk cache path for a CapCut effect (subdir name varies)."""
    cache_dir = EFFECT_CACHE / effect_id
    if not cache_dir.exists():
        return None
    subs = [s for s in os.listdir(cache_dir) if (cache_dir / s).is_dir()]
    if not subs:
        return None
    return str(cache_dir / subs[0]).replace("\\", "/")


def apply_effect_to_all_captions(draft: dict, template_effect: dict,
                                 skip_texts: set[str] = None) -> int:
    """Replicate a template effect material to all caption segments.

    Args:
        draft: full draft JSON dict
        template_effect: existing materials.effects entry to copy (must have effect_id + path)
        skip_texts: set of caption strings to skip (e.g. {"<a title card you already styled>"})

    Returns: number of captions patched
    """
    skip_texts = skip_texts or set()
    texts = draft.get("materials", {}).get("texts", [])
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]

    # Find a reference segment to copy refs pattern from (use the one already using template_effect)
    template_id = template_effect["id"]
    reference_refs = None
    for tr in text_tracks:
        for seg in tr.get("segments", []):
            refs = seg.get("extra_material_refs", [])
            if template_id in refs:
                reference_refs = list(refs)
                break
        if reference_refs:
            break

    if not reference_refs:
        raise ValueError("No caption segment uses the template_effect — can't infer refs pattern")

    n_processed = 0
    for tr in text_tracks:
        for seg in tr.get("segments", []):
            mat = next((t for t in texts if t["id"] == seg.get("material_id")), None)
            if not mat:
                continue
            co = json.loads(mat.get("content", "{}"))
            text = co.get("text", "")
            if not text or text in skip_texts:
                continue
            # Skip if already has the template effect
            if template_id in seg.get("extra_material_refs", []):
                continue

            # Clone the template effect material with a new UUID
            new_effect = copy.deepcopy(template_effect)
            new_effect["id"] = str(uuid_mod.uuid4()).upper()
            draft["materials"]["effects"].append(new_effect)

            # Replicate refs pattern: replace template_id positions with new_effect["id"]
            new_refs = [new_effect["id"] if r == template_id else r for r in reference_refs]
            seg["extra_material_refs"] = new_refs
            n_processed += 1

    return n_processed


def swap_effect(draft: dict, old_effect_id: str, new_effect_id: str,
                new_effect_name: str = None) -> int:
    """Swap all materials.effects entries with old_effect_id → new_effect_id.

    Used for bulk style change (e.g. bubble → ART 花字).
    """
    new_cache_path = get_effect_cache_path(new_effect_id)
    if not new_cache_path:
        raise ValueError(f"Effect cache not found for {new_effect_id} at {EFFECT_CACHE / new_effect_id}")

    n = 0
    for e in draft.get("materials", {}).get("effects", []):
        if e.get("effect_id") == old_effect_id:
            e["effect_id"] = new_effect_id
            e["resource_id"] = new_effect_id
            e["path"] = new_cache_path
            if new_effect_name:
                e["name"] = new_effect_name
            n += 1
    return n


def apply_effect_to_segment(draft: dict, segment_idx: int, effect_id: str,
                            track_type: str = "text",
                            effect_name: str = None) -> dict:
    """M47 fix — proper effect application that:
    (1) Creates materials.effects entry with full schema
    (2) Adds entry id to segment.extra_material_refs
    (3) Verifies effect_cache path exists

    M47 lesson: 之前 build script 只加 effect material 但 effect_id field 沒 properly link
    OR segment refs 沒指到對的 material id → CapCut 開啟時看不到花字效果。

    Args:
        draft: full draft dict
        segment_idx: 0-indexed segment in the first track of track_type
        effect_id: CapCut internal effect ID (e.g. '7580172785490611461')
        track_type: 'text' / 'video'
        effect_name: optional display name (defaults to lookup)

    Returns: the newly created effect material entry
    Raises: ValueError if effect cache not found / segment idx out of range
    """
    import uuid as uuid_mod

    cache_path = get_effect_cache_path(effect_id)
    if not cache_path:
        raise ValueError(f"Effect {effect_id} cache not found at {EFFECT_CACHE / effect_id}")

    tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == track_type]
    if not tracks:
        raise ValueError(f"No {track_type} tracks found")
    segments = tracks[0].get("segments", [])
    if segment_idx >= len(segments):
        raise ValueError(f"Segment idx {segment_idx} out of range (have {len(segments)} segs)")
    seg = segments[segment_idx]

    # Build effect material entry — schema MUST include category_name='panel-text-flower'
    # for 花字 effects so CapCut treats them correctly
    new_eff = {
        "id": str(uuid_mod.uuid4()).upper(),
        "effect_id": effect_id,
        "resource_id": effect_id,
        "third_resource_id": effect_id,
        "name": effect_name or f"effect_{effect_id[:8]}",
        "report_name": effect_name or "",
        "type": "text_effect",
        "sub_type": "",
        "path": cache_path,
        "value": 1.0,
        "visible": True,
        "item_effect_type": 0,
        "category_id": "panel-text-flower",
        "category_name": "panel-text-flower",
        "category_key": "text-flower",
        "platform": "all",
        "request_id": "",
        "source_platform": 0,
        "is_local": False,
        "covers": [],
        "version": "",
        "apply_target_type": 0,
        "formula_id": "",
    }
    draft.setdefault("materials", {}).setdefault("effects", []).append(new_eff)

    # Link to segment
    refs = seg.setdefault("extra_material_refs", [])
    refs.append(new_eff["id"])

    return new_eff


def count_effects_by_id(draft: dict) -> dict[str, int]:
    """Tally how many materials.effects entries point at each effect_id."""
    from collections import Counter
    effects = draft.get("materials", {}).get("effects", [])
    return dict(Counter(e.get("effect_id", "?") for e in effects))
