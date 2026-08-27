# -*- coding: utf-8 -*-
"""Fail-closed gateway for missing bitmap and texture assets.

The runtime cannot call Codex's built-in Imagegen tool by itself.  It emits a
small, durable request that the orchestrating Codex turn must fulfil with the
built-in image generation tool.  Generated files remain unselectable until Hao
reviews them through the Asset Workshop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
_PROJECT_KNOWLEDGE = ROOT / "knowledge"
_PUBLIC_KNOWLEDGE = ROOT.parent / "knowledge" / "runtime"
KNOWLEDGE_ROOT = (_PROJECT_KNOWLEDGE if _PROJECT_KNOWLEDGE.exists() else
                  _PUBLIC_KNOWLEDGE)
POLICY_PATH = KNOWLEDGE_ROOT / "imagegen_asset_policy.json"


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return "imagegen-gap-" + digest


def build_request(*, semantic_target: str, domain: str, aspect: str,
                  asset_kind: str = "supporting_bitmap",
                  proof_required: bool = False) -> dict[str, Any]:
    target = str(semantic_target or "").strip()
    if proof_required:
        return {
            "status": "VERIFIED_SOURCE_REQUIRED",
            "kind": "project_source_required",
            "semantic_target": target,
            "reason": "Proof, prices, locations, results and real products cannot be generated.",
            "render_fallback": "clean_hold",
        }
    request_id = _slug("|".join((target, domain, aspect, asset_kind)))
    return {
        "status": "IMAGEGEN_REQUIRED",
        "kind": "imagegen_required",
        "request_id": request_id,
        "semantic_target": target,
        "domain": str(domain or "general"),
        "aspect": str(aspect or "portrait"),
        "asset_kind": asset_kind,
        "tool": "OpenAI built-in imagegen",
        "prompt_contract": {
            "use_case": "stylized-concept",
            "primary_request": target,
            "constraints": [
                "production-usable isolated bitmap or atlas",
                "no text, logo or watermark unless exact approved copy is supplied",
                "no unrelated decoration",
                "truth label illustrative_not_evidence for realistic generations"
            ],
            "avoid": [
                "cheap vector blob", "generic icon", "clip-art", "fake proof"
            ]
        },
        "ingest_contract": {
            "destination": "assets/workshop",
            "human_review": "pending",
            "selectable": False,
            "mobile_review_required": True
        },
        "render_fallback": "clean_hold"
    }


def validate_request(request: dict[str, Any]) -> list[str]:
    errors = []
    if request.get("status") == "IMAGEGEN_REQUIRED":
        if request.get("tool") != "OpenAI built-in imagegen":
            errors.append("missing assets must route to built-in imagegen")
        ingest = request.get("ingest_contract") or {}
        if ingest.get("selectable") is not False or ingest.get("human_review") != "pending":
            errors.append("generated asset must remain pending and unselectable")
        if request.get("render_fallback") != "clean_hold":
            errors.append("unfulfilled request must fail closed to clean hold")
    return errors


def self_test() -> None:
    policy = load_policy()
    assert policy["hard_gates"]["no_procedural_premium_bitmap_fallback"]
    request = build_request(semantic_target="real torn-paper fibre atlas",
                            domain="travel", aspect="portrait")
    assert request["status"] == "IMAGEGEN_REQUIRED"
    assert not validate_request(request)
    proof = build_request(semantic_target="店家真實地址", domain="food",
                          aspect="portrait", proof_required=True)
    assert proof["status"] == "VERIFIED_SOURCE_REQUIRED"
    print("imagegen_asset_gateway self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a fail-closed Imagegen asset request")
    sub = parser.add_subparsers(dest="command", required=True)
    request = sub.add_parser("request")
    request.add_argument("--semantic-target", required=True)
    request.add_argument("--domain", default="general")
    request.add_argument("--aspect", default="portrait")
    request.add_argument("--asset-kind", default="supporting_bitmap")
    request.add_argument("--proof-required", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    result = build_request(semantic_target=args.semantic_target, domain=args.domain,
                           aspect=args.aspect, asset_kind=args.asset_kind,
                           proof_required=args.proof_required)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
