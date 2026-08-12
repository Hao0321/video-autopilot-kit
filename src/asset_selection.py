# -*- coding: utf-8 -*-
"""Ranking, selection and release audit for the virtual asset registry."""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable

from asset_registry_shared import DOMAIN_FOLEY, SFX_SYNONYMS, _compact_candidate, _terms
from domain_taxonomy import SUPPORTED_DOMAINS, infer_domain


def _read_json_from_text(text: str) -> dict:
    try:
        return json.loads(text or "{}")
    except ValueError:
        return {}


class AssetSelectionMixin:
    """Score the loaded catalog and enforce asset quality gates."""

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(row["category"] for row in self.records).items()))

    def _rank_visual(self, category: str, query: str, domain: str, aspect: str,
                     energy: float, roles: set[str] | None = None, limit: int = 3) -> list[dict]:
        query_terms = _terms(query)
        ranked = []
        for row in self.records:
            if row["category"] != category or not row.get("selectable") or not row.get("exists"):
                continue
            if roles and row.get("role") not in roles:
                continue
            score, reasons = 0.0, []
            if domain in row.get("domains", []) or "general" in row.get("domains", []):
                score += 4.5 if domain in row.get("domains", []) else 1.0
                reasons.append("題材相符" if domain in row.get("domains", []) else "通用")
            row_aspect = row.get("aspect", "any")
            if row_aspect in {"any", "square", aspect}:
                score += 2.0
                reasons.append("畫幅相符")
            else:
                score -= 4.0
                reasons.append("需安全重構")
            semantic = " ".join([str(row.get("description", "")), " ".join(map(str, row.get("tags", [])))])
            overlap = query_terms.intersection(_terms(semantic))
            if overlap:
                score += min(8.0, 2.0 * len(overlap))
                reasons.append("語意:" + "/".join(sorted(overlap, key=len, reverse=True)[:2]))
            closeness = 1.0 - min(1.0, abs(float(row.get("energy", .5)) - float(energy)))
            score += 2.0 * closeness
            if row.get("semantic_verified"):
                score += .5
            repeat = int(row.get("recent_use_count", 0))
            fatigue = float(row.get("fatigue_score", 0))
            if repeat or fatigue:
                score -= min(5.0, 4.5 * fatigue + .18 * repeat)
                reasons.append("近期重用扣分")
            confidence = max(0.0, min(1.0, score / 16.0))
            ranked.append((_compact_candidate(row, score, confidence, reasons), row_aspect))
        ranked.sort(key=lambda pair: (-pair[0]["score"], pair[0]["path"]))
        return [item for item, _aspect_name in ranked[:limit]]

    def select_broll(self, cue: str, domain: str = "auto", aspect: str = "landscape",
                     energy: float = .5, limit: int = 3) -> list[dict]:
        domain = infer_domain(cue, domain)
        return self._rank_visual("broll", cue, domain, aspect, energy, {"broll"}, limit)

    def select_motion(self, cue: str, domain: str = "auto", aspect: str = "landscape",
                      energy: float = .5, roles: Iterable[str] = ("background", "title_bed"),
                      limit: int = 3) -> list[dict]:
        domain = infer_domain(cue, domain)
        return self._rank_visual("motion", cue, domain, aspect, energy, set(roles), limit)

    def select_template(self, cue: str, domain: str = "auto", aspect: str = "landscape",
                        role: str = "background", energy: float = .5, limit: int = 2) -> list[dict]:
        domain = infer_domain(cue, domain)
        return self._rank_visual("template", cue, domain, aspect, energy, {role}, limit)

    def select_text_overlay(self, cue: str, domain: str = "auto",
                            energy: float = .9, limit: int = 2) -> list[dict]:
        """Select transparent glossy-glow words for high-value semantic beats."""
        domain = infer_domain(cue, domain)
        semantic_alias = "glow_focus 重點"
        for pattern, alias in (
            (r"\bVS\b|對決|對打", "glow_versus VS"),
            (r"失敗|輸|錯誤", "glow_fail 失敗"),
            (r"成功|贏|通過|完成", "glow_success 成功"),
            (r"揭曉|公布|答案", "glow_reveal 揭曉"),
            (r"倍|加速|更快", "glow_speed 快 3 倍"),
            (r"結果|結論", "glow_result 結果"),
            (r"\bAI\b|人工智慧", "glow_ai AI"),
        ):
            if re.search(pattern, str(cue or ""), re.I):
                semantic_alias = alias
                break
        ranked = self._rank_visual("text_overlay", str(cue or "") + " " + semantic_alias,
                                   domain, "any", energy, {"text_overlay"}, max(limit, 8))
        target = semantic_alias.split()[0].removeprefix("glow_")
        preferred = [item for item in ranked if target in Path(item["path"]).stem.lower()]
        preferred.sort(key=lambda item: (-item["score"], item["path"]))
        return preferred[:limit]

    def select_particle_source(self, cue: str, domain: str = "auto",
                               energy: float = .9, limit: int = 2) -> list[dict]:
        """Select semantic particle sources; currently money is never generic confetti."""
        domain = infer_domain(cue, domain)
        if not re.search(r"[$＄]|美元|美金|\bUSD\b|\bdollars?\b", str(cue or ""), re.I):
            return []
        return self._rank_visual(
            "particle_source", str(cue or "") + " USD dollar money value price prize",
            domain, "any", energy, {"value_particle_overlay"}, limit,
        )

    def select_sfx(self, cue: str, domain: str = "auto", energy: float = .5,
                   limit: int = 2) -> list[dict]:
        domain = infer_domain(cue, domain)
        text = str(cue or "").lower()
        wanted = set(DOMAIN_FOLEY.get(domain, ()))
        for family, words in SFX_SYNONYMS.items():
            if any(word in text for word in words):
                wanted.add(family)
        ranked = []
        for row in self.records:
            if row["category"] != "sfx" or not row.get("exists"):
                continue
            family = str(row.get("role", ""))
            semantic = " ".join([family, str(row.get("description", "")), " ".join(map(str, row.get("tags", [])))])
            overlap = _terms(" ".join(wanted) + " " + text).intersection(_terms(semantic))
            score = min(8.0, 2.5 * len(overlap))
            reasons = ["音效語意:" + "/".join(sorted(overlap)[:2])] if overlap else []
            score += 1.5 * (1 - min(1.0, abs(float(row.get("energy", .5)) - energy)))
            repeat = int(row.get("recent_use_count", 0))
            score -= min(2.5, 2.2 * float(row.get("fatigue_score", 0)) + .12 * repeat)
            if score <= 1.6:
                continue
            ranked.append(_compact_candidate(row, score, min(1.0, score / 9.0), reasons or ["能量相符"]))
        ranked.sort(key=lambda item: (-item["score"], item["path"]))
        return ranked[:limit]

    def select_music(self, topic: str, domain: str = "auto", duration: float = 30.0,
                     energy: float = .55, mood: str = "auto", format: str = "shorts",
                     limit: int = 3) -> list[dict]:
        domain = infer_domain(topic, domain)
        target_bpm = 72 + 66 * float(energy) + (8 if format in {"short", "shorts", "portrait"} else 0)
        ranked = []
        for row in self.records:
            if row["category"] != "bgm" or not row.get("exists"):
                continue
            score, reasons = 0.0, []
            if domain in row.get("domains", []):
                score += 6.0
                reasons.append("題材相符")
            elif "general" in row.get("domains", []):
                score += 2.0
                reasons.append("通用備選")
            try:
                bpm = float(row.get("bpm"))
                score += 2.0 * (1 - min(1.0, abs(bpm - target_bpm) / 55.0))
                reasons.append("BPM %.0f" % bpm)
            except (TypeError, ValueError):
                score -= .5
            score += 2.0 * (1 - min(1.0, abs(float(row.get("energy", .5)) - float(energy))))
            track_mood = row.get("mood", "balanced")
            if mood != "auto" and mood == track_mood:
                score += 1.5
                reasons.append("情緒相符")
            track_dur = float(row.get("duration_sec") or 0)
            if track_dur >= float(duration) + 1:
                score += 2.0
                reasons.append("足長免 loop")
            elif track_dur:
                score -= 1.2
                reasons.append("需 playlist")
            repeat = int(row.get("recent_use_count", 0))
            fatigue = float(row.get("fatigue_score", 0))
            if repeat or fatigue:
                score -= min(5.0, 4.6 * fatigue + .18 * repeat)
                reasons.append("近期重用扣分")
            item = _compact_candidate(row, score, max(0.0, min(1.0, score / 13.5)), reasons)
            item.update({"bpm": row.get("bpm"), "duration_sec": row.get("duration_sec"),
                         "mood": track_mood, "scene": row.get("scene")})
            ranked.append(item)
        ranked.sort(key=lambda item: (-item["score"], item["path"]))
        return ranked[:limit]

    def audit(self, full: bool = False, release: bool = False) -> dict:
        errors, warnings = [], []
        selectable = [r for r in self.records if r.get("selectable")]
        missing = [r["path"] for r in selectable if not r.get("exists")]
        absolute = [r["path"] for r in self.records if Path(r["path"]).is_absolute()]
        duplicate_ids = [key for key, count in Counter(r["asset_id"] for r in self.records).items() if count > 1]
        if missing:
            errors.append(f"{len(missing)} selectable paths missing")
        if absolute:
            errors.append(f"{len(absolute)} canonical paths are absolute")
        if duplicate_ids:
            errors.append(f"{len(duplicate_ids)} duplicate asset IDs")
        if not any(r["category"] == "bgm" for r in selectable):
            errors.append("no selectable BGM")
        if not any(r["category"] == "broll" for r in selectable):
            errors.append("no selectable B-roll")

        unknown = Counter(r["category"] for r in selectable
                          if r.get("license") == "unknown" or str(r.get("license", "")).startswith("pending"))
        if unknown:
            warnings.append("license/provenance pending: " + ", ".join(f"{k}={v}" for k, v in sorted(unknown.items())))
        inventory_only = sum(r.get("metadata_origin") == "inventory" for r in selectable)
        if inventory_only:
            warnings.append(f"{inventory_only} selectable assets only have inventory metadata")
        coverage = {domain: sum(r["category"] == "broll" and domain in r.get("domains", [])
                                for r in selectable) for domain in SUPPORTED_DOMAINS}
        gaps = [domain for domain, count in coverage.items() if domain != "general" and count == 0]
        if gaps:
            warnings.append("true B-roll coverage gaps: " + ", ".join(gaps))

        if full:
            for row in selectable:
                if row["category"] != "sfx" or Path(row["path"]).suffix.lower() != ".wav":
                    continue
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "a:0",
                     "-show_entries", "stream=codec_name,sample_rate", "-of", "json",
                     str(self._absolute(row["path"]))], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
                data = _read_json_from_text(probe.stdout)
                stream = (data.get("streams") or [{}])[0]
                if probe.returncode or stream.get("sample_rate") != "48000" or not str(stream.get("codec_name", "")).startswith("pcm_"):
                    errors.append("SFX must be 48k PCM: " + row["path"])

        if release:
            public = [r for r in selectable if r["path"].startswith("community/hao-motion-kit/")
                      or r.get("release_candidate")]
            bad_public = [r["path"] for r in public
                          if r.get("license") == "unknown"
                          or str(r.get("license", "")).startswith("pending")
                          or r.get("provenance") == "unknown"]
            if bad_public:
                errors.append(f"{len(bad_public)} release-candidate assets lack a final license/provenance")

        return {
            "status": "GREEN" if not errors else "RED", "schema_version": 1,
            "counts": self.counts(), "selectable": len(selectable), "coverage": coverage,
            "errors": errors, "warnings": warnings,
        }
