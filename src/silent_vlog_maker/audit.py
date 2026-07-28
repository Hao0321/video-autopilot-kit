"""
silent_vlog_maker.audit — R1 Pre-flight Source Audit (11 維度，2026-05-23 v2 升級).

從 7 維度 → 11 維度：加 GPS / 拍攝時間（含 TZ）/ camera model / audio codec / file size。

修復重大 bug：creation_time 改用 `TAG:com.apple.quicktime.creationdate`（真實拍攝時間 + TZ）
之前用 `TAG:creation_time` 是 file import time，導致一支美食 vlog 的時間軸錯亂。
"""
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# R1 v2: Pre-flight Source Audit (11 dimensions)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ClipAudit:
    # ─── Identification ───
    filename: str
    filepath: str = ""
    file_size_mb: float = 0.0

    # ─── Video codec ───
    codec: str = "unknown"
    width: int = 0
    height: int = 0
    fps: float = 30.0
    rotation: int = 0
    color_transfer: str = "unknown"  # arib-std-b67 = HLG / smpte2084 = HDR10 / bt709 = SDR
    pix_fmt: str = "unknown"
    duration_sec: float = 0.0

    # ─── Time（M12 修復：用真實拍攝時間 + TZ）───
    creation_time_real: Optional[str] = None  # com.apple.quicktime.creationdate (真實拍攝時間 + TZ)
    creation_time_import: Optional[str] = None  # TAG:creation_time (import time — fallback)
    creation_time_local: Optional[str] = None  # 24-hour HH:MM e.g. "14:41" (from real time)
    creation_time_natural: Optional[str] = None  # 「下午2:41」for Vlog voice overlays
    creation_date_local: Optional[str] = None  # "2025-10-20" — for chronological sort key

    # ─── GPS（NEW v2）───
    gps_lat: Optional[float] = None  # decimal degrees, e.g. 0.0000
    gps_lng: Optional[float] = None  # decimal degrees, e.g. 0.0000
    gps_altitude: Optional[float] = None  # meters
    gps_accuracy_m: Optional[float] = None  # horizontal accuracy in meters

    # ─── Camera（NEW v2）───
    camera_make: Optional[str] = None  # "Apple"
    camera_model: Optional[str] = None  # e.g. "<phone/camera model>"
    camera_software: Optional[str] = None  # e.g. "<os/firmware version>"

    # ─── Audio（NEW v2）───
    audio_codec: Optional[str] = None  # "aac"
    audio_channels: Optional[int] = None  # 1 / 2
    audio_sample_rate: Optional[int] = None  # 48000
    audio_bitrate_kbps: Optional[int] = None  # 256

    @property
    def is_hdr(self) -> bool:
        return self.color_transfer in ("arib-std-b67", "smpte2084") or "10le" in self.pix_fmt

    @property
    def is_portrait(self) -> bool:
        return abs(self.rotation) == 90 or (self.height > self.width)

    @property
    def display_resolution(self) -> tuple[int, int]:
        if abs(self.rotation) == 90:
            return self.height, self.width
        return self.width, self.height

    @property
    def has_gps(self) -> bool:
        return self.gps_lat is not None and self.gps_lng is not None

    @property
    def google_maps_url(self) -> Optional[str]:
        if not self.has_gps:
            return None
        return f"https://www.google.com/maps/?q={self.gps_lat},{self.gps_lng}"


