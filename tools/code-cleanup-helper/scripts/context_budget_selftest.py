"""Context budget calibration fixtures, separate from measurement and CLI."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

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


def run_self_test(api) -> None:
    import tempfile
    globals().update({name: getattr(api, name) for name in ("ENCODING", "Tokenizer", "evaluate", "exit_code", "_emit")})
    with tempfile.TemporaryDirectory(prefix="cleanup-context-budget-") as raw:
        root = Path(raw)
        (root / "alpha.md").write_text("alpha", encoding="utf-8")
        (root / "beta.md").write_text("beta", encoding="utf-8")
        (root / "dense.md").write_text("dense" * 200, encoding="utf-8")
        green = _test_measurements(root)
        _test_invalid(root)
        _test_output_and_unavailable(root, green)
