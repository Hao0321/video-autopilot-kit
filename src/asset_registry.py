# -*- coding: utf-8 -*-
"""Asset Intelligence Hub for video-autopilot.

The hub keeps existing manifests as their source of truth and builds a small,
portable decision view at runtime.  It never copies media and never exposes the
whole library to the model: one job receives only ranked candidates in
``current_asset_plan.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from asset_memory import migrate_index_paths, record_asset_paths, record_plan_usage
from domain_taxonomy import DOMAIN_KEYWORDS, SUPPORTED_DOMAINS, infer_domain, normalize_domain
from project_paths import discover_project_root


from asset_registry_shared import (
    DEFAULT_PLAN_TOKENS, DOMAIN_FOLEY, PLAN_NAME, SKILL_ROOT,
    _estimate_tokens, recommend_bgm_scene,
)


from asset_catalog import AssetCatalogMixin
from asset_selection import AssetSelectionMixin


class AssetRegistry(AssetSelectionMixin, AssetCatalogMixin):
    """Virtual registry built from existing manifests; no binary copies."""


def _read_json_from_text(text: str) -> dict:
    try:
        return json.loads(text or "{}")
    except ValueError:
        return {}


def _normalize_cues(cues, duration: float, topic: str) -> list[dict]:
    rows = []
    for cue in cues or []:
        if isinstance(cue, dict):
            start = float(cue.get("start", cue.get("t", 0)))
            end = float(cue.get("end", start + cue.get("duration", 2)))
            text = str(cue.get("text", cue.get("source_text", "")))
        elif isinstance(cue, (tuple, list)) and len(cue) >= 3:
            start, end, text = float(cue[0]), float(cue[1]), str(cue[2])
        else:
            continue
        if text.strip() and end > start:
            rows.append({"start": round(max(0, start), 2), "end": round(min(duration, end), 2),
                         "text": text.strip()[:80]})
    if not rows:
        rows = [{"start": 0.0, "end": round(min(duration, 3.0), 2), "text": str(topic or "主題")[:80]}]
    rows.sort(key=lambda row: row["start"])
    if len(rows) <= 6:
        return rows
    indices = sorted({round(i * (len(rows) - 1) / 5) for i in range(6)})
    return [rows[i] for i in indices]


def _energy_at(t: float, curve) -> float:
    for part in curve or []:
        if float(part.get("start", 0)) <= t < float(part.get("end", 0)):
            return float(part.get("energy", .5))
    return .55


def _source_required(text: str) -> bool:
    return bool(re.search(
        r"\d|價格|售價|地址|地點|戰績|分數|規格|證據|實測|後台|截圖|文件|紀錄|營收|收益|下載|轉換率",
        str(text or ""), re.I))


def _impact_text_candidate(text: str) -> bool:
    return bool(re.search(
        r"AI|VS|成功|失敗|結果|揭曉|重點|倍|贏|輸|冠軍|第一|最終|\d+(?:[.,]\d+)?(?:%|倍|萬|元)?",
        str(text or ""), re.I))


def _select_cue_asset(*, source_required: bool, broll: list[dict],
                      motion: list[dict], template: list[dict]) -> dict:
    if source_required:
        return {"tier": 0, "kind": "project_source_required", "status": "needs_verified_source",
                "reason": "數字／地點／規格／實測不可用庫存素材冒充"}
    if broll and broll[0]["confidence"] >= .48 and "需安全重構" not in broll[0]["reason"]:
        return {"tier": 1, "kind": "semantic_broll", **broll[0]}
    if motion:
        return {"tier": 2, "kind": "topic_motion", **motion[0]}
    if template:
        return {"tier": 3, "kind": "editorial_card", **template[0]}
    return {"tier": 4, "kind": "clean_hold", "status": "no_unrelated_filler",
            "reason": "無可靠素材時保留乾淨畫面／安全重構"}


def _plan_asset_cues(registry: AssetRegistry, cue_rows: list[dict], *, topic: str,
                     domain: str, aspect: str, energy_curve) -> list[dict]:
    cue_plan = []
    for index, cue in enumerate(cue_rows, 1):
        energy = _energy_at((cue["start"] + cue["end"]) / 2, energy_curve)
        query = (str(topic or "") + " " + cue["text"]).strip()
        requires_source = _source_required(cue["text"])
        # Proof cues cannot use library visuals as evidence.  Do not even carry
        # those unused candidates into the small runtime packet.
        broll = [] if requires_source else registry.select_broll(query, domain, aspect, energy, limit=2)
        motion = [] if requires_source else registry.select_motion(query, domain, aspect, energy, limit=1)
        template = [] if requires_source else registry.select_template(query, domain, aspect, "background", energy, limit=1)
        sfx = registry.select_sfx(cue["text"], domain, energy, limit=1)
        text_overlay = (registry.select_text_overlay(cue["text"], domain, max(.82, energy), limit=1)
                        if _impact_text_candidate(cue["text"]) else [])
        particle = registry.select_particle_source(cue["text"], domain, max(.86, energy), limit=1)
        cue_plan.append({
            "cue_id": f"cue-{index:02d}", **cue, "energy": round(energy, 2),
            "source_required": requires_source,
            "selected": _select_cue_asset(
                source_required=requires_source, broll=broll,
                motion=motion, template=template,
            ),
            "broll_candidates": broll, "sfx_candidates": sfx,
            "text_overlay_candidates": text_overlay,
            "particle_candidates": particle,
            "missing_foley": [] if sfx else list(DOMAIN_FOLEY.get(domain, ()))[:3],
        })
    return cue_plan


def _asset_policy(format: str) -> dict:
    policy = {
        "priority": ["project_source_or_proof", "semantic_broll", "topic_motion", "editorial_card", "clean_hold"],
        "rule": "缺畫面不等於可塞不相關庫存片；數字、地點、規格與實測必須回到可驗證來源。",
        "token_rule": "只讀本檔排名候選，不載入完整 registry 或逐檔 probe。",
    }
    if format == "interview":
        policy.update({
            "profile": "no_face_documentary",
            "forbidden_assets": ["face", "reaction_window", "ai_avatar", "silhouette_substitute"],
            "speaker_system": "H=blue square; G=lime circle or approved text mark; never color-only",
            "waveform_limit": "full-screen waveform <= 3 seconds",
            "proof_rule": "guest claims use approved screenshot/document/screen recording only; fallback tiers cannot impersonate proof",
        })
    return policy


def _fit_asset_plan_budget(plan: dict, max_tokens: int) -> None:
    plan["token_budget"] = {"max_tokens": int(max_tokens), "estimated_tokens": _estimate_tokens(plan)}
    if plan["token_budget"]["estimated_tokens"] > int(max_tokens):
        for cue in plan["cues"]:
            cue["broll_candidates"] = cue["broll_candidates"][:1]
            cue["sfx_candidates"] = cue["sfx_candidates"][:1]
            cue["text_overlay_candidates"] = cue.get("text_overlay_candidates", [])[:1]
        if len(plan["cues"]) > 4:
            plan["cues"] = plan["cues"][:3] + plan["cues"][-1:]
        plan["token_budget"]["estimated_tokens"] = _estimate_tokens(plan)
    if plan["token_budget"]["estimated_tokens"] > int(max_tokens):
        if len(plan["cues"]) > 3:
            plan["cues"] = plan["cues"][:2] + plan["cues"][-1:]
        plan["music"]["candidates"] = plan["music"].get("candidates", [])[:1]
        plan["shared_assets"]["particles"] = plan["shared_assets"].get("particles", [])[:1]
        plan["token_budget"]["estimated_tokens"] = _estimate_tokens(plan)
    if plan["token_budget"]["estimated_tokens"] > int(max_tokens):
        # The selected asset already carries the decision.  Alternative arrays
        # are optional context and must never block an edit merely because paths
        # or provenance strings are verbose.
        for cue in plan["cues"]:
            cue["broll_candidates"] = []
            cue["sfx_candidates"] = []
            cue["text_overlay_candidates"] = []
            cue["missing_foley"] = cue.get("missing_foley", [])[:1]
        plan["token_budget"]["estimated_tokens"] = _estimate_tokens(plan)
    if plan["token_budget"]["estimated_tokens"] > int(max_tokens):
        keep = {"tier", "kind", "asset_id", "path", "status", "reason", "confidence"}
        for cue in plan["cues"]:
            cue["selected"] = {key: value for key, value in cue["selected"].items() if key in keep}
            cue.pop("missing_foley", None)
        plan["token_budget"]["estimated_tokens"] = _estimate_tokens(plan)
    plan["token_budget"]["within_budget"] = (
        plan["token_budget"]["estimated_tokens"] <= int(max_tokens)
    )
    if not plan["token_budget"]["within_budget"]:
        raise ValueError("asset plan exceeds token budget: %r" % plan["token_budget"])


def build_asset_plan(topic: str, domain: str = "auto", format: str = "shorts", duration: float = 30,
                     cues=None, energy_curve=None, registry: AssetRegistry | None = None,
                     max_tokens: int = DEFAULT_PLAN_TOKENS) -> dict:
    registry = registry or AssetRegistry()
    duration = max(.1, float(duration))
    domain = infer_domain(topic, domain)
    aspect = "portrait" if format in {"short", "shorts", "portrait", "9:16"} else "landscape"
    cue_rows = _normalize_cues(cues, duration, topic)
    average_energy = sum(_energy_at((r["start"] + r["end"]) / 2, energy_curve) for r in cue_rows) / len(cue_rows)
    music = registry.select_music(topic, domain, duration, average_energy, format=format, limit=3)
    cue_plan = _plan_asset_cues(
        registry, cue_rows, topic=topic, domain=domain,
        aspect=aspect, energy_curve=energy_curve,
    )

    selected_music = music[0] if music else None
    shared_particles = {}
    for cue in cue_plan:
        candidates = cue.pop("particle_candidates", [])
        cue["particle_asset_ids"] = [item["asset_id"] for item in candidates]
        for item in candidates:
            shared_particles.setdefault(item["asset_id"], item)
    strategy = ("none" if not selected_music else "single_track"
                if float(selected_music.get("duration_sec") or 0) >= duration + 1
                else "playlist_crossfade")
    plan = {
        "schema_version": 1,
        "route": {"topic": str(topic or "")[:180], "domain": domain, "format": format,
                  "aspect": aspect, "duration_sec": round(duration, 2)},
        "policy": _asset_policy(format),
        "registry_counts": registry.counts(),
        "shared_assets": {"particles": list(shared_particles.values())},
        "music": {"strategy": strategy, "selected": selected_music, "candidates": music,
                  "index_reused": True, "voice_compatibility": "unknown tracks need mix-stage check"},
        "cues": cue_plan,
        "usage_history": {"applied_as_soft_repeat_penalty": True, "record_only_after_asset_is_used": True},
    }
    _fit_asset_plan_budget(plan, max_tokens)
    return plan


def write_asset_plan(output_dir: str | os.PathLike, **kwargs) -> dict:
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / PLAN_NAME
    plan = build_asset_plan(**kwargs)
    payload = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    cache_hit = target.is_file() and target.read_text(encoding="utf-8") == payload
    if not cache_hit:
        fd, temp_name = tempfile.mkstemp(prefix=".asset-plan-", suffix=".tmp", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    plan["runtime"] = {"path": str(target), "cache_hit": cache_hit}
    return plan


def self_test() -> None:
    registry = AssetRegistry()
    assert all(not Path(row["path"]).is_absolute() for row in registry.records)
    assert len({row["asset_id"] for row in registry.records}) == len(registry.records)
    # A clean public install intentionally contains no user's BGM/B-roll.
    # Selection may be empty, but planning must fail closed instead of inventing
    # a path or borrowing a maintainer asset.
    assert all(not Path(row["path"]).is_absolute()
               for row in registry.select_music("拉麵實測", "food", 20, .6, limit=1))
    assert all(not Path(row["path"]).is_absolute()
               for row in registry.select_motion("AI 教學", "ai", "portrait", .6, limit=1))
    assert not registry.select_text_overlay("最終結果", "general", limit=1), \
        "缺少核准 Image 素材時不可拿 VS 或 deprecated 程式字頂替"
    with tempfile.TemporaryDirectory(prefix="asset-hub-") as temp_dir:
        a = write_asset_plan(temp_dir, topic="拉麵 150 元實測", domain="auto", format="shorts",
                             duration=24, cues=[(0, 2, "先看拉麵"), (8, 10, "價格 150 元"),
                                                (18, 21, "最後口感")])
        b = write_asset_plan(temp_dir, topic="拉麵 150 元實測", domain="auto", format="shorts",
                             duration=24, cues=[(0, 2, "先看拉麵"), (8, 10, "價格 150 元"),
                                                (18, 21, "最後口感")])
        assert a["token_budget"]["within_budget"] and b["runtime"]["cache_hit"]
        assert a["cues"][1]["selected"]["kind"] == "project_source_required"
        bounded = build_asset_plan(
            topic="鶯歌手拉坏與老街", domain="travel", format="shorts", duration=18,
            cues=[(i * 2, i * 2 + 1.8, "旅遊鏡頭與字幕候選 %02d" % i) for i in range(9)],
            max_tokens=900,
        )
        assert bounded["token_budget"]["within_budget"], bounded["token_budget"]
        assert len(bounded["cues"]) <= 6
        interview = write_asset_plan(temp_dir, topic="創辦人營收訪談", domain="interview",
                                     format="interview", duration=60,
                                     cues=[(0, 10, "營收後台證據"), (10, 30, "核心方法")])
        assert interview["policy"]["profile"] == "no_face_documentary"
        assert "face" in interview["policy"]["forbidden_assets"]
    report = registry.audit()
    assert report["status"] in {"GREEN", "RED"} and "errors" in report
    print("asset_registry self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Video Autopilot Asset Intelligence Hub")
    sub = parser.add_subparsers(dest="command")
    plan = sub.add_parser("plan")
    plan.add_argument("--topic", required=True)
    plan.add_argument("--domain", default="auto")
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--duration", type=float, default=30)
    plan.add_argument("--output-dir", default=str(SKILL_ROOT / "_runtime"))
    audit = sub.add_parser("audit")
    audit.add_argument("--full", action="store_true")
    audit.add_argument("--release", action="store_true")
    commit = sub.add_parser("commit")
    commit.add_argument("plan_path")
    commit.add_argument("--content-id", required=True)
    commit.add_argument("--feedback", default="")
    migrate = sub.add_parser("migrate-index")
    migrate.add_argument("--write", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "plan":
        result = write_asset_plan(args.output_dir, topic=args.topic, domain=args.domain,
                                  format=args.format, duration=args.duration)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "audit":
        result = AssetRegistry().audit(full=args.full, release=args.release)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("ASSET HEALTH " + result["status"])
        return 0 if result["status"] == "GREEN" else 1
    if args.command == "commit":
        print("recorded", record_plan_usage(args.plan_path, args.content_id, args.feedback), "asset usages")
        return 0
    if args.command == "migrate-index":
        result = migrate_index_paths(write=args.write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result["external_paths"] else 1
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
