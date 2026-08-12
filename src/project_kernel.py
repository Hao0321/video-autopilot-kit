# -*- coding: utf-8 -*-
"""Manifest-driven control plane for Video Autopilot.

The kernel audits architecture, capacity and installed-skill drift.  It does
not edit or delete media.  Existing builders remain independent execution
modules behind this control plane.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from project_paths import MANIFEST_NAMES, discover_project_root


ABSOLUTE_LITERAL = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|Hao0321_YT_Claude|Program Files)|Path\(r?[\"'][A-Za-z]:[\\/])")
TEXT_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ps1"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(root: str | os.PathLike | None = None) -> tuple[Path, dict]:
    workspace = Path(root).expanduser().resolve() if root else discover_project_root()
    path = next((workspace / name for name in MANIFEST_NAMES
                 if (workspace / name).is_file()), workspace / MANIFEST_NAMES[0])
    data = _read_json(path)
    if data.get("schema_version") != 2 or not data.get("project_id"):
        raise ValueError(f"Unsupported or incomplete manifest: {path}")
    return workspace, data


def _ignored(relative: str, patterns: list[str]) -> bool:
    normalized = relative.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def _effective_function_lines(node: ast.AST, source_lines: list[str]) -> int:
    """Count executable/source structure without charging static multiline copy as logic.

    Physical length is still reported for navigation.  This metric prevents interview
    scripts, card copy and other declarative text from being mistaken for complex code.
    """
    excluded: set[int] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            end = getattr(child, "end_lineno", child.lineno)
            excluded.update(range(child.lineno + 1, end + 1))
    end = getattr(node, "end_lineno", node.lineno)
    return sum(
        1
        for line_no in range(node.lineno, end + 1)
        if line_no not in excluded
        and source_lines[line_no - 1].strip()
        and not source_lines[line_no - 1].lstrip().startswith("#")
    )


def _literalish(node: ast.AST) -> bool:
    """Return True for declarative values that do not add runtime complexity."""
    if isinstance(node, (ast.Constant, ast.Dict, ast.List, ast.Tuple, ast.Set)):
        return all(_literalish(child) for child in ast.iter_child_nodes(node))
    if isinstance(node, ast.UnaryOp):
        return _literalish(node.operand)
    if isinstance(node, ast.BinOp):
        return _literalish(node.left) and _literalish(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in {"Path", "_p"}:
            return False
        return all(_literalish(arg) for arg in node.args) and all(
            _literalish(keyword.value) for keyword in node.keywords
        )
    if isinstance(node, ast.Name):
        return node.id in {"True", "False", "None"}
    return False


def _effective_module_lines(tree: ast.Module, source_lines: list[str]) -> int:
    """Measure maintainable Python logic, not embedded copy or assertion fixtures."""
    excluded: set[int] = set()
    for child in ast.walk(tree):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            end = getattr(child, "end_lineno", child.lineno)
            excluded.update(range(child.lineno + 1, end + 1))
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.lower() in {
            "_selftest", "selftest", "self_test", "_selftest_body"
        }:
            end = getattr(child, "end_lineno", child.lineno)
            excluded.update(range(child.lineno, end + 1))
    for child in tree.body:
        if isinstance(child, (ast.Assign, ast.AnnAssign)):
            value = child.value
            if value is not None and _literalish(value):
                end = getattr(child, "end_lineno", child.lineno)
                excluded.update(range(child.lineno, end + 1))
    return sum(
        1
        for line_no, line in enumerate(source_lines, 1)
        if line_no not in excluded
        and line.strip()
        and not line.lstrip().startswith("#")
    )


def _directory_metrics(path: Path) -> dict:
    files = 0
    logical_total = 0
    physical_total = 0
    seen_storage: set[tuple[int, int]] = set()
    if path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    stat = item.stat()
                    logical_total += stat.st_size
                    identity = (stat.st_dev, stat.st_ino)
                    if identity not in seen_storage:
                        physical_total += stat.st_size
                        seen_storage.add(identity)
                    files += 1
                except OSError:
                    pass
    saved = logical_total - physical_total
    return {
        "files": files,
        "bytes": physical_total,
        "physical_bytes": physical_total,
        "logical_bytes": logical_total,
        "hardlink_saved_bytes": saved,
        "gb": round(physical_total / (1024 ** 3), 3),
        "logical_gb": round(logical_total / (1024 ** 3), 3),
    }


def inventory(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    rows = {}
    for key, relative in manifest.get("roots", {}).items():
        rows[key] = _directory_metrics(workspace / relative)
    return {"root": str(workspace), "roots": rows}


def _python_metrics(path: Path) -> tuple[int, list[str], ast.Module | None]:
    try:
        source_text = path.read_text(encoding="utf-8", errors="replace")
        source_lines = source_text.splitlines()
        tree = ast.parse(source_text)
    except (SyntaxError, OSError):
        return _line_count(path), [], None
    return _effective_module_lines(tree, source_lines), source_lines, tree


def _function_findings(tree: ast.Module | None, source_lines: list[str], relative: str,
                       budgets: dict, long_allow: dict) -> tuple[list[dict], list[dict]]:
    findings, intentional = [], []
    if tree is None:
        return findings, intentional
    warning = int(budgets.get("function_warning", 50))
    severe = int(budgets.get("function_severe", 100))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        physical = int(end - node.lineno + 1)
        effective = _effective_function_lines(node, source_lines)
        if effective <= warning:
            continue
        key = f"{relative}:{node.name}"
        reason = None
        if node.name.startswith(("_selftest", "self_test")):
            reason = "self-test assertion table"
        elif key in long_allow:
            reason = long_allow[key]
        row = {
            "path": relative, "function": node.name, "lines": effective,
            "physical_lines": physical,
        }
        if reason:
            row["reason"] = reason
            intentional.append(row)
        else:
            row["level"] = "severe" if effective > severe else "warning"
            findings.append(row)
    return findings, intentional


def _large_file_finding(path: Path, relative: str, budgets: dict,
                        large_allow: dict) -> tuple[dict | None, bool, list[str], ast.Module | None]:
    physical = _line_count(path)
    kind = "python" if path.suffix.lower() == ".py" else "markdown"
    warning = int(budgets.get(f"{kind}_warning", 500))
    severe = int(budgets.get(f"{kind}_severe", 1000))
    lines, source_lines, tree = (physical, [], None)
    if kind == "python":
        lines, source_lines, tree = _python_metrics(path)
    if lines <= warning:
        return None, False, source_lines, tree
    row = {
        "path": relative, "lines": lines, "physical_lines": physical,
        "level": "severe" if lines > severe else "warning",
    }
    if relative in large_allow:
        row["reason"] = large_allow[relative]
        return row, True, source_lines, tree
    return row, False, source_lines, tree


def source_audit(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    config = manifest.get("audit", {})
    ignores = config.get("ignore_globs", [])
    path_allow = set(config.get("absolute_path_allowlist", []))
    long_allow = config.get("long_function_allowlist", {})
    large_allow = config.get("large_file_allowlist", {})
    budgets = manifest.get("budgets", {}).get("source_lines", {})
    knowledge_paths = set(manifest.get("budgets", {}).get("knowledge_lines", {}))
    large, intentional_large, functions, intentional_functions, absolute = [], [], [], [], []
    scanned = 0
    for source_root in config.get("source_roots", []):
        base = workspace / source_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
                continue
            relative = path.relative_to(workspace).as_posix()
            if _ignored(relative, ignores):
                continue
            scanned += 1
            if path.suffix.lower() in {".py", ".md"} and relative not in knowledge_paths:
                row, allowed, source_lines, tree = _large_file_finding(
                    path, relative, budgets, large_allow
                )
                if row:
                    (intentional_large if allowed else large).append(row)
                if path.suffix.lower() == ".py":
                    found, accepted = _function_findings(
                        tree, source_lines, relative, budgets, long_allow
                    )
                    functions.extend(found)
                    intentional_functions.extend(accepted)
            if path.suffix.lower() in {".py", ".ps1"} and relative not in path_allow:
                text = path.read_text(encoding="utf-8", errors="replace")
                if ABSOLUTE_LITERAL.search(text):
                    absolute.append(relative)
    return {
        "scanned": scanned,
        "large_files": sorted(large, key=lambda row: row["lines"], reverse=True),
        "intentional_large_files": sorted(intentional_large, key=lambda row: row["lines"], reverse=True),
        "large_functions": sorted(functions, key=lambda row: row["lines"], reverse=True),
        "intentional_long_functions": sorted(
            intentional_functions, key=lambda row: row["lines"], reverse=True
        ),
        "absolute_path_files": sorted(set(absolute)),
    }


def knowledge_audit(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    rows = []
    for relative, policy in manifest.get("budgets", {}).get("knowledge_lines", {}).items():
        path = workspace / relative
        lines = _line_count(path) if path.is_file() else 0
        frozen = str(policy.get("policy", "")).startswith("legacy-freeze")
        rows.append({
            "path": relative,
            "lines": lines,
            "warning": int(policy["warning"]),
            "rotate": int(policy["rotate"]),
            "state": "FROZEN" if frozen else (
                "ROTATE" if lines >= int(policy["rotate"]) else (
                    "WARN" if lines >= int(policy["warning"]) else "OK"
                )
            ),
            "policy": policy.get("policy", "archive-before-rewrite"),
        })
    return {"files": rows}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sync_hash(path: Path) -> str:
    """Compare Skill text portably across Git's LF/CRLF checkouts."""
    payload = path.read_bytes()
    if b"\x00" not in payload:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _sync_files(workspace: Path, skill: dict) -> list[Path]:
    source = workspace / skill["source"]
    found: dict[str, Path] = {}
    for pattern in skill.get("include", []):
        for path in source.glob(pattern):
            if path.is_file():
                found[path.relative_to(source).as_posix()] = path
    return [found[key] for key in sorted(found)]


