# -*- coding: utf-8 -*-
"""Asset Workshop: plan, ingest, split and audit reusable image atlases.

Image generation stays an explicit creative step.  This module owns the
deterministic parts around it: stable jobs, alpha-safe sprite extraction,
provenance, duplicate detection and registry-ready metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from asset_registry_shared import discover_project_root
from mrbeast_source_map import asset_backlog as mrbeast_asset_backlog
from mrbeast_source_map import load_map as load_mrbeast_source_map
from mrbeast_source_map import validate_map as validate_mrbeast_source_map


SKILL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = discover_project_root(SKILL_ROOT)
WORKSHOP_ROOT = PROJECT_ROOT / "assets" / "workshop"
MANIFEST_PATH = WORKSHOP_ROOT / "manifest.json"
PLAN_PATH = WORKSHOP_ROOT / "production_plan.json"
PREVIEW_PATH = WORKSHOP_ROOT / "catalog-preview.webp"
VALID_ROLES = {
    "photoreal_cutout",
    "prerendered_3d",
    "vfx_overlay",
    "japanese_lifestyle_illustration",
    "minimal_monochrome_icon",
}
from asset_workshop_plan import (
    NONREAL_EDITORIAL_DOMAINS,
    default_plan,
)
ROWS = 4
COLS = 4


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                     dir=path.parent, delete=False,
                                     prefix=".asset-workshop-", suffix=".tmp") as handle:
        handle.write(payload)
        temporary = handle.name
    os.replace(temporary, path)


from asset_image_ops import (
    _sha256,
    _perceptual_hash,
    _trim_alpha,
    _clean_low_alpha_fringe,
)




def write_plan(output: Path = PLAN_PATH) -> dict:
    plan = default_plan()
    _atomic_json(output, plan)
    manifest_path = output.parent / "manifest.json"
    if not manifest_path.exists():
        manifest = {
            "schema_version": 1,
            "asset_count": 0,
            "assets": [],
            "batches": {},
            "license": "project-original-open",
            "provenance_policy": "Only Hao-approved batches enter the active workshop library.",
        }
        _atomic_json(manifest_path, manifest)
        render_preview(manifest, output.parent / "catalog-preview.webp")
    return plan


def register_taste_board(source: str | os.PathLike, *, board_id: str,
                         family: str, domains: list[str], workshop_root: Path = WORKSHOP_ROOT) -> dict:
    """Store a style calibration board without making it an editable/selectable asset."""
    if family == "japanese_lifestyle_calm" and not set(domains).issubset(NONREAL_EDITORIAL_DOMAINS):
        raise ValueError("Japanese calm non-real direction is limited to travel, food and cafe")
    if family not in {"photoreal_production", "japanese_lifestyle_calm"}:
        raise ValueError("unsupported taste-board family: " + family)
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    image = Image.open(source_path).convert("RGB")
    output_dir = workshop_root / "taste-boards"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{board_id}.png"
    if source_path != output.resolve():
        shutil.copy2(source_path, output)
    manifest_path = workshop_root / "manifest.json"
    manifest = _read(manifest_path, {
        "schema_version": 1, "asset_count": 0, "assets": [], "batches": {},
        "license": "project-original-open",
    })
    boards = [row for row in manifest.get("taste_boards", []) if row.get("id") != board_id]
    boards.append({
        "id": board_id,
        "family": family,
        "domains": domains,
        "path": output.relative_to(PROJECT_ROOT).as_posix(),
        "resolution": [image.width, image.height],
        "sha256": _sha256(output),
        "provenance": "OpenAI built-in image generation; Hao Asset Workshop taste calibration",
        "truth_label": "illustrative_not_evidence",
        "status": "taste_board_only",
        "selectable": False,
        "human_review": "pending",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    })
    manifest["taste_boards"] = boards
    manifest["taste_board_count"] = len(boards)
    _atomic_json(manifest_path, manifest)
    render_preview(manifest, workshop_root / "catalog-preview.webp")
    return {"status": "GREEN", "id": board_id, "family": family,
            "selectable": False, "human_review": "pending", "path": str(output)}


def review_taste_board(board_id: str, decision: str,
                       workshop_root: Path = WORKSHOP_ROOT) -> dict:
    if decision not in {"approved", "rejected", "needs_edit"}:
        raise ValueError("unsupported review decision: " + decision)
    manifest_path = workshop_root / "manifest.json"
    manifest = _read(manifest_path, {})
    matched = False
    for row in manifest.get("taste_boards", []):
        if row.get("id") == board_id:
            row["human_review"] = decision
            row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            row["selectable"] = False
            matched = True
    if not matched:
        raise KeyError("unknown taste board: " + board_id)
    _atomic_json(manifest_path, manifest)
    render_preview(manifest, workshop_root / "catalog-preview.webp")
    return {"status": "GREEN", "id": board_id, "human_review": decision,
            "selectable": False}


def review_asset_batch(batch_id: str, decision: str,
                       workshop_root: Path = WORKSHOP_ROOT) -> dict:
    """Approve a whole atom batch or remove a rejected batch from the library.

    A generated atom is never selectable while review is pending. Rejection is
    intentionally batch-scoped so the atlas, split atoms and manifest rows
    cannot drift apart or linger as unregistered garbage.
    """
    if decision not in {"approved", "rejected", "needs_edit"}:
        raise ValueError("unsupported review decision: " + decision)
    manifest_path = workshop_root / "manifest.json"
    manifest = _read(manifest_path, {})
    rows = [row for row in manifest.get("assets", []) if row.get("batch_id") == batch_id]
    if not rows:
        raise KeyError("unknown asset batch: " + batch_id)
    if decision == "rejected":
        for row in rows:
            path = (PROJECT_ROOT / str(row.get("path", ""))).resolve()
            if path.is_file() and workshop_root.resolve() in path.parents:
                path.unlink()
        atom_dir = (workshop_root / "atoms" / batch_id).resolve()
        if atom_dir.is_dir() and workshop_root.resolve() in atom_dir.parents:
            shutil.rmtree(atom_dir)
        batch = (manifest.get("batches") or {}).get(batch_id, {})
        atlas = (PROJECT_ROOT / str(batch.get("source_atlas", ""))).resolve()
        if atlas.is_file() and workshop_root.resolve() in atlas.parents:
            atlas.unlink()
        manifest["assets"] = [row for row in manifest.get("assets", [])
                              if row.get("batch_id") != batch_id]
        manifest.get("batches", {}).pop(batch_id, None)
    else:
        for row in rows:
            row["human_review"] = decision
            row["selectable"] = decision == "approved"
            row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        manifest.setdefault("batches", {}).setdefault(batch_id, {})["human_review"] = decision
    manifest["asset_count"] = len(manifest.get("assets", []))
    _atomic_json(manifest_path, manifest)
    render_preview(manifest, workshop_root / "catalog-preview.webp")
    return {"status": "GREEN", "batch_id": batch_id, "human_review": decision,
            "selectable": decision == "approved", "asset_count": len(rows)}


def normalize_selection_gates(workshop_root: Path = WORKSHOP_ROOT) -> dict:
    """Migrate old manifests to the approval-gated selection contract."""
    manifest_path = workshop_root / "manifest.json"
    manifest = _read(manifest_path, {})
    changed = 0
    for row in manifest.get("assets", []):
        expected = row.get("human_review") == "approved"
        if row.get("selectable") is not expected:
            row["selectable"] = expected
            changed += 1
    for row in manifest.get("taste_boards", []):
        if row.get("selectable") is not False:
            row["selectable"] = False
            changed += 1
    _atomic_json(manifest_path, manifest)
    render_preview(manifest, workshop_root / "catalog-preview.webp")
    return {"status": "GREEN", "changed": changed,
            "selection_contract": "approved assets only; taste boards never"}


def _entry(*, batch_id: str, index: int, name: str, role: str,
           domains: list[str], source: Path, output: Path, image: Image.Image) -> dict:
    alpha = image.getchannel("A")
    visible = sum(value > 8 for value in alpha.getdata())
    coverage = visible / float(image.width * image.height)
    relative = output.relative_to(PROJECT_ROOT).as_posix()
    return {
        "id": f"{batch_id}-{index + 1:02d}", "name": name, "path": relative,
        "category": "workshop_asset", "role": role, "domains": domains,
        "tags": [batch_id, role, name], "media_type": "image", "aspect": "square",
        "resolution": [image.width, image.height], "alpha": True,
        "coverage_ratio": round(coverage, 4), "sha256": _sha256(output),
        "perceptual_hash": _perceptual_hash(image), "license": "project-original-open",
        "provenance": "OpenAI built-in image generation; Hao Asset Workshop deterministic split",
        "source_atlas": source.relative_to(PROJECT_ROOT).as_posix(),
        "capability_label": ("prerendered_3d_element" if role == "prerendered_3d" else
                             "synthetic_photoreal_cutout" if role == "photoreal_cutout" else
                             "japanese_lifestyle_editorial" if role == "japanese_lifestyle_illustration" else
                             "minimal_monochrome_icon" if role == "minimal_monochrome_icon"
                             else "vfx_overlay"),
        "truth_label": ("illustrative_not_evidence" if role in {
            "photoreal_cutout", "prerendered_3d", "japanese_lifestyle_illustration"
        } else "graphic_overlay"),
        "edge_cleanup": "preserve_translucency" if "steam" in name or "smoke" in name
                        else "low_alpha_fringe_cutoff_28",
        "coverage_credit": "ui_annotation_only" if role == "minimal_monochrome_icon"
                           else "narrative_asset_candidate",
        "selectable": False, "human_review": "pending",
    }


def _validate_minimal_icon(image: Image.Image) -> None:
    """Reject multicolour, shaded or busy pixels before an icon enters review."""
    rgba = image.convert("RGBA")
    visible = [rgb for rgb, alpha in zip(rgba.convert("RGB").getdata(),
                                         rgba.getchannel("A").getdata()) if alpha > 32]
    if not visible:
        raise ValueError("icon has no visible pixels")
    bins = Counter(tuple(channel // 24 for channel in pixel) for pixel in visible)
    if bins.most_common(1)[0][1] / len(visible) < 0.90:
        raise ValueError("icons must be single-colour, flat and minimal; gradients/shading are blocked")


def ingest_atlas(source: str | os.PathLike, *, batch_id: str, role: str,
                 names: list[str], domains: list[str], rows: int = ROWS,
                 cols: int = COLS, workshop_root: Path = WORKSHOP_ROOT) -> dict:
    if role not in VALID_ROLES:
        raise ValueError("unsupported workshop role: " + role)
    if role == "japanese_lifestyle_illustration" and not set(domains).issubset(NONREAL_EDITORIAL_DOMAINS):
        raise ValueError("non-real editorial illustration is limited to travel, food and cafe")
    if len(names) != rows * cols:
        raise ValueError("names must match atlas cells")
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    image = Image.open(source_path).convert("RGBA")
    atlas_dir = workshop_root / "atlases"
    sprite_dir = workshop_root / "atoms" / batch_id
    atlas_dir.mkdir(parents=True, exist_ok=True)
    sprite_dir.mkdir(parents=True, exist_ok=True)
    stored_atlas = atlas_dir / f"{batch_id}.png"
    if source_path != stored_atlas.resolve():
        shutil.copy2(source_path, stored_atlas)
    entries = []
    for index, name in enumerate(names):
        row, column = divmod(index, cols)
        left = round(column * image.width / cols)
        right = round((column + 1) * image.width / cols)
        top = round(row * image.height / rows)
        bottom = round((row + 1) * image.height / rows)
        cell = image.crop((left, top, right, bottom))
        sprite = _trim_alpha(_clean_low_alpha_fringe(
            cell, preserve_translucency=("steam" in name or "smoke" in name)
        ))
        if role == "minimal_monochrome_icon":
            _validate_minimal_icon(sprite)
        output = sprite_dir / f"{index + 1:02d}-{name}.png"
        sprite.save(output, optimize=True)
        entries.append(_entry(batch_id=batch_id, index=index, name=name, role=role,
                              domains=domains, source=stored_atlas, output=output, image=sprite))
    manifest = _read(workshop_root / "manifest.json", {"schema_version": 1, "assets": [], "batches": {}})
    manifest["assets"] = [row for row in manifest.get("assets", []) if row.get("batch_id") != batch_id]
    for row in entries:
        row["batch_id"] = batch_id
    manifest["assets"].extend(entries)
    manifest.setdefault("batches", {})[batch_id] = {
        "source_atlas": stored_atlas.relative_to(PROJECT_ROOT).as_posix(),
        "role": role, "domains": domains, "asset_count": len(entries),
        "generated_with": "OpenAI built-in image generation", "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest["asset_count"] = len(manifest["assets"])
    manifest["license"] = "project-original-open"
    manifest["provenance_policy"] = "No third-party creator assets; functional benchmark principles only."
    _atomic_json(workshop_root / "manifest.json", manifest)
    render_preview(manifest, workshop_root / "catalog-preview.webp")
    return {"status": "GREEN", "batch_id": batch_id, "created": len(entries), "manifest": str(workshop_root / "manifest.json")}


def render_preview(manifest: dict | None = None, output: Path = PREVIEW_PATH) -> Path:
    manifest = manifest or _read(MANIFEST_PATH, {"assets": []})
    assets = manifest.get("assets", [])
    boards = manifest.get("taste_boards", [])
    if not assets and not boards:
        canvas = Image.new("RGB", (960, 260), "#f2efe7")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        draw.rounded_rectangle((28, 28, 932, 232), 24, fill="#fbfaf6", outline="#c9c2b5", width=2)
        draw.text((68, 84), "HAO ASSET WORKSHOP", font=font, fill="#26231f")
        draw.text((68, 124), "No approved assets. Real footage or clean hold remains the default.",
                  font=font, fill="#6f685e")
        draw.text((68, 164), "Create a small taste board before any bulk generation.",
                  font=font, fill="#8a6f47")
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, quality=88, method=6)
        return output
    if boards and not assets:
        columns, card_w, card_h = 2, 820, 590
        rows = max(1, (len(boards) + columns - 1) // columns)
        canvas = Image.new("RGB", (columns * card_w, rows * card_h), "#eeeae1")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        for index, row in enumerate(boards):
            x, y = (index % columns) * card_w, (index // columns) * card_h
            draw.rounded_rectangle((x + 14, y + 14, x + card_w - 14, y + card_h - 14), 24,
                                   fill="#faf8f2", outline="#b9b2a7", width=2)
            path = PROJECT_ROOT / row["path"]
            if path.is_file():
                board = Image.open(path).convert("RGB")
                board.thumbnail((760, 455), Image.Resampling.LANCZOS)
                canvas.paste(board, (x + (card_w - board.width) // 2, y + 34))
            draw.text((x + 30, y + 512), row["family"], font=font, fill="#25221d")
            draw.text((x + 30, y + 540), "TASTE BOARD ONLY / HAO REVIEW PENDING / NOT SELECTABLE",
                      font=font, fill="#9a5b3c")
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, quality=88, method=6)
        return output
    cell_w, cell_h, columns = 260, 310, 8
    rows = max(1, (len(assets) + columns - 1) // columns)
    canvas = Image.new("RGB", (cell_w * columns, cell_h * rows), "#11151d")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, row in enumerate(assets):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        draw.rounded_rectangle((x + 6, y + 6, x + cell_w - 6, y + cell_h - 6), 18,
                               fill="#1d2430", outline="#334155", width=2)
        path = PROJECT_ROOT / row["path"]
        if path.is_file():
            image = Image.open(path).convert("RGBA")
            image.thumbnail((220, 220), Image.Resampling.LANCZOS)
            px = x + (cell_w - image.width) // 2
            canvas.paste(image.convert("RGB"), (px, y + 15), image.getchannel("A"))
        label = row["id"][:30]
        draw.text((x + 16, y + 250), label, font=font, fill="#f8fafc")
        draw.text((x + 16, y + 272), row["role"], font=font, fill="#84cc16")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=88, method=6)
    return output


def audit(workshop_root: Path = WORKSHOP_ROOT) -> dict:
    manifest = _read(workshop_root / "manifest.json", {})
    assets = manifest.get("assets", [])
    taste_boards = manifest.get("taste_boards", [])
    errors, warnings = [], []
    ids, sha = set(), {}
    for row in assets:
        asset_id = row.get("id")
        path = PROJECT_ROOT / str(row.get("path", ""))
        if not asset_id or asset_id in ids:
            errors.append("duplicate or missing id: " + str(asset_id))
        ids.add(asset_id)
        if not path.is_file():
            errors.append("missing asset: " + str(row.get("path")))
            continue
        image = Image.open(path)
        if "A" not in image.getbands() or image.getchannel("A").getextrema()[0] > 8:
            errors.append("asset lacks usable transparency: " + str(row.get("path")))
        coverage = float(row.get("coverage_ratio", 0))
        thin_component = any(token in str(row.get("name", "")) for token in ("line", "route"))
        minimum_coverage = .008 if thin_component else .05
        if coverage < minimum_coverage or coverage > .92:
            errors.append("invalid visible coverage: " + str(row.get("path")))
        digest = _sha256(path)
        if digest in sha:
            errors.append("exact duplicate: %s == %s" % (row.get("path"), sha[digest]))
        sha[digest] = row.get("path")
        if row.get("human_review") != "approved":
            warnings.append("human review pending: " + str(row.get("id")))
            if row.get("selectable") is not False:
                errors.append("unapproved asset became selectable: " + str(row.get("id")))
        elif row.get("selectable") is not True:
            errors.append("approved asset is not selectable: " + str(row.get("id")))
    for row in taste_boards:
        path = PROJECT_ROOT / str(row.get("path", ""))
        if not path.is_file():
            errors.append("missing taste board: " + str(row.get("path")))
        if row.get("selectable") is not False or row.get("status") != "taste_board_only":
            errors.append("taste board became selectable: " + str(row.get("id")))
        if row.get("human_review") != "approved":
            warnings.append("taste board review pending: " + str(row.get("id")))
    if not assets:
        warnings.append("workshop contains no accepted assets; use real footage or clean hold")
    expected = {
        str(row.get("path", "")).replace("/", os.sep) for row in [*assets, *taste_boards]
        if row.get("path")
    }
    expected.update(
        str(row.get("source_atlas", "")).replace("/", os.sep)
        for row in (manifest.get("batches") or {}).values() if row.get("source_atlas")
    )
    expected.update({
        str((workshop_root / "manifest.json").relative_to(PROJECT_ROOT)),
        str((workshop_root / "production_plan.json").relative_to(PROJECT_ROOT)),
        str((workshop_root / "catalog-preview.webp").relative_to(PROJECT_ROOT)),
    })
    actual = {
        str(path.relative_to(PROJECT_ROOT)) for path in workshop_root.rglob("*")
        if path.is_file() and "_review" not in path.relative_to(workshop_root).parts
    }
    for orphan in sorted(actual - expected):
        errors.append("unregistered workshop orphan: " + orphan.replace(os.sep, "/"))
    return {"status": "GREEN" if not errors else "RED", "schema_version": 1,
            "asset_count": len(assets), "taste_board_count": len(taste_boards),
            "errors": errors, "warnings": warnings,
            "role_counts": {role: sum(row.get("role") == role for row in assets) for role in sorted(VALID_ROLES)}}


def self_test() -> None:
    from asset_workshop_commands import self_test as _implementation
    return _implementation(globals())


def main(argv=None) -> int:
    from asset_workshop_commands import main as _implementation
    return _implementation(globals(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
