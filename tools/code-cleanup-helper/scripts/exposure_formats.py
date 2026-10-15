"""Bounded static format triage; compressed and external payloads remain unknown."""
from __future__ import annotations
import json
from pathlib import Path
import re
from sync_safety import unique_object

TEXT_WINDOW = 64 * 1024
TEXT_OVERLAP = 4096
MAP_BYTES = 8 * 1024 * 1024
MAP_NODES = 4096
MAP_DEPTH = 32
PATH_ASCII = re.compile(rb"(?i)(?:[A-Z]:[\\/]+Users[\\/]|/(?:Users|home)/)")
OPAQUE_SUFFIXES = {".zip", ".gz", ".tgz", ".bz2", ".xz", ".zst", ".tar", ".rar", ".7z", ".asar", ".pak"}
OPAQUE_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\x1f\x8b",
                b"BZh", b"\xfd7zXZ\x00", b"7z\xbc\xaf\x27\x1c", b"Rar!\x1a\x07", b"\x28\xb5\x2f\xfd")


def encoded_path_pattern(encoding: str) -> re.Pattern:
    unit = rb"[A-Z]\x00" if encoding.endswith("le") else rb"\x00[A-Z]"
    slash = b"(?:" + b"|".join(re.escape(x.encode(encoding)) for x in ("/", "\\")) + b")"
    windows = unit + re.escape(":".encode(encoding)) + slash + b"+" + re.escape("Users".encode(encoding)) + slash
    posix = b"(?:" + b"|".join(re.escape(x.encode(encoding)) for x in ("/Users/", "/home/")) + b")"
    return re.compile(b"(?:" + windows + b"|" + posix + b")", re.IGNORECASE)


PATH_PATTERNS = (PATH_ASCII, encoded_path_pattern("utf-16-le"), encoded_path_pattern("utf-16-be"))


def path_offsets(data: bytes) -> list[int]:
    spans = []
    patterns = PATH_PATTERNS if b"\0" in data else (PATH_ASCII,)
    for pattern in patterns:
        match = pattern.search(data)
        if match and not any(match.start() < end and match.end() > start for start, end in spans):
            spans.append(match.span())
    return sorted(start for start, _end in spans)


def credential_candidate(data: bytes, patterns: tuple[bytes, ...]) -> bool:
    """Bound decode memory independently of delivered file size; overlap boundary tokens."""
    compiled = [re.compile(pattern.decode("ascii")) for pattern in patterns]
    for start in range(0, len(data), TEXT_WINDOW):
        window = data[max(0, start - TEXT_OVERLAP):start + TEXT_WINDOW]
        candidates = (window, window.replace(b"\0", b"")) if b"\0" in window else (window,)
        for candidate in candidates:
            text = candidate.decode("utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in compiled):
                return True
    return False


def source_map(data: bytes) -> tuple[bool, list[str]]:
    if len(data) > MAP_BYTES:
        return False, ["source-map-unparsed"]
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object)
        return inspect_maps(value)
    except (ValueError, UnicodeError, RecursionError):
        return False, ["source-map-unparsed"]


def inspect_maps(value: object) -> tuple[bool, list[str]]:
    pending, nodes, found, gaps = [(value, 0)], 0, False, set()
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if depth > MAP_DEPTH or nodes > MAP_NODES:
            gaps.add("source-map-bound-unparsed")
            break
        if not isinstance(current, dict) or type(current.get("version")) is not int or current["version"] != 3:
            gaps.add("source-map-unparsed")
            continue
        contents = current.get("sourcesContent")
        found |= isinstance(contents, list) and any(isinstance(x, str) and x for x in contents)
        if "sections" in current:
            sections = current["sections"]
            if not isinstance(sections, list) or len(sections) > MAP_NODES:
                gaps.add("source-map-bound-unparsed")
                continue
            for section in sections:
                if not isinstance(section, dict) or ("url" in section) == ("map" in section):
                    gaps.add("source-map-unparsed")
                elif "url" in section:
                    gaps.add("source-map-external-section-not-read")
                else:
                    pending.append((section["map"], depth + 1))
    return bool(found), sorted(gaps)


def opaque_container(path: Path, data: bytes) -> bool:
    return (path.suffix.casefold() in OPAQUE_SUFFIXES or data.startswith(OPAQUE_MAGIC)
            or data[257:262] == b"ustar")
