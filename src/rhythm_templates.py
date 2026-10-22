"""Frame-exact rhythm planning; no media rendering or application mutation.

CLI: python rhythm_templates.py plan --story story.json --catalog catalog.json --out plan.json
     python rhythm_templates.py check --plan plan.json --catalog catalog.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

SCHEMA = "editkin.rhythm-candidate/v1"
PROFILES = {
    "shorts.rhythm": {"format": "portrait", "width": 720, "height": 1280,
                      "pattern": [2, 3, 3, 3, 3, 4, 3, 3], "groupScenes": 12},
    "longform.rhythm": {"format": "landscape", "width": 1280, "height": 720,
                        "pattern": [3, 4, 4, 4], "groupScenes": 16},
}
ROLE_TAGS = {
    "hook": {"hook", "impact", "opening"}, "brand": {"title", "hook"},
    "concept": {"multi_line", "swap", "stack"},
    "emphasis": {"emphasis", "pulse", "pop"}, "chapter": {"chapter", "news", "headline"},
    "recap": {"multi_line", "swap"}, "texture": {"marquee", "repeat", "flow", "loop"},
}


class RhythmError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise RhythmError(code)


def digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rate(value):
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise RhythmError("INVALID_FPS") from None
    require(1 <= result <= 240, "INVALID_FPS")
    return result


def exact_frames(seconds, fps):
    frames = Fraction(str(seconds)) * fps
    require(frames.denominator == 1, "DURATION_NOT_FRAME_EXACT")
    return frames.numerator


def reading_seconds(lines):
    # Conservative screening, not a typography/taste certification.
    units = sum(sum(1 if ord(c) > 127 else 0.45 for c in line) for line in lines)
    return max(1.5, 0.8 + units / 6)


def partition(total, minimums, maximums, targets):
    """Bounded O(n) water-fill. Tail frames are distributed; never append filler."""
    require(len(minimums) == len(maximums) == len(targets) > 0, "EMPTY_STORY")
    require(sum(minimums) <= total <= sum(maximums), "INSUFFICIENT_CONTENT_OR_TIME")
    result = [min(high, max(low, target)) for low, high, target
              in zip(minimums, maximums, targets)]
    difference = total - sum(result)
    for i in range(len(result)):
        room = maximums[i] - result[i] if difference > 0 else result[i] - minimums[i]
        step = min(abs(difference), room)
        result[i] += step if difference > 0 else -step
        difference += -step if difference > 0 else step
        if difference == 0:
            break
    require(difference == 0, "PARTITION_FAILED")
    return result


def index_catalog(catalog):
    require(catalog.get("engineVersion") and isinstance(catalog.get("items"), list),
            "INVALID_CATALOG")
    return {item["id"]: item for item in catalog["items"]}


def frame_size(data, profile):
    width, height = data.get("width", profile["width"]), data.get("height", profile["height"])
    require(type(width) is int and type(height) is int and
            all(16 <= side <= 7680 and side % 2 == 0 for side in (width, height)), "INVALID_SIZE")
    require(width * profile["height"] == height * profile["width"], "WRONG_FORMAT_REFLOW")
    return width, height


def scene_count(total, fps, scenes, override=None):
    # 8–12 is the default brief, not a limit over a newer explicit creative request.
    if override is not None:
        require(isinstance(override, dict) and set(override) == {"count", "reason"},
                "INVALID_SCENE_COUNT_OVERRIDE")
        require(type(override["count"]) is int and 2 <= override["count"] <= 30
                and isinstance(override["reason"], str) and len(override["reason"].strip()) >= 8,
                "INVALID_SCENE_COUNT_OVERRIDE")
        require(len(scenes) == override["count"], "EXPLICIT_SCENE_COUNT_MISMATCH")
        return
    # Documented continuous proof/presenter holds retain their existing exception.
    if Fraction(total, 1) / fps == 30 and not any(s.get("holdReason") for s in scenes):
        require(8 <= len(scenes) <= 12, "THIRTY_SECOND_SCENE_COUNT_8_TO_12")


def choose_item(scene, items, previous):
    tags = ROLE_TAGS.get(scene.get("role"), set())
    ranked = sorted(items.values(), key=lambda item: (
        -len(tags.intersection(item.get("tags", []))), item["id"]))
    candidates = ([scene["itemId"]] if scene.get("itemId") else
                  [item["id"] for item in ranked if tags.intersection(item.get("tags", []))])
    for item_id in candidates:
        item = items.get(item_id)
        if (item and item.get("implemented") and item.get("artStatus") == "certified"
                and item.get("kind") == "text" and (scene.get("itemId") or item_id != previous)):
            return item
    raise RhythmError("NO_CERTIFIED_ITEM_FOR_ROLE")


def validate_lines(lines):
    require(isinstance(lines, list) and 1 <= len(lines) <= 4, "INVALID_LINES")
    require(all(isinstance(line, str) and line.strip() and len(line) <= 48
                and not any(ord(c) < 32 for c in line) for line in lines), "INVALID_LINES")


def plan_story(story, catalog):
    require(story.get("profile") in PROFILES, "UNKNOWN_PROFILE")
    profile = PROFILES[story["profile"]]
    width, height = frame_size(story, profile)
    fps = rate(story.get("fps", "30"))
    total = exact_frames(story["durationSeconds"], fps)
    sources = story.get("scenes", [])
    require(isinstance(sources, list) and 0 < len(sources) <= 50000, "EMPTY_OR_OVERSIZED_STORY")
    scene_count(total, fps, sources, story.get("sceneCountOverride"))
    items = index_catalog(catalog)
    scenes, minimums, maximums, targets = [], [], [], []
    previous = None
    for i, source in enumerate(sources):
        require(isinstance(source.get("id"), str) and source["id"].strip(), "MISSING_SCENE_ID")
        validate_lines(source.get("lines"))
        item = choose_item(source, items, previous)
        previous = item["id"]
        minimum = math.ceil(max(2, reading_seconds(source["lines"])) * fps)
        maximum = math.floor(5 * fps)
        if source.get("holdReason"):
            require(source.get("role") in ("proof", "presenter"), "INVALID_HOLD_EXCEPTION")
            maximum = exact_frames(source["durationSeconds"], fps)
            minimum = maximum
        require(minimum <= maximum, "TEXT_OVERLOAD")
        target_seconds = source.get("durationSeconds", profile["pattern"][i % len(profile["pattern"])] )
        target = round(Fraction(str(target_seconds)) * fps)
        if "durationSeconds" in source:
            require(minimum <= target <= maximum, "SCENE_DURATION_OUT_OF_BOUNDS")
            minimum = maximum = target
        minimums.append(minimum)
        maximums.append(maximum)
        targets.append(target)
        scene = {
            "id": source["id"], "role": source["role"], "itemId": item["id"],
            "itemRevision": item["revision"], "lines": source["lines"],
            "params": {"lines": source["lines"], "font": source.get("font", "display"),
                       "palette": {"theme": source.get("palette", "ref_lime")},
                       "energy": source.get("energy", "standard"),
                       "plate": source.get("plate", item["showcasePlate"]), "seed": i + 17},
            "meaning": source.get("meaning", "/".join(source["lines"])),
            "cut": "clean", "holdReason": source.get("holdReason"),
        }
        scenes.append(scene)
    durations = partition(total, minimums, maximums, targets)
    cursor = 0
    for scene, duration in zip(scenes, durations):
        scene.update(startFrame=cursor, durationFrames=duration)
        scene["params"]["durationSeconds"] = float(Fraction(duration, 1) / fps)
        cursor += duration
    result = {"schema": SCHEMA, "profile": story["profile"], "fps": str(fps),
              "width": width, "height": height, "totalFrames": total,
              "engineVersion": catalog["engineVersion"], "catalogDigest": digest(catalog),
              "artStatus": "ART_PENDING_REVIEW", "scenes": scenes,
              "groups": [list(range(i, min(i + profile["groupScenes"], len(scenes))))
                         for i in range(0, len(scenes), profile["groupScenes"])],
              "audio": {"kind": "original_synth", "bpm": 120, "voice": False}}
    if story.get("sceneCountOverride") is not None:
        result["sceneCountOverride"] = dict(story["sceneCountOverride"])
    validate_plan(result, catalog)
    return result


def validate_plan(plan, catalog):
    require(plan.get("schema") == SCHEMA, "UNKNOWN_SCHEMA")
    require(plan.get("profile") in PROFILES, "UNKNOWN_PROFILE")
    profile = PROFILES[plan["profile"]]
    frame_size(plan, profile)
    require(plan.get("catalogDigest") == digest(catalog)
            and plan.get("engineVersion") == catalog.get("engineVersion"), "STALE_CATALOG")
    fps = rate(plan["fps"])
    items = index_catalog(catalog)
    require(isinstance(plan.get("totalFrames"), int) and plan["totalFrames"] > 0, "INVALID_TOTAL")
    scenes = plan.get("scenes", [])
    require(bool(scenes), "EMPTY_STORY")
    scene_count(plan["totalFrames"], fps, scenes, plan.get("sceneCountOverride"))
    cursor, seen, prior = 0, set(), None
    for scene in scenes:
        duration = scene["durationFrames"]
        require(type(scene["startFrame"]) is int and type(duration) is int, "NON_INTEGER_FRAME")
        require(scene["startFrame"] == cursor, "GAP_OR_OVERLAP")
        require(scene["id"] not in seen, "DUPLICATE_SCENE_ID")
        seen.add(scene["id"])
        validate_lines(scene["lines"])
        hold = bool(scene.get("holdReason"))
        require(not hold or scene["role"] in ("proof", "presenter"), "INVALID_HOLD_EXCEPTION")
        require(duration >= math.ceil(max(2, reading_seconds(scene["lines"])) * fps)
                and (duration <= math.floor(5 * fps) or hold), "SCENE_DURATION_OUT_OF_BOUNDS")
        item = items.get(scene["itemId"], {})
        require(item.get("implemented") and item.get("kind") == "text"
                and item.get("artStatus") == "certified"
                and item.get("revision") == scene["itemRevision"], "UNCERTIFIED_OR_STALE_ITEM")
        require(scene["params"].get("lines") == scene["lines"], "TEXT_PARAMS_MISMATCH")
        require(abs(scene["params"]["durationSeconds"] - float(Fraction(duration, 1) / fps)) < 1e-8,
                "DURATION_PARAMS_MISMATCH")
        require(scene["params"].get("plate") in ("bg", "accent", "paper"), "TRANSPARENT_BASE")
        signature = tuple(scene["lines"])
        require(signature != prior, "ADJACENT_DUPLICATE_CONTENT")
        prior = signature
        cursor += duration
    require(cursor == plan["totalFrames"], "INCOMPLETE_COVERAGE")
    flattened = [i for group in plan["groups"] for i in group]
    require(flattened == list(range(len(scenes))) and all(
        0 < len(group) <= profile["groupScenes"] for group in plan["groups"]), "INVALID_GROUPS")
    return {"status": "PASS", "sceneCount": len(scenes), "coverage": 1.0,
            "durationSeconds": float(Fraction(cursor, 1) / fps),
            "minSceneSeconds": float(min(s["durationFrames"] for s in scenes) / fps),
            "maxSceneSeconds": float(max(s["durationFrames"] for s in scenes) / fps),
            "items": sorted(set(s["itemId"] for s in scenes)), "artStatus": "ART_PENDING_REVIEW"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "check"))
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--story", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8-sig"))
    if args.action == "plan":
        require(args.story is not None and args.out is not None, "STORY_AND_OUT_REQUIRED")
        require(not args.out.exists(), "REFUSE_OVERWRITE")
        result = plan_story(json.loads(args.story.read_text(encoding="utf-8-sig")), catalog)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        require(args.plan is not None, "PLAN_REQUIRED")
        result = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    print(json.dumps(validate_plan(result, catalog), ensure_ascii=False))


if __name__ == "__main__":
    main()
