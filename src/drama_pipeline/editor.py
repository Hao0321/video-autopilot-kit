"""Deterministic episode assembly, media QA, and publish-package creation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from storage_lifecycle import activate_policy, atomic_publish, canonical_output_path

from .store import ProjectStore, sha256_file, utc_now, write_json_atomic
from .tasks import queue_summary, task_for_shot


def _run(command: list[str], label: str) -> None:
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if run.returncode:
        raise RuntimeError(f"{label} failed: {run.stderr[-1600:]}")


def _probe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate",
        "-of", "json", str(path),
    ]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if run.returncode:
        raise RuntimeError(f"ffprobe failed: {run.stderr[-1000:]}")
    data = json.loads(run.stdout)
    streams = data.get("streams", [])
    video = next((row for row in streams if row.get("codec_type") == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "has_video": bool(video),
        "has_audio": any(row.get("codec_type") == "audio" for row in streams),
    }


def _resolution(config: dict[str, Any]) -> tuple[int, int]:
    width, height = str(config.get("resolution", "1080x1920")).lower().split("x", 1)
    return int(width), int(height)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("msjhbd.ttc", "msjh.ttc", "mingliu.ttc", "arial.ttf"):
        candidate = fonts / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _dialogue_caption(task: dict[str, Any]) -> str:
    lines = []
    for line in task.get("payload", {}).get("dialogue", []):
        if isinstance(line, dict) and str(line.get("text", "")).strip():
            lines.append(str(line["text"]).strip())
    return "\n".join(lines)


def _caption_png(text: str, output: Path, size: tuple[int, int]) -> Path:
    width, height = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(max(24, width // 22))
    chars = max(8, width // max(20, width // 22))
    rows = [part for line in text.splitlines() for part in textwrap.wrap(line, width=chars)]
    rows = rows[:3] or [text]
    spacing = max(8, width // 100)
    boxes = [draw.textbbox((0, 0), row, font=font) for row in rows]
    line_height = max(box[3] - box[1] for box in boxes)
    block_height = len(rows) * line_height + (len(rows) - 1) * spacing
    top = int(height * 0.78) - block_height // 2
    margin = max(18, width // 30)
    draw.rounded_rectangle(
        (margin, top - margin // 2, width - margin, top + block_height + margin // 2),
        radius=max(12, width // 70), fill=(0, 0, 0, 150),
    )
    for index, row in enumerate(rows):
        box = boxes[index]
        x = (width - (box[2] - box[0])) // 2
        y = top + index * (line_height + spacing)
        draw.text((x + 2, y + 2), row, font=font, fill=(0, 0, 0, 220))
        draw.text((x, y), row, font=font, fill=(255, 255, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output


def _base_normalize(source: Path, output: Path, duration: float, size: tuple[int, int]) -> None:
    width, height = size
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,"
        f"tpad=stop_mode=clone:stop_duration={duration:.3f},format=yuv420p"
    )
    command = ["ffmpeg", "-y", "-i", str(source)]
    if _probe(source)["has_audio"]:
        command += ["-map", "0:v:0", "-map", "0:a:0", "-vf", vf, "-af", "apad"]
    else:
        command += [
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-map", "0:v:0", "-map", "1:a:0", "-vf", vf,
        ]
    command += [
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(output),
    ]
    _run(command, "shot normalization")


def _burn_caption(source: Path, caption: Path, output: Path, duration: float) -> None:
    command = [
        "ffmpeg", "-y", "-i", str(source), "-loop", "1", "-i", str(caption),
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]", "-map", "0:a:0", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "copy", "-pix_fmt", "yuv420p", str(output),
    ]
    _run(command, "caption burn-in")


def _normalize_shot(store: ProjectStore, task: dict[str, Any], output: Path) -> Path:
    source = Path(task["result"]["file"]).resolve()
    duration = float(task["payload"]["duration"])
    size = _resolution(store.config())
    base = output.with_name(output.stem + "_base.mp4")
    base.parent.mkdir(parents=True, exist_ok=True)
    _base_normalize(source, base, duration, size)
    caption = _dialogue_caption(task)
    if caption:
        image = _caption_png(caption, output.with_suffix(".caption.png"), size)
        _burn_caption(base, image, output, duration)
    else:
        os.replace(base, output)
    return output


def _episode_tasks(store: ProjectStore, episode: dict[str, Any]) -> list[dict[str, Any]]:
    queue = store.queue()
    rows = []
    for scene in episode.get("scenes", []):
        for shot in scene.get("shots", []):
            task = task_for_shot(queue, shot["id"])
            if not task or task.get("status") != "complete" or not task.get("result"):
                raise RuntimeError(f"Shot generation is incomplete: {shot['id']}")
            rows.append(task)
    return rows


def _concat_list(paths: list[Path], output: Path) -> Path:
    lines = []
    for path in paths:
        escaped = path.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _contact_sheet(video: Path, output: Path) -> Path:
    duration = max(_probe(video)["duration"], 0.1)
    frames = []
    for index, ratio in enumerate((0.08, 0.32, 0.56, 0.80)):
        frame = output.parent / f"{output.stem}_{index}.jpg"
        command = [
            "ffmpeg", "-y", "-ss", f"{duration * ratio:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", "scale=240:-2", str(frame),
        ]
        _run(command, "QA frame extraction")
        frames.append(frame)
    images = [Image.open(frame).convert("RGB") for frame in frames]
    sheet = Image.new("RGB", (images[0].width * len(images), images[0].height), (12, 12, 12))
    for index, image in enumerate(images):
        sheet.paste(image, (index * image.width, 0))
        image.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)
    return output


def _qa_episode(path: Path, expected: float, size: tuple[int, int]) -> dict[str, Any]:
    probe = _probe(path)
    duration_ok = abs(probe["duration"] - expected) <= max(1.0, expected * 0.04)
    checks = {
        "file_nonempty": path.is_file() and path.stat().st_size > 1024,
        "video_stream": probe["has_video"],
        "audio_stream": probe["has_audio"],
        "resolution": (probe["width"], probe["height"]) == size,
        "duration": duration_ok,
    }
    return {"all_green": all(checks.values()), "checks": checks, "probe": probe, "expected_duration": expected}


def build_episode(store: ProjectStore, episode: dict[str, Any]) -> dict[str, Any]:
    episode_id = episode["id"]
    episode_dir = store.episodes_dir / episode_id
    work = episode_dir / "_work"
    out_dir = episode_dir / "_out"
    work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    activate_policy(out_dir)
    tasks = _episode_tasks(store, episode)
    normalized = [
        _normalize_shot(store, task, work / f"shot_{index:03d}.mp4")
        for index, task in enumerate(tasks, start=1)
    ]
    listing = _concat_list(normalized, work / "concat.txt")
    candidate = work / "episode_candidate.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(candidate)], "episode concat")
    expected = sum(float(task["payload"]["duration"]) for task in tasks)
    qa = _qa_episode(candidate, expected, _resolution(store.config()))
    write_json_atomic(episode_dir / "qa_report.json", qa)
    _contact_sheet(candidate, episode_dir / "contact_sheet.jpg")
    if not qa["all_green"]:
        raise RuntimeError(f"Episode QA failed: {episode_id}: {qa['checks']}")
    current = atomic_publish(candidate, canonical_output_path(out_dir))
    return {
        "episode_id": episode_id,
        "current": str(current),
        "sha256": sha256_file(current),
        "bytes": current.stat().st_size,
        "qa": qa,
    }


def _publish_markdown(store: ProjectStore, package: dict[str, Any]) -> str:
    config, pack = store.config(), store.pack()
    rows = [
        f"# {pack['project']['title']} 發布包",
        "",
        f"題材：{config['topic']}",
        f"平台：{config['surface']}",
        "AI 揭露：本系列含 AI 輔助生成的影像、聲音或剪輯內容。",
        "",
        "## 集數",
        "",
    ]
    for episode in package["episodes"]:
        rows.append(f"- {episode['episode_id']}: `{episode['current']}` ({episode['sha256'][:12]})")
    rows += ["", "公開發布狀態：等待使用者明確確認。", ""]
    return "\n".join(rows)


def build_all(store: ProjectStore) -> dict[str, Any]:
    summary = queue_summary(store.queue())
    if summary.get("pending") or summary.get("running") or summary.get("blocked"):
        raise RuntimeError(f"Generation queue is incomplete: {summary}")
    store.set_stage("build", "running", "assembling episodes")
    try:
        episodes = [build_episode(store, item) for item in store.pack().get("episodes", [])]
    except Exception as exc:
        store.set_stage("build", "failed", str(exc))
        raise
    store.set_stage("build", "complete", f"{len(episodes)} episode(s)")
    store.set_stage("qa", "complete", "all episode checks green")
    package = {
        "schema_version": 1,
        "project_id": store.config()["project_id"],
        "created_at": utc_now(),
        "episodes": episodes,
        "public_publish_status": "awaiting_explicit_confirmation",
        "ai_disclosure_required": True,
    }
    write_json_atomic(store.root / "publish_package.json", package)
    (store.root / "publish_package.md").write_text(_publish_markdown(store, package), encoding="utf-8")
    write_json_atomic(
        store.root / "ready_for_approval.json",
        {"ready": True, "created_at": utc_now(), "publish_package": "publish_package.json", "approved": False},
    )
    store.set_stage("publish", "waiting", "explicit user confirmation required")
    return package


def approve_publish(store: ProjectStore, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("Explicit --confirm is required")
    package_path = store.root / "publish_package.json"
    if not package_path.is_file():
        raise RuntimeError("Build and QA must finish before approval")
    record = {
        "approved": True,
        "approved_at": utc_now(),
        "publish_package_sha256": sha256_file(package_path),
        "note": "Approval recorded. No external platform upload was performed by this command.",
    }
    write_json_atomic(store.root / "ready_for_approval.json", record)
    store.set_stage("publish", "ready", "approved for an external publishing adapter")
    store.log("publish_approved", record)
    return record
