# -*- coding: utf-8 -*-
"""Publishing hub command-line adapter (public distribution).

Routes creator-owned publishing state changes without performing a public upload.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from types import ModuleType
from typing import Any

from publish_contract import selftest as contract_selftest


def _hub(module: ModuleType | None = None) -> ModuleType:
    if module is None:
        raise RuntimeError(
            "publish_hub_cli is an adapter; invoke it through publish_hub.main()"
        )
    return module


def selftest(module: ModuleType | None = None) -> None:
    import tempfile
    from pathlib import Path

    hub = _hub(module)
    assert hub._slug('a:b/c*', fallback="x") == "a_b_c"
    assert hub.READY.parent == hub.HUB and hub.PUBLISHED.parent == hub.HUB
    assert hub.HUB.name == "_PUBLISH_HUB"
    root_entry = hub._root_entry_text()
    assert "(videos/" not in root_entry
    assert 'publish_hub.py" sync' in root_entry
    assert 'publish_hub.py" open' in root_entry
    parsed = _parser().parse_args(["mark-published", "S001"])
    assert parsed.platform == "reported_by_creator"
    contract_selftest()
    assert hub._withdrawn_ids() >= set()

    with tempfile.TemporaryDirectory(prefix="publish-hub-metadata-") as temporary:
        root = Path(temporary)
        originals = {name: getattr(hub, name) for name in (
            "ROOT", "READY", "PUBLISHED", "HUB_AUDIT",
            "_content_manifests", "rebuild_index",
        )}
        try:
            hub.ROOT = root
            hub.READY = root / "hub" / "READY"
            hub.PUBLISHED = root / "hub" / "PUBLISHED"
            hub.HUB_AUDIT = root / "hub" / "_AUDIT"
            package = hub.READY / "shorts" / "review" / "S001"
            package.mkdir(parents=True)
            video = package / "current.mp4"
            video.write_bytes(b"synthetic-published-metadata-fixture")
            manifest = package / "publish.json"
            manifest.write_text(json.dumps({
                "content_id": "S001", "format": "shorts", "status": "review",
                "video": video.name, "sha256": hub._sha256(video),
            }), encoding="utf-8")
            hub._content_manifests = lambda _content_id: [manifest]
            hub.rebuild_index = lambda: {"status": "GREEN"}
            result = hub.mark_published("S001")
            published = json.loads((hub.PUBLISHED / "shorts" / "published" /
                                    "S001" / "publish.json").read_text(encoding="utf-8"))
            metadata = published["published"]
            assert result["published"] == metadata
            assert metadata["platform"] == "reported_by_creator"
            assert metadata["video_id"] is None and metadata["url"] is None
            assert metadata["reported_on"] and metadata["note"]
        finally:
            for name, value in originals.items():
                setattr(hub, name, value)
    print("publish_hub self-test GREEN")


def open_hub(module: ModuleType | None = None) -> dict[str, Any]:
    hub = _hub(module)
    hub.HUB.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(hub.HUB))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(hub.HUB)])
    else:
        subprocess.Popen(["xdg-open", str(hub.HUB)])
    return {"status": "OPENED", "hub": str(hub.HUB),
            "start_here": str(hub.START_HERE)}


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Video Autopilot publishing hub")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("sync")
    subs.add_parser("audit")
    subs.add_parser("open")
    subs.add_parser("review-queue")
    withdraw = subs.add_parser("withdraw-content")
    withdraw.add_argument("content_ids", nargs="+")
    withdraw.add_argument("--reason", required=True)
    withdraw.add_argument("--actor", default="creator")
    mark = subs.add_parser("mark-published")
    mark.add_argument("content_ids", nargs="+")
    mark.add_argument("--date", default="")
    mark.add_argument("--platform", default="reported_by_creator")
    mark.add_argument("--note", default="")
    migration = subs.add_parser("migrate-layout")
    migration.add_argument("--apply", action="store_true")
    subs.add_parser("remix-plan")
    retire = subs.add_parser("retire-legacy-ready")
    retire.add_argument("--apply", action="store_true")
    dedupe = subs.add_parser("dedupe-verified")
    dedupe.add_argument("--apply", action="store_true")
    versioned = subs.add_parser("retire-versioned-renders")
    versioned.add_argument("--apply", action="store_true")
    subs.add_parser("selftest")
    return parser


def main(argv: list[str] | None = None,
         module: ModuleType | None = None) -> int:
    hub = _hub(module)
    args = _parser().parse_args(argv)
    if args.command == "selftest":
        selftest(hub)
        return 0
    if args.command == "sync":
        hub_migration = hub.migrate_legacy_layout(apply=True)
        layout = hub.migrate_status_layout()
        payload = {
            "hub_migration": hub_migration,
            "layout_migrations": layout,
            "ready_shorts": hub.migrate_ready_shorts(),
            "published_shorts": hub.import_published_shorts(),
            "longform": hub.import_longform(),
            "legacy_miaoli_remix": hub.create_miaoli_remix_plan(),
            "remix": hub.create_remix_plans(),
        }
        payload["registry"] = hub.rebuild_index()
    elif args.command == "audit":
        payload = hub.audit()
    elif args.command == "open":
        payload = open_hub(hub)
    elif args.command == "review-queue":
        payload = hub.autonomy_queue_summary()
    elif args.command == "withdraw-content":
        payload = hub.withdraw_content(args.content_ids, reason=args.reason,
                                       actor=args.actor)
    elif args.command == "mark-published":
        payload = {"status": "GREEN", "results": [
            hub.mark_published(content_id, date=args.date or None,
                               platform=args.platform, note=args.note)
            for content_id in args.content_ids
        ]}
    elif args.command == "migrate-layout":
        payload = hub.migrate_legacy_layout(apply=args.apply)
    elif args.command == "remix-plan":
        payload = hub.create_remix_plans()
    elif args.command == "retire-legacy-ready":
        payload = hub.retire_legacy_ready(apply=args.apply)
    elif args.command == "dedupe-verified":
        payload = hub.consolidate_verified_duplicates(apply=args.apply)
    else:
        payload = hub.retire_versioned_job_outputs(apply=args.apply)
    _print(payload)
    return 0 if payload.get("status", "GREEN") != "RED" else 1
