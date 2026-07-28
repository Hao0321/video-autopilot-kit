"""
silent_vlog_maker.scene_audit — M12 chronological sort + GPS-aware scene clustering.

把 N 個 clip 自動分組成「場景」(scene)：
- 連續拍攝（時間 gap < 30 min）+ 同地點（GPS distance < 1km）= 同一場景
- 跨日 / 跨城市自動切

旅遊 vlog 的痛點解法：上百個檔案手動排「Day 1 早上 / Day 1 下午 / Day 2 早上」
→ 系統化抽取，省 30+ min planning time。
"""
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .audit import ClipAudit


# ─────────────────────────────────────────────────────────────────────
# Scene dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Scene:
    """A cluster of consecutively-shot clips (same time window + same location)."""
    scene_id: int
    clips: list[ClipAudit] = field(default_factory=list)
    start_time_iso: Optional[str] = None  # earliest clip's real_time
    end_time_iso: Optional[str] = None
    duration_sec: float = 0.0  # sum of clip durations
    span_min: float = 0.0  # wall-clock span from first to last shot
    center_lat: Optional[float] = None  # avg of GPS coords
    center_lng: Optional[float] = None
    location_label: Optional[str] = None  # human-readable (user/Claude can write)
    date_local: Optional[str] = None  # "2025-10-20"
    period: Optional[str] = None  # "早上" / "中午" / "下午" / "晚上"

    @property
    def num_clips(self) -> int:
        return len(self.clips)

    @property
    def google_maps_url(self) -> Optional[str]:
        if self.center_lat is None:
            return None
        return f"https://www.google.com/maps/?q={self.center_lat},{self.center_lng}"

    @property
    def filenames(self) -> list[str]:
        return [c.filename for c in self.clips]


# ─────────────────────────────────────────────────────────────────────
# GPS distance (Haversine — accurate for short distances)
# ─────────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two GPS points in kilometers."""
    R = 6371.0  # earth radius km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ─────────────────────────────────────────────────────────────────────
# Scene clustering — combined time + GPS
# ─────────────────────────────────────────────────────────────────────

def cluster_scenes(
    audits: list[ClipAudit],
    time_gap_min: float = 30.0,
    location_radius_km: float = 1.0,
) -> list[Scene]:
    """Cluster clips into scenes by time gap + location proximity.

    Algorithm:
        1. Sort by real_time
        2. Walk through sorted list. New scene starts when EITHER:
           - time gap from previous clip > time_gap_min
           - GPS distance from scene center > location_radius_km (if both have GPS)
        3. Cumulative scene timeline.

    Args:
        time_gap_min: 30 min default (long enough to capture "lunch break", short enough to split day-trip stops)
        location_radius_km: 1 km default (one tourist spot / one hotel area)

    Returns:
        list of Scene objects in chronological order.
    """
    # Filter clips with valid time, sort chronologically
    sortable = [a for a in audits if a.creation_time_real or a.creation_time_import]
    if not sortable:
        return []

    def sort_key(a: ClipAudit):
        # Prefer real time, fallback to import time
        t = a.creation_time_real or a.creation_time_import or ""
        # Normalize: strip TZ, parse to ISO sortable form
        if "+" in t:
            t = t.split("+")[0]
        elif "Z" in t:
            t = t.replace("Z", "")
        return t

    sorted_clips = sorted(sortable, key=sort_key)

    scenes: list[Scene] = []
    current_scene: Optional[Scene] = None
    prev_clip: Optional[ClipAudit] = None
    scene_id = 0

    for clip in sorted_clips:
        clip_dt = _parse_dt(clip.creation_time_real or clip.creation_time_import)
        if clip_dt is None:
            continue

        # Decide: same scene or new scene
        same_scene = False
        if current_scene and prev_clip:
            prev_dt = _parse_dt(prev_clip.creation_time_real or prev_clip.creation_time_import)
            if prev_dt:
                gap_min = (clip_dt - prev_dt).total_seconds() / 60.0
                time_ok = gap_min <= time_gap_min

                # GPS check (if both clips have GPS)
                gps_ok = True
                if clip.has_gps and current_scene.center_lat is not None:
                    dist = haversine_km(
                        clip.gps_lat, clip.gps_lng,
                        current_scene.center_lat, current_scene.center_lng,
                    )
                    gps_ok = dist <= location_radius_km

                same_scene = time_ok and gps_ok

        if not same_scene:
            scene_id += 1
            current_scene = Scene(scene_id=scene_id)
            scenes.append(current_scene)

        current_scene.clips.append(clip)
        prev_clip = clip

        # Update scene aggregates
        _update_scene_aggregates(current_scene)

    return scenes


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse various time formats → naive datetime (for comparisons)."""
    if not s:
        return None
    # Strip TZ
    s = s.split("+")[0].split("-08:00")[0] if "+" in s or "-08:00" in s else s.replace("Z", "")
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _update_scene_aggregates(scene: Scene) -> None:
    """Recompute scene's aggregated fields after adding a clip."""
    if not scene.clips:
        return

    # Time range
    dts = [_parse_dt(c.creation_time_real or c.creation_time_import) for c in scene.clips]
    dts = [d for d in dts if d]
    if dts:
        first_dt = min(dts)
        last_dt = max(dts)
        scene.start_time_iso = first_dt.strftime("%Y-%m-%dT%H:%M:%S")
        scene.end_time_iso = last_dt.strftime("%Y-%m-%dT%H:%M:%S")
        scene.span_min = (last_dt - first_dt).total_seconds() / 60.0
        scene.date_local = first_dt.strftime("%Y-%m-%d")
        scene.period = _period_label(first_dt.hour)

    # Total clip duration
    scene.duration_sec = sum(c.duration_sec for c in scene.clips)

    # GPS center (average of clips with GPS)
    gps_clips = [c for c in scene.clips if c.has_gps]
    if gps_clips:
        scene.center_lat = sum(c.gps_lat for c in gps_clips) / len(gps_clips)
        scene.center_lng = sum(c.gps_lng for c in gps_clips) / len(gps_clips)


def _period_label(hour24: int) -> str:
    """Map 24h hour → 早上 / 中午 / 下午 / 晚上."""
    if 5 <= hour24 < 12:
        return "早上"
    elif hour24 == 12:
        return "中午"
    elif 13 <= hour24 < 18:
        return "下午"
    elif 18 <= hour24 < 23:
        return "晚上"
    return "凌晨"


def print_scene_timeline(scenes: list[Scene]) -> None:
    """Print human-readable scene timeline."""
    print(f"\n=== Scene Timeline ({len(scenes)} scenes) ===")
    for s in scenes:
        label = f" — {s.location_label}" if s.location_label else ""
        gps = f" 📍 ({s.center_lat:.4f},{s.center_lng:.4f})" if s.center_lat else ""
        time_range = f"{s.start_time_iso[11:16]}-{s.end_time_iso[11:16]}" if s.start_time_iso and s.end_time_iso else ""
        print(f"  Scene {s.scene_id} [{s.date_local} {s.period} {time_range}]"
              f" {s.num_clips} clips / {s.duration_sec:.0f}s footage{gps}{label}")
        for c in s.clips:
            t = c.creation_time_local or "??:??"
            print(f"    {t}  {c.filename} ({c.duration_sec:.1f}s)")
