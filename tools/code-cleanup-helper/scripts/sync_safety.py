"""Read-only, bounded publication planning shared by skill maintainer scripts."""

from __future__ import annotations
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import copy

MANIFEST = ".code-cleanup-managed.json"
PRIVATE_DIRS = {".git", ".rd", "__pycache__", "node_modules", ".skill-staging", ".skill-proposals"}
MAX_BYTES = 8 * 1024 * 1024
SECRET_PATTERNS = (rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                   rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b", rb"\bAKIA[A-Z0-9]{16}\b")


class SyncError(ValueError):
    """The complete publication delta could not be safely planned."""


def relative_name(raw: str) -> str:
    parts = raw.split("/")
    if not raw or "\\" in raw or ":" in raw or PurePosixPath(raw).is_absolute():
        raise SyncError("unsafe relative path")
    if any(p in {"", ".", ".."} or p.endswith((".", " ")) or any(ord(c) < 32 for c in p) for p in parts):
        raise SyncError("unsafe relative path segment")
    if any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?", p) for p in parts):
        raise SyncError("reserved path segment")
    return raw


def link_like(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def checked_root(path: Path, *, allow_missing: bool = False) -> Path:
    """Reject linked ancestors before resolving their spelling away."""
    absolute = path.expanduser().absolute()
    for current in [*reversed(absolute.parents), absolute]:
        try:
            info = current.lstat()
        except FileNotFoundError:
            if not allow_missing:
                raise SyncError("publication root is missing") from None
        else:
            if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
                raise SyncError("publication root link/reparse rejected")
            if not stat.S_ISDIR(info.st_mode):
                raise SyncError("publication root is not a directory")
    return absolute.resolve()


def safe_path(root: Path, raw: str) -> Path:
    current = root
    for part in relative_name(raw).split("/"):
        current = current / part
        if (current.exists() or current.is_symlink()) and link_like(current):
            raise SyncError("link/reparse path rejected")
    current.resolve().relative_to(root.resolve())
    return current


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        data = handle.read(MAX_BYTES + 1)
        after = os.fstat(handle.fileno())
    if len(data) > MAX_BYTES:
        raise SyncError("publication file exceeds byte limit")
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise SyncError("publication input changed during read")
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SyncError("duplicate manifest key")
        result[key] = value
    return result


def ownership(root: Path) -> tuple[dict[str, str | None], str | None]:
    path = safe_path(root, MANIFEST)
    if not path.exists():
        return {}, None
    data = read_bytes(path)
    value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object)
    if not isinstance(value, dict) or value.get("schema_version") not in {1, 2}:
        raise SyncError("unsupported ownership manifest")
    paths, hashes = value.get("managed_paths"), value.get("managed_sha256", {})
    if not isinstance(paths, list) or not isinstance(hashes, dict):
        raise SyncError("invalid ownership manifest")
    if any(not isinstance(p, str) for p in paths) or len({p.casefold() for p in paths}) != len(paths):
        raise SyncError("duplicate or invalid managed path")
    result = {}
    for name in paths:
        relative_name(name)
        prior = hashes.get(name)
        if value["schema_version"] == 2 and (not isinstance(prior, str) or not re.fullmatch(r"[0-9a-f]{64}", prior)):
            raise SyncError("invalid ownership digest")
        result[name] = prior
    if value["schema_version"] == 2 and set(hashes) != set(paths):
        raise SyncError("ownership path/hash membership differs")
    return result, digest(data)


def privacy_check(data: bytes, name: str, config: dict) -> None:
    base = name.rsplit("/", 1)[-1].casefold()
    env_file = base == ".env" or (base.startswith(".env.") and base not in {".env.example", ".env.template"})
    if env_file or base in {"auth.json", "credentials.json", "id_rsa", "id_ed25519"} or base.endswith((".pem", ".key")):
        raise SyncError("private file selected for publication")
    texts = [data.decode("utf-8-sig", errors="ignore"), data.decode("utf-16-le", errors="ignore"),
             data.decode("utf-16-be", errors="ignore"), data.replace(b"\0", b"").decode("utf-8", errors="ignore")]
    for policy in [config.get("privacy", {}), config.get("sync", {}).get("privacy", {})]:
        for token in policy.get("tokens", []):
            if token and any(str(token).casefold() in text.casefold() for text in texts):
                raise SyncError("publication privacy token matched")
        for raw in policy.get("patterns", []):
            try:
                pattern = re.compile(raw, re.IGNORECASE)
            except re.error as exc:
                raise SyncError("invalid publication privacy pattern") from exc
            if any(pattern.search(text) for text in texts):
                raise SyncError("publication privacy pattern matched")
    if any(re.search(pattern.decode("ascii"), text) for pattern in SECRET_PATTERNS for text in texts):
        raise SyncError("credential-shaped publication content")


def source_files(root: Path, config: dict) -> list[str]:
    patterns = config.get("exclude", []) + config.get("sync", {}).get("ignore", [])
    rows = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False, onerror=walk_error):
        base = Path(directory)
        names[:] = [n for n in names if n not in PRIVATE_DIRS]
        if any(link_like(base / n) for n in names):
            raise SyncError("source directory link/reparse rejected")
        for name in files:
            rel = (base / name).relative_to(root).as_posix()
            if name.endswith((".pyc", ".pyo")) or name == MANIFEST:
                continue
            if not any(fnmatch.fnmatch(rel, p.replace("\\", "/")) for p in patterns):
                safe_path(root, rel)
                rows.append(rel)
                if len(rows) > 4096:
                    raise SyncError("publication file count exceeds limit")
    if len({p.casefold() for p in rows}) != len(rows):
        raise SyncError("case-folding publication path collision")
    return sorted(rows)


