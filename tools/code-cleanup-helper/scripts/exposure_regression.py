"""Owned exposure fixtures; passing them is not an anti-reversing guarantee."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
import check_release_exposure as checker


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="cleanup-exposure-") as raw:
        root = Path(raw)
        clean = root / "clean.txt"
        clean.write_bytes(b"owned clean fixture\n")
        assert checker.audit(clean)["status"] == "PASS"
        empty = root / "empty"
        empty.mkdir()
        assert checker.audit(empty)["status"] == "NOT_CHECKED", "empty scope became clean"
        data = bytearray(256)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:68] = b"PE\0\0"
        struct.pack_into("<H", data, 84, 120)
        struct.pack_into("<H", data, 88, 0x20B)
        struct.pack_into("<H", data, 158, 0x140)
        native = root / "owned.exe"
        native.write_bytes(data)
        report = checker.audit(native)
        flags = report["inventory"][0]["facts"]["pe"]
        assert flags["aslr"] and flags["nx_compatible"]
        assert flags["runtime_enforcement"] == "NOT_CHECKED", "PE bits became runtime proof"
        assert report["evidence_class"] == "static-release-exposure-only"
        private_path = "C:" + "/Users/" + "fixture-owner/private-project/"
        exposed = root / "exposed.bin"
        exposed.write_bytes(private_path.encode() + b"\x01" + private_path.encode("utf-16-le"))
        report = checker.audit(exposed)
        assert len(report["findings"]) == 2 and report["status"] == "REVIEW"
        assert "fixture-owner" not in json.dumps(report), "recovered private string was reflected"
        credential = "gh" + "p_" + "a" * 36
        exposed.write_bytes(b"\x01" + credential.encode("utf-16-le"))
        report = checker.audit(exposed)
        assert report["findings"][0]["code"] == "credential-shaped-content"
        assert credential not in json.dumps(report), "credential was reflected"
        source_map = root / "bundle.js.map"
        source_map.write_text(json.dumps({"version": 3, "sources": ["a.ts"], "sourcesContent": ["sensitive original source"]}), encoding="utf-8")
        report = checker.audit(source_map)
        assert report["findings"][0]["code"] == "source-map-original-source"
        assert "sensitive original source" not in json.dumps(report)
        archive = root / "payload.zip"
        archive.write_bytes(b"PK\x03\x04unknown compressed content")
        assert checker.audit(archive)["status"] == "NOT_CHECKED", "archive envelope proved payload"
        native.write_bytes(b"MZ")
        assert checker.audit(native)["status"] == "NOT_CHECKED", "malformed PE became clean"
        with patch.object(checker, "MAX_FILE_BYTES", 2):
            assert checker.audit(clean)["status"] == "NOT_CHECKED", "oversized file was silently excluded"
    return {"status": "PASS",
            "positiveFixtureIds": ["exposure.encoded-paths", "exposure.encoded-credential", "exposure.source-content"],
            "negativeFixtureIds": ["exposure.clean-control", "exposure.archive-unknown", "exposure.malformed-pe",
                                   "exposure.byte-bound", "exposure.no-reflection"],
            "scope": "owned static-exposure calibration; no runtime or anti-reversing claim"}


if __name__ == "__main__":
    run_self_test()
    print("Release exposure regression controls passed")
