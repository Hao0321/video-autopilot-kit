# -*- coding: utf-8 -*-
"""Self-authored integer-frame seek contract for browser-rendered scenes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def seek_payload(graph: dict[str, Any], frame: int) -> dict[str, Any]:
    contract = graph.get("frame_contract") or {}
    fps = int(contract.get("fps", 0))
    first = int(contract.get("first_frame", 0))
    last = int(contract.get("last_frame", -1))
    if fps <= 0 or frame < first or frame > last:
        raise ValueError("invalid frame or frame contract")
    active = []
    for node in graph.get("nodes") or []:
        start, end = [int(value) for value in node.get("frame_window", [0, 0])]
        if start <= frame < end:
            active.append({
                "id": node["id"], "adapter": node["adapter"],
                "local_frame": frame - start, "duration_frames": end - start,
                "immutable_props": node.get("props") or {},
            })
    return {
        "type": "hao:seek-frame", "frame": frame, "time": frame / fps,
        "fps": fps, "wall_clock_access": "forbidden", "active_nodes": active,
    }


def self_test() -> None:
    graph = {
        "frame_contract": {"fps": 30, "first_frame": 0, "last_frame": 59},
        "nodes": [{"id": "a", "adapter": "hao_browser_seek", "frame_window": [10, 20], "props": {"x": 1}}],
    }
    assert seek_payload(graph, 9)["active_nodes"] == []
    assert seek_payload(graph, 12)["active_nodes"][0]["local_frame"] == 2
    print("browser_seek_runtime self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hao browser integer-frame seek runtime")
    parser.add_argument("command", choices=("seek", "selftest"))
    parser.add_argument("graph", nargs="?")
    parser.add_argument("--frame", type=int, default=0)
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    if not args.graph:
        parser.error("graph is required")
    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    print(json.dumps(seek_payload(graph, args.frame), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
