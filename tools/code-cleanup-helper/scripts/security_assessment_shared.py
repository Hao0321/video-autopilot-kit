"""Shared constants and primitives for security-assessment validation."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
FORBIDDEN_RECEIPT_KEYS = {
    "match", "matchedvalue", "matched_value", "rawmatch", "raw_match", "snippet", "secret", "password",
    "token", "apikey", "api_key", "rawstdout", "rawstderr",
}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|bearer)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(?:[a-z]:\\Users\\|/" r"Users/|/" r"home/)[^\s\"']+"),
)
TASK_STATUSES = {"completed", "findings", "not_tested", "failed", "timed_out", "cancelled"}
TERMINAL_COMPLETE = {"completed", "findings"}
SEVERITIES = {"informational", "low", "medium", "high", "critical"}
CONFIDENCE = {"low", "medium", "high"}
FINDING_STATUSES = {"open", "resolved", "false_positive"}
ACTIVITY_TIERS = {"local-static", "passive-discovery", "low-impact-contact", "active-safe"}
LICENSE_DISPOSITIONS = {
    "allowed", "source-offer", "source-archive", "upstream-pinned",
    "generated-inventory", "not-distributed", "manual-review",
}
LIMIT_FIELDS = {
    "timeoutSeconds": 86_400,
    "memoryMiB": 1_048_576,
    "pids": 4_096,
    "outputBytes": 1_073_741_824,
    "outputFiles": 100_000,
    "outputDepth": 128,
}
AUTH_LIMIT_FIELDS = {
    "requestsPerSecond": 100,
    "concurrency": 32,
    "deadlineSeconds": 86_400,
}
METADATA_DESTINATIONS = {"169.254.169.254", "metadata.google.internal"}
MAX_RECEIPT_BYTES = 5 * 1024 * 1024
MAX_EVIDENCE_BYTES = 256 * 1024 * 1024
MAX_EVIDENCE_COUNT = 512
MAX_TOTAL_EVIDENCE_BYTES = 256 * 1024 * 1024
MAX_NESTING_DEPTH = 32
MAX_LIST_ITEMS = 1_024
MAX_OBJECT_FIELDS = 128
MAX_STRING_CHARS = 8_192
MAX_TOTAL_NODES = 50_000
MAX_TOTAL_STRING_CHARS = 2 * 1024 * 1024
MAX_INTEGER_ABS = (1 << 63) - 1
WINDOWS_INVALID_PATH_CHARS = frozenset('<>:"|?*')
WINDOWS_RESERVED_NAMES = frozenset({
    "con", "prn", "aux", "nul", "clock$", "conin$", "conout$",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
})
WINDOWS_DEVICE_DIGIT_TRANSLATION = str.maketrans({"¹": "1", "²": "2", "³": "3"})
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
TARGET_IDENTITY_PROFILE = "cleanup-security-target-identity/v1"
TARGET_PRODUCT_MAX_CHARS = 200
TARGET_PRODUCT_MAX_UTF8_BYTES = 512
TARGET_VERSION_MAX_CHARS = 128
TARGET_VERSION_MAX_UTF8_BYTES = 256
SECURITY_CONTROL_PROFILE = "cleanup-security-control-coverage/v1"
SECURITY_CONTROL_IDS = (
    "security.scan-scope",
    "security.scan-coverage",
    "security.scanner-provenance",
    "security.finding-normalization",
    "security.engine-admission",
    "security.adapter-integrity",
)


FailureSink = Callable[..., None]
GapSink = Callable[..., None]


class BoundedFileError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def file_identity(
    path: Path,
    *,
    max_bytes: int | None = None,
    require_nonempty: bool = False,
) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise BoundedFileError("not-regular")
        if require_nonempty and before.st_size <= 0:
            raise BoundedFileError("empty")
        if max_bytes is not None and before.st_size > max_bytes:
            raise BoundedFileError("too-large")
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            if max_bytes is not None and size > max_bytes:
                raise BoundedFileError("too-large")
            digest.update(chunk)
        after = os.fstat(handle.fileno())
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(getattr(before, field, None) != getattr(after, field, None) for field in stable_fields):
            raise BoundedFileError("changed")
        if size != before.st_size:
            raise BoundedFileError("changed")
    return {"bytes": size, "sha256": digest.hexdigest()}


def read_bytes_bounded(path: Path, *, max_bytes: int) -> tuple[bytes, dict[str, Any]]:
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > max_bytes:
            reason = "empty" if before.st_size <= 0 else "too-large" if before.st_size > max_bytes else "not-regular"
            raise BoundedFileError(reason)
        raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes or handle.read(1):
            raise BoundedFileError("too-large")
        after = os.fstat(handle.fileno())
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(getattr(before, field, None) != getattr(after, field, None) for field in stable_fields):
            raise BoundedFileError("changed")
        if len(raw) != before.st_size:
            raise BoundedFileError("changed")
    return raw, {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def link_like(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def _valid_path_part(part: str) -> bool:
    basename = (
        part.split(".", 1)[0]
        .rstrip(" .")
        .casefold()
        .translate(WINDOWS_DEVICE_DIGIT_TRANSLATION)
    )
    return bool(
        part
        and not part.endswith((" ", "."))
        and basename not in WINDOWS_RESERVED_NAMES
        and not any(character in WINDOWS_INVALID_PATH_CHARS for character in part)
        and not any(unicodedata.category(character).startswith("C") for character in part)
    )


def safe_path(root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not relative_path(value):
        return None, "path must be a non-empty root-relative POSIX string"
    relative = PurePosixPath(value)
    unresolved = root
    for part in relative.parts:
        unresolved = unresolved / part
        if link_like(unresolved):
            return None, "path traverses a symlink or junction"
    try:
        candidate = unresolved.resolve()
    except (OSError, RuntimeError):
        return None, "path cannot be resolved safely"
    if candidate != root and root not in candidate.parents:
        return None, "path resolves outside the project root"
    return candidate, None


def relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    relative = PurePosixPath(value)
    return bool(
        relative.parts
        and not relative.is_absolute()
        and "." not in relative.parts
        and ".." not in relative.parts
        and all(_valid_path_part(part) for part in relative.parts)
        and relative.as_posix() == value
    )


def closed_fields(value: Any, allowed: set[str], label: str, fail: FailureSink) -> None:
    if isinstance(value, dict):
        unknown = sorted(set(value) - allowed)
        if unknown:
            fail("unknown-field", f"{label} contains fields outside schema v1", location=label, fields=unknown)


def timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def iso_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def string_list(
    value: Any,
    label: str,
    fail: FailureSink,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        fail("invalid-string-list", f"{label} must be a string array", location=label)
        return []
    folded = [item.casefold() for item in value]
    if len(folded) != len(set(folded)):
        fail("duplicate-id", f"{label} contains case-insensitive duplicates", location=label)
    if not value and not allow_empty:
        fail("empty-list", f"{label} must not be empty", location=label)
    return value


def bounded_limits(
    value: Any,
    expected: dict[str, int],
    label: str,
    fail: FailureSink,
) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(expected):
        fail("invalid-resource-bounds", f"{label} must declare the closed-world limit set", location=label)
        return {}
    result: dict[str, int] = {}
    for name, ceiling in expected.items():
        observed = value.get(name)
        if isinstance(observed, bool) or not isinstance(observed, int) or not 0 < observed <= ceiling:
            fail("unbounded-resource", f"{label}.{name} must be positive and bounded", location=f"{label}.{name}")
        else:
            result[name] = observed
    return result


def sensitive_receipt_content(value: Any, path: str = "receipt") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9_]", "", str(key).casefold())
            child_path = f"{path}.{key}"
            if normalized in FORBIDDEN_RECEIPT_KEYS:
                hits.append(child_path)
            hits.extend(sensitive_receipt_content(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(sensitive_receipt_content(child, f"{path}[{index}]"))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
        hits.append(path)
    return hits


def redact_sensitive_values(value: Any) -> Any:
    """Remove sensitive string values from any user-visible result structure."""
    if isinstance(value, dict):
        return {key: redact_sensitive_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_values(child) for child in value]
    if isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
        return "[REDACTED]"
    return value


def safe_identity_text(value: Any, *, max_chars: int) -> bool:
    """Accept a bounded printable identity that is safe to return to callers."""
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and len(value) <= max_chars
        and not any(unicodedata.category(character).startswith("C") for character in value)
        and not any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS)
    )


def safe_target_identity(value: Any, *, max_chars: int, max_utf8_bytes: int) -> bool:
    return bool(
        safe_identity_text(value, max_chars=max_chars)
        and isinstance(value, str)
        and unicodedata.normalize("NFC", value) == value
        and len(value.encode("utf-8")) <= max_utf8_bytes
    )


def document_structure_within_limits(document: Any) -> bool:
    """Bound recursive work before schema-specific validation begins."""
    stack: list[tuple[Any, int]] = [(document, 0)]
    seen_containers: set[int] = set()
    nodes = 0
    string_chars = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_TOTAL_NODES or depth > MAX_NESTING_DEPTH:
            return False
        if isinstance(value, dict):
            identity = id(value)
            if identity in seen_containers or len(value) > MAX_OBJECT_FIELDS:
                return False
            seen_containers.add(identity)
            for key, child in value.items():
                if not isinstance(key, str) or len(key) > MAX_STRING_CHARS:
                    return False
                string_chars += len(key)
                stack.append((child, depth + 1))
        elif isinstance(value, list):
            identity = id(value)
            if identity in seen_containers or len(value) > MAX_LIST_ITEMS:
                return False
            seen_containers.add(identity)
            stack.extend((child, depth + 1) for child in value)
        elif isinstance(value, str):
            if len(value) > MAX_STRING_CHARS:
                return False
            string_chars += len(value)
        elif isinstance(value, bool) or value is None:
            pass
        elif isinstance(value, int):
            if abs(value) > MAX_INTEGER_ABS:
                return False
        elif isinstance(value, float):
            return False
        if string_chars > MAX_TOTAL_STRING_CHARS:
            return False
    return True
