# -*- coding: utf-8 -*-
"""Fail-closed license and provenance governance for the asset registry."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from asset_registry import AssetRegistry


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
POLICY_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "asset_license_policy.json"
OVERRIDES_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "asset_license_overrides.json"
DEFAULT_REPORT = PROJECT_ROOT / "assets" / "license_audit.json"


def _read(path: str | Path, default) -> dict:
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError): return default


def _atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path.with_suffix(path.suffix + ".candidate")
    candidate.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(candidate, path)


def classify(record: dict, policy: dict) -> str:
    license_name = str(record.get("license") or "unknown")
    provenance = str(record.get("provenance") or "unknown")
    if not provenance or provenance == "unknown": return "blocked_missing_provenance"
    if license_name in policy.get("redistributable", []): return "redistributable"
    if license_name in policy.get("project_use_only", []): return "project_use_only"
    if license_name in policy.get("blocked", []) or license_name.startswith("pending"): return "blocked_unknown_or_pending"
    return "blocked_unrecognized_license"


def normalized_records(registry: AssetRegistry, overrides: dict | None = None) -> list[dict]:
    overrides = (overrides or {}).get("overrides", {})
    rows = []
    for record in registry.records:
        row = dict(record)
        override = overrides.get(row["path"])
        if override:
            row["license"] = override.get("license", row.get("license"))
            row["provenance"] = override.get("provenance", row.get("provenance"))
            row["override_note"] = override.get("note")
        rows.append(row)
    return rows


def audit(registry: AssetRegistry | None = None, output: str | Path | None = DEFAULT_REPORT) -> dict:
    registry = registry or AssetRegistry()
    policy = _read(POLICY_PATH, {})
    rows = normalized_records(registry, _read(OVERRIDES_PATH, {}))
    statuses = Counter(classify(row, policy) for row in rows if row.get("selectable"))
    unknown_by_category = Counter(row.get("category", "unknown") for row in rows
                                  if row.get("selectable") and classify(row, policy).startswith("blocked"))
    report = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "GREEN_FAIL_CLOSED", "selectable": sum(bool(x.get("selectable")) for x in rows),
        "classification_counts": dict(statuses), "blocked_by_category": dict(unknown_by_category),
        "public_export_rule": "redistributable only; blocked rows are excluded, not guessed",
    }
    if output: _atomic(Path(output), report)
    return report


def export_public_manifest(output: str | Path, registry: AssetRegistry | None = None) -> dict:
    registry = registry or AssetRegistry()
    policy = _read(POLICY_PATH, {})
    rows = normalized_records(registry, _read(OVERRIDES_PATH, {}))
    allowed = []
    for row in rows:
        if row.get("selectable") and row.get("exists") and classify(row, policy) == "redistributable":
            allowed.append({k: row.get(k) for k in ("asset_id", "path", "category", "role", "domains", "license", "provenance")})
    manifest = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                "fail_closed": True, "asset_count": len(allowed), "assets": allowed}
    _atomic(Path(output), manifest)
    return manifest


def _selftest() -> None:
    policy = _read(POLICY_PATH, {})
    assert classify({"license":"CC-BY-4.0","provenance":"generator.py"}, policy) == "redistributable"
    assert classify({"license":"unknown","provenance":"inventory"}, policy).startswith("blocked")
    assert classify({"license":"private-user-provided","provenance":"user"}, policy) == "project_use_only"
    with tempfile.TemporaryDirectory(prefix="hao-license-test-") as td:
        class Fake:
            records = [{"asset_id":"a","path":"a.mp4","category":"motion","role":"overlay","domains":["general"],"license":"CC0-1.0","provenance":"test","selectable":True,"exists":True},
                       {"asset_id":"b","path":"b.mp3","category":"bgm","role":"bgm","domains":["general"],"license":"unknown","provenance":"unknown","selectable":True,"exists":True}]
        result = export_public_manifest(Path(td) / "public.json", Fake())
        assert result["asset_count"] == 1 and result["assets"][0]["asset_id"] == "a"
    print("asset_license_governance self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    au = sub.add_parser("audit"); au.add_argument("--output", default=str(DEFAULT_REPORT))
    ex = sub.add_parser("export-public"); ex.add_argument("output")
    args = ap.parse_args(argv)
    if args.cmd == "selftest": _selftest(); return 0
    result = audit(output=args.output) if args.cmd == "audit" else export_public_manifest(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
