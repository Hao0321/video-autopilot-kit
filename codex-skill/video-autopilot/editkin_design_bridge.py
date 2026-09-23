"""Compile the redistributable Video Autopilot design DNA for Editkin v4.

This read-only entry point travels with the Skill. It produces instructions and
source hashes, never a quality certification or a rendered asset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "design_runtime"
sys.path.insert(0, str(RUNTIME / "src"))

SOURCE_FILES = (
    "SKILL.md",
    "workflow_contract.json",
    "editkin_design_bridge.py",
    "design_runtime/src/aesthetic_score.py",
    "design_runtime/src/design_system_v6.py",
    "design_runtime/knowledge/runtime/aesthetic_standard.json",
    "design_runtime/knowledge/runtime/design_reference_dna.json",
    "references/design-reference-dna-v6.md",
    "references/caption-art-direction.md",
)


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprints() -> list[dict[str, str]]:
    return [{"path": relative, "sha256": hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}
            for relative in SOURCE_FILES]


def compile_brief(request: dict) -> dict:
    if not 1 <= len(request.get("beats", [])) <= 64:
        raise ValueError("Expected 1–64 design beats")
    before = fingerprints()
    from aesthetic_score import load_standard, resolve_style_route
    from design_system_v6 import compile_recipe

    fmt = "longform" if request["format"] in {"longform", "podcast", "interview"} else "shorts"
    standard = load_standard()
    route = resolve_style_route(request["domain"], fmt, standard)
    recipes = [{"beatId": beat["id"], "recipe": compile_recipe(
        request["domain"], fmt, beat["role"], energy=beat["energy"],
        subject=beat["subject"], style_family=request.get("styleFamily"))}
        for beat in request["beats"]]
    context = {
        "profile": "public-video-autopilot-design-v6",
        "route": route,
        "topic": request["topic"],
        "duration": request["duration"],
        "principles": standard["reference_basis"]["shared_dna"],
        "guardrails": standard["domain_routes"].get(request["domain"], standard["domain_routes"]["general"])["avoid"],
        "boundary": "Public design recipes guide actual Editkin commands. They do not prove visual quality, source truth, or human approval.",
    }
    if fingerprints() != before:
        raise ValueError("Public design sources changed during compilation; prepare again")
    return {"schema": "hao.editkin.current-design-brief/v1", "request": request,
            "sources": before, "sourceSha256": digest(before),
            "context": context, "recipes": recipes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args()
    print(json.dumps(compile_brief(json.loads(args.request_json)), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
