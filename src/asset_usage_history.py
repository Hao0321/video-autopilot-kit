"""Read a bounded physical JSONL tail without loading an entire usage history."""
from __future__ import annotations
import os
from pathlib import Path

TAIL_BYTES = 4 * 1024 * 1024
BLOCK_BYTES = 64 * 1024


def tail_lines(path: Path, count: int = 2400) -> list[str]:
    if type(count) is not int or count < 1:
        raise ValueError("asset usage tail count must be a positive integer")
    chunks, newlines, read = [], 0, 0
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        position = handle.seek(0, os.SEEK_END)
        while position > 0 and newlines <= count:
            size = min(BLOCK_BYTES, position, TAIL_BYTES - read)
            if size <= 0:
                raise ValueError("asset usage tail exceeds the bounded reader; inspect the history")
            position -= size
            handle.seek(position)
            block = handle.read(size)
            chunks.append(block)
            newlines += block.count(b"\n")
            read += len(block)
        after = os.fstat(handle.fileno())
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("asset usage history changed during read; refresh again")
    data = b"".join(reversed(chunks))
    if position:
        data = data.split(b"\n", 1)[1]  # The first fragment may begin inside UTF-8 or a JSON row.
    lines = data.split(b"\n")
    if lines and not lines[-1]:
        lines.pop()
    return [line.decode("utf-8", errors="replace") for line in lines[-count:]]
