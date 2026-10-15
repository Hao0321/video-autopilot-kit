"""Public sync output containment and portable text byte semantics."""
from __future__ import annotations
import hashlib
import stat
from pathlib import Path, PurePosixPath
from public_sync_inventory import PRIVATE_PUBLIC_FILES, SYNC_RECEIPT_PATH, sync_expected_output_paths

OUTPUT_HASH_SEMANTICS = "sha256:utf8-bom-stripped:lf-normalized"

def _path_entry_metadata(path: Path):
    """Return no-follow metadata, or ``None`` only when the entry is absent."""
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        # An existing but unreadable entry is not safe to traverse.  The
        # caller deliberately reports a generic rule rather than the OS error,
        # because an error can contain a resolved private machine path.
        return False

def _is_link_or_reparse(path: Path, metadata) -> bool:
    """Recognize POSIX links and Windows symlink/junction reparse points."""
    if path.is_symlink():
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))

def _is_contained_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

def _resolve_entry(path: Path, *, strict: bool) -> Path:
    """Small seam used by deterministic no-symlink-permission self-tests."""
    return path.resolve(strict=strict)

def _safe_relative_output_path(relative: str) -> bool:
    """Accept only canonical POSIX paths below the distribution root."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return False
    raw_parts = relative.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in raw_parts):
        return False
    posix = PurePosixPath(relative)
    native = Path(relative)
    return (
        not posix.is_absolute()
        and not native.is_absolute()
        and not native.drive
        and posix.as_posix() == relative
    )

def _output_path_boundary_rule(repository: Path, relative: str) -> str | None:
    """Return a stable fail-closed rule for an unsafe managed output path.

    Neither the leaf nor an existing ancestor may be a symlink or reparse
    point.  This stricter rule prevents in-root alias collisions as well as
    outside-root writes.  No resolved path is returned to callers.
    """
    if not _safe_relative_output_path(relative):
        return "invalid-relative-path"
    try:
        resolved_root = _resolve_entry(repository, strict=False)
    except (OSError, RuntimeError):
        return "unresolvable-root"

    current = repository
    parts = relative.split("/")
    for index, part in enumerate(parts):
        current = current / part
        metadata = _path_entry_metadata(current)
        if metadata is None:
            # Once a component is absent, every deeper component is absent too.
            # Its nearest existing parent was already proven contained.
            break
        if metadata is False:
            return "unreadable-entry"
        alias = _is_link_or_reparse(current, metadata)
        if index == len(parts) - 1 and alias:
            return "output-alias"
        if alias:
            return "ancestor-alias"
        try:
            resolved = _resolve_entry(current, strict=True)
        except (OSError, RuntimeError):
            return "unresolvable-entry"
        if not _is_contained_path(resolved, resolved_root):
            return "ancestor-escape"
    return None

def _output_path_boundary_violations(
    repository: Path,
    relatives,
) -> dict[str, str]:
    violations: dict[str, str] = {}
    for relative in sorted(set(relatives)):
        rule = _output_path_boundary_rule(repository, relative)
        if rule is not None:
            violations[relative] = rule
    return violations

def _boundary_error(relative: str, rule: str) -> str:
    display = relative if _safe_relative_output_path(relative) else "<invalid-output-path>"
    return f"sync output path boundary violation [{rule}]: {display}"

def _assert_sync_output_boundaries(repository: Path) -> None:
    # Cleanup targets are mutations too.  Keep them explicit rather than
    # relying on their current ancestors overlapping expected output trees.
    managed = (
        set(sync_expected_output_paths())
        | set(PRIVATE_PUBLIC_FILES)
        | {SYNC_RECEIPT_PATH}
    )
    violations = _output_path_boundary_violations(repository, managed)
    if violations:
        details = [
            _boundary_error(relative, rule)
            for relative, rule in sorted(violations.items())[:20]
        ]
        raise ValueError("unsafe public sync destination: " + "; ".join(details))

def _write_utf8(path: Path, text: str) -> None:
    """Write deterministic LF text on every supported Python version."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

def _text_sha256(path: Path) -> str:
    """Hash the exact canonical UTF-8/LF payload shipped by release_manager."""
    text = path.read_bytes().decode("utf-8-sig")
    payload = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
