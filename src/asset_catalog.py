# -*- coding: utf-8 -*-
"""Manifest and filesystem loaders for the virtual asset registry."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from asset_registry_shared import (
    AUDIO_EXTS, MEDIA_EXTS, _aspect, _energy, _mood, _read_json,
    _resolution, _resolve_project_root, _scene_domains, _stable_id,
)
from domain_taxonomy import DOMAIN_KEYWORDS, infer_domain, normalize_domain
from asset_memory import load_usage_snapshot


class AssetCatalogMixin:
    """Build the canonical virtual catalog without copying any media."""

    def __init__(self, project_root: str | os.PathLike | None = None):
        self.root = Path(project_root).resolve() if project_root else _resolve_project_root()
        self.assets = self.root / "assets"
        self.kit = self.root / "community" / "hao-motion-kit"
        self._by_path: dict[str, dict] = {}
        self.records: list[dict] = []
        self._usage = self._load_usage()
        self.refresh()

    def _canonical_path(self, path: str | os.PathLike) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            return candidate.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(candidate.resolve())

    def _absolute(self, canonical: str) -> Path:
        path = Path(canonical)
        return path if path.is_absolute() else self.root / path

    def _upsert(self, record: dict) -> None:
        path = self._canonical_path(record["path"])
        existing = self._by_path.get(path, {})
        merged = {**existing, **{k: v for k, v in record.items() if v is not None}}
        merged["path"] = path
        self._by_path[path] = merged

    def _load_usage(self) -> dict[str, dict]:
        return load_usage_snapshot(self.root)

    def refresh(self) -> "AssetRegistry":
        self._by_path.clear()
        self._load_broll_and_sfx()
        self._load_support_assets()
        self._load_private_motion()
        self._load_domain_broll()
        self._load_bgm()
        self._load_public_kit()
        self.records = []
        for path, row in sorted(self._by_path.items()):
            row.setdefault("category", "unknown")
            row.setdefault("media_type", "video")
            row.setdefault("role", row["category"])
            row.setdefault("domains", ["general"])
            row["domains"] = list(dict.fromkeys(normalize_domain(x) for x in row["domains"]))
            row.setdefault("tags", [])
            row.setdefault("aspect", "any")
            row.setdefault("energy", .5)
            row.setdefault("loopable", False)
            row.setdefault("license", "unknown")
            row.setdefault("provenance", "unknown")
            row.setdefault("selectable", True)
            row["exists"] = self._absolute(path).is_file()
            row["asset_id"] = _stable_id(row["category"], path)
            usage = self._usage.get(row["asset_id"], {})
            row["recent_use_count"] = int(usage.get("recent_content_count", 0))
            row["usage_streak"] = int(usage.get("consecutive_content_streak", 0))
            row["fatigue_score"] = float(usage.get("fatigue_score", 0))
            row["fatigue_level"] = usage.get("fatigue_level", "low")
            self.records.append(row)
        return self

    def _load_domain_broll(self) -> None:
        """Load original editorial fillers as B-roll, not as transitions/motion beds."""
        manifest_path = self.assets / "broll" / "domain_fill" / "manifest.json"
        manifest = _read_json(manifest_path, {})
        for item in manifest.get("assets", []):
            self._upsert({
                "path": self.root / item.get("path", ""), "category": "broll", "media_type": "video",
                "role": "broll", "description": item.get("usage", item.get("label", "")),
                "tags": list(item.get("tags", [])), "domains": [item.get("domain", "general")],
                "duration_sec": item.get("duration"), "resolution": _resolution(item.get("resolution")),
                "aspect": item.get("aspect", _aspect(item.get("resolution"))), "fps": item.get("fps"),
                "energy": item.get("energy", .5), "loopable": bool(item.get("loop")),
                "license": item.get("license", manifest.get("license", "unknown")),
                "provenance": item.get("provenance", "domain_broll_pack.py"),
                "metadata_origin": "domain-broll-manifest", "semantic_verified": True,
                "release_candidate": True, "selectable": True,
            })

    def _load_broll_and_sfx(self) -> None:
        index = _read_json(self.assets / "index.json", {})
        self._load_index_broll(index)
        self._load_inventory_broll()
        self._load_sfx(index)

    def _load_index_broll(self, index: dict) -> None:
        for rel, meta in index.get("broll_actual", {}).items():
            if rel.startswith("_") or not isinstance(meta, dict):
                continue
            text = " ".join([str(meta.get("desc", "")), " ".join(map(str, meta.get("tags", [])))])
            scores = {d: sum(text.lower().count(k.lower()) for k in keys)
                      for d, keys in DOMAIN_KEYWORDS.items()}
            domains = [d for d, score in scores.items() if score > 0] or [infer_domain(text)]
            source_like = "/_sources/" in ("/" + rel.replace("\\", "/"))
            preview_like = Path(rel).stem.lower() in {"preview", "showreel"}
            generated_motion = rel.replace("\\", "/").startswith("generated/") and \
                Path(rel).suffix.lower() in {".mp4", ".mov", ".webm"}
            self._upsert({
                "path": self.assets / "broll" / rel,
                "category": "source" if source_like else ("motion" if generated_motion else "broll"),
                "media_type": "image" if Path(rel).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else "video",
                "role": "source_master" if source_like else ("preview" if preview_like else
                        ("background" if generated_motion else "broll")),
                "description": meta.get("desc") or Path(rel).stem, "tags": list(meta.get("tags", [])),
                "domains": domains, "duration_sec": meta.get("duration_sec"),
                "resolution": _resolution(meta.get("resolution")), "aspect": _aspect(meta.get("resolution")),
                "fps": meta.get("fps"), "energy": .5,
                "license": meta.get("license", "project-original" if generated_motion else "unknown"),
                "provenance": meta.get("provenance", "assets/broll/generated/_sources" if generated_motion
                                       else "assets/index.json"),
                "semantic_verified": bool(meta.get("desc") and "unknown" not in str(meta.get("desc"))),
                "selectable": not (source_like or preview_like), "metadata_origin": "index",
            })

    def _load_inventory_broll(self) -> None:
        broll_root = self.assets / "broll"
        if not broll_root.is_dir():
            return
        for path in sorted(broll_root.rglob("*")):
            if (not path.is_file() or path.suffix.lower() not in MEDIA_EXTS
                    or self._canonical_path(path) in self._by_path):
                continue
            rel = path.relative_to(broll_root).as_posix()
            source_like = rel.startswith("generated/_sources/")
            preview_like = path.stem.lower() in {"preview", "showreel"}
            generated_motion = rel.startswith("generated/") and path.suffix.lower() in {".mp4", ".mov", ".webm"}
            self._upsert({
                "path": path, "category": "source" if source_like else ("motion" if generated_motion else "broll"),
                "media_type": "image" if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else "video",
                "role": "source_master" if source_like else ("preview" if preview_like else
                        ("background" if generated_motion else "broll")),
                "description": path.stem.replace("_", " "), "domains": [infer_domain(path.stem)],
                "tags": [], "selectable": not (source_like or preview_like),
                "metadata_origin": "inventory", "license": "project-original" if generated_motion else "unknown",
                "provenance": "assets/broll/generated/_sources" if generated_motion else "filesystem inventory",
            })

    def _load_sfx(self, index: dict) -> None:
        for rel, meta in index.get("sfx_actual", {}).items():
            if rel.startswith("_") or not isinstance(meta, dict):
                continue
            family = str(meta.get("family") or Path(rel).stem.split("_")[0]).lower()
            self._upsert({
                "path": self.assets / "sfx" / rel, "category": "sfx", "media_type": "audio",
                "role": family, "description": meta.get("use", family), "tags": [family, meta.get("use", "")],
                "domains": ["general"], "duration_sec": meta.get("duration_sec"), "aspect": "any",
                "energy": .8 if family in {"hit", "riser"} else .5,
                "license": meta.get("license", "unknown"), "provenance": meta.get("provenance", "assets/index.json"),
                "metadata_origin": "index",
            })
        sfx_manifest_path = self.assets / "sfx" / "manifest.json"
        sfx_manifest = _read_json(sfx_manifest_path, {})
        format_gate = sfx_manifest.get("format_gate", {})
        for family, files in sfx_manifest.get("families", {}).items():
            for file_name in files:
                self._upsert({
                    "path": self.assets / "sfx" / file_name, "category": "sfx", "media_type": "audio",
                    "role": family, "domains": ["general"], "aspect": "any",
                    "license": sfx_manifest.get("license_status", "unknown"),
                    "provenance": sfx_manifest.get("provenance", "unknown"),
                    "release_candidate": bool(sfx_manifest.get("release_candidate")),
                    "codec": format_gate.get("codec"), "sample_rate_hz": format_gate.get("sample_rate_hz"),
                    "channels": format_gate.get("channels"), "metadata_origin": "sfx-manifest",
                })

    def _load_support_assets(self) -> None:
        index = _read_json(self.assets / "index.json", {})
        for family, meta in index.get("fonts_actual", {}).items():
            if str(family).startswith("_") or not isinstance(meta, dict):
                continue
            for path in meta.get("files", []):
                self._upsert({
                    "path": path, "category": "font", "media_type": "font", "role": "font_family",
                    "description": family, "tags": list(meta.get("tags", [])) + [meta.get("use_case", "")],
                    "domains": ["general"], "aspect": "any", "selectable": True,
                    "license": meta.get("license", "unknown"), "provenance": meta.get("provenance", "assets/index.json"),
                    "metadata_origin": "index", "family": family,
                })

        faces_path = self.assets / "face" / "faces.json"
        faces = _read_json(faces_path, {})
        usage = faces.get("_usage", {})
        for emotion, file_name in faces.items():
            if str(emotion).startswith("_") or not isinstance(file_name, str):
                continue
            usage_tags = [label for label, key in usage.items() if emotion in str(key).split("|")]
            self._upsert({
                "path": faces_path.parent / file_name, "category": "face", "media_type": "image",
                "role": "thumbnail_reaction", "description": emotion,
                "tags": [emotion] + usage_tags, "domains": ["general"], "aspect": "square",
                "energy": .7 if emotion in {"shocked", "laugh", "frustrated"} else .45,
                "selectable": True, "allowed_formats": ["thumbnail", "reaction_window"],
                "license": "private-user-provided", "provenance": "assets/face/faces.json",
                "metadata_origin": "face-manifest",
            })

    def _load_private_motion(self) -> None:
        manifest_path = self.assets / "broll" / "motion" / "manifest.json"
        manifest = _read_json(manifest_path, {})
        for item in manifest.get("assets", []):
            self._upsert({
                "path": item.get("path"), "category": "motion", "media_type": "video",
                "role": item.get("role", "background"), "description": item.get("usage", item.get("id", "")),
                "tags": list(item.get("tags", [])), "domains": item.get("domains", [item.get("theme", "general")]),
                "duration_sec": item.get("duration"), "resolution": _resolution(item.get("resolution")),
                "aspect": item.get("aspect", _aspect(item.get("resolution"))), "fps": item.get("fps"),
                "energy": item.get("energy", .5), "loopable": bool(item.get("loop")),
                "blend_mode": item.get("blend_mode", "normal"), "guardrail": item.get("guardrail"),
                "license": "project-original", "provenance": str(manifest_path.relative_to(self.root).as_posix()),
                "metadata_origin": "private-motion-manifest", "selectable": True,
            })

    def _load_bgm(self) -> None:
        bgm_root = self.assets / "bgm"
        indexed: set[Path] = set()
        if bgm_root.is_dir():
            for index_path in sorted(bgm_root.rglob("bgm_index.json")):
                data = _read_json(index_path, {})
                scene = index_path.parent.relative_to(bgm_root).as_posix()
                for track in data.get("tracks", []):
                    path = index_path.parent / str(track.get("file", ""))
                    indexed.add(path.resolve())
                    bpm, rms = track.get("bpm"), track.get("rms_db")
                    self._upsert({
                        "path": path, "category": "bgm", "media_type": "audio", "role": "bgm",
                        "description": path.stem, "tags": [scene, track.get("suggested_use", "")],
                        "domains": _scene_domains(scene), "duration_sec": track.get("duration_sec"),
                        "aspect": "any", "bpm": bpm, "rms_db": rms,
                        "energy": _energy(bpm, rms), "mood": _mood(bpm, track.get("suggested_use", "")),
                        "suggested_use": track.get("suggested_use"), "vocal_presence": "unknown",
                        "license": track.get("license", "unknown"), "provenance": track.get("provenance", "unknown"),
                        "metadata_origin": "bgm_index", "scene": scene,
                    })
            for path in sorted(bgm_root.rglob("*")):
                if path.is_file() and path.suffix.lower() in AUDIO_EXTS and path.resolve() not in indexed:
                    scene = path.parent.relative_to(bgm_root).as_posix()
                    self._upsert({
                        "path": path, "category": "bgm", "media_type": "audio", "role": "bgm",
                        "description": path.stem, "tags": [scene], "domains": _scene_domains(scene),
                        "aspect": "any", "license": "unknown", "provenance": "filesystem inventory",
                        "metadata_origin": "inventory", "scene": scene,
                    })

    def _load_motion_manifest(self) -> None:
        manifest_path = self.kit / "manifest.json"
        manifest = _read_json(manifest_path, {})
        for item in manifest.get("assets", []):
            self._upsert({
                "path": self.kit / item.get("package_path", ""), "category": "motion", "media_type": "video",
                "role": item.get("role", "background"), "description": item.get("usage", item.get("label", "")),
                "tags": [item.get("family", ""), item.get("motif", ""), item.get("label", "")],
                "domains": [item.get("domain", "general")], "duration_sec": item.get("duration"),
                "resolution": _resolution(item.get("resolution")), "aspect": item.get("aspect", "any"),
                "fps": item.get("fps"), "energy": item.get("energy", .5), "loopable": bool(item.get("loop")),
                "blend_mode": item.get("blend_mode", "normal"), "license": "CC-BY-4.0",
                "provenance": "community/hao-motion-kit/SOURCE_PROVENANCE.json",
                "metadata_origin": "community-motion-manifest", "selectable": True,
            })

    def _load_template_manifest(self) -> None:
        template_path = self.kit / "templates" / "manifest.json"
        templates = _read_json(template_path, {})
        routing = templates.get("routing", {})
        reverse: dict[str, list[str]] = defaultdict(list)
        for topic, style in routing.items():
            domain = normalize_domain(topic)
            if domain != "general" or topic == "general":
                reverse[style].append(domain)
        for item in templates.get("assets", []):
            style = item.get("style", "shape_play")
            self._upsert({
                "path": self.kit / item.get("package_path", ""), "category": "template", "media_type": "image",
                "role": item.get("role", "background"), "description": style,
                "tags": [style] + list(item.get("topic_examples", [])),
                "domains": reverse.get(style, ["general"]), "resolution": _resolution(item.get("resolution")),
                "aspect": item.get("aspect", "any"), "energy": .5, "loopable": False,
                "style": style, "license": "CC-BY-4.0",
                "provenance": "community/hao-motion-kit/SOURCE_PROVENANCE.json",
                "metadata_origin": "template-manifest", "selectable": True,
            })

    def _load_procedural_glow_manifest(self) -> None:
        glow_path = self.kit / "assets" / "glow_text" / "manifest.json"
        glow = _read_json(glow_path, {})
        for item in glow.get("assets", []):
            self._upsert({
                "path": self.kit / item.get("clip", ""), "category": "text_overlay",
                "media_type": "video", "role": "text_overlay",
                "description": item.get("text", item.get("id", "")),
                "tags": list(item.get("tags", [])) + [item.get("palette", ""), item.get("id", "")],
                "domains": item.get("domains", ["general"]),
                "duration_sec": item.get("duration"),
                "resolution": _resolution(item.get("resolution")), "aspect": "any",
                "fps": item.get("fps"), "energy": .9, "loopable": False,
                "alpha": bool(item.get("alpha")), "codec": item.get("codec"),
                "companion_still": item.get("still"), "license": item.get("license", "CC-BY-4.0"),
                "provenance": "community/hao-motion-kit/SOURCE_PROVENANCE.json",
                "metadata_origin": "procedural-glow-text-manifest",
                "selectable": bool(item.get("selectable", False)),
            })

    def _load_imagegen_glow_manifest(self) -> None:
        imagegen_path = self.kit / "assets" / "glow_text" / "imagegen" / "manifest.json"
        imagegen = _read_json(imagegen_path, {})
        for item in imagegen.get("assets", []):
            self._upsert({
                "path": self.kit / item.get("file", ""), "category": "text_overlay",
                "media_type": "image", "role": "text_overlay",
                "description": item.get("text", item.get("id", "")),
                "tags": list(item.get("tags", [])) + [item.get("id", "")],
                "domains": item.get("domains", ["general"]),
                "resolution": _resolution(item.get("resolution")), "aspect": "any",
                "energy": .96, "loopable": False, "blend_mode": item.get("blend_mode", "screen"),
                "quality_tier": item.get("quality_tier"),
                "license": item.get("license", "CC-BY-4.0"),
                "provenance": "community/hao-motion-kit/SOURCE_PROVENANCE.json",
                "metadata_origin": "imagegen-text-manifest",
                "selectable": bool(item.get("selectable", False)),
            })

    def _load_money_manifest(self) -> None:
        money_path = self.kit / "assets" / "money_burst" / "imagegen" / "manifest.json"
        money = _read_json(money_path, {})
        for item in money.get("assets", []):
            self._upsert({
                "path": self.kit / item.get("file", ""), "category": "particle_source",
                "media_type": "image", "role": item.get("role", "value_particle_overlay"),
                "description": "recognizable USD value-particle overlay source; never an edit transition",
                "tags": list(item.get("tags", [])) + [item.get("id", "")],
                "domains": item.get("domains", ["general"]),
                "resolution": _resolution(item.get("resolution")), "aspect": "any",
                "energy": .96, "loopable": False, "alpha": True,
                "quality_tier": item.get("quality_tier"),
                "renderer": item.get("renderer"),
                "is_transition": bool(item.get("is_transition", False)),
                "license": item.get("license", "CC-BY-4.0"),
                "provenance": "community/hao-motion-kit/SOURCE_PROVENANCE.json",
                "metadata_origin": "imagegen-money-manifest",
                "selectable": bool(item.get("selectable", False)),
            })

    def _load_public_kit(self) -> None:
        self._load_motion_manifest()
        self._load_template_manifest()
        self._load_procedural_glow_manifest()
        self._load_imagegen_glow_manifest()
        self._load_money_manifest()
