"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import json
from pathlib import Path


def _write_programmatic_plan(output_dir, plan):
    from composition_runtime import SCHEMA, compile_graph
    fps = 30
    total_frames = max(1, round(float(plan["duration"]) * fps))
    tracks = [{
        "id": "canvas", "component": "solid", "start_frame": 0,
        "duration_frames": total_frames, "z": 0,
        "props": {"color": "#00000000"},
    }]
    for index, event in enumerate(plan.get("events") or []):
        start = max(0, min(total_frames - 1, round(float(event["t"]) * fps)))
        length = max(1, round(float(event["duration"]) * fps))
        length = min(length, total_frames - start)
        tracks.append({
            "id": f"event-{index:03d}", "component": "component_scene",
            "start_frame": start, "duration_frames": length,
            "z": 10 + index,
            "props": {
                "role": event.get("type"), "card": event.get("card"),
                "transition": event.get("transition"),
                "domain": plan["domain"], "format": plan["format"],
            },
        })
    composition = {
        "schema": SCHEMA,
        "id": f"{plan['domain']}-{plan['format']}-visual-plan",
        "width": 1080 if plan["format"] == "short" else 1920,
        "height": 1920 if plan["format"] == "short" else 1080,
        "fps": fps, "duration_frames": total_frames,
        "variables": {"domain": plan["domain"], "format": plan["format"]},
        "tracks": tracks,
    }
    render_graph = compile_graph(composition, Path(output_dir))
    composition_name = plan["programmatic_runtime"]["composition"]
    graph_name = plan["programmatic_runtime"]["render_graph"]
    Path(output_dir, composition_name).write_text(
        json.dumps(composition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(output_dir, graph_name).write_text(
        json.dumps(render_graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan["programmatic_runtime"].update({
        "status": "GREEN", "fps": fps, "duration_frames": total_frames,
        "track_count": len(tracks),
        "composition_sha256": render_graph["composition_sha256"],
        "render_graph_sha256": render_graph["render_graph_sha256"],
    })
