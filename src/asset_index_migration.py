# -*- coding: utf-8 -*-
"""Portable asset-index migration isolated from registry construction."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from asset_usage import project_root, read_json


def migrate_index_paths(write: bool = False, root_value: str | os.PathLike | None = None) -> dict:
    root = project_root(root_value)
    index_path = root / "assets" / "index.json"
    data = read_json(index_path, {})
    converted, external = 0, []

    def portable(child):
        nonlocal converted
        if not isinstance(child, str) or not Path(child).is_absolute():
            return child
        try:
            converted += 1
            return Path(child).resolve().relative_to(root).as_posix()
        except ValueError:
            external.append(child)
            return child

    def walk(value):
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if isinstance(child, str):
                    value[key] = portable(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, str):
                    value[index] = portable(child)
                else:
                    walk(child)

    walk(data)
    meta = data.setdefault("_meta", {})
    meta["schema_version"] = "0.4"
    meta["path_policy"] = "project_relative; resolve at runtime via asset_registry"
    meta["description"] = "Portable asset metadata; selection remains asset_registry's responsibility."
    counts = meta.setdefault("counts", {})
    for label, key in (("broll", "broll_actual"), ("sfx", "sfx_actual"), ("font_families", "fonts_actual"), ("face", "face")):
        counts[label] = sum(not str(name).startswith("_") for name in data.get(key, {}))
    counts["face"] = int(data.get("face", {}).get("count", counts.get("face", 0)))
    counts["bgm_indexed"] = sum(len(read_json(path, {}).get("tracks", [])) for path in (root / "assets" / "bgm").rglob("bgm_index.json"))
    meta["asset_count"] = sum(int(value) for value in counts.values())
    meta["asset_count_scope"] = "central indexes + BGM pointers; public kit is virtual"
    if write:
        meta["portable_path_migration_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=".asset-index-", suffix=".tmp", dir=index_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.replace(temp_name, index_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    return {"converted": converted, "external_paths": external, "written": bool(write), "index": str(index_path)}
