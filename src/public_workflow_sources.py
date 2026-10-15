"""Bind each authority's declared source closure without importing its code."""
from __future__ import annotations
import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from workflow_primitives import WorkflowError

MAX_SOURCE_BYTES = 1024 * 1024


def bounded_source(path: Path, label: str) -> bytes:
    before = path.lstat()
    def identity(info):
        return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size,
                getattr(info, "st_file_attributes", 0) & 0x400, info.st_nlink)
    def stable(info):
        return (*identity(info), info.st_mtime_ns, info.st_ctime_ns)
    if (not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400
            or before.st_nlink != 1 or not 0 < before.st_size <= MAX_SOURCE_BYTES):
        raise WorkflowError("Executable source must be a bounded unaliased regular file: " + label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(MAX_SOURCE_BYTES + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    if (len(data) != before.st_size or identity(before) != identity(opened)
            or stable(opened) != stable(after) or stable(before) != stable(current)
            or identity(current) != identity(after)):
        raise WorkflowError("Executable source changed during its bounded read: " + label)
    return data


def declared_sources(data: bytes) -> tuple[str, ...]:
    try:
        tree = ast.parse(data.decode("utf-8-sig"))
        declarations = [n.value for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "WORKFLOW_EXECUTABLE_SOURCES" for t in n.targets)]
        if len(declarations) != 1:
            raise ValueError("one declaration required")
        value = ast.literal_eval(declarations[0])
        if not isinstance(value, (list, tuple)) or not 3 <= len(value) <= 128:
            raise ValueError("bounded source list required")
        for name in value:
            if (not isinstance(name, str) or "\\" in name or ":" in name
                    or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                    or str(PurePosixPath(name)) != name or not name):
                raise ValueError("unsafe relative source")
        if len(set(name.casefold() for name in value)) != len(value):
            raise ValueError("duplicate source")
        if not {"workflow_state.py", "workflow_contract.json", "engine_continuity.py"}.issubset(value):
            raise ValueError("missing source authority")
        return tuple(value)
    except (SyntaxError, ValueError, TypeError, RecursionError, UnicodeError) as error:
        raise WorkflowError("Invalid declared workflow source closure") from error


def source_fingerprints(root: Path) -> list[dict]:
    try:
        declaration = bounded_source(root / "workflow_state.py", "workflow_state.py")
        names = declared_sources(declaration)
        rows = []
        for name in names:
            path = root / name
            parent = path.parent
            while parent != root:
                info = parent.lstat()
                if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise WorkflowError("Executable source ancestor is an alias: " + name)
                parent = parent.parent
            data = bounded_source(path, name)
            if name == "workflow_state.py" and data != declaration:
                raise WorkflowError("Workflow declaration changed during source binding")
            rows.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        return rows
    except OSError as error:
        raise WorkflowError("Cannot bind current workflow source closure") from error
