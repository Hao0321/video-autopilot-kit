"""Project source metrics; one implementation behind the compatibility facade."""
from __future__ import annotations

import ast
import fnmatch
import json
import os
import re
from pathlib import Path


ABSOLUTE_LITERAL = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")

TEXT_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ps1"}

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

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

def source_audit(workspace: Path, manifest: dict) -> dict:
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