def walk_error(_error: OSError) -> None:
    raise SyncError("publication source subtree is unreadable")


def plan_sync(source: Path, destination: Path, config: dict, *, adopt_existing: bool = False,
              allow_empty: bool = False) -> dict:
    source = checked_root(source)
    destination = checked_root(destination, allow_missing=True)
    if source == destination or source in destination.parents or destination in source.parents:
        raise SyncError("publication roots overlap")
    previous, manifest_hash = ownership(destination)
    rows, total = [], 0
    selected = source_files(source, config)
    if not selected and not allow_empty:
        raise SyncError("empty publication selection requires explicit --allow-empty retirement")
    for name in selected:
        data = read_bytes(safe_path(source, name))
        total += len(data)
        if total > 64 * 1024 * 1024:
            raise SyncError("publication total bytes exceed limit")
        privacy_check(data, name, config)
        target = safe_path(destination, name)
        old = read_bytes(target) if target.exists() else None
        current_hash = digest(old) if old is not None else None
        if old is not None and old != data:
            prior = previous.get(name)
            if prior is not None and current_hash != prior:
                raise SyncError("modified managed destination would be overwritten")
            if prior is None and not adopt_existing:
                raise SyncError("unowned/legacy destination requires reviewed adoption")
        rows.append({"path": name, "data": data, "sha256": digest(data),
                     "before": current_hash, "changed": old != data})
    stale = []
    for name in sorted(set(previous) - {row["path"] for row in rows}):
        target = safe_path(destination, name)
        if target.exists():
            old_hash = digest(read_bytes(target))
            if previous[name] is None or old_hash != previous[name]:
                raise SyncError("stale destination has unknown or modified ownership")
            stale.append({"path": name, "before": old_hash})
    return {"source": source, "destination": destination, "rows": rows,
            "stale": stale, "manifest_before": manifest_hash,
            "selection_config": copy.deepcopy(config), "selected_paths": selected}


def verify_plan(plan: dict) -> None:
    checked_root(plan["source"])
    checked_root(plan["destination"], allow_missing=True)
    if source_files(plan["source"], plan["selection_config"]) != plan["selected_paths"]:
        raise SyncError("selected source inventory changed after planning")
    if ownership(plan["destination"])[1] != plan["manifest_before"]:
        raise SyncError("ownership manifest changed after planning")
    for row in plan["rows"]:
        if digest(read_bytes(safe_path(plan["source"], row["path"]))) != row["sha256"]:
            raise SyncError("source changed after planning")
    for row in [*plan["rows"], *plan["stale"]]:
        target = safe_path(plan["destination"], row["path"])
        current = digest(read_bytes(target)) if target.exists() else None
        if current != row["before"]:
            raise SyncError("destination changed after planning")
