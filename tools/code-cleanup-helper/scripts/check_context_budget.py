#!/usr/bin/env python3
"""Measure bounded Skill context routes without Token false-green claims."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable


SCHEMA_VERSION = 1
ENCODING = "o200k_base"
TOKENIZER_ID = f"tiktoken:{ENCODING}"


class ContextBudgetError(RuntimeError):
    """A trustworthy measurement cannot be produced."""

class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ContextBudgetError(message)

@dataclass(frozen=True)
class Tokenizer:
    available: bool
    version: str | None
    reason: str | None
    count: Callable[[str], int] | None
    implementation: str = "tiktoken"

    def as_json(self) -> dict[str, Any]:
        return {
            "id": TOKENIZER_ID, "encoding": ENCODING,
            "implementation": self.implementation, "version": self.version,
            "available": self.available, "exact": self.available,
            "reason": self.reason,
        }

def load_tokenizer() -> Tokenizer:
    """Load only the requested exact tokenizer; never return an estimate."""
    try:
        import tiktoken  # type: ignore[import-not-found]
        encoder = tiktoken.get_encoding(ENCODING)
        try:
            version = importlib.metadata.version("tiktoken")
        except importlib.metadata.PackageNotFoundError:
            version = getattr(tiktoken, "__version__", "unknown")
        counter = lambda text: len(encoder.encode(text, disallowed_special=()))
        return Tokenizer(True, str(version), None, counter)
    except Exception as exc:  # dependency or cached encoding data is optional
        return Tokenizer(False, None, f"{type(exc).__name__}: {exc}", None)

def _finding(status: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"status": status, "code": code, "message": message, **details}

def _manifest_identity(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

def _memory_identity(document: Any) -> dict[str, Any]:
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _manifest_identity("<in-memory>", payload)

def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextBudgetError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _unknown(value: dict[str, Any], allowed: set[str], location: str) -> list[dict[str, Any]]:
    return [
        _finding("BLOCK", "unknown-field", f"{location} has unsupported field {key!r}",
                 location=location, field=key)
        for key in sorted(set(value) - allowed)
    ]

def _budgets(value: dict[str, Any], location: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    result: dict[str, int] = {}
    findings: list[dict[str, Any]] = []
    for key in ("maxBytes", "maxTokens"):
        candidate = value.get(key)
        if not isinstance(candidate, int) or isinstance(candidate, bool) or candidate <= 0:
            findings.append(_finding("BLOCK", "invalid-budget",
                f"{location}.{key} must be a positive integer", location=location,
                field=key, value=candidate))
        else:
            result[key] = candidate
    return result, findings

def _safe_path(root: Path, value: Any) -> tuple[Path | None, str | None, str | None]:
    if not isinstance(value, str) or not value:
        return None, "unsafe-path", "path must be a non-empty repo-relative POSIX string"
    if "\\" in value or "\x00" in value:
        return None, "unsafe-path", "path must use POSIX separators and contain no NUL"
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        return None, "unsafe-path", "absolute or drive-qualified paths are forbidden"
    if posix.as_posix() != value or any(part in {"", ".", ".."} for part in posix.parts):
        return None, "unsafe-path", "path must be normalized and cannot traverse"
    cursor = root
    for part in posix.parts:
        cursor /= part
        junction = hasattr(cursor, "is_junction") and cursor.is_junction()  # type: ignore[attr-defined]
        if cursor.is_symlink() or junction:
            return None, "symlink-file", "symlinks and junctions are forbidden"
    try:
        cursor.resolve(strict=False).relative_to(root)
    except (OSError, ValueError):
        return None, "unsafe-path", "path resolves outside the root"
    return cursor, None, None

def _validate_file(entry: Any, root: Path, route_id: str, location: str,
                   route_seen: dict[str, str], all_seen: dict[str, str]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(entry, dict):
        return None, [_finding("BLOCK", "invalid-file-entry", f"{location} must be an object",
                               routeId=route_id, location=location)]
    findings = _unknown(entry, {"path", "maxBytes", "maxTokens"}, location)
    budgets, budget_findings = _budgets(entry, location)
    findings.extend(budget_findings)
    value = entry.get("path")
    candidate, code, error = _safe_path(root, value)
    if error:
        findings.append(_finding("BLOCK", str(code), f"{location}: {error}",
                                 routeId=route_id, path=value))
        return None, findings
    assert isinstance(value, str) and candidate is not None
    folded = value.casefold()
    if folded in route_seen:
        findings.append(_finding("BLOCK", "duplicate-file", f"duplicate file {value!r}",
                                 routeId=route_id, path=value, duplicateOf=route_seen[folded]))
    else:
        route_seen[folded] = value
    if folded in all_seen and all_seen[folded] != value:
        findings.append(_finding("BLOCK", "duplicate-file", "case-ambiguous manifest files",
                                 routeId=route_id, path=value, duplicateOf=all_seen[folded]))
    else:
        all_seen[folded] = value
    if not candidate.exists():
        findings.append(_finding("BLOCK", "missing-file", f"context file is missing: {value}",
                                 routeId=route_id, path=value))
    elif not candidate.is_file():
        findings.append(_finding("BLOCK", "unsupported-file", f"not a regular file: {value}",
                                 routeId=route_id, path=value))
    if findings:
        return None, findings
    return {"path": value, "candidate": candidate, **budgets}, []

def _validate_route(route: Any, index: int, root: Path, route_seen: dict[str, str],
                    all_files: dict[str, str]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    location = f"routes[{index}]"
    if not isinstance(route, dict):
        return None, [_finding("BLOCK", "invalid-route", f"{location} must be an object")]
    findings = _unknown(route, {"id", "files", "maxBytes", "maxTokens"}, location)
    budgets, budget_findings = _budgets(route, location)
    findings.extend(budget_findings)
    route_id = route.get("id")
    if not isinstance(route_id, str) or not route_id or route_id.strip() != route_id:
        findings.append(_finding("BLOCK", "invalid-route-id", f"{location}.id is invalid"))
        route_id = f"<invalid:{index}>"
    elif route_id.casefold() in route_seen:
        findings.append(_finding("BLOCK", "duplicate-route-id", f"duplicate route ID {route_id!r}",
                                 routeId=route_id, duplicateOf=route_seen[route_id.casefold()]))
    else:
        route_seen[route_id.casefold()] = route_id
    files = route.get("files")
    normalized: list[dict[str, Any]] = []
    if not isinstance(files, list) or not files:
        findings.append(_finding("BLOCK", "empty-files", f"{location}.files must be non-empty",
                                 routeId=route_id))
    else:
        local_seen: dict[str, str] = {}
        for file_index, entry in enumerate(files):
            item, problems = _validate_file(entry, root, route_id,
                f"{location}.files[{file_index}]", local_seen, all_files)
            findings.extend(problems)
            if item:
                normalized.append(item)
    if findings:
        return None, findings
    return {"id": route_id, "files": normalized, **budgets}, []

def _validate(document: Any, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(document, dict):
        return [], [_finding("BLOCK", "invalid-manifest", "manifest must be an object")]
    findings = _unknown(document, {"schemaVersion", "tokenizer", "routes"}, "manifest")
    if document.get("schemaVersion") != 1 or isinstance(document.get("schemaVersion"), bool):
        findings.append(_finding("BLOCK", "schema-version", "schemaVersion must be 1"))
    if document.get("tokenizer") != ENCODING:
        findings.append(_finding("BLOCK", "tokenizer-contract", f"tokenizer must be {ENCODING!r}"))
    configured = document.get("routes")
    if not isinstance(configured, list) or not configured:
        findings.append(_finding("BLOCK", "empty-routes", "routes must be a non-empty array"))
        return [], findings
    routes: list[dict[str, Any]] = []
    route_seen: dict[str, str] = {}
    all_files: dict[str, str] = {}
    for index, route in enumerate(configured):
        item, problems = _validate_route(route, index, root, route_seen, all_files)
        findings.extend(problems)
        if item:
            routes.append(item)
    return routes, findings

def _measure(path: Path, tokenizer: Tokenizer) -> dict[str, Any]:
    try:
        before, payload, after = path.stat(), path.read_bytes(), path.stat()
    except OSError as exc:
        raise ContextBudgetError(f"cannot read {path}: {exc}") from exc
    identity = lambda stat: (stat.st_size, stat.st_mtime_ns, getattr(stat, "st_ino", 0))
    if identity(before) != identity(after) or len(payload) != after.st_size:
        raise ContextBudgetError(f"file changed while being measured: {path}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContextBudgetError(f"file is not valid UTF-8: {path}: {exc}") from exc
    tokens, token_error = None, tokenizer.reason
    if tokenizer.available and tokenizer.count:
        try:
            tokens, token_error = tokenizer.count(text), None
        except Exception as exc:
            token_error = f"{type(exc).__name__}: {exc}"
    return {"bytes": len(payload), "chars": len(text), "tokens": tokens,
            "sha256": hashlib.sha256(payload).hexdigest(), "tokenError": token_error}

def _check(actual: int | None, maximum: int, reason: str | None = None) -> dict[str, Any]:
    if actual is None:
        return {"status": "NOT_CHECKED", "actual": None, "maximum": maximum,
                "reason": reason or "exact measurement unavailable"}
    return {"status": "GREEN" if actual <= maximum else "BLOCK", "actual": actual,
            "maximum": maximum, "remaining": maximum - actual}

def _status(items: list[str]) -> str:
    return "BLOCK" if "BLOCK" in items else "NOT_CHECKED" if "NOT_CHECKED" in items else "GREEN"

def _file_report(route_id: str, item: dict[str, Any], tokenizer: Tokenizer,
                 cache: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    key, path = item["path"].casefold(), item["path"]
    try:
        if key not in cache:
            cache[key] = _measure(item["candidate"], tokenizer)
        metrics = cache[key]
    except ContextBudgetError as exc:
        report = {"path": path, "status": "BLOCK", "budgets": {
            "maxBytes": item["maxBytes"], "maxTokens": item["maxTokens"]},
            "measurement": None, "checks": {}}
        return report, [_finding("BLOCK", "measurement-error", str(exc),
                                 routeId=route_id, path=path)]
    byte_check = _check(metrics["bytes"], item["maxBytes"])
    token_check = _check(metrics["tokens"], item["maxTokens"], metrics["tokenError"])
    findings: list[dict[str, Any]] = []
    for name, check in (("byte", byte_check), ("token", token_check)):
        if check["status"] == "BLOCK":
            findings.append(_finding("BLOCK", f"file-{name}-budget-exceeded",
                f"{path} exceeds its {name} budget", routeId=route_id, path=path,
                actual=check["actual"], maximum=check["maximum"]))
        elif check["status"] == "NOT_CHECKED":
            findings.append(_finding("NOT_CHECKED", "file-token-budget-not-checked",
                f"{path} exact Token budget was not checked", routeId=route_id, path=path,
                maximum=check["maximum"], reason=check["reason"]))
    report = {"path": path, "status": _status([byte_check["status"], token_check["status"]]),
        "budgets": {"maxBytes": item["maxBytes"], "maxTokens": item["maxTokens"]},
        "measurement": {key: metrics[key] for key in ("bytes", "chars", "tokens", "sha256")},
        "checks": {"bytes": byte_check, "tokens": token_check}}
    return report, findings

def _route_report(route: dict[str, Any], tokenizer: Tokenizer,
                  cache: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    files, findings = [], []
    for item in route["files"]:
        report, problems = _file_report(route["id"], item, tokenizer, cache)
        files.append(report)
        findings.extend(problems)
    measured = [item for item in files if item["measurement"]]
    totals = {name: sum(item["measurement"][name] for item in measured)
              for name in ("bytes", "chars")}
    values = [item["measurement"]["tokens"] for item in measured]
    totals["tokens"] = sum(values) if len(measured) == len(files) and all(v is not None for v in values) else None
    totals["files"] = len(files)
    byte_check = _check(totals["bytes"], route["maxBytes"])
    token_reason = next((item["checks"].get("tokens", {}).get("reason") for item in files
                         if item["status"] == "NOT_CHECKED"), None)
    token_check = _check(totals["tokens"], route["maxTokens"], token_reason)
    for name, check in (("byte", byte_check), ("token", token_check)):
        if check["status"] == "BLOCK":
            findings.append(_finding("BLOCK", f"route-{name}-budget-exceeded",
                f"route {route['id']!r} exceeds its aggregate {name} budget",
                routeId=route["id"], actual=check["actual"], maximum=check["maximum"]))
        elif check["status"] == "NOT_CHECKED":
            findings.append(_finding("NOT_CHECKED", "route-token-budget-not-checked",
                f"route {route['id']!r} exact Token budget was not checked",
                routeId=route["id"], maximum=check["maximum"], reason=check["reason"]))
    statuses = [item["status"] for item in files] + [byte_check["status"], token_check["status"]]
    report = {"id": route["id"], "status": _status(statuses),
        "budgets": {"maxBytes": route["maxBytes"], "maxTokens": route["maxTokens"]},
        "totals": totals, "checks": {"bytes": byte_check, "tokens": token_check}, "files": files}
    return report, findings

def _base(root: Path, manifest: dict[str, Any], tokenizer: Tokenizer) -> dict[str, Any]:
    return {"schemaVersion": 1, "root": str(root), "manifest": manifest,
            "tokenizer": tokenizer.as_json(), "aggregateMethod": "sum-of-file-measurements"}

def _summary(routes: list[dict[str, Any]], unique_files: int) -> dict[str, int]:
    return {"configuredRoutes": len(routes),
        "greenRoutes": sum(item["status"] == "GREEN" for item in routes),
        "blockedRoutes": sum(item["status"] == "BLOCK" for item in routes),
        "notCheckedRoutes": sum(item["status"] == "NOT_CHECKED" for item in routes),
        "routeFileEntries": sum(len(item["files"]) for item in routes), "uniqueFiles": unique_files}

def evaluate(document: Any, root: Path, manifest: dict[str, Any] | None = None,
             tokenizer: Tokenizer | None = None) -> dict[str, Any]:
    root, tokenizer = root.resolve(), tokenizer or load_tokenizer()
    base = _base(root, manifest or _memory_identity(document), tokenizer)
    if not root.is_dir():
        findings = [_finding("BLOCK", "invalid-root", f"target is not a directory: {root}")]
        return {**base, "status": "BLOCK", "blocking": True, "inventory": [],
                "routes": [], "summary": _summary([], 0), "findings": findings}
    routes, findings = _validate(document, root)
    if findings:
        configured = len(document.get("routes", [])) if isinstance(document, dict) and isinstance(document.get("routes"), list) else 0
        summary = _summary([], 0)
        summary["configuredRoutes"] = configured
        return {**base, "status": "BLOCK", "blocking": True, "inventory": [],
                "routes": [], "summary": summary, "findings": findings}
    cache: dict[str, dict[str, Any]] = {}
    reports: list[dict[str, Any]] = []
    findings = []
    for route in routes:
        report, problems = _route_report(route, tokenizer, cache)
        reports.append(report)
        findings.extend(problems)
    display = {item["path"].casefold(): item["path"] for route in routes for item in route["files"]}
    inventory = [{"path": display[key], **{name: metrics[name]
                  for name in ("bytes", "chars", "tokens", "sha256")}}
                 for key, metrics in sorted(cache.items())]
    status = _status([item["status"] for item in reports])
    return {**base, "status": status, "blocking": status != "GREEN", "inventory": inventory,
            "routes": reports, "summary": _summary(reports, len(inventory)), "findings": findings}

def exit_code(report: dict[str, Any]) -> int:
    if report.get("status") == "GREEN":
        return 0
    findings = report.get("findings", [])
    if report.get("status") == "NOT_CHECKED" or any(x.get("status") == "NOT_CHECKED" for x in findings):
        return 2
    budget = {f"{owner}-{unit}-budget-exceeded" for owner in ("file", "route")
              for unit in ("byte", "token")}
    codes = {item.get("code") for item in findings}
    return 1 if codes and codes <= budget else 2

def _emit(path: Path | None, document: dict[str, Any], quiet: bool) -> None:
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if path:
        destination = path.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
        os.close(handle)
        temporary_path = Path(temporary)
        try:
            temporary_path.write_text(payload, encoding="utf-8", newline="\n")
            os.replace(temporary_path, destination)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
    if not quiet:
        print(payload, end="")

def _test_tokenizer(available: bool = True) -> Tokenizer:
    counter = (lambda text: len(text.encode())) if available else None
    return Tokenizer(available, "self-test" if available else None,
                     None if available else "unavailable fixture", counter, "self-test-exact-counter")

def _test_manifest(routes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schemaVersion": 1, "tokenizer": ENCODING, "routes": routes}

def _test_route(route_id: str, paths: list[str], total: int = 100) -> dict[str, Any]:
    return {"id": route_id, "files": [{"path": path, "maxBytes": 10, "maxTokens": 10}
            for path in paths], "maxBytes": total, "maxTokens": total}

def _test_measurements(root: Path) -> dict[str, Any]:
    tokenizer = _test_tokenizer()
    green = _test_manifest([_test_route("green", ["alpha.md", "beta.md"])])
    if evaluate(green, root, tokenizer=tokenizer)["status"] != "GREEN":
        raise AssertionError("green control failed")
    dense = _test_manifest([_test_route("dense", ["dense.md"], 2000)])
    report = evaluate(dense, root, tokenizer=tokenizer)
    if not any(item["code"] == "file-byte-budget-exceeded" for item in report["findings"]):
        raise AssertionError("dense single-line overflow passed")
    aggregate = _test_manifest([_test_route("aggregate", ["alpha.md", "beta.md"], 8)])
    report = evaluate(aggregate, root, tokenizer=tokenizer)
    if any(item["status"] != "GREEN" for item in report["routes"][0]["files"]):
        raise AssertionError("aggregate fixture did not preserve passing files")
    if not any(item["code"] == "route-byte-budget-exceeded" for item in report["findings"]):
        raise AssertionError("aggregate overflow passed")
    return green

def _test_invalid(root: Path) -> None:
    tokenizer = _test_tokenizer()
    missing = _test_manifest([_test_route("missing", ["missing.md"])])
    if not any(item["code"] == "missing-file" for item in evaluate(missing, root, tokenizer=tokenizer)["findings"]):
        raise AssertionError("missing file passed")
    invalid = _test_manifest([_test_route("duplicate", ["alpha.md", "ALPHA.MD", "../x.md"]),
                              _test_route("DUPLICATE", ["beta.md"])])
    codes = {item["code"] for item in evaluate(invalid, root, tokenizer=tokenizer)["findings"]}
    if not {"duplicate-file", "duplicate-route-id", "unsafe-path"} <= codes:
        raise AssertionError(f"invalid manifest controls incomplete: {codes}")
    bad = _test_manifest([_test_route("bad-budget", ["alpha.md"])])
    bad["routes"][0]["files"][0]["maxBytes"] = 0
    if not any(item["code"] == "invalid-budget" for item in evaluate(bad, root, tokenizer=tokenizer)["findings"]):
        raise AssertionError("malformed budget passed")

def _test_output_and_unavailable(root: Path, green: dict[str, Any]) -> None:
    report = evaluate(green, root, tokenizer=_test_tokenizer(False))
    if report["status"] != "NOT_CHECKED" or not report["blocking"] or exit_code(report) != 2:
        raise AssertionError("unavailable tokenizer produced a false PASS")
    output = root / "quiet-output.json"
    _emit(output, report, quiet=True)
    if json.loads(output.read_text(encoding="utf-8")) != report:
        raise AssertionError("quiet output was not one preserved JSON document")

def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-context-budget-") as raw:
        root = Path(raw)
        (root / "alpha.md").write_text("alpha", encoding="utf-8")
        (root / "beta.md").write_text("beta", encoding="utf-8")
        (root / "dense.md").write_text("dense" * 200, encoding="utf-8")
        green = _test_measurements(root)
        _test_invalid(root)
        _test_output_and_unavailable(root, green)

def _error(message: str, root: Path | None = None,
           manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    base = _base(root.resolve() if root else Path.cwd().resolve(), manifest or {}, load_tokenizer())
    finding = _finding("BLOCK", "measurement-error", message)
    return {**base, "status": "BLOCK", "blocking": True, "inventory": [], "routes": [],
            "summary": _summary([], 0), "findings": [finding]}

def build_parser() -> argparse.ArgumentParser:
    parser = JsonParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser

def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except ContextBudgetError as exc:
        report = _error(str(exc))
        _emit(None, report, False)
        return 2
    if args.quiet and not args.output:
        report = _error("--quiet requires --output", args.target)
        _emit(None, report, False)
        return 2
    if args.self_test:
        try:
            run_self_test()
            report = {"schemaVersion": 1, "status": "GREEN", "selfTest": "passed",
                      "cases": ["green-control", "dense-single-line-overflow", "aggregate-overflow",
                                "missing-duplicate-traversal", "malformed-budget",
                                "tokenizer-unavailable", "quiet-json-output"]}
            _emit(args.output, report, args.quiet)
            return 0
        except Exception as exc:
            report = _error(f"self-test failed: {type(exc).__name__}: {exc}")
            _emit(args.output, report, args.quiet)
            return 2
    if not args.target or not args.manifest:
        report = _error("target and --manifest are required", args.target)
        _emit(args.output, report, args.quiet)
        return 2
    identity: dict[str, Any] | None = None
    try:
        source = args.manifest.absolute()
        junction = hasattr(source, "is_junction") and source.is_junction()  # type: ignore[attr-defined]
        if source.is_symlink() or junction:
            raise ContextBudgetError("manifest cannot be a symlink or junction")
        source = source.resolve(strict=True)
        if not source.is_file():
            raise ContextBudgetError("manifest must be a regular file")
        payload = source.read_bytes()
        identity = _manifest_identity(str(source), payload)
        document = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=_json_object)
        report = evaluate(document, args.target, identity, load_tokenizer())
    except (OSError, UnicodeError, json.JSONDecodeError, ContextBudgetError) as exc:
        report = _error(f"{type(exc).__name__}: {exc}", args.target, identity)
    _emit(args.output, report, args.quiet)
    return exit_code(report)

if __name__ == "__main__":
    raise SystemExit(main())