def sync_status(root: str | os.PathLike | None = None, skill_id: str | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    results = []
    for skill in manifest.get("skills", []):
        if skill_id and skill["id"] != skill_id:
            continue
        source = workspace / skill["source"]
        destination = Path.home() / ".codex" / "skills" / skill["destination"]
        missing, different, matched = [], [], 0
        files = _sync_files(workspace, skill)
        for src in files:
            relative = src.relative_to(source)
            target = destination / relative
            if not target.is_file():
                missing.append(relative.as_posix())
            elif _sync_hash(src) != _sync_hash(target):
                different.append(relative.as_posix())
            else:
                matched += 1
        results.append({
            "id": skill["id"],
            "status": "GREEN" if not missing and not different else "RED",
            "source": str(source),
            "destination": str(destination),
            "declared_files": len(files),
            "matched": matched,
            "missing": missing,
            "different": different,
        })
    status = "GREEN" if results and all(row["status"] == "GREEN" for row in results) else "RED"
    return {"status": status, "skills": results, "policy": "additive; destination files are never deleted"}


def sync_apply(root: str | os.PathLike | None = None, skill_id: str | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    copied = {}
    for skill in manifest.get("skills", []):
        if skill_id and skill["id"] != skill_id:
            continue
        source = workspace / skill["source"]
        destination = Path.home() / ".codex" / "skills" / skill["destination"]
        destination.mkdir(parents=True, exist_ok=True)
        count = 0
        for src in _sync_files(workspace, skill):
            target = destination / src.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or _sync_hash(src) != _sync_hash(target):
                shutil.copy2(src, target)
                count += 1
        copied[skill["id"]] = count
    result = sync_status(workspace, skill_id)
    result["copied"] = copied
    return result


def _source_warnings(sources: dict) -> list[str]:
    warnings = []
    if sources["absolute_path_files"]:
        warnings.append(f"portable-path debt in {len(sources['absolute_path_files'])} active files")
    severe = [row for row in sources["large_files"] if row["level"] == "severe"]
    severe_functions = [row for row in sources["large_functions"] if row["level"] == "severe"]
    if severe:
        warnings.append(f"{len(severe)} source files exceed severe line budget")
    elif sources["large_files"]:
        warnings.append(f"{len(sources['large_files'])} modules/references remain above refactor warning budget")
    if severe_functions:
        warnings.append(f"{len(severe_functions)} functions exceed 100-line severe budget")
    return warnings


def _knowledge_warnings(knowledge: dict) -> list[str]:
    warnings = []
    rotate = [row for row in knowledge["files"] if row["state"] == "ROTATE"]
    warn_knowledge = [row for row in knowledge["files"] if row["state"] == "WARN"]
    if rotate:
        warnings.append(f"{len(rotate)} knowledge files reached rotation threshold")
    elif warn_knowledge:
        warnings.append(f"{len(warn_knowledge)} knowledge files near rotation threshold")
    return warnings


def _storage_warnings(sizes: dict, manifest: dict) -> list[str]:
    warnings = []
    storage_budget = manifest.get("budgets", {}).get("storage_gb", {})
    videos_gb = sizes["roots"].get("videos", {}).get("gb", 0)
    videos_logical_gb = sizes["roots"].get("videos", {}).get("logical_gb", videos_gb)
    videos_saved_gb = round(
        sizes["roots"].get("videos", {}).get("hardlink_saved_bytes", 0) / (1024 ** 3), 3
    )
    assets_gb = sizes["roots"].get("assets", {}).get("gb", 0)
    if videos_gb >= float(storage_budget.get("videos_warning", 12)):
        warnings.append(
            f"videos physical storage {videos_gb}GB reached warning budget "
            f"(logical {videos_logical_gb}GB; hardlinks save {videos_saved_gb}GB)"
        )
    if assets_gb >= float(storage_budget.get("assets_warning", 5)):
        warnings.append(f"assets storage {assets_gb}GB reached warning budget")
    return warnings


def doctor(root: str | os.PathLike | None = None, *, quick: bool = False) -> dict:
    workspace, manifest = load_manifest(root)
    errors = [
        f"missing required path: {relative}"
        for relative in manifest.get("required_paths", [])
        if not (workspace / relative).exists()
    ]
    sources = source_audit(workspace)
    knowledge = knowledge_audit(workspace)
    sizes = inventory(workspace)
    warnings = (
        _source_warnings(sources)
        + _knowledge_warnings(knowledge)
        + _storage_warnings(sizes, manifest)
    )

    sync = sync_status(workspace)
    if sync["status"] != "GREEN":
        warnings.append("installed skill copy is absent or differs; run project_kernel.py sync apply")

    return {
        "status": "GREEN" if not errors else "RED",
        "root": str(workspace),
        "architecture_version": manifest.get("architecture_version"),
        "errors": errors,
        "warnings": warnings,
        "source_audit": sources if not quick else {
            "scanned": sources["scanned"],
            "large_count": len(sources["large_files"]),
            "large_function_count": len(sources["large_functions"]),
            "absolute_path_count": len(sources["absolute_path_files"]),
        },
        "knowledge": knowledge,
        "storage": sizes["roots"],
        "sync": sync,
    }


def self_test() -> None:
    workspace, manifest = load_manifest()
    assert manifest["architecture_version"] == "5.2"
    assert (workspace / manifest["planes"]["control"][0]).is_file()
    assert inventory(workspace)["roots"]["skills"]["files"] > 0
    with tempfile.TemporaryDirectory(prefix="kernel-") as temp:
        probe = Path(temp) / "x.txt"
        probe.write_text("ok", encoding="utf-8")
        assert _hash(probe) == hashlib.sha256(b"ok").hexdigest()
        alias = Path(temp) / "x-alias.txt"
        os.link(probe, alias)
        metrics = _directory_metrics(Path(temp))
        assert metrics["logical_bytes"] == 4
        assert metrics["physical_bytes"] == 2
        assert metrics["hardlink_saved_bytes"] == 2
    print("project_kernel self-test GREEN")


def _print_human(result: dict, label: str) -> None:
    print(f"{label} {result.get('status', 'GREEN')}")
    if "architecture_version" in result:
        print(f"architecture={result['architecture_version']} root={result['root']}")
    for item in result.get("errors", []):
        print(f"[RED] {item}")
    for item in result.get("warnings", []):
        print(f"[WARN] {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Video Autopilot manifest control plane")
    subs = parser.add_subparsers(dest="command", required=True)
    doctor_cmd = subs.add_parser("doctor")
    doctor_cmd.add_argument("--quick", action="store_true")
    doctor_cmd.add_argument("--json", action="store_true")
    inv_cmd = subs.add_parser("inventory")
    inv_cmd.add_argument("--json", action="store_true")
    sync_cmd = subs.add_parser("sync")
    sync_cmd.add_argument("action", choices=("status", "apply"), nargs="?", default="status")
    sync_cmd.add_argument("--skill", default=None)
    sync_cmd.add_argument("--json", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "doctor":
        result = doctor(quick=args.quick)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_human(result, "KERNEL")
        return 0 if result["status"] == "GREEN" else 1
    if args.command == "inventory":
        result = inventory()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    result = sync_apply(skill_id=args.skill) if args.action == "apply" else sync_status(skill_id=args.skill)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result, "SYNC")
        for row in result["skills"]:
            print(f"[{row['status']}] {row['id']}: {row['matched']}/{row['declared_files']}")
    return 0 if result["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
