# -*- coding: utf-8 -*-
"""Portable asset-index migration isolated from registry construction."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from asset_usage import project_root, read_json, write_text_atomic


def _load_index(index_path: Path) -> tuple[dict, str | None]:
    """Return (index, raw text). A missing index is empty; an unparsable one is refused."""
    if not index_path.exists():
        return {}, None
    try:
        raw = index_path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ValueError("refusing to migrate %s: not readable JSON (%s); restore it (for example "
                         "from %s.previous) and retry" % (index_path, exc, index_path.name)) from exc
    if not isinstance(data, dict):
        raise ValueError("refusing to migrate %s: the top level is not a JSON object" % index_path)
    return data, raw


def migrate_index_paths(write: bool = False, root_value: str | os.PathLike | None = None) -> dict:
    root = project_root(root_value)
    index_path = root / "assets" / "index.json"
    data, previous = _load_index(index_path)
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
        if previous is not None:  # keep the pre-migration index for rollback
            write_text_atomic(index_path.with_name(index_path.name + ".previous"), previous)
        write_text_atomic(index_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return {"converted": converted, "external_paths": external, "written": bool(write), "index": str(index_path)}


def _selftest() -> None:
    """An unparsable index is refused untouched; a migration keeps a .previous copy."""
    with tempfile.TemporaryDirectory(prefix="asset-index-test-") as td:
        root = Path(td).resolve()
        index = root / "assets" / "index.json"
        index.parent.mkdir(parents=True)
        clips = {"clip%02d" % i: {"path": str(root / "assets" / "broll" / ("%d.mp4" % i))}
                 for i in range(20)}
        text = json.dumps({"broll_actual": clips})
        index.write_text(text[:-3], encoding="utf-8")  # truncated by an interrupted sync
        corrupt = index.read_bytes()
        for write in (False, True):
            try:
                migrate_index_paths(write=write, root_value=root)
                raise AssertionError("an unparsable index was migrated")
            except ValueError as exc:
                assert "refusing to migrate" in str(exc)
        assert index.read_bytes() == corrupt and not index.with_name("index.json.previous").exists()
        index.write_text(text, encoding="utf-8")
        result = migrate_index_paths(write=True, root_value=root)
        migrated = json.loads(index.read_text(encoding="utf-8"))
        assert result["converted"] == 20 and len(migrated["broll_actual"]) == 20
        assert migrated["broll_actual"]["clip00"]["path"] == "assets/broll/0.mp4"
        assert index.with_name("index.json.previous").read_text(encoding="utf-8") == text
        assert sorted(p.name for p in index.parent.iterdir()) == ["index.json", "index.json.previous"]
    print("asset_index_migration self-test GREEN")


if __name__ == "__main__":
    _selftest()
