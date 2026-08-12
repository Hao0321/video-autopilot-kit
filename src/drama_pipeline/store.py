"""Durable project state for AI short-drama production.

All mutable state is scoped to one project.  Writes are atomic, source media is
never deleted, and every transition is appended to an audit log.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
PROJECT_SUBDIR = Path("videos") / "_AUTOPILOT" / "ai-short-drama"
SAFE_ID = re.compile(r"[^a-z0-9_-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str, fallback: str = "drama") -> str:
    ascii_value = value.strip().lower().encode("ascii", "ignore").decode("ascii")
    slug = SAFE_ID.sub("-", ascii_value).strip("-_")
    if not slug:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        slug = f"{fallback}-{digest}"
    return slug[:64]


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    handle, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ProjectStore:
    """Filesystem-backed short-drama job with resumable stage state."""

    def __init__(self, workspace: Path, project_dir: Path):
        self.workspace = workspace.expanduser().resolve()
        self.projects_root = (self.workspace / PROJECT_SUBDIR).resolve()
        self.root = project_dir.expanduser().resolve()
        if not is_within(self.root, self.projects_root):
            raise ValueError(f"Project must stay inside {self.projects_root}: {self.root}")

        self.config_path = self.root / "project.json"
        self.state_path = self.root / "state.json"
        self.pack_path = self.root / "production_pack.json"
        self.queue_path = self.root / "generation_queue.json"
        self.log_path = self.root / "events.jsonl"
        self.work_dir = self.root / "_work"
        self.assets_dir = self.root / "assets"
        self.episodes_dir = self.root / "episodes"

    @classmethod
    def create(
        cls,
        workspace: Path,
        *,
        topic: str,
        project_id: str | None = None,
        episodes: int = 3,
        duration: int = 60,
        format_name: str = "ai_live_action",
        market: str = "zh-TW social",
        surface: str = "TikTok/Reels/Shorts",
        aspect: str = "9:16",
        resolution: str = "1080x1920",
        provider: str = "browser",
        model: str = "seedance-2.5-capability-gated",
        max_retries: int = 2,
        references: list[str] | None = None,
    ) -> "ProjectStore":
        workspace = workspace.expanduser().resolve()
        if episodes < 1 or episodes > 60:
            raise ValueError("episodes must be between 1 and 60")
        if duration < 15 or duration > 180:
            raise ValueError("duration must be between 15 and 180 seconds")
        if max_retries < 0 or max_retries > 5:
            raise ValueError("max_retries must be between 0 and 5")

        base_id = slugify(project_id or topic)
        projects_root = (workspace / PROJECT_SUBDIR).resolve()
        projects_root.mkdir(parents=True, exist_ok=True)
        candidate = projects_root / base_id
        if candidate.exists():
            suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
            candidate = projects_root / f"{base_id}-{suffix}"
        store = cls(workspace, candidate)
        store._make_dirs()

        config = {
            "schema_version": SCHEMA_VERSION,
            "project_id": store.root.name,
            "topic": topic.strip(),
            "created_at": utc_now(),
            "episodes": episodes,
            "episode_duration_seconds": duration,
            "format": format_name,
            "market": market,
            "surface": surface,
            "aspect": aspect,
            "resolution": resolution,
            "provider": provider,
            "model": model,
            "max_retries": max_retries,
            "references": [str(Path(item).expanduser().resolve()) for item in references or []],
            "publish_requires_approval": True,
        }
        state = {
            "schema_version": SCHEMA_VERSION,
            "project_id": store.root.name,
            "stage": "initialized",
            "status": "ready",
            "updated_at": utc_now(),
            "stages": {
                name: {"status": "pending", "updated_at": None, "detail": ""}
                for name in ("plan", "validate", "compile", "generate", "build", "qa", "publish")
            },
            "last_error": None,
        }
        write_json_atomic(store.config_path, config)
        write_json_atomic(store.state_path, state)
        store.log("project_created", {"config": config})
        return store

    @classmethod
    def open(cls, workspace: Path, project: str | os.PathLike[str]) -> "ProjectStore":
        workspace = workspace.expanduser().resolve()
        raw = Path(project).expanduser()
        project_dir = raw.resolve() if raw.is_absolute() else (workspace / PROJECT_SUBDIR / raw).resolve()
        store = cls(workspace, project_dir)
        if not store.config_path.is_file():
            raise FileNotFoundError(f"Not a drama project: {store.root}")
        return store

    def _make_dirs(self) -> None:
        for path in (
            self.root,
            self.work_dir,
            self.assets_dir / "anchors",
            self.assets_dir / "shots",
            self.episodes_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def config(self) -> dict[str, Any]:
        return read_json(self.config_path)

    def state(self) -> dict[str, Any]:
        return read_json(self.state_path)

    def pack(self) -> dict[str, Any]:
        return read_json(self.pack_path)

    def queue(self) -> dict[str, Any]:
        return read_json(self.queue_path, {"schema_version": 1, "tasks": []})

    def save_pack(self, data: dict[str, Any]) -> None:
        write_json_atomic(self.pack_path, data)
        self.log("production_pack_saved", {"sha256": sha256_file(self.pack_path)})

    def save_queue(self, data: dict[str, Any]) -> None:
        data["updated_at"] = utc_now()
        write_json_atomic(self.queue_path, data)

    def set_stage(self, stage: str, status: str, detail: str = "") -> None:
        data = self.state()
        if stage not in data["stages"]:
            raise ValueError(f"Unknown stage: {stage}")
        data["stage"] = stage
        data["status"] = status
        data["updated_at"] = utc_now()
        data["stages"][stage] = {
            "status": status,
            "updated_at": data["updated_at"],
            "detail": detail,
        }
        if status == "failed":
            data["last_error"] = detail
        elif status in {"complete", "ready", "waiting"}:
            data["last_error"] = None
        write_json_atomic(self.state_path, data)
        self.log("stage_changed", {"stage": stage, "status": status, "detail": detail})

    def log(self, event: str, payload: dict[str, Any] | None = None) -> None:
        row = {"time": utc_now(), "event": event, "payload": payload or {}}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def relative(self, path: Path) -> str:
        resolved = path.expanduser().resolve()
        if not is_within(resolved, self.root):
            raise ValueError(f"Artifact is outside project: {resolved}")
        return resolved.relative_to(self.root).as_posix()

    def artifact(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not is_within(path, self.root):
            raise ValueError(f"Artifact path escapes project: {relative}")
        return path

    def summary(self) -> dict[str, Any]:
        queue = self.queue()
        counts: dict[str, int] = {}
        for task in queue.get("tasks", []):
            status = task.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return {
            "project": self.config(),
            "state": self.state(),
            "queue_counts": counts,
            "root": str(self.root),
            "production_pack": str(self.pack_path) if self.pack_path.is_file() else None,
        }
