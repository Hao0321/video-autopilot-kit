# -*- coding: utf-8 -*-
"""Hao Cinematic Wave — 跨題材節奏導演。

把自動剪輯從「固定每 N 秒塞效果」改成三層規劃：
1. macro：cold open → build → breath → payoff 的能量波；
2. meso：依領域使用 wide / medium / detail / reaction 的鏡頭組句；
3. micro：語意字卡、motivated transition、J/L cut、room tone、foley 與音樂重擊。

輸出 deterministic JSON，可供 Shorts renderer、長片 PLAN 與 QA 共用。
這是從公開影片與通用電影剪輯原理歸納出的 Hao 自有系統，不複製任何頻道的
logo、字卡、音效包、逐鏡腳本或品牌版式。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from pathlib import Path

from art_direction import THEMES, resolve_theme
from aesthetic_score import resolve_style_route
from design_system_v6 import compile_recipe as compile_design_recipe
from mrbeast_editing_system import plan_sequence as plan_information_sequence
from three_d_system import plan_3d
from asset_registry import PLAN_NAME as ASSET_PLAN_NAME, write_asset_plan
from camera_transition_director import (
    plan_shot_dynamics_system,
    validate_shot_dynamics_system,
)
from caption_director import plan_caption_system, validate_caption_system
from context_router import PACKET_NAME, write_context_packet
from domain_taxonomy import infer_domain as infer_taxonomy_domain
from editorial_templates import STYLES as EDITORIAL_STYLES, resolve_style as resolve_editorial_style
from motion_asset_pack import plan_asset_cues
from template_compiler import compile_template_program
from mediastorm_craft import apply_transition_decisions, compile_craft_plan
from visual_style_router import (plan_color_system, plan_filter_system,
                                 plan_trend_system)
from visual_plan_support import (audio_plan as _audio_plan,
                                 PROFILES, SEMANTIC_CARDS,
                                 template_roles as _template_roles,
                                 visual_guardrails as _visual_guardrails)

def _caption_rows(captions) -> list[dict]:
    rows = []
    for c in captions or []:
        if isinstance(c, dict):
            rows.append({"start": float(c.get("start", c.get("s", 0))),
                         "end": float(c.get("end", c.get("e", 0))),
                         "text": str(c.get("text", "")),
                         "source_kind": str(c.get("kind", c.get("source_kind", "main"))),
                         # Preserve composition evidence used by the caption
                         # director.  Dropping this bit previously let a clean
                         # tracked showcase hook be promoted back into a giant
                         # centre-screen IMPACT title.
                         "tracked_subject_overlaps": bool(
                             c.get("tracked_subject_overlaps", False))})
        elif len(c) >= 3:
            rows.append({"start": float(c[0]), "end": float(c[1]), "text": str(c[2]),
                         "source_kind": str(c[3]) if len(c) > 3 else "main"})
    return sorted(rows, key=lambda x: x["start"])


def infer_domain(text: str = "", hint: str | None = None) -> str:
    """先尊重明確 hint，再以可解釋 keyword score 判斷「怎麼剪」。"""
    return infer_taxonomy_domain(text, hint, PROFILES)


def _card_for(text: str, fallback: tuple[str, ...], i: int) -> str:
    for words, card in SEMANTIC_CARDS:
        if any(w in text for w in words):
            return card
    return fallback[i % len(fallback)]


def _format_kind(duration: float, value: str) -> str:
    key = str(value or "auto").lower()
    if key == "auto":
        return "short" if duration <= 75 else "longform"
    if key in ("short", "shorts", "reel", "reels"):
        return "short"
    if key in ("long", "longform", "youtube"):
        return "longform"
    raise ValueError("unknown format %r" % value)


def _make_energy_curve(duration: float, format_kind: str) -> list[dict]:
    if format_kind == "short":
        blueprint = (
            ("cold_open", .08, .96, "先給結果／衝突，不先解釋"),
            ("promise", .21, .64, "說清楚觀眾會得到什麼"),
            ("build", .50, .76, "用鏡頭組句累積資訊"),
            ("turn", .68, .90, "錯誤、反差或新變數"),
            ("breath", .76, .28, "保留現場聲，讓高潮有落差"),
            ("payoff", .91, 1.00, "兌現標題與開場承諾"),
            ("resolve", 1.0, .50, "乾淨收尾或接回 loop"),
        )
    else:
        cold_end = min(.04, max(.015, 8.0 / duration))
        promise_end = min(.11, cold_end + max(.035, 15.0 / duration))
        blueprint = (
            ("cold_open", cold_end, .94, "先給結果／衝突，不播 logo 前奏"),
            ("promise", promise_end, .62, "建立問題與觀看承諾"),
            ("context", .27, .50, "讓觀眾理解人、地、限制"),
            ("build_1", .47, .72, "第一輪證據／行動"),
            ("reset", .53, .38, "短換氣、換景或觀點重設"),
            ("build_2", .73, .84, "第二輪推進與反差"),
            ("breath", .79, .25, "高潮前縮音樂，保留呼吸／room tone"),
            ("payoff", .93, 1.00, "主證據、揭曉或情緒高點"),
            ("resolve", 1.0, .48, "餘韻、結論與下一步"),
        )
    out, start = [], 0.0
    for name, end_f, energy, intent in blueprint:
        end = duration if end_f >= 1 else round(duration * end_f, 3)
        end = max(start, min(duration, end))
        out.append({"name": name, "start": round(start, 3), "end": round(end, 3),
                    "energy": energy, "intent": intent})
        start = end
    out[-1]["end"] = round(duration, 3)
    return out


def _energy_at(t: float, curve: list[dict]) -> float:
    for act in curve:
        if act["start"] <= t < act["end"] or (t == act["end"] == curve[-1]["end"]):
            return float(act["energy"])
    return float(curve[-1]["energy"])


def _shot_target(base: tuple[float, float], energy: float) -> list[float]:
    # 高能縮短，低能拉長；仍保留題材自身的快慢尺度。
    scale = 1.48 - .82 * energy
    return [round(max(.45, base[0] * scale), 2), round(max(.72, base[1] * scale), 2)]


def _nearest_caption(rows: list[dict], t: float, tolerance: float) -> dict | None:
    if not rows:
        return None
    near = min(rows, key=lambda r: abs(r["start"] - t))
    return near if abs(near["start"] - t) <= tolerance else None


def _event_anchors(curve: list[dict], duration: float, format_kind: str,
                   count: int, rng: random.Random) -> list[tuple[float, str]]:
    preferred = ("build", "turn", "payoff") if format_kind == "short" else (
        "promise", "build_1", "reset", "build_2", "payoff")
    anchors = [(a["start"], a["name"]) for a in curve if a["name"] in preferred]
    if len(anchors) > count:
        # 均勻抽取並保留最後 payoff；不能永遠只拿前幾段而漏掉兌現點。
        picks = [round(i * (len(anchors) - 1) / (count - 1)) for i in range(count)]
        anchors = [anchors[i] for i in picks]
    # 長片需要更多斷點時，在高能 act 內不等距補點；breath/resolve 不補。
    while len(anchors) < count:
        usable = [a for a in curve if a["name"] not in ("cold_open", "breath", "resolve")
                  and a["end"] - a["start"] > 2.0]
        act = usable[len(anchors) % len(usable)]
        anchors.append((rng.uniform(act["start"] + .2, act["end"] - .2), act["name"]))
    return sorted(anchors, key=lambda x: x[0])[:count]


def _visual_events(duration: float, rows: list[dict], profile: dict, curve: list[dict],
                   format_kind: str, theme_cfg: dict, rng: random.Random) -> list[dict]:
    events = []
    if duration < 3:
        return events
    target = min(3, max(2, round(duration / 9.0))) if format_kind == "short" \
        else min(9, max(3, round(duration / 38.0)))
    anchors = _event_anchors(curve, duration, format_kind, target, rng)
    previous, last_end = None, -1.0
    tolerance = 2.8 if format_kind == "short" else 6.0
    for i, (target_t, act_name) in enumerate(anchors):
        near = _nearest_caption(rows, target_t, tolerance)
        t = near["start"] if near else target_t
        text = near["text"] if near else ""
        if t < 1.0 or t > duration - .9 or t < last_end + .12:
            continue
        card = _card_for(text, profile["cards"], i)
        if card == previous:
            card = profile["cards"][(i + 1) % len(profile["cards"])]
        read_bonus = min(.28, len(text) * .008)
        event_dur = round(min(.86, .46 + read_bonus), 2)
        if t + event_dur > duration - .15:
            continue
        events.append({
            "t": round(t, 2), "duration": event_dur, "type": "pattern_interrupt",
            "card": card, "transition": "clean_cut", "sfx": None,
            "intensity": round(_energy_at(t, curve), 2), "source_text": text[:42],
            "reason": "payoff_marker" if act_name == "payoff" else "semantic_turn",
        })
        previous, last_end = card, t + event_dur
    return events


def _sequence_plan(curve: list[dict], profile: dict) -> list[dict]:
    out = []
    for i, act in enumerate(curve):
        pattern = profile["sequence"][i % len(profile["sequence"])]
        transition = "cut" if act["name"] in ("cold_open", "breath", "resolve") \
            else profile["transitions"][i % len(profile["transitions"])]
        out.append({
            "start": act["start"], "end": act["end"], "act": act["name"],
            "energy": act["energy"], "shot_duration_target": _shot_target(profile["shot"], act["energy"]),
            "shot_pattern": list(pattern), "transition_out": transition,
            "cut_motivation": ("hold_for_contrast" if act["name"] == "breath"
                               else "action_or_information_change"),
            "audio_focus": profile["sound"][i % len(profile["sound"])],
            "direction_rule": profile["direction"],
        })
    return out


def _assemble_visual_plan(*, duration: float, domain: str, theme: str,
                          format_kind: str, editorial: dict, profile: dict,
                          aesthetic_route: dict,
                          design_system_v6: dict,
                          template_program: dict,
                          mediastorm_craft: dict,
                          high_information_system: dict,
                          three_d_system: dict,
                          curve: list[dict], events: list[dict],
                          sequence_plan: list[dict], audio_plan: dict,
                          motion_assets: dict, caption_system: dict,
                          shot_dynamics_system: dict, color_system: dict,
                          trend_system: dict, filter_system: dict) -> dict:
    payoff = next(a for a in curve if a["name"] == "payoff")
    template_aspect = "portrait" if format_kind == "short" else "landscape"
    compiled_style = template_program["plans"][0]["route"]["style"]
    return {
        "version": 9, "genre": domain, "domain": domain, "theme": theme,
        "format": format_kind, "duration": round(duration, 3),
        "style": "hao_cinematic_wave", "background": "domain_bright_editorial",
        "influence_note": "使用者提供的跨領域設計與影片參考用於提煉顏色、排版、圖形、尺度與鏡頭原理；允許原創品牌字型感、Logo 式識別、粗描邊與卡通貼紙語法，不直接搬用第三方受保護資產",
        "template_system": {
            "engine": "template_compiler.py -> community/hao-motion-kit/template_engine.py",
            "compiler": template_program["compiler"],
            "style": compiled_style,
            "legacy_fallback_style": editorial["key"],
            "aspect": template_aspect, "roles": _template_roles(events),
            "program": template_program,
            "rule": "模板是可組裝構圖計畫，不是強制插入的全螢幕場景；題材決定構圖語法並依畫幅真正重排",
        },
        "aesthetic_system": {
            "standard_id": aesthetic_route["standard_id"],
            "standard_version": aesthetic_route["standard_version"],
            "primary_family": aesthetic_route["primary_family"],
            "primary_label": aesthetic_route["primary_label"],
            "support_families": aesthetic_route["support_families"],
            "allowed_templates": aesthetic_route["allowed_templates"],
            "avoid": aesthetic_route["avoid"],
            "format_rule": aesthetic_route["format_rule"],
            "formal_benchmarks": aesthetic_route["formal_benchmarks"],
            "benchmark_rule": "MrBeast 資訊能量與影視颶風電影工藝在長片與短片都必須評分；只調整權重，不取消任一軸。",
            "parity_claim_policy": "只對有參考時間碼、素材前提、輸出、逐幀 QA 與 Hao 審片的單一效果宣稱功能對等；禁止籠統宣稱全部 100% 複製。",
            "rule": "跨長短片共用母美術標準；依格式調整權重，不照抄參考圖。",
        },
        "design_system_v6": design_system_v6,
        "mediastorm_craft": mediastorm_craft,
        "high_information_system": high_information_system,
        "three_d_system": three_d_system,
        "programmatic_runtime": {
            "schema": "hao.motion-composition/v1",
            "engine": "composition_runtime.py",
            "implementation": "self_authored",
            "scope": "all_formats_all_domains",
            "clock": "integer_frame_only",
            "third_party_video_frameworks": "benchmark_only_not_runtime_dependencies",
            "composition": "current_composition.json",
            "render_graph": "current_render_graph.json",
            "status": "PLANNED",
        },
        "hook_plan": {
            "strategy": "result_first_cold_open", "visual": profile["hook"],
            "promise_deadline": next(a["end"] for a in curve if a["name"] == "promise"),
            "rule": "標題／縮圖承諾先兌現；logo 與自我介紹不得擋在前面",
        },
        "energy_curve": curve, "shot_duration_target": list(profile["shot"]),
        "sequence_plan": sequence_plan, "sfx_density": profile["sfx"],
        "visual_grammar": profile["grammar"], "audio_plan": audio_plan,
        "payoff_plan": {
            "start": payoff["start"], "end": payoff["end"],
            "rule": "breath 之後才進 payoff；至少停留一顆可讀清的乾淨鏡頭",
        },
        "events": events, "motion_assets": motion_assets, "caption_system": caption_system,
        "color_system": color_system,
        "filter_system": filter_system,
        "trend_system": trend_system,
        "shot_dynamics_system": shot_dynamics_system,
        "guardrails": _visual_guardrails(domain),
    }


def plan_visual_rhythm(duration: float, captions=None, genre: str = "auto", seed: object = 0,
                       format: str = "auto", context_text: str = "",
                       color_profile: str | None = None,
                       color_strength: float | None = None) -> dict:
    duration = float(duration)
    if duration <= 0:
        raise ValueError("duration must be > 0")
    rows = _caption_rows(captions)
    text = (str(context_text or "") + " " + " ".join(r["text"] for r in rows)).strip()
    domain = infer_domain(text, genre)
    profile = PROFILES[domain]
    theme = profile["theme"]
    cfg = resolve_theme(theme)
    format_kind = _format_kind(duration, format)
    rng = random.Random(f"cinematic-wave-v3:{domain}:{duration:.3f}:{seed}")
    curve = _make_energy_curve(duration, format_kind)
    events = _visual_events(duration, rows, profile, curve, format_kind, cfg, rng)
    sequence_plan = _sequence_plan(curve, profile)
    # Do not trust a profile name as proof that a transition can be executed.
    # At planning time there is no shot-pair evidence, so the craft gate keeps
    # clean cuts and records every requested transition for later re-evaluation.
    mediastorm_craft = compile_craft_plan(
        duration=duration, format=format_kind, domain=domain,
        sequence_plan=sequence_plan, evidence=[], seed=seed,
    )
    sequence_plan = apply_transition_decisions(sequence_plan, mediastorm_craft)
    audio_plan = _audio_plan(curve, profile, rng)
    motion_assets = plan_asset_cues(curve, events, format_kind, domain)
    caption_system = plan_caption_system(rows, duration, format_kind, domain, curve)
    shot_dynamics_system = plan_shot_dynamics_system(
        rows, duration=duration, format_kind=format_kind, domain=domain, seed=seed,
    )
    color_system = plan_color_system(
        domain, format_kind, profile_override=color_profile,
        strength_override=color_strength,
    )
    trend_system = plan_trend_system(domain, format_kind)
    filter_system = plan_filter_system(domain, format_kind, color_system["profile"])
    aesthetic_route = resolve_style_route(domain, format_kind)
    design_system_v6 = compile_design_recipe(
        domain, format_kind, "first_frame",
        energy=float(curve[0]["energy"]), subject="real_footage",
    )
    # The visual director exposes capability, but never invents evidence. Actual
    # effects are selected later only after tracking/matte/source checks exist.
    high_information_system = plan_information_sequence([], format=format_kind)
    high_information_system.update({
        "status": "AWAITING_EVIDENCE",
        "candidate_events": [
            "promise_cold_open", "tracked_callout", "subject_sheen",
            "proof_freeze", "breath_reset",
        ],
        "selection_rule": "select only after every event prerequisite is present",
    })
    route_3d = (
        "product_turntable" if domain in {"toy", "product", "automotive"}
        else "data_space" if domain in {"ai", "business"}
        else "depth_cards"
    )
    subject_3d = (
        "battle_top" if domain == "toy" else
        "vehicle" if domain == "automotive" else
        "glass_ui" if domain in {"ai", "business"} else
        "generic_product"
    )
    three_d_system = plan_3d(
        route_3d, format=format_kind, subject=subject_3d,
        available=[], purpose="optional_enrichment",
    )
    editorial = resolve_editorial_style(text or domain)
    if editorial["key"] not in aesthetic_route["allowed_templates"]:
        editorial = resolve_editorial_style(text or domain, aesthetic_route["primary_template"])
    template_program = compile_template_program(
        domain, format_kind, _template_roles(events), title=text,
        energy=float(curve[0]["energy"]),
        subject=("battle_top" if domain == "toy" else "real_footage"),
        seed=seed, style_hint=editorial["key"],
    )
    plan = _assemble_visual_plan(
        duration=duration, domain=domain, theme=theme, format_kind=format_kind,
        editorial=editorial, profile=profile, aesthetic_route=aesthetic_route,
        design_system_v6=design_system_v6, template_program=template_program,
        mediastorm_craft=mediastorm_craft,
        high_information_system=high_information_system,
        three_d_system=three_d_system,
        curve=curve, events=events,
        sequence_plan=sequence_plan, audio_plan=audio_plan,
        motion_assets=motion_assets, caption_system=caption_system,
        shot_dynamics_system=shot_dynamics_system, color_system=color_system,
        trend_system=trend_system, filter_system=filter_system,
    )
    errors = validate_visual_plan(plan)
    if errors:
        raise AssertionError("visual plan invalid: " + "; ".join(errors))
    return plan


def _validate_events(events: list[dict], duration: float) -> list[str]:
    bad, last_card, glitch_count, last_end = [], None, 0, -1.0
    for event in events:
        start, event_duration = float(event["t"]), float(event["duration"])
        if start < 0 or start + event_duration > duration + .05:
            bad.append("event outside duration @%.2f" % start)
        if start < last_end - .05:
            bad.append("events overlap @%.2f" % start)
        if event.get("card") == last_card and event.get("type") == "pattern_interrupt":
            bad.append("same card repeated: %s" % last_card)
        if "glitch" in str(event.get("transition")):
            glitch_count += 1
        last_card, last_end = event.get("card"), start + event_duration
    if glitch_count > 1:
        bad.append("glitch used more than once")
    return bad


def _validate_energy_curve(curve: list[dict], duration: float) -> list[str]:
    if not curve:
        return ["missing energy curve"]
    bad, cursor = [], 0.0
    for act in curve:
        if abs(float(act["start"]) - cursor) > .01:
            bad.append("energy curve gap @%.2f" % cursor)
        if not 0 <= float(act["energy"]) <= 1:
            bad.append("energy outside 0..1")
        cursor = float(act["end"])
    if abs(cursor - duration) > .02:
        bad.append("energy curve does not end at duration")
    named = {act["name"]: act for act in curve}
    if "breath" not in named or "payoff" not in named:
        bad.append("missing breath/payoff")
    elif float(named["payoff"]["energy"]) <= float(named["breath"]["energy"]):
        bad.append("payoff must exceed breath energy")
    elif abs(float(named["breath"]["end"]) - float(named["payoff"]["start"])) > .02:
        bad.append("breath must lead directly into payoff")
    return bad


def _validate_motion(plan: dict, expected_aspect: str) -> list[str]:
    bad, motion = [], plan.get("motion_assets") or {}
    if motion.get("aspect") != expected_aspect:
        bad.append("motion asset aspect mismatch")
    cues = motion.get("cues") or []
    if sum(cue.get("role") == "transition" for cue in cues) > 2:
        bad.append("too many motion transitions")
    if sum(cue.get("role") == "overlay" for cue in cues) > 2:
        bad.append("too many motion overlays")
    if any(not cue.get("asset_id") or not cue.get("path") for cue in cues):
        bad.append("motion cue missing asset reference")
    return bad


def _validate_template_system(plan: dict, expected_aspect: str) -> list[str]:
    bad, templates = [], plan.get("template_system") or {}
    if templates.get("style") not in EDITORIAL_STYLES:
        bad.append("unknown editorial template style")
    if templates.get("aspect") != expected_aspect:
        bad.append("editorial template aspect mismatch")
    if not templates.get("roles"):
        bad.append("missing editorial template roles")
    program = templates.get("program") or {}
    if templates.get("compiler") != "hao-template-compiler-v2":
        bad.append("missing component template compiler")
    program_format = "shorts" if plan.get("format") == "short" else "longform"
    if not program.get("plans") or program.get("format") != program_format:
        bad.append("missing or mismatched template program")
    if len(program.get("signatures") or []) != len(set(program.get("signatures") or [])):
        bad.append("template program repeats a fatigued signature")
    if any((row.get("render_adapter") or {}).get("full_screen_card")
           for row in program.get("plans") or []):
        bad.append("generic full-screen template scene is forbidden")
    return bad


def _validate_aesthetic_system(plan: dict) -> list[str]:
    bad, system = [], plan.get("aesthetic_system") or {}
    if system.get("standard_id") != "hao-aesthetic-standard":
        bad.append("missing Hao aesthetic standard")
    if not system.get("primary_family") or not system.get("allowed_templates"):
        bad.append("incomplete aesthetic style route")
    style = (plan.get("template_system") or {}).get("style")
    if style not in (system.get("allowed_templates") or []):
        bad.append("template style is outside aesthetic domain route")
    if not (system.get("format_rule") or {}).get("rule"):
        bad.append("missing format-specific aesthetic rule")
    required = {"mrbeast_information_energy", "yingshi_hurricane_cinematic_craft"}
    if set(system.get("formal_benchmarks") or []) != required:
        bad.append("both MrBeast and 影視颶風 benchmarks are required")
    if not system.get("parity_claim_policy"):
        bad.append("missing effect parity claim policy")
    craft = plan.get("mediastorm_craft") or {}
    if craft.get("system") != "hao-mediastorm-craft-v1":
        bad.append("missing evidence-gated 影視颶風 craft planner")
    transitions = (craft.get("editing") or {}).get("transitions") or []
    if any(row.get("status") == "READY" and row.get("missing") for row in transitions):
        bad.append("影視颶風 transition claims READY without evidence")
    if any(row.get("selected") != "clean_cut" for row in transitions):
        bad.append("visual planning cannot approve expressive transitions before shot-pair evidence")
    compiled = plan.get("design_system_v6") or {}
    if compiled.get("compiler") != "hao-design-system-v6":
        bad.append("missing v6 design DNA compiler")
    if (compiled.get("source") or {}).get("reference_count") != 47:
        bad.append("v6 design DNA must route all 47 abstract references")
    if (compiled.get("route") or {}).get("primary_family") != system.get("primary_family"):
        bad.append("v6 design route disagrees with aesthetic system")
    information = plan.get("high_information_system") or {}
    if information.get("system") != "hao-high-information-editing-v1":
        bad.append("missing evidence-gated high-information editing system")
    if information.get("selected"):
        bad.append("visual director cannot preselect effects before evidence exists")
    system_3d = plan.get("three_d_system") or {}
    if system_3d.get("system") != "hao-3d-system-v1":
        bad.append("missing 3D capability route")
    if system_3d.get("status") == "READY" and system_3d.get("missing"):
        bad.append("3D route claims READY with missing prerequisites")
    if not system_3d.get("truth_boundary"):
        bad.append("3D route missing truth boundary")
    return bad


def _validate_budget_reference(data: dict | None, *, expected: str,
                               path_error: str, budget_error: str) -> list[str]:
    if not data:
        return []
    bad = []
    if data.get("packet", data.get("plan")) != expected:
        bad.append(path_error)
    if int(data.get("estimated_tokens", 10**9)) > int(data.get("max_tokens", 0)):
        bad.append(budget_error)
    return bad


def validate_visual_plan(plan: dict) -> list[str]:
    bad, duration = [], float(plan.get("duration", 0))
    if plan.get("domain", plan.get("genre")) not in PROFILES:
        bad.append("unknown domain")
    if plan.get("theme") not in THEMES:
        bad.append("unknown theme")
    bad.extend(_validate_events(plan.get("events", []), duration))
    bad.extend(_validate_energy_curve(plan.get("energy_curve") or [], duration))
    if any(len(seq.get("shot_pattern") or []) < 3
           for seq in plan.get("sequence_plan") or []):
        bad.append("shot sequence has fewer than 3 functions")
    expected_aspect = "portrait" if plan.get("format") == "short" else "landscape"
    bad.extend(_validate_motion(plan, expected_aspect))
    bad.extend(_validate_template_system(plan, expected_aspect))
    bad.extend(_validate_aesthetic_system(plan))
    color = plan.get("color_system") or {}
    if not color.get("profile") or not color.get("one_look_only"):
        bad.append("missing single-look color system")
    if color.get("stage") != "source_before_graphics":
        bad.append("color grade must run before graphics")
    if float(color.get("base_strength", 1.0)) > float(color.get("max_strength", 0.0)):
        bad.append("color grade strength exceeds profile ceiling")
    trend = plan.get("trend_system") or {}
    if not trend.get("dominant_signal") or not trend.get("limit"):
        bad.append("missing restrained trend route")
    filters = plan.get("filter_system") or {}
    if filters.get("scope") != "all_formats_all_domains":
        bad.append("filter library must apply to every format and domain")
    if filters.get("grade") != color.get("profile"):
        bad.append("filter grade route must match the single-look color system")
    if filters.get("auto_selected"):
        bad.append("filter candidates cannot auto-select without shot evidence")
    bad.extend(validate_caption_system(plan.get("caption_system") or {}, duration))
    bad.extend(validate_shot_dynamics_system(plan.get("shot_dynamics_system") or {}, duration))
    runtime = plan.get("programmatic_runtime") or {}
    if runtime.get("schema") != "hao.motion-composition/v1":
        bad.append("missing canonical programmatic composition schema")
    if runtime.get("implementation") != "self_authored":
        bad.append("programmatic runtime must be self-authored")
    if runtime.get("scope") != "all_formats_all_domains":
        bad.append("programmatic runtime must apply to every format and domain")
    if runtime.get("third_party_video_frameworks") != "benchmark_only_not_runtime_dependencies":
        bad.append("third-party video frameworks may only be benchmarks")
    bad.extend(_validate_budget_reference(
        plan.get("context_budget"), expected=PACKET_NAME,
        path_error="context packet must use stable current path",
        budget_error="context packet exceeds token budget",
    ))
    bad.extend(_validate_budget_reference(
        plan.get("asset_intelligence"), expected=ASSET_PLAN_NAME,
        path_error="asset plan must use stable current path",
        budget_error="asset plan exceeds token budget",
    ))
    return bad


def write_visual_plan(path: str, **kwargs) -> dict:
    plan = plan_visual_rhythm(**kwargs)
    output_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(output_dir, exist_ok=True)
    if plan["format"] == "longform":
        from longform_maker.emphasis_overlays import build_emphasis_overlay_ass
        overlay_name = "current_emphasis_overlays.ass"
        build_emphasis_overlay_ass(
            plan["caption_system"].get("emphasis_overlays") or [],
            os.path.join(output_dir, overlay_name),
        )
        plan["caption_system"]["emphasis_overlay_ass"] = overlay_name
    context = write_context_packet(
        output_dir,
        mode="build",
        format="shorts" if plan["format"] == "short" else "longform",
        domain=plan["domain"],
        topic=kwargs.get("context_text", ""),
    )
    plan["context_budget"] = {
        "packet": PACKET_NAME,
        "estimated_tokens": context["budget"]["estimated_tokens"],
        "max_tokens": context["budget"]["max_tokens"],
        "cache_hit": context["runtime"]["cache_hit"],
    }
    asset_plan = write_asset_plan(
        output_dir,
        topic=kwargs.get("context_text", "") or plan["domain"],
        domain=plan["domain"],
        format="shorts" if plan["format"] == "short" else "longform",
        duration=plan["duration"],
        cues=kwargs.get("captions"),
        energy_curve=plan["energy_curve"],
    )
    selected_music = (asset_plan.get("music") or {}).get("selected") or {}
    plan["asset_intelligence"] = {
        "plan": ASSET_PLAN_NAME,
        "selected_bgm": selected_music.get("path"),
        "music_strategy": (asset_plan.get("music") or {}).get("strategy"),
        "cue_count": len(asset_plan.get("cues") or []),
        "registry_counts": asset_plan.get("registry_counts", {}),
        "estimated_tokens": asset_plan["token_budget"]["estimated_tokens"],
        "max_tokens": asset_plan["token_budget"]["max_tokens"],
        "cache_hit": asset_plan["runtime"]["cache_hit"],
    }
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
    errors = validate_visual_plan(plan)
    if errors:
        raise AssertionError("visual plan invalid after context routing: " + "; ".join(errors))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return plan


def _self_test() -> None:
    caps = [(0, 2, "AI 教學先看結果"), (7, 9, "為什麼會失敗"), (15, 17, "三個步驟")]
    a = plan_visual_rhythm(28, caps, "auto", seed=7)
    b = plan_visual_rhythm(28, caps, "auto", seed=7)
    assert a == b and a["domain"] == "ai" and a["version"] == 9
    assert a["template_system"]["style"] == "cyan_lab"
    assert a["aesthetic_system"]["primary_family"] == "cobalt_lime_ui"
    assert a["caption_system"]["profile"] == "shorts_semantic_kinetic"
    assert a["color_system"]["profile"] == "ai_cobalt_crisp"
    assert a["color_system"]["stage"] == "source_before_graphics"
    assert a["trend_system"]["dominant_signal"] == "connectioneering"
    assert a["high_information_system"]["status"] == "AWAITING_EVIDENCE"
    assert a["three_d_system"]["status"] == "DOWNGRADED"
    assert a["programmatic_runtime"]["scope"] == "all_formats_all_domains"
    assert a["programmatic_runtime"]["implementation"] == "self_authored"
    assert a["three_d_system"]["requested_route"] == "data_space"
    assert not validate_visual_plan(a)
    assert infer_domain("拉麵只要 150 元") == "food"
    food = plan_visual_rhythm(28, [(0, 2, "傳統海鮮湯麵")], "food", seed=8)
    assert food["template_system"]["style"] == "food_heritage"
    toy = plan_visual_rhythm(28, [(0, 2, "戰鬥陀螺對決")], "toy", seed=9)
    assert toy["three_d_system"]["requested_route"] == "product_turntable"
    assert toy["three_d_system"]["effective_route"] == "verified_multiview_2d"
    assert infer_domain("重機試駕與過彎") == "automotive"
    assert infer_domain("與創辦人深度訪談") == "interview"
    interview = PROFILES["interview"]
    interview_blob = repr(interview)
    assert "two_shot" not in interview_blob and "speaker_close" not in interview_blob
    assert "approved_source" in interview_blob and "reaction face" in interview_blob
    assert infer_domain("手機相機盲測評測") == "product"
    long_plan = plan_visual_rhythm(240, [(0, 3, "紀錄片人物故事")], "documentary", seed=2)
    acts = {x["name"]: x for x in long_plan["energy_curve"]}
    assert long_plan["format"] == "longform" and acts["payoff"]["energy"] > acts["breath"]["energy"]
    assert long_plan["caption_system"]["profile"] == "longform_clean_locked"
    assert all(event["mode"] == "clean" for event in long_plan["caption_system"]["events"])
    value_plan = plan_visual_rhythm(
        45, [(0, 2, "$1 BILLION"), (8, 10, "$50 MILLION"), (13, 15, "$300 MILLION")],
        "business", seed="value-ladder",
    )
    assert value_plan["shot_dynamics_system"]["value_particle_overlay"]["enabled"]
    assert value_plan["shot_dynamics_system"]["value_particle_overlay"]["is_transition"] is False
    assert value_plan["shot_dynamics_system"]["value_ladder"]["beat_count"] == 3
    for key in PROFILES:
        p = plan_visual_rhythm(42, [(4, 7, "問題與結果"), (25, 28, "最後實測")], key, seed=key)
        assert p["domain"] == key and p["theme"] in THEMES and not validate_visual_plan(p)
    with tempfile.TemporaryDirectory(prefix="visual-assets-") as temp_dir:
        output = os.path.join(temp_dir, "visual_plan.json")
        integrated = write_visual_plan(
            output, duration=24, captions=caps, genre="food", format="shorts",
            context_text="拉麵實測", seed="asset-hub",
        )
        assert integrated["programmatic_runtime"]["status"] == "GREEN"
        assert os.path.isfile(os.path.join(temp_dir, "current_composition.json"))
        assert os.path.isfile(os.path.join(temp_dir, "current_render_graph.json"))
        assert integrated["asset_intelligence"]["plan"] == ASSET_PLAN_NAME
        assert os.path.isfile(os.path.join(temp_dir, ASSET_PLAN_NAME))
        assert os.path.isfile(os.path.join(temp_dir, PACKET_NAME))
        long_output = os.path.join(temp_dir, "long_visual_plan.json")
        long_integrated = write_visual_plan(
            long_output, duration=120,
            captions=[{"start": 1, "end": 3, "text": "累積 270萬 瀏覽", "kind": "main"}],
            genre="ai", format="longform", context_text="AI 教學成果", seed="long-caption",
        )
        assert long_integrated["caption_system"]["emphasis_overlay_ass"] == \
            "current_emphasis_overlays.ass"
        assert os.path.isfile(os.path.join(temp_dir, "current_emphasis_overlays.ass"))
    print("visual_director self-test OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--genre", default="ai")
    ap.add_argument("--format", default="auto")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    _self_test()
    plan = plan_visual_rhythm(args.duration, genre=args.genre, format=args.format, seed="cli")
    if args.out:
        write_visual_plan(args.out, duration=args.duration, genre=args.genre,
                          format=args.format, seed="cli")
        print("visual plan ->", args.out)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
