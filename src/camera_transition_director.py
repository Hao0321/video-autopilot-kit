# -*- coding: utf-8 -*-
"""Plan motivated shot dynamics without confusing overlays with transitions.

The planner keeps five layers separate:

1. camera move;
2. edit transition (an actual cut between shots);
3. graphic transition (an object/layer replacement inside a composition);
4. graphic overlay;
5. particle/impact overlay.

This distinction is mandatory for value-comparison sequences.  A USD burst is
an impact/value overlay.  It becomes neither a camera move nor a transition
merely because it crosses the foreground.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path


VALUE_PATTERN = re.compile(
    r"(?:[$＄]\s*[\d,.]+(?:\s*(?:million|billion|m|b))?)|"
    r"(?:[\d,.]+\s*(?:美元|美金|萬元|萬|億元|億|元|塊|million|billion|倍|%|％))|"
    r"(?:價格|價值|成本|預算|獎金|收入|營收|市值|售價|報價)", re.I,
)
USD_PATTERN = re.compile(r"[$＄]|美元|美金|(?:million|billion)(?:\s+dollars?)?", re.I)
REVEAL_PATTERN = re.compile(r"揭曉|公布|答案|結果|終於|竟然|最後|贏家|winner|reveal", re.I)
PRECISION_PATTERN = re.compile(r"點擊|輸入|設定|選單|程式碼|code|終端|表格|數據來源|文件|逐字", re.I)


GRAMMAR = {
    "clean_cut": {
        "layer": "edit_transition", "duration_frames": [0, 0],
        "continuity": "information_or_action",
        "recipe": "在語意、動作或聲音完成點直接切；沒有鏡頭證據時，預設只准 clean cut。",
    },
    "motivated_push_in": {
        "layer": "camera_move", "duration_frames": [6, 10],
        "continuity": "attention_vector",
        "recipe": "快速推近 106%→122%，落點配 hit；只用在承諾、揭曉或最高價值，不算剪點。",
    },
    "speed_ramped_pullback_reveal": {
        "layer": "camera_move", "duration_frames": [10, 22],
        "continuity": "subject_to_environment_scale",
        "recipe": "由近景主體高速拉遠揭露完整場景；來源必須有真實廣角餘量或已核准的 2.5D/3D 合成。",
    },
    "whip_object_swap": {
        "layer": "graphic_transition", "duration_frames": [10, 18],
        "continuity": "matched_direction_scale_and_anchor",
        "recipe": "舊物件沿同一方向甩出，新物件從相反畫緣接力進場；峰值模糊可替換物件，但不代表一定有 shot cut。",
    },
    "comparison_pullback": {
        "layer": "camera_move", "duration_frames": [14, 30],
        "continuity": "shared_composite_space_and_scale_hierarchy",
        "recipe": "從最後一個比較物件連續拉遠，露出同一合成空間中的全部對象與貼身標籤。",
    },
    "tracked_value_label": {
        "layer": "graphic_overlay", "duration_frames": [24, 90],
        "continuity": "object_anchor",
        "recipe": "以 tracked_graphics.py 把金額字綁定可信 initial_bbox；字跟著主體與鏡頭動，失追短 hold 後隱藏，不漂浮猜路徑。",
        "renderer": "tracked_graphics.py",
        "requires": ["verified_initial_bbox", "value_evidence"],
    },
    "challenge_ledger_hud": {
        "layer": "graphic_overlay", "duration_frames": [60, 900],
        "continuity": "stateful_progress",
        "recipe": "左上角以 active/completed/upcoming 狀態記錄挑戰或價值階梯；它是持續 HUD，不是轉場或空白字卡。",
        "renderer": "tracked_graphics.py",
        "requires": ["verified_items", "active_index_or_timed_events"],
    },
    "usd_value_particles": {
        "layer": "particle_overlay", "duration_frames": [36, 84],
        "continuity": "value_impact",
        "recipe": "美元粒子在金額落點後由字與主體周圍爆發；它是價值／衝擊疊加，不是轉場。",
    },
    "impact_flash": {
        "layer": "impact_overlay", "duration_frames": [2, 5],
        "continuity": "reveal_landing",
        "recipe": "只在總覽完全落定時做極短曝光衝擊；不能用閃白掩飾無動機剪接。",
    },
    "whip_pan_cut": {
        "layer": "edit_transition", "duration_frames": [8, 15],
        "continuity": "matched_camera_direction",
        "recipe": "只有前後兩顆真鏡頭在同方向甩動，且剪點位於峰值模糊時，才叫 whip-pan cut。",
    },
    "match_scale_cut": {
        "layer": "edit_transition", "duration_frames": [0, 5],
        "continuity": "object_scale_and_screen_position",
        "recipe": "兩顆真鏡頭的主體尺寸、重心與視線方向匹配後切換；無 shot evidence 不得自動宣稱。",
    },
    "occlusion_cut": {
        "layer": "edit_transition", "duration_frames": [5, 12],
        "continuity": "foreground_motion_and_hidden_edit_point",
        "recipe": "真實前景遮住至少 70% 畫面，且剪點確實位於遮擋期間；單純粒子飛過不算。",
    },
    "parallax_drift": {
        "layer": "camera_move", "duration_frames": [18, 42],
        "continuity": "depth",
        "recipe": "背景、主體、前景分三層不同速平移；用於靜態圖，不冒充真攝影運鏡。",
    },
    "speed_ramp_cut": {
        "layer": "edit_transition", "duration_frames": [8, 16],
        "continuity": "motion_peak",
        "recipe": "只有兩顆真鏡頭在動作峰值切換才成立；單一鏡頭 speed ramp 是 camera move，不是 cut。",
    },
}

EVENT_GROUPS = {
    "camera_move": "camera_moves",
    "edit_transition": "edit_transitions",
    "graphic_transition": "graphic_transitions",
    "graphic_overlay": "overlays",
    "particle_overlay": "overlays",
    "impact_overlay": "overlays",
}


def _rows(captions) -> list[dict]:
    result = []
    for item in captions or []:
        if isinstance(item, dict):
            start = float(item.get("start", item.get("t", 0)))
            end = float(item.get("end", start + item.get("duration", 1.5)))
            text = str(item.get("text", item.get("source_text", "")))
        elif isinstance(item, (tuple, list)) and len(item) >= 3:
            start, end, text = float(item[0]), float(item[1]), str(item[2])
        else:
            continue
        if end > start and text.strip():
            result.append({"start": start, "end": end, "text": text.strip()})
    return sorted(result, key=lambda row: row["start"])


def _event(time: float, kind: str, reason: str, source_text: str,
           *, strength: str = "strong", cluster: str | None = None,
           conditional: str | None = None) -> dict:
    item = {
        "t": round(max(0, time), 2), "kind": kind,
        "layer": GRAMMAR[kind]["layer"], "strength": strength,
        "reason": reason, "source_text": source_text[:72],
        "continuity": GRAMMAR[kind]["continuity"],
    }
    if cluster:
        item["cluster"] = cluster
    if conditional:
        item["requires_evidence"] = conditional
    if GRAMMAR[kind].get("renderer"):
        item["renderer"] = GRAMMAR[kind]["renderer"]
    if GRAMMAR[kind].get("requires"):
        item["render_requires"] = list(GRAMMAR[kind]["requires"])
    return item


def _dedupe_and_budget(events: list[dict], duration: float, format_kind: str) -> list[dict]:
    """Dedupe within a layer only; camera, text and particles may share a beat."""
    strong_limit = max(2, round(duration / (6 if format_kind == "short" else 15)))
    output, strong_count = [], 0
    for event in sorted(events, key=lambda item: (item["t"], item["layer"], item["kind"])):
        same_layer = next((index for index in range(len(output) - 1, -1, -1)
                           if output[index]["layer"] == event["layer"] and
                           abs(event["t"] - output[index]["t"]) < .16), None)
        if same_layer is not None:
            continue
        structural = event["layer"] in {"camera_move", "edit_transition", "graphic_transition"}
        if structural and event["strength"] == "strong" and not event.get("cluster"):
            if strong_count >= strong_limit:
                continue
            strong_count += 1
        if event["t"] <= duration - .08:
            output.append(event)
    return output


def _group_events(events: list[dict]) -> dict[str, list[dict]]:
    groups = {name: [] for name in EVENT_GROUPS.values()}
    for event in events:
        groups[EVENT_GROUPS[event["layer"]]].append(event)
    return groups


def _plan_value_sequence(value_rows: list[dict], duration: float, format_kind: str,
                         seed: object) -> tuple[list[dict], str | None, float | None]:
    if not value_rows:
        return [], None, None
    digest = hashlib.sha256(("|".join(row["text"] for row in value_rows) + str(seed)).encode("utf-8")).hexdigest()[:8]
    cluster = f"value-ladder-{digest}"
    events = []
    hero = value_rows[0]
    if not PRECISION_PATTERN.search(hero["text"]):
        events.append(_event(
            hero["start"], "speed_ramped_pullback_reveal", "hero_value_environment_reveal",
            hero["text"], cluster=cluster,
            conditional="wide_reveal_plate_or_approved_2.5d_3d_composite",
        ))
    for index, row in enumerate(value_rows):
        if PRECISION_PATTERN.search(row["text"]):
            continue
        events.append(_event(row["start"], "tracked_value_label", "bind_value_to_object",
                             row["text"], strength="medium", cluster=cluster))
        if index:
            events.append(_event(
                row["start"], "whip_object_swap", "directional_value_object_replacement",
                row["text"], cluster=cluster,
                conditional="matched_scale_anchor_and_same_whip_direction",
            ))
    if len(value_rows) >= 2:
        summary = " / ".join(row["text"][:20] for row in value_rows[:8])
        events.append(_event(
            hero["start"], "challenge_ledger_hud", "persist_value_or_challenge_progress",
            summary, strength="medium", cluster=cluster,
            conditional="verified_items_and_timed_active_state",
        ))
    comparison_t = None
    if len(value_rows) >= 3:
        comparison_t = min(duration - .15, value_rows[-1]["end"] + (.08 if format_kind == "short" else .18))
        summary = " / ".join(row["text"][:20] for row in value_rows[-4:])
        events.append(_event(
            comparison_t, "comparison_pullback", "reveal_shared_value_hierarchy", summary,
            cluster=cluster, conditional="all_objects_exist_in_shared_composite_space",
        ))
        events.append(_event(comparison_t + .28, "impact_flash", "comparison_landing", summary,
                             strength="medium", cluster=cluster))
    return events, cluster, comparison_t


def _plan_semantic_reveals(rows: list[dict]) -> list[dict]:
    return [
        _event(row["start"], "motivated_push_in", "semantic_reveal", row["text"])
        for row in rows
        if REVEAL_PATTERN.search(row["text"])
        and not VALUE_PATTERN.search(row["text"])
        and not PRECISION_PATTERN.search(row["text"])
    ]


def _plan_usd_overlay(value_rows: list[dict], comparison_t: float | None,
                      format_kind: str, cluster: str | None) -> tuple[list[dict], dict | None]:
    money_rows = [row for row in value_rows if USD_PATTERN.search(row["text"])]
    if not money_rows:
        return [], None
    instances = [{"t": round(money_rows[0]["start"] + .45, 2), "purpose": "hero_value_impact"}]
    if comparison_t is not None:
        instances.append({"t": round(comparison_t + .18, 2), "purpose": "comparison_payoff"})
    events = [
        _event(instance["t"], "usd_value_particles", instance["purpose"], money_rows[0]["text"],
               strength="medium", cluster=cluster)
        for instance in instances
    ]
    packet = {
        "enabled": True, "classification": "particle_overlay", "is_transition": False,
        "instances": instances, "duration": 2.4 if format_kind == "longform" else 1.7,
        "profile": "hero",
        "asset_source": "community/hao-motion-kit/assets/money_burst/imagegen/usd-100-front-back-alpha-v1.png",
        "renderer": "community/hao-motion-kit/money_burst_assets.py",
        "runtime_clip": f"current_money_burst_{'portrait' if format_kind == 'short' else 'landscape'}_hero.mov",
        "composition": "美元在金額字後方與前景形成景深；必須在價值落點後出現，不負責換鏡。",
        "guardrail": "只有明確美元語意才用；粒子遮到畫面仍只是 overlay，除非另有真剪點與遮擋證據。",
    }
    return events, packet


def _system_payload(value_rows: list[dict], events: list[dict], groups: dict,
                    particle_packet: dict | None, cluster: str | None, seed: object) -> dict:
    rng = random.Random(hashlib.sha256(str(seed).encode("utf-8")).hexdigest())
    return {
        "version": 2,
        "principle": "classify_layer_before_naming_transition",
        "layer_taxonomy": {
            "camera_move": "同一鏡頭或同一合成空間的視點／尺度運動，沒有剪點。",
            "edit_transition": "兩顆 shot 之間確實存在剪點。",
            "graphic_transition": "同一合成畫面內物件或圖層被替換，不自動等同 shot cut。",
            "graphic_overlay": "追蹤字卡、標籤與資訊層。",
            "particle_overlay": "美元、紙屑等衝擊層；本身不是轉場。",
        },
        "inspiration_boundary": "提煉速度、尺度、方向、合成與資訊階層；不複製第三方成片、Logo 或固定版式。",
        "official_sequence_audit": {
            "hook": "近景人物到金色遊輪全貌是 speed-ramped pullback reveal；美元在金額落點後疊加。",
            "value_steps": "$50M 到 $300M 是同方向 whip object swap；峰值模糊可藏替換，但不能僅憑畫面宣稱 shot cut。",
            "overview": "$300M 到全價值總覽是 comparison pullback；落點再疊 impact flash 與美元粒子。",
            "correction": "money burst = particle overlay, never auto-labelled as transition",
            "record_hud": "左上 badge／ladder 是 stateful challenge ledger；以 tracked_graphics.py 更新 active item，不是轉場。",
        },
        "aesthetic_permissions": {
            "allowed": ["original_brand_like_typography", "original_logo_marks", "thick_outlines", "cartoon_stickers", "glossy_3d_text"],
            "rule": "依題材與語意選用，不把任何一項誤寫成全域禁令；第三方受保護資產仍需授權。",
        },
        "value_ladder": {
            "detected": bool(value_rows), "beat_count": len(value_rows), "cluster": cluster,
            "sequence": ["hero_pullback_reveal", "directional_whip_object_swaps", "comparison_pullback", "impact_overlays"]
                        if len(value_rows) >= 3 else ["hero_reveal", "directional_object_compare"] if value_rows else [],
            "hud_renderer": "tracked_graphics.py" if len(value_rows) >= 2 else None,
            "hud_mode": "ladder" if len(value_rows) >= 2 else None,
        },
        "timeline_events": events,
        **groups,
        "value_particle_overlay": particle_packet,
        "shot_edit_policy": {
            "default": "clean_cut",
            "nonclean_requires": ["two_verified_shots", "visible_motion_or_occluder", "documented_cut_point"],
            "never_infer_from": ["money_particles", "impact_flash", "motion_blur_alone"],
        },
        "grammar": GRAMMAR,
        "limits": {
            "structural_effect_spacing": "價值階梯內可連續；其他 Shorts 約 6 秒、長片約 15 秒才一個強結構動作。",
            "whip": "物件或鏡頭方向、尺度與錨點必須匹配；shot cut 必須另有來源證據。",
            "occlusion_cut": "真前景遮擋至少 70%，且剪點實際位於遮擋期間；overlay 不能自證。",
            "precision_ui": "程式碼、表格、設定與 proof 使用 clean cut，不用強模糊遮住證據。",
            "effect_aftercare": "強效果後至少接一顆乾淨可讀鏡頭。",
        },
        "sound_recipe": {
            "speed_ramped_pullback_reveal": ["riser", "sub_hit_at_wide_reveal"],
            "whip_object_swap": ["directional_whoosh"],
            "comparison_pullback": ["riser", "sub_drop", "music_release"],
            "usd_value_particles": ["paper_flutter", "cash_scatter", "impact_hit"],
        },
        "variation_seed": rng.randrange(1, 10**7),
    }


def plan_shot_dynamics_system(captions, *, duration: float, format_kind: str,
                              domain: str = "general", seed: object = 0) -> dict:
    if format_kind not in {"short", "longform"}:
        raise ValueError("format_kind must be short or longform")
    duration = float(duration)
    rows = _rows(captions)
    value_rows = [row for row in rows if VALUE_PATTERN.search(row["text"])]
    events, cluster, comparison_t = _plan_value_sequence(value_rows, duration, format_kind, seed)
    events.extend(_plan_semantic_reveals(rows))
    particle_events, particle_packet = _plan_usd_overlay(
        value_rows, comparison_t, format_kind, cluster,
    )
    events.extend(particle_events)
    events = _dedupe_and_budget(events, duration, format_kind)
    return _system_payload(
        value_rows, events, _group_events(events), particle_packet, cluster, seed,
    )


def validate_shot_dynamics_system(system: dict, duration: float) -> list[str]:
    errors = []
    if system.get("principle") != "classify_layer_before_naming_transition":
        errors.append("missing layer-classification principle")
    events = system.get("timeline_events") or []
    for event in events:
        grammar = GRAMMAR.get(event.get("kind"))
        if not grammar:
            errors.append("unknown shot-dynamics kind")
            continue
        if event.get("layer") != grammar["layer"]:
            errors.append("event layer does not match grammar")
        if not 0 <= float(event.get("t", -1)) <= float(duration):
            errors.append("shot-dynamics event outside duration")
        if not event.get("reason") or not event.get("continuity"):
            errors.append("unmotivated shot-dynamics event")
    ladder = system.get("value_ladder") or {}
    if ladder.get("beat_count", 0) >= 3 and "comparison_pullback" not in ladder.get("sequence", []):
        errors.append("three-step value ladder missing comparison pullback")
    particles = system.get("value_particle_overlay")
    if particles:
        if particles.get("classification") != "particle_overlay" or particles.get("is_transition") is not False:
            errors.append("USD particles misclassified as transition")
        if "usd-100" not in str(particles.get("asset_source", "")):
            errors.append("USD particle overlay must use recognizable USD source")
    if any(event.get("kind") == "occlusion_cut" for event in events):
        errors.append("occlusion cut cannot be auto-planned without shot-level evidence")
    expected = _group_events(events)
    for key, values in expected.items():
        if values != (system.get(key) or []):
            errors.append(f"event grouping mismatch: {key}")
    return errors


# Backward-compatible imports for older callers.  New plans and documentation
# use the precise shot-dynamics name.
plan_camera_transition_system = plan_shot_dynamics_system
validate_camera_transition_system = validate_shot_dynamics_system


def self_test() -> None:
    rows = [
        (0, 1.2, "$1 BILLION 的遊艇"),
        (2.0, 3.0, "$50 MILLION"),
        (3.2, 4.2, "$300 MILLION"),
        (5.0, 6.2, "最後一起比較結果"),
    ]
    plan = plan_shot_dynamics_system(rows, duration=12, format_kind="longform", domain="business", seed=7)
    kinds = [event["kind"] for event in plan["timeline_events"]]
    assert "speed_ramped_pullback_reveal" in kinds
    assert kinds.count("whip_object_swap") == 2
    assert "challenge_ledger_hud" in kinds
    assert "comparison_pullback" in kinds and "usd_value_particles" in kinds
    assert next(event for event in plan["overlays"] if event["kind"] == "tracked_value_label")["renderer"] == "tracked_graphics.py"
    assert plan["edit_transitions"] == []
    assert plan["value_particle_overlay"]["is_transition"] is False
    assert plan["value_particle_overlay"]["asset_source"].endswith("usd-100-front-back-alpha-v1.png")
    assert not validate_shot_dynamics_system(plan, 12)
    clean = plan_shot_dynamics_system([(0, 2, "點擊設定並輸入程式碼")], duration=8,
                                      format_kind="short", domain="ai", seed=2)
    assert not clean["timeline_events"] and clean["value_particle_overlay"] is None
    reveal = plan_shot_dynamics_system([(0, 1, "最後公布贏家")], duration=5,
                                       format_kind="short", seed=3)
    assert reveal["camera_moves"][0]["kind"] == "motivated_push_in"
    print("camera_transition_director self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan layered camera, edit, graphic and overlay events")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--format", choices=("short", "longform"), default="short")
    parser.add_argument("--text", default="$1 到 $1,000,000 的挑戰")
    parser.add_argument("--out", default="")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        self_test()
        return 0
    plan = plan_shot_dynamics_system([(0, 2, args.text)], duration=args.duration,
                                     format_kind=args.format, seed="cli")
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
