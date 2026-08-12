"""Run quality_check against one real project video, never a synthetic fixture."""
from __future__ import annotations

from pathlib import Path

from project_paths import discover_project_root
from silent_vlog_maker.quality_check import verify_output


def _smallest_real_video(videos: Path) -> Path:
    candidates = [
        path for path in videos.rglob("*.mp4")
        if path.is_file() and "_archive" not in path.parts and path.stat().st_size > 100_000
    ]
    if not candidates:
        raise RuntimeError("quality-check corpus requires one non-archive project MP4")
    return min(candidates, key=lambda path: path.stat().st_size)


def main() -> None:
    root = discover_project_root(Path(__file__))
    video = _smallest_real_video(root / "videos")
    result = verify_output(video, expected_outro=False)
    width, height = result["resolution"]
    assert width > 0 and height > 0 and result["duration_sec"] > 0
    print("quality_check corpus GREEN", video.relative_to(root).as_posix())


if __name__ == "__main__":
    main()
