"""Owned encoded, indexed-map and opaque-payload false-green controls."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import check_release_exposure as checker
import exposure_formats as formats


def check_paths(root: Path) -> None:
    fixture = root / "owned.bin"
    for prefix in ("C:" + "/Users/", "/home/", "/Users/"):
        for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
            marker = prefix + "fixture-identity/private"
            fixture.write_bytes(b"\x01" + marker.encode(encoding))
            report = checker.audit(fixture)
            assert report["status"] == "REVIEW", (prefix, encoding)
            assert "fixture-identity" not in json.dumps(report), "private path was reflected"
            assert len(report["findings"]) == 1, "overlapping UTF-16 alignments duplicated a candidate"
    fixture.write_bytes(b"near miss: /homework/public /UsersGuide/public")
    assert checker.audit(fixture)["status"] == "PASS"


def check_maps(root: Path) -> None:
    path = root / "indexed.map"
    leaf = {"version": 3, "sources": ["owned.ts"], "sourcesContent": ["owned-original-source"]}
    value = {"version": 3, "sections": [{"offset": {"line": 0, "column": 0}, "map": leaf}]}
    path.write_text(json.dumps(value), encoding="utf-8")
    report = checker.audit(path)
    assert report["status"] == "REVIEW" and report["findings"][0]["code"] == "source-map-original-source"
    assert "owned-original-source" not in json.dumps(report)
    unknowns = [b"not json", b'{"version":true}', b'{"version":3,"sections":"invalid"}',
                b'{"version":3,"sourcesContent":["owned-source"],"sourcesContent":[]}',
                b'{"version":3,"sections":[{"url":"https://invalid.example/owned.map"}]}']
    for data in unknowns:
        path.write_bytes(data)
        assert checker.audit(path)["status"] == "NOT_CHECKED", "uninspected source map became clean"
    for _ in range(formats.MAP_DEPTH + 2):
        value = {"version": 3, "sections": [{"map": value}]}
    path.write_text(json.dumps(value), encoding="utf-8")
    assert checker.audit(path)["status"] == "NOT_CHECKED", "source-map depth bound became clean"
    path.write_text(json.dumps({"version": 3, "sources": ["public.js"], "sourcesContent": [None, ""]}), encoding="utf-8")
    assert checker.audit(path)["status"] == "PASS"


def check_containers(root: Path) -> None:
    path = root / "payload.bin"
    for magic in formats.OPAQUE_MAGIC:
        path.write_bytes(magic + b"owned opaque payload")
        assert checker.audit(path)["status"] == "NOT_CHECKED", "container magic became clean"
    for suffix in formats.OPAQUE_SUFFIXES:
        candidate = root / ("payload" + suffix)
        candidate.write_bytes(b"opaque envelope without recognized magic")
        assert checker.audit(candidate)["status"] == "NOT_CHECKED", "container suffix became clean"
    path.write_bytes(b"\0" * 257 + b"ustar" + b"\0" * 16)
    assert checker.audit(path)["status"] == "NOT_CHECKED"
    path.write_bytes(b"PK plain public text; not an archive signature")
    assert checker.audit(path)["status"] == "PASS"


def check_text_windows(root: Path) -> None:
    path = root / "boundary.bin"
    key = "gh" + "p_" + "a" * 36
    for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
        token = key.encode(encoding)
        for displacement in (1, 10, 32, 70):
            path.write_bytes(b"!" * (formats.TEXT_WINDOW - displacement) + token + b"!")
            report = checker.audit(path)
            assert report["status"] == "REVIEW", (encoding, displacement)
            assert key not in json.dumps(report)
    path.write_bytes(("gh" + "p_" + "a" * 29).encode())
    assert checker.audit(path)["status"] == "PASS", "short near-miss key matched"
    path.write_bytes(b"clean bytes")
    with patch.object(checker, "MAX_TOTAL_BYTES", 2):
        assert checker.audit(path)["status"] == "NOT_CHECKED", "total bound became clean"


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="cleanup-formats-") as raw:
        root = Path(raw)
        check_paths(root)
        check_maps(root)
        check_containers(root)
        check_text_windows(root)
    return {"status": "PASS", "scope": "owned static format and bounded decoder controls"}


if __name__ == "__main__":
    print(json.dumps(run_self_test()))
