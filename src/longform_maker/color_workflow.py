# -*- coding: utf-8 -*-
"""Longform/Vlog/Podcast adapter for Visual Master.

Run this on camera footage before title cards, subtitles, HUDs or tracked
graphics. The adapter creates new media and a report instead of touching raw
files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from visual_master import apply_to_video, plan_color_system


def prepare_source(input_path: str, output_path: str, *, domain: str = "documentary",
                   format_kind: str = "longform") -> dict:
    plan = plan_color_system(domain, format_kind)
    report = apply_to_video(input_path, output_path, plan["profile"], plan["base_strength"])
    report["color_system"] = plan
    sidecar = Path(output_path).with_suffix(Path(output_path).suffix + ".grade.json")
    sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _selftest() -> None:
    assert plan_color_system("interview", "podcast")["profile"] == "podcast_skin_neutral"
    assert plan_color_system("travel", "vlog")["profile"] == "travel_airy_local"
    assert plan_color_system("documentary", "longform")["base_strength"] < 0.3
    print("longform color_workflow self-test OK")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--domain", default="documentary")
    parser.add_argument("--format", default="longform", choices=("longform", "vlog", "podcast"))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        _selftest(); return 0
    if not args.input or not args.output:
        parser.error("input and output are required unless --selftest is used")
    print(json.dumps(prepare_source(args.input, args.output, domain=args.domain,
                                    format_kind=args.format), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
