"""
capcut_helpers.audit — Lightweight draft state audit (caption count / mute / effects / timing).

Generalized from a travel-vlog full-audit script — 任何專案都能直接用。
"""
import json
from collections import Counter

from .mute import audit_mute_state


def audit_draft(draft: dict) -> dict:
    """Run all standard audit checks. Returns report dict."""
    report = {}

    # 1. Video / Audio tracks summary
    tracks = draft.get("tracks", [])
    video_tracks = [tr for tr in tracks if tr.get("type") == "video"]
    audio_tracks = [tr for tr in tracks if tr.get("type") == "audio"]
    text_tracks = [tr for tr in tracks if tr.get("type") == "text"]

    report["tracks"] = {
        "video": len(video_tracks),
        "audio": len(audio_tracks),
        "text": len(text_tracks),
    }

    # 2. Mute state (M29)
    report["mute"] = audit_mute_state(draft)

    # 3. Captions
    texts = draft.get("materials", {}).get("texts", [])
    caption_texts = []
    for t in texts:
        try:
            co = json.loads(t.get("content", "{}"))
            text = co.get("text", "").strip()
            if text:
                caption_texts.append(text)
        except json.JSONDecodeError:
            continue
    report["captions"] = {
        "count": len(caption_texts),
        "samples": caption_texts[:5],
    }

    # 4. Effects distribution
    effects = draft.get("materials", {}).get("effects", [])
    effect_names = Counter(e.get("name", "?") for e in effects)
    report["effects"] = {
        "total": len(effects),
        "distribution": dict(effect_names.most_common()),
    }

    # 5. BGM
    auds = draft.get("materials", {}).get("audios", [])
    report["bgm"] = {
        "count": len(auds),
        "first_name": auds[0].get("name", "?") if auds else None,
    }

    # 6. Canvas (blur backgrounds for portrait photos)
    canvases = draft.get("materials", {}).get("canvases", [])
    canvas_types = Counter(c.get("type", "?") for c in canvases)
    report["canvases"] = dict(canvas_types)

    # 7. Caption timing (gaps / overlaps)
    if text_tracks:
        text_track = text_tracks[0]
        prev_end = 0
        gaps = []
        overlaps = []
        for seg in text_track.get("segments", []):
            tr = seg.get("target_timerange", {})
            start = tr.get("start", 0) / 1e6
            dur = tr.get("duration", 0) / 1e6
            end = start + dur
            gap = start - prev_end
            if gap > 0.2:
                gaps.append({"start_sec": round(start, 2), "gap_sec": round(gap, 2)})
            if gap < -0.1:
                overlaps.append({"start_sec": round(start, 2), "overlap_sec": round(-gap, 2)})
            prev_end = end
        report["timing"] = {
            "total_end_sec": round(prev_end, 2),
            "gaps": gaps,
            "overlaps": overlaps,
        }

    return report


def print_audit_report(report: dict) -> None:
    """Print human-readable audit report."""
    print("=" * 70)
    print("CapCut Draft Audit")
    print("=" * 70)

    t = report.get("tracks", {})
    print(f"\nTracks: video={t.get('video', 0)} / audio={t.get('audio', 0)} / text={t.get('text', 0)}")

    m = report.get("mute", {})
    rate = m.get("success_rate", 0) * 100
    print(f"\nMute: {m.get('fully_muted', 0)}/{m.get('total_segments', 0)} fully muted ({rate:.0f}%)")
    if m.get("partial_muted"):
        for idx, missing in m["partial_muted"][:5]:
            print(f"  ⚠️  Seg {idx} missing: {missing}")

    c = report.get("captions", {})
    print(f"\nCaptions: {c.get('count', 0)} total")
    for s in c.get("samples", []):
        print(f"  - {s[:50]}")

    e = report.get("effects", {})
    print(f"\nEffects: {e.get('total', 0)} total")
    for name, cnt in e.get("distribution", {}).items():
        print(f"  {cnt:3}  {name}")

    bgm = report.get("bgm", {})
    print(f"\nBGM: {bgm.get('count', 0)} (first: {bgm.get('first_name', 'NONE')})")

    canv = report.get("canvases", {})
    print(f"\nCanvases: {canv}")

    tim = report.get("timing", {})
    if tim:
        print(f"\nTiming: ends at {tim.get('total_end_sec', 0)}s")
        gaps = tim.get("gaps", [])
        overlaps = tim.get("overlaps", [])
        if gaps:
            print(f"  ⚠️  {len(gaps)} caption gap(s):")
            for g in gaps[:3]:
                print(f"    {g['gap_sec']}s gap at {g['start_sec']}s")
        if overlaps:
            print(f"  ⚠️  {len(overlaps)} caption overlap(s):")
            for o in overlaps[:3]:
                print(f"    {o['overlap_sec']}s overlap at {o['start_sec']}s")
