# -*- coding: utf-8 -*-
"""Small pure helpers extracted from visual_director for readable orchestration."""
from __future__ import annotations

import random

from visual_profiles import PROFILES, SEMANTIC_CARDS


_CARD_ROLE_MAP = {
    "price": "stat", "score": "stat", "proof": "stat", "steps": "steps",
    "question": "quote", "quote": "quote", "chapter": "chapter",
    "location": "lower_third", "route": "chapter", "verdict": "chapter",
}


def template_roles(events: list[dict]) -> list[str]:
    roles = []
    for event in events:
        role = _CARD_ROLE_MAP.get(str(event.get("card", "")), "hook")
        if role not in roles:
            roles.append(role)
    return roles or ["hook", "chapter"]


def audio_plan(curve: list[dict], profile: dict, rng: random.Random) -> dict:
    breath = next(a for a in curve if a["name"] == "breath")
    payoff = next(a for a in curve if a["name"] == "payoff")
    turn = next((a for a in curve if a["name"] in ("turn", "build_2")), payoff)
    silence_dur = min(.72, max(.24, (breath["end"] - breath["start"]) * .24))
    return {
        "layers": ["dialogue_or_production", "room_tone", "subject_foley", "music"],
        "domain_details": list(profile["sound"]),
        "bridges": [
            {"t": round(turn["start"], 2), "kind": "J-cut", "lead_sec": round(rng.uniform(.28, .62), 2),
             "purpose": "讓下一場先被聽見，再換畫面", "status": "AWAITING_EVIDENCE",
             "requires": ["incoming_audio_clean", "dialogue_or_ambient_motivates_next_scene"],
             "fallback": "clean_cut"},
            {"t": round(payoff["end"], 2), "kind": "L-cut", "tail_sec": round(rng.uniform(.35, .85), 2),
             "purpose": "讓 payoff 的聲音帶入反應／餘韻", "status": "AWAITING_EVIDENCE",
             "requires": ["outgoing_audio_clean", "audio_tail_has_semantic_value"],
             "fallback": "clean_cut"},
        ],
        "pre_payoff_space": {
            "start": round(max(breath["start"], payoff["start"] - silence_dur), 2),
            "end": round(payoff["start"], 2), "music_db_delta": -8,
            "keep": "room_tone_or_breath", "purpose": "先縮音樂，再讓 payoff 變大",
        },
        "music_energy_curve": [{"start": a["start"], "end": a["end"], "energy": a["energy"]}
                               for a in curve],
    }


def visual_guardrails(domain: str) -> list[str]:
    sentence_group = (
        "同一組句至少包含 proof／context／detail 三種功能；不得用人物反應鏡頭補洞"
        if domain == "interview" else
        "同一組句至少包含 wide／medium／detail 或 reaction 三種功能"
    )
    domain_rule = (
        "no_face_documentary：禁人物臉、AI 頭像、剪影、reaction face；純波形滿版不超過 3 秒"
        if domain == "interview" else
        "人物、產品、HUD、操作與 proof 不得被裝飾層遮擋"
    )
    return [
        "畫面先回答旁白，裝飾永遠第二順位",
        "每次切鏡必須由情緒、資訊、動作、視線或聲音之一驅動",
        "品牌字型感、原創 Logo、粗描邊與卡通貼紙感可依題材使用，不是全域禁令",
        sentence_group,
        "音畫不要每刀一起硬切；章節與場景優先用 J-cut／L-cut",
        "高能效果後至少留一個乾淨鏡頭；payoff 前保留短呼吸",
        "glitch 全片最多一次；字卡不可等距出現；同卡型不可連發",
        "字幕白為主、題材色只標重點；真實現場聲優先於罐頭 whoosh",
        domain_rule,
    ]
