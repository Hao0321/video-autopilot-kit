"""
silent_vlog_maker.frame_audit — M9/M21/M34 hi-res frame extraction + grid + scene cache.

解決 #003 馬來西亞 vlog 8/18 caption 錯位的根本痛點：
- 每 clip 抽 4 hi-res frames (start/early/mid/late) at 640×360
- 拼大 grid 一張圖讓 Claude Read 一次看完
- 描述 cache 寫 JSON，後續 build script 用作 ground truth
"""
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .audit import ClipAudit


# ─────────────────────────────────────────────────────────────────────
# Frame extraction (M9 / M21 / M34 強化)
# ─────────────────────────────────────────────────────────────────────

def extract_frames_hires(
    clip_path: Path,
    output_dir: Path,
    n_frames: int = 4,
    frame_width: int = 640,
    frame_height: int = 360,
    label: bool = True,
    duration_sec: float = None,  # 已知長度就不再 ffprobe (2026-06-10 perf)
) -> list[Path]:
    """Extract N hi-res frames at start/dur*1/3/dur*2/3/dur-0.5 — for caption verify.

    640×360 比舊版 320×180 大 4x，能看清招牌字 / 品牌 / 文字（M36 升級）。

    Returns: list of frame paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get duration (caller 已有 ClipAudit.duration_sec 時直接用 — 省 1 次 ffprobe/clip)
    if duration_sec and duration_sec > 0:
        dur = float(duration_sec)
    else:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(clip_path)],
            capture_output=True, text=True
        )
        try:
            dur = float(result.stdout.strip())
        except (ValueError, AttributeError):
            return []

    # Compute timestamps: start, early, mid, late
    if n_frames == 4:
        timestamps = [
            min(0.5, dur * 0.1),
            dur * 0.33,
            dur * 0.66,
            max(dur - 0.5, dur * 0.9),
        ]
    elif n_frames == 3:
        timestamps = [0.5, dur / 2, max(dur - 0.5, dur * 0.9)]
    else:
        timestamps = [dur * (i + 1) / (n_frames + 1) for i in range(n_frames)]

    stem = clip_path.stem
    frame_paths = []
    for i, ts in enumerate(timestamps):
        out_path = output_dir / f"{stem}_f{i}_{ts:.1f}s.jpg"
        vf = f"scale={frame_width}:{frame_height}:force_original_aspect_ratio=decrease," \
             f"pad={frame_width}:{frame_height}:(ow-iw)/2:(oh-ih)/2,format=yuvj420p"
        if label:
            # Yellow label with timestamp + filename — easy ID in grid
            vf += (
                f",drawtext=text='{stem} @{ts:.1f}s':fontsize=20:fontcolor=yellow:"
                f"borderw=2:bordercolor=black:x=10:y=10"
            )
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(ts), "-i", str(clip_path),
                 "-vf", vf, "-frames:v", "1", "-q:v", "3", str(out_path)],
                check=True
            )
            frame_paths.append(out_path)
        except subprocess.CalledProcessError:
            continue

    return frame_paths


def make_audit_grid(
    frame_paths: list[Path],
    output_path: Path,
    cols: int = 4,
    cell_w: int = 640,
    cell_h: int = 360,
) -> Optional[Path]:
    """Stitch frames into single hi-res grid image.

    Default 4 cols = one clip per row (4 frames = start/early/mid/late side-by-side).
    Pass cols=8+ if combining multiple clips per row.
    """
    if not frame_paths:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(frame_paths)
    rows = (n + cols - 1) // cols

    inputs = []
    for p in frame_paths:
        inputs.extend(["-i", str(p)])

    # Build xstack layout
    filter_inputs = "".join(f"[{i}:v]" for i in range(n))
    layout_parts = []
    for i in range(n):
        col = i % cols
        row = i // cols
        x = f"{col * cell_w}" if col > 0 else "0"
        y = f"{row * cell_h}" if row > 0 else "0"
        layout_parts.append(f"{x}_{y}")
    filter_complex = f"{filter_inputs}xstack=inputs={n}:layout={'|'.join(layout_parts)}"

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             *inputs, "-filter_complex", filter_complex, str(output_path)],
            check=True
        )
        return output_path
    except subprocess.CalledProcessError:
        return None


def audit_all_clips_frames(
    audits: list[ClipAudit],
    output_dir: Path,
    n_frames_per_clip: int = 4,
    grid_cols: int = 4,
    clips_per_grid: int = 6,
) -> list[Path]:
    """Process all clips: extract 4 hi-res frames each, build N grids of M clips.

    For 24 clips × 4 frames = 96 frames → 4 grids of 6 clips × 4 frames each (4×6 layout).

    Returns: list of grid image paths (Claude Read them to learn each clip's content).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "_frames"
    frames_dir.mkdir(exist_ok=True)

    all_frames = []
    for clip in audits:
        clip_path = Path(clip.filepath) if clip.filepath else Path(clip.filename)
        if not clip_path.exists():
            continue
        frames = extract_frames_hires(clip_path, frames_dir, n_frames=n_frames_per_clip,
                                      duration_sec=getattr(clip, 'duration_sec', None))
        all_frames.append((clip.filename, frames))

    # Build grids: clips_per_grid clips per grid, n_frames_per_clip frames per clip
    grid_paths = []
    for grid_idx in range(0, len(all_frames), clips_per_grid):
        batch = all_frames[grid_idx:grid_idx + clips_per_grid]
        batch_frames = [f for _, frames in batch for f in frames]
        if not batch_frames:
            continue
        out = output_dir / f"audit_grid_{grid_idx // clips_per_grid + 1:02d}.jpg"
        result = make_audit_grid(batch_frames, out, cols=n_frames_per_clip)
        if result:
            grid_paths.append(result)

    return grid_paths


# ─────────────────────────────────────────────────────────────────────
# Scene description cache (Claude writes after Read grid)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class FrameDescription:
    filename: str  # IMG_5998.MOV
    description: str  # "iPhone 街景拍攝 — 桃園機場 walkway，遠景航廈 + 旅客拖行李"
    key_elements: list[str] = field(default_factory=list)  # ["機場 walkway", "拖行李", "航廈"]
    text_visible: list[str] = field(default_factory=list)  # 招牌字 / 標示牌 actual text
    suitable_captions: list[str] = field(default_factory=list)  # 適合配的文案類型


def load_descriptions(cache_path: Path) -> dict[str, FrameDescription]:
    """Load existing scene descriptions cache."""
    if not cache_path.exists():
        return {}
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return {
        k: FrameDescription(
            filename=v["filename"],
            description=v["description"],
            key_elements=v.get("key_elements", []),
            text_visible=v.get("text_visible", []),
            suitable_captions=v.get("suitable_captions", []),
        )
        for k, v in data.items()
    }


def save_descriptions(descriptions: dict[str, FrameDescription], cache_path: Path) -> None:
    """Save descriptions to JSON cache for build script ground truth."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        k: {
            "filename": v.filename,
            "description": v.description,
            "key_elements": v.key_elements,
            "text_visible": v.text_visible,
            "suitable_captions": v.suitable_captions,
        }
        for k, v in descriptions.items()
    }
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