def parse_iso6709(s: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Parse iPhone GPS ISO6709 format → (lat, lng, altitude_m).

    Format: '+00.0000+000.0000+000.000/'  (signed decimal degrees + altitude)
    Returns (None, None, None) on parse failure.
    """
    if not s:
        return None, None, None
    # Match signed lat + signed lng + optional signed altitude
    m = re.match(r'^([+-]\d+\.?\d*)([+-]\d+\.?\d*)([+-]\d+\.?\d*)?/?$', s.strip())
    if not m:
        return None, None, None
    try:
        lat = float(m.group(1))
        lng = float(m.group(2))
        alt = float(m.group(3)) if m.group(3) else None
        return lat, lng, alt
    except (ValueError, TypeError):
        return None, None, None


def parse_apple_creation_date(s: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse '2025-10-20T11:29:40+0800' → (local_iso, local_HHMM, local_natural).

    iPhone com.apple.quicktime.creationdate already in LOCAL time + TZ offset.
    No need for UTC→Local conversion.
    """
    if not s:
        return None, None, None
    try:
        # Normalize +0800 → +08:00 for ISO compliance
        s_iso = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', s)
        dt = datetime.fromisoformat(s_iso)
        hhmm = dt.strftime("%H:%M")
        natural = _to_chinese_natural_time(dt.hour, dt.minute)
        return dt.strftime("%Y-%m-%dT%H:%M:%S"), hhmm, natural
    except (ValueError, TypeError):
        return None, None, None


def _to_chinese_natural_time(hour24: int, minute: int) -> str:
    """24h → 「下午2:41」「早上7:28」(natural Chinese form for Vlog voice)."""
    if 0 <= hour24 < 5:
        period = "凌晨"
        hour12 = hour24 if hour24 != 0 else 12
    elif 5 <= hour24 < 12:
        period = "早上"
        hour12 = hour24
    elif hour24 == 12:
        period = "中午"
        hour12 = 12
    elif 13 <= hour24 < 18:
        period = "下午"
        hour12 = hour24 - 12
    else:  # 18-23
        period = "晚上"
        hour12 = hour24 - 12
    return f"{period}{hour12}:{minute:02d}"


def audit_raw_files(raw_dir: Path, tz_offset_hours: int = 8) -> list[ClipAudit]:
    """R1 v2 Pre-flight audit — 11 dimensions scan."""
    audits = []
    seen_names = set()
    candidates = []
    for ext in (".mov", ".mp4"):
        for p in sorted(raw_dir.iterdir()):
            if p.suffix.lower() == ext and p.name.lower() not in seen_names:
                seen_names.add(p.name.lower())
                candidates.append(p)

    for clip in candidates:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", str(clip)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            continue

        # Parse stream blocks separately (avoid mixing video/audio fields).
        # ffprobe outputs codec_name BEFORE codec_type → must buffer per-stream then dispatch.
        video_fields = {}
        audio_fields = {}
        format_fields = {}
        current_block = None
        stream_buf = {}

        def flush_stream():
            nonlocal stream_buf
            if not stream_buf:
                return
            codec_type = stream_buf.get("codec_type", "")
            if codec_type == "video":
                for k, v in stream_buf.items():
                    if k not in video_fields:
                        video_fields[k] = v
            elif codec_type == "audio":
                for k, v in stream_buf.items():
                    if k not in audio_fields:
                        audio_fields[k] = v
            stream_buf = {}

        for line in result.stdout.splitlines():
            line = line.strip()
            if line == "[STREAM]":
                current_block = "stream"
                stream_buf = {}
            elif line == "[/STREAM]":
                flush_stream()
                current_block = None
            elif line == "[FORMAT]":
                current_block = "format"
            elif line == "[/FORMAT]":
                current_block = None
            elif "=" in line and current_block:
                k, _, v = line.partition("=")
                if current_block == "stream":
                    stream_buf[k] = v
                elif current_block == "format":
                    format_fields[k] = v

        # ─── Video codec ───
        fps_str = video_fields.get("r_frame_rate", "30/1")
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0
        except (ValueError, ZeroDivisionError):
            fps = 30.0

        # Rotation: side_data or TAG:rotate
        rotation = 0
        for line in result.stdout.splitlines():
            if "rotation=" in line and "side_data" not in line:
                try:
                    rotation = int(float(line.split("=")[1]))
                    break
                except (ValueError, IndexError):
                    pass
        if rotation == 0 and video_fields.get("TAG:rotate"):
            try:
                rotation = int(video_fields["TAG:rotate"])
            except ValueError:
                pass

        # ─── M12 fix: use Apple real creation time + TZ ───
        # Priority: format.com.apple.quicktime.creationdate > video.TAG:creation_time > format.TAG:creation_time
        apple_real_time = format_fields.get("TAG:com.apple.quicktime.creationdate")
        import_time_utc = format_fields.get("TAG:creation_time") or video_fields.get("TAG:creation_time")

        real_iso, hhmm, natural = parse_apple_creation_date(apple_real_time) if apple_real_time else (None, None, None)

        # Fallback: import_time UTC → local
        if not real_iso and import_time_utc:
            real_iso, hhmm, natural = _convert_utc_to_local(import_time_utc, tz_offset_hours)

        creation_date_local = real_iso[:10] if real_iso else None  # "2025-10-20"

        # ─── GPS ───
        gps_str = format_fields.get("TAG:com.apple.quicktime.location.ISO6709")
        gps_lat, gps_lng, gps_alt = parse_iso6709(gps_str) if gps_str else (None, None, None)
        gps_accuracy = None
        try:
            gps_accuracy = float(format_fields.get("TAG:com.apple.quicktime.location.accuracy.horizontal", ""))
        except (ValueError, TypeError):
            pass

        # ─── Camera ───
        camera_make = format_fields.get("TAG:com.apple.quicktime.make")
        camera_model = format_fields.get("TAG:com.apple.quicktime.model")
        camera_software = format_fields.get("TAG:com.apple.quicktime.software")

        # ─── Audio ───
        audio_codec = audio_fields.get("codec_name")
        audio_channels = int(audio_fields["channels"]) if audio_fields.get("channels", "").isdigit() else None
        audio_sample_rate = int(audio_fields["sample_rate"]) if audio_fields.get("sample_rate", "").isdigit() else None
        audio_bitrate_kbps = None
        if audio_fields.get("bit_rate", "").isdigit():
            audio_bitrate_kbps = int(audio_fields["bit_rate"]) // 1000

        # ─── File size ───
        try:
            file_size_mb = round(int(format_fields.get("size", "0")) / (1024 * 1024), 2)
        except ValueError:
            file_size_mb = 0.0

        audits.append(ClipAudit(
            filename=clip.name,
            filepath=str(clip),
            file_size_mb=file_size_mb,
            codec=video_fields.get("codec_name", "unknown"),
            width=int(video_fields.get("width", 0)) if video_fields.get("width", "").isdigit() else 0,
            height=int(video_fields.get("height", 0)) if video_fields.get("height", "").isdigit() else 0,
            fps=fps,
            rotation=rotation,
            color_transfer=video_fields.get("color_transfer", "unknown"),
            pix_fmt=video_fields.get("pix_fmt", "unknown"),
            duration_sec=float(format_fields.get("duration", "0") or "0"),
            creation_time_real=apple_real_time,
            creation_time_import=import_time_utc,
            creation_time_local=hhmm,
            creation_time_natural=natural,
            creation_date_local=creation_date_local,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            gps_altitude=gps_alt,
            gps_accuracy_m=gps_accuracy,
            camera_make=camera_make,
            camera_model=camera_model,
            camera_software=camera_software,
            audio_codec=audio_codec,
            audio_channels=audio_channels,
            audio_sample_rate=audio_sample_rate,
            audio_bitrate_kbps=audio_bitrate_kbps,
        ))
    return audits


def _convert_utc_to_local(utc_iso: str, tz_offset_hours: int) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Legacy fallback when Apple creation date missing."""
    try:
        utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        local = utc + timedelta(hours=tz_offset_hours)
        hhmm = local.strftime("%H:%M")
        natural = _to_chinese_natural_time(local.hour, local.minute)
        return local.strftime("%Y-%m-%dT%H:%M:%S"), hhmm, natural
    except (ValueError, TypeError):
        return None, None, None


def utc_to_local(utc_iso: str, tz_offset_hours: int = 8, natural: bool = False) -> str:
    """Legacy R14 function (kept for backward compat).

    Args:
        utc_iso: 2026-05-01T06:41:58.000000Z (Z suffix)
        tz_offset_hours: your local UTC offset (e.g. +8 for a UTC+8 region)
        natural: If True, return Chinese natural form「下午2:41」.
    """
    try:
        utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        local = utc + timedelta(hours=tz_offset_hours)
        if not natural:
            return local.strftime("%H:%M")
        return _to_chinese_natural_time(local.hour, local.minute)
    except (ValueError, TypeError):
        return ""


def print_audit_report(audits: list[ClipAudit]) -> None:
    """Print enhanced human-readable audit report (11 dimensions)."""
    print(f"\n=== R1 v2 Pre-flight Source Audit ({len(audits)} clips) ===")
    any_hdr = any(a.is_hdr for a in audits)
    any_portrait = any(a.is_portrait for a in audits)
    any_gps = any(a.has_gps for a in audits)
    cameras = {a.camera_model for a in audits if a.camera_model}
    dates = {a.creation_date_local for a in audits if a.creation_date_local}

    print(f"HDR: {'⚠️ YES — need R10 tonemap' if any_hdr else '✅ No'}")
    print(f"Portrait: {'📱 YES' if any_portrait else '🖥️  Landscape'}")
    print(f"GPS: {'📍 YES — ' + str(sum(1 for a in audits if a.has_gps)) + '/' + str(len(audits)) + ' clips have GPS' if any_gps else '❌ No GPS data'}")
    print(f"Cameras: {', '.join(cameras) if cameras else 'unknown'}")
    print(f"Dates: {sorted(dates)}")
    print(f"Total size: {sum(a.file_size_mb for a in audits):.1f} MB")
    print(f"Total duration: {sum(a.duration_sec for a in audits):.1f}s")
    print()
    for a in audits:
        flags = []
        if a.is_hdr: flags.append("HDR")
        if a.is_portrait: flags.append("portrait")
        if a.has_gps: flags.append("GPS")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        gps_str = f" @ ({a.gps_lat:.4f},{a.gps_lng:.4f})" if a.has_gps else ""
        print(f"  {a.filename}: {a.codec} {a.width}x{a.height} {a.fps:.0f}fps "
              f"dur={a.duration_sec:.1f}s "
              f"local={a.creation_time_local or 'N/A'}{gps_str}{flag_str}")


# ─────────────────────────────────────────────────────────────────────
# R13: Smart cut points (skip 開頭手震對焦)
# ─────────────────────────────────────────────────────────────────────

def smart_cut_offset(clip_duration: float) -> float:
    """R13 heuristic — skip handshake/autofocus at clip start.

    | Clip duration | Skip offset |
    |---------------|-------------|
    | ≥ 10s         | 2.5s        |
    | 5-10s         | 1.2s        |
    | 3-5s          | 0.6s        |
    | < 3s          | 0s          |
    """
    if clip_duration >= 10:
        return 2.5
    elif clip_duration >= 5:
        return 1.2
    elif clip_duration >= 3:
        return 0.6
    return 0.0
