# -*- coding: utf-8 -*-
"""Media I/O adapters for Hao Filter Library.

Only mature low-level engines are used: FFmpeg for muxing, OpenCV/NumPy for
frame-addressable rendering and the existing Visual Master for grading.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np

from filter_primitives import apply_subject, apply_temporal, composite_transition
from visual_master import BT709_ENCODE_ARGS, rgb_decode_filter, to_yuv_filter


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("command failed: " + (result.stderr or "")[-1200:])


def media_info(path: str | Path) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    return {"path": str(Path(path).resolve()), "fps": fps, "frames": frames,
            "duration": frames / max(1.0, fps), "width": width, "height": height}


def _log_tail(log: Any) -> str:
    log.seek(0)
    return log.read().decode("utf-8", errors="replace")[-1200:]


class _PipeWriter:
    """BGR frames -> explicit BT.709 yuv420p, lossless x264 (was a lossy mp4v file)."""

    def __init__(self, path: Path, fps: float, width: int, height: int):
        self.shape = (height, width, 3)
        self.log = tempfile.TemporaryFile()       # a file, not a pipe: no stderr deadlock
        self.process = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
             "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps:.6f}", "-i", "-",
             "-an", "-vf", to_yuv_filter("yuv420p"), "-c:v", "libx264", "-qp", "0",
             "-preset", "ultrafast", *BT709_ENCODE_ARGS, str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.log)

    def write(self, frame: np.ndarray) -> None:
        if frame.shape != self.shape or frame.dtype != np.uint8:
            raise ValueError(f"frame {frame.shape} {frame.dtype} != writer {self.shape} uint8")
        assert self.process.stdin is not None
        self.process.stdin.write(np.ascontiguousarray(frame).tobytes())

    def release(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except BrokenPipeError:
            pass
        code = self.process.wait()
        error = _log_tail(self.log)
        self.log.close()
        if code:
            raise RuntimeError("frame writer failed: " + error)


def _open_writer(path: Path, fps: float, width: int, height: int) -> _PipeWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    return _PipeWriter(path, fps, width, height)


def _read_frames(path: str | Path, start: float, count: int,
                 width: int, height: int, fps: float | None = None) -> Iterator[np.ndarray]:
    """Decode to true BT.709 BGR (explicit matrix, HDR tone-mapped) at ``fps``."""
    filters = ([f"fps={fps:.6f}"] if fps else []) + [
        rgb_decode_filter(path),
        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={width}:{height}", "format=bgr24"]
    log = tempfile.TemporaryFile()
    process = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{max(0.0, start):.6f}",
         "-i", str(path), "-an", "-frames:v", str(count), "-vf", ",".join(filters),
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, stderr=log)
    size = width * height * 3
    last: np.ndarray | None = None
    try:
        for _ in range(count):
            data = process.stdout.read(size) if process.stdout else b""
            if len(data) == size:
                last = np.frombuffer(data, np.uint8).reshape(height, width, 3)
            if last is None:
                raise RuntimeError(f"no decodable frames in {path}: " + _log_tail(log))
            yield last.copy()
    finally:
        process.kill()
        process.wait()
        if process.stdout:
            process.stdout.close()
        log.close()


def _mux_source_audio(video_only: Path, source: str | Path, output: Path,
                      start: float, duration: float | None) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(video_only), "-ss", f"{max(0.0, start):.6f}"]
    if duration is not None:
        command.extend(["-t", f"{max(0.01, duration):.6f}"])
    command.extend(["-i", str(source), "-map", "0:v:0", "-map", "1:a?",
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", *BT709_ENCODE_ARGS, "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(output)])
    _run(command)


def _finalize(video_only: Path, output: Path, source: str | Path | None = None,
              start: float = 0.0, duration: float | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if source:
        _mux_source_audio(video_only, source, output, start, duration)
    else:
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
              "-i", str(video_only), "-an", "-c:v", "libx264", "-crf", "18",
              "-preset", "veryfast", "-pix_fmt", "yuv420p", *BT709_ENCODE_ARGS,
              "-movflags", "+faststart", str(output)])


def render_grade(input_path: str | Path, output_path: str | Path,
                 profile: str, strength: float, *, start: float = 0.0,
                 duration: float | None = None, width: int | None = None,
                 height: int | None = None) -> dict[str, Any]:
    from visual_master import apply_to_video
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    info = media_info(input_path)
    needs_window = (start > 0.0 or duration is not None or width is not None
                    or height is not None)
    if needs_window:
        with tempfile.TemporaryDirectory(prefix="hao-grade-window-") as temp_dir:
            normalized = Path(temp_dir) / "source.mp4"
            chosen_width = int(width or info["width"])
            chosen_height = int(height or info["height"])
            actual_duration = (duration if duration is not None else
                               max(0.01, info["duration"] - start))
            _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                  "-ss", f"{max(0.0, start):.6f}", "-t",
                  f"{max(0.01, actual_duration):.6f}", "-i", str(input_path),
                  "-vf", (f"scale={chosen_width}:{chosen_height}:"
                          "force_original_aspect_ratio=increase,"
                          f"crop={chosen_width}:{chosen_height}"),
                  "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
                  "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                  "-movflags", "+faststart", str(normalized)])
            report = apply_to_video(str(normalized), str(output), profile,
                                    strength=strength)
    else:
        report = apply_to_video(str(input_path), str(output), profile,
                                strength=strength)
    return {"status": "GREEN", "renderer": "visual_master", "output": str(output),
            "profile": profile, "strength": strength, "report": report}


def render_temporal(input_path: str | Path, output_path: str | Path,
                    style: str, strength: float, *, start: float = 0.0,
                    duration: float | None = None, width: int | None = None,
                    height: int | None = None, seed: int = 321,
                    material: np.ndarray | None = None,
                    material_status: dict[str, Any] | None = None) -> dict[str, Any]:
    info = media_info(input_path)
    fps = min(60.0, max(12.0, info["fps"]))
    width = int(width or info["width"])
    height = int(height or info["height"])
    actual_duration = duration if duration is not None else max(0.01, info["duration"] - start)
    count = max(1, round(actual_duration * fps))
    output = Path(output_path)
    with tempfile.TemporaryDirectory(prefix="hao-filter-") as temp_dir:
        video_only = Path(temp_dir) / "video.mp4"
        writer = _open_writer(video_only, fps, width, height)
        try:
            for index, frame in enumerate(_read_frames(input_path, start, count, width, height, fps)):
                progress = index / max(1, count - 1)
                writer.write(apply_temporal(frame, style, progress, strength,
                                            seed=seed + index, material=material))
        finally:
            writer.release()
        _finalize(video_only, output, input_path, start, actual_duration)
    return {"status": "GREEN", "renderer": ("material_temporal" if material is not None
                                               else "procedural_temporal"), "style": style,
            "output": str(output), "fps": fps, "frames": count,
            "duration": round(count / fps, 4), "strength": strength,
            "material": material_status}


def render_transition(outgoing_path: str | Path, incoming_path: str | Path,
                      output_path: str | Path, style: str, strength: float,
                      *, duration: float = 0.65, width: int | None = None,
                      height: int | None = None, seed: int = 321,
                      material: np.ndarray | None = None,
                      material_status: dict[str, Any] | None = None) -> dict[str, Any]:
    first = media_info(outgoing_path)
    second = media_info(incoming_path)
    fps = min(60.0, max(12.0, first["fps"]))
    width = int(width or first["width"])
    height = int(height or first["height"])
    count = max(3, round(duration * fps))
    start = max(0.0, first["duration"] - duration)
    outgoing = _read_frames(outgoing_path, start, count, width, height, fps)
    incoming = _read_frames(incoming_path, 0.0, count, width, height, fps)
    output = Path(output_path)
    with tempfile.TemporaryDirectory(prefix="hao-transition-") as temp_dir:
        video_only = Path(temp_dir) / "video.mp4"
        writer = _open_writer(video_only, fps, width, height)
        try:
            for index, (before, after) in enumerate(zip(outgoing, incoming)):
                progress = index / max(1, count - 1)
                writer.write(composite_transition(before, after, style, progress,
                                                  strength, seed=seed,
                                                  material=material))
        finally:
            writer.release()
        _finalize(video_only, output)
    return {"status": "GREEN", "renderer": ("material_transition" if material is not None
                                               else "procedural_transition"), "style": style,
            "output": str(output), "fps": fps, "frames": count,
            "duration": round(count / fps, 4), "strength": strength,
            "material": material_status,
            "audio_contract": "timeline engine supplies J/L cut, transient or SFX"}


class _MatteReader:
    def __init__(self, path: str | Path, width: int, height: int, start: float):
        self.path = Path(path)
        self.width, self.height = width, height
        self.still = self.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if self.still:
            image = cv2.imread(str(self.path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise ValueError(f"cannot open matte: {path}")
            self.image = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
            self.cap = None
        else:
            self.image = None
            self.cap = cv2.VideoCapture(str(self.path))
            if not self.cap.isOpened():
                raise ValueError(f"cannot open matte video: {path}")
            self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, start) * 1000.0)

    def read(self) -> np.ndarray:
        if self.image is not None:
            return self.image.copy()
        assert self.cap is not None
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("matte ended before source video")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()


def render_subject(input_path: str | Path, matte_path: str | Path,
                   output_path: str | Path, style: str, strength: float,
                   *, start: float = 0.0, duration: float | None = None,
                   width: int | None = None, height: int | None = None) -> dict[str, Any]:
    info = media_info(input_path)
    fps = min(60.0, max(12.0, info["fps"]))
    width = int(width or info["width"])
    height = int(height or info["height"])
    actual_duration = duration if duration is not None else max(0.01, info["duration"] - start)
    count = max(1, round(actual_duration * fps))
    matte = _MatteReader(matte_path, width, height, start)
    output = Path(output_path)
    with tempfile.TemporaryDirectory(prefix="hao-subject-filter-") as temp_dir:
        video_only = Path(temp_dir) / "video.mp4"
        writer = _open_writer(video_only, fps, width, height)
        try:
            for index, frame in enumerate(_read_frames(input_path, start, count, width, height, fps)):
                progress = index / max(1, count - 1)
                writer.write(apply_subject(frame, matte.read(), style, progress, strength))
        finally:
            writer.release()
            matte.close()
        _finalize(video_only, output, input_path, start, actual_duration)
    return {"status": "GREEN", "renderer": "procedural_subject", "style": style,
            "output": str(output), "matte": str(Path(matte_path).resolve()),
            "fps": fps, "frames": count, "duration": round(count / fps, 4)}


def write_report(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def dependencies() -> dict[str, Any]:
    return {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"),
            "opencv": cv2.__version__, "numpy": np.__version__}


def _selftest() -> None:
    """Identity effects must reproduce SMPTE HD bars (> 45 dB) and tag bt709 output."""
    def rgb(path: Path) -> np.ndarray:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-vf",
                              "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
                              "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).astype(np.float64)

    with tempfile.TemporaryDirectory(prefix="filter-renderers-test-") as temp_dir:
        root = Path(temp_dir)
        tagged, untagged = root / "bars709.mp4", root / "bars_untagged.mp4"
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
              "smptehdbars=size=640x360:rate=30", "-t", "0.5", "-vf", to_yuv_filter(),
              "-c:v", "libx264", "-qp", "0", *BT709_ENCODE_ARGS, str(tagged)])
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(tagged), "-c:v", "copy", "-bsf:v",
              "h264_metadata=colour_primaries=2:transfer_characteristics=2:matrix_coefficients=2",
              str(untagged)])
        reference = rgb(tagged)
        for source in (tagged, untagged):
            outputs = [root / ("temporal_" + source.name), root / ("transition_" + source.name)]
            render_temporal(source, outputs[0], "blur_snap", 0.0, duration=0.3)
            render_transition(source, source, outputs[1], "luma_fade", 1.0, duration=0.3)
            for output in outputs:
                mse = float(((rgb(output) - reference) ** 2).mean())
                psnr = 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)
                tag = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                      "-show_entries", "stream=color_space", "-of", "csv=p=0",
                                      str(output)], capture_output=True, text=True).stdout.strip()
                assert psnr > 45.0 and tag == "bt709", (output.name, round(psnr, 2), tag)
    print("filter_renderers self-test OK")


if __name__ == "__main__":
    _selftest()
