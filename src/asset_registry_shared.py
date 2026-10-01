# -*- coding: utf-8 -*-
"""Shared constants and pure helpers for asset intelligence."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable

from domain_taxonomy import infer_domain
from project_paths import discover_project_root


SKILL_ROOT = Path(__file__).resolve().parent
PLAN_NAME = "current_asset_plan.json"
DEFAULT_PLAN_TOKENS = 1200
MEDIA_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

BGM_SCENE_DOMAINS = {
    "教學": ("ai", "business", "product"),
    "美食": ("food",), "咖啡廳甜點": ("cafe", "food"), "家常料理": ("food",),
    "夜市文化": ("food", "travel"), "夜市老街傳統文化": ("food", "travel"),
    "旅遊": ("travel",), "散步": ("travel",), "走路散步": ("travel",),
    "出國": ("travel",), "度假": ("travel",), "露營": ("travel", "nature"),
    "海洋": ("travel", "nature"), "森林": ("nature", "travel"),
    "森林自然": ("nature", "travel"),
    "登山": ("fitness", "travel", "nature"), "登山健行": ("fitness", "travel", "nature"),
    "美術館": ("travel", "documentary", "architecture"),
    "美術館展覽": ("travel", "documentary", "architecture"),
    "玩具": ("toy", "product", "diy"), "玩具開箱": ("toy", "product", "diy"),
    "_通用": ("general",),
}

DOMAIN_FOLEY = {
    "ai": ("clean_click", "keyboard", "ui_tick"),
    "food": ("sizzle", "knife", "crunch", "room_tone"),
    "travel": ("footstep", "transport", "crowd", "wild_track"),
    "product": ("button", "material_touch", "mechanical", "proof_tick"),
    "toy": ("package", "snap", "plastic", "reveal_hit"),
    "game": ("gameplay", "impact", "reaction"),
    "diy": ("tool", "material_contact", "completion_hit"),
    "cafe": ("pour", "cup", "steam", "quiet_room"),
    "documentary": ("location_tone", "cloth", "footstep"),
    "interview": ("room_tone", "cloth", "chair"),
    "automotive": ("engine", "wind", "gear", "road"),
    "fitness": ("breath", "footfall", "equipment", "impact"),
    "fashion": ("fabric", "step", "zip", "camera"),
    "architecture": ("room_tone", "footstep", "door", "city"),
    "business": ("tick", "paper", "keyboard", "impact"),
    "nature": ("wild_track", "wind", "water", "animal"),
    "music": ("audience", "stage", "room_tone"),
    "general": ("room_tone", "whoosh", "hit", "tick"),
}

SFX_SYNONYMS = {
    "whoosh": ("whoosh", "swoosh", "轉場", "滑入", "飛入"),
    "hit": ("hit", "impact", "重擊", "落點", "強調", "reveal"),
    "pop": ("pop", "彈出", "貼圖", "出現"),
    "riser": ("riser", "build", "升起", "揭曉", "轉折"),
    "tick": ("tick", "click", "勾選", "按鈕", "計時", "proof"),
}


def _resolve_project_root(start: Path | None = None) -> Path:
    return discover_project_root(start or Path(__file__))


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _estimate_tokens(value) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", text))
    return cjk + math.ceil(max(0, len(text) - cjk) / 4)


def _stable_id(category: str, path: str) -> str:
    digest = hashlib.sha1((category + ":" + path.lower()).encode("utf-8")).hexdigest()[:12]
    return f"{category}:{digest}"


def _resolution(value) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
    match = re.search(r"(\d{2,5})\s*[xX×]\s*(\d{2,5})", str(value or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def _aspect(value) -> str:
    size = _resolution(value)
    if not size:
        return "any"
    width, height = size
    if abs(width - height) / max(width, height) < .08:
        return "square"
    return "landscape" if width > height else "portrait"


def _scene_domains(scene: str) -> list[str]:
    if scene in BGM_SCENE_DOMAINS:
        return list(BGM_SCENE_DOMAINS[scene])
    domain = infer_domain(scene)
    return [domain]


def recommend_bgm_scene(domain: str, topic: str = "") -> str:
    """Return the best existing BGM scene without inspecting audio again."""
    domain = infer_domain(topic, domain)
    priority = {
        "ai": "教學", "food": "美食", "cafe": "咖啡廳甜點", "travel": "旅遊",
        "toy": "玩具開箱", "product": "玩具開箱", "diy": "玩具開箱", "nature": "森林自然",
        "fitness": "登山健行", "architecture": "美術館展覽", "documentary": "美術館展覽",
    }
    return priority.get(domain, "_通用")


def _energy(bpm, rms_db) -> float:
    try:
        bpm_score = min(1.0, max(0.0, (float(bpm) - 65.0) / 85.0))
    except (TypeError, ValueError):
        bpm_score = .5
    try:
        rms_score = min(1.0, max(0.0, (float(rms_db) + 28.0) / 18.0))
    except (TypeError, ValueError):
        rms_score = .5
    return round(.65 * bpm_score + .35 * rms_score, 3)


def _mood(bpm, suggested: str = "") -> str:
    text = str(suggested or "").lower()
    try:
        value = float(bpm)
    except (TypeError, ValueError):
        value = 100.0
    if "high" in text or "reveal" in text or value >= 122:
        return "energetic"
    if value <= 88:
        return "calm"
    return "balanced"


def _terms(text: str) -> set[str]:
    src = str(text or "").lower()
    out = set(re.findall(r"[a-z0-9][a-z0-9_+-]{1,}", src))
    for chunk in re.findall(r"[\u3400-\u9fff]{2,}", src):
        out.add(chunk)
        for n in (2, 3):
            out.update(chunk[i:i + n] for i in range(max(0, len(chunk) - n + 1)))
    return out


def _compact_candidate(record: dict, score: float, confidence: float, reasons: Iterable[str]) -> dict:
    return {
        "asset_id": record["asset_id"], "path": record["path"], "role": record.get("role"),
        "score": round(score, 2), "confidence": round(confidence, 2),
        "reason": "、".join(list(reasons)[:3]),
    }
