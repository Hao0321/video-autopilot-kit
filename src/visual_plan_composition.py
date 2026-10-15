"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import random
from art_direction import resolve_theme
from aesthetic_score import resolve_style_route
from design_system_v6 import compile_recipe as compile_design_recipe
from mrbeast_editing_system import plan_sequence as plan_information_sequence
from three_d_system import plan_3d
from camera_transition_director import plan_shot_dynamics_system
from caption_director import plan_caption_system
from domain_taxonomy import infer_domain as infer_taxonomy_domain
from editorial_templates import resolve_style as resolve_editorial_style
from motion_asset_pack import plan_asset_cues
from template_compiler import compile_template_program
from mediastorm_craft import apply_transition_decisions, compile_craft_plan
from visual_style_router import plan_color_system, plan_filter_system, plan_trend_system
from visual_plan_support import audio_plan as _audio_plan, PROFILES, SEMANTIC_CARDS, shot_selection_policy, template_roles as _template_roles, visual_guardrails as _visual_guardrails
from visual_plan_validation import validate_visual_plan


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
            "parity_claim_policy": "只對有參考時間碼、素材前提、輸出、逐幀 QA 與 creator 審片的單一效果宣稱功能對等；禁止籠統宣稱全部 100% 複製。",
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


def _plan_information_and_3d(domain, format_kind):
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
    return high_information_system, three_d_system


def plan_visual_rhythm(duration: float, captions=None, genre: str = "auto", seed: object = 0,
                       format: str = "auto", context_text: str = "",
                       color_profile: str | None = None,
                       color_strength: float | None = None,
                       shot_style: str = "auto") -> dict:
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
    high_information_system, three_d_system = _plan_information_and_3d(domain, format_kind)
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
    # Style is a story choice, separate from topic/domain. Captions cannot
    # prove facial reactions, camera movement, available audio, or source rights.
    plan["shot_selection"] = shot_selection_policy(shot_style)
    errors = validate_visual_plan(plan)
    if errors:
        raise AssertionError("visual plan invalid: " + "; ".join(errors))
    return plan
