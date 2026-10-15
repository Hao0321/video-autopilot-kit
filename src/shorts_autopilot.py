# -*- coding: utf-8 -*-
"""Short-form autopilot orchestration (public distribution).

Routes scan, plan, build, QA and delivery around an explicit source folder and structured receipts.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

# Reject the retired CLI before updater, workspace discovery or renderer imports.
if __name__ == "__main__" and sys.argv[1:2] == ["build"]:
    sys.stderr.write("Retired Shorts build entrypoint. Use workflow_contract.py create for the Editkin v4 audit/apply/render/review path.\n")
    raise SystemExit(2)

# Windows may expose a CP950 console even though project plans are UTF-8.
# Warnings must never abort a render merely because a caption contains a
# Japanese punctuation mark, emoji, or another otherwise valid glyph.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="backslashreplace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "longform_maker"))

from av_util import contact_sheet, duration as _dur, grab_frame, run as _run  # noqa: E402
from storage_lifecycle import (  # noqa: E402
    activate_policy,
    atomic_publish,
    canonical_output_path,
    finalize_success,
)
from project_paths import asset_path, discover_project_root, video_path  # noqa: E402
import publish_hub  # noqa: E402
from shorts_delivery import (  # noqa: E402
    apply_tracked_graphics,
    run_short_qa,
    write_short_report,
)

PROJECT_ROOT = str(discover_project_root(HERE))
from shorts_scan import (
    INBOX,
    _scan_input_clips,
    _write_scan_previews,
    _write_scan_plan,
)
BGM_ROOT = str(asset_path("bgm"))
LATEST_PIPELINE_RELEASE = "shorts-v9-2026.08.21"
LATEST_VISUAL_PLAN_VERSION = 9
LATEST_COMPOSITION_SCHEMA = "hao.motion-composition/v1"


# ───────────────────────────────────────────── 步驟1：scan


def scan(folder_id: str) -> dict:
    """正規化 + GPS + 接觸表 + 標價牌放大圖 + _plan.py 骨架。"""
    info, src_dir, work = _scan_input_clips(folder_id)

    # 2) 接觸表（每 clip 3 幀）
    _write_scan_previews(info, work)

    # 4) 自動排片段（機械可算的全做完）
    ap = auto_plan(info)

    # 5) _plan.py（片段已排好，只剩文字待填）
    _write_scan_plan(ap, folder_id, info, src_dir, work)

    with open(os.path.join(work, "_scan.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return info


# ───────────────────────────────────────────── 自動排片段（更聰明）

from shorts_planning import (
    _clip_metrics,
    _best_window,
    _wave_segment_durations,
    auto_plan,
)


# ───────────────────────────────────────────── 步驟3：build + QA

def _bgm_candidates(folder_name: str) -> list:
    """BGM 候選。2026-07-29 去靜默：

    舊版三層靜默疊加——資料夾名打錯→無聲換 _通用（氣氛全錯不會知道）→
    _通用 也空→pick_bgm 回 None→render 拿 None 繼續跑，要到 QA 的 LUFS
    才間接發現，訊息還跟真因無關。改成：fallback 大聲印、全空直接 raise。
    （順修：舊 fallback 只 glob *.mp3，_通用 放 wav 會被漏。）
    """
    def _glob(name):
        d = os.path.join(BGM_ROOT, name)
        return (sorted(glob.glob(os.path.join(d, "*.wav"))) +
                sorted(glob.glob(os.path.join(d, "*.mp3"))))

    if not os.path.isdir(os.path.join(BGM_ROOT, folder_name)):
        print("   WARN BGM folder does not exist: %r -> fallback _通用" % folder_name)
    cands = _glob(folder_name)
    if not cands:
        print("   WARN BGM folder %r has no wav/mp3 -> fallback _通用" % folder_name)
        cands = _glob("_通用")
    if not cands:
        raise AssertionError(
            "BGM candidates empty: folder %r and _通用 both have no wav/mp3 -- "
            "silent Short relies on BGM as the only audio; no BGM = broken deliverable. "
            "Fix the folder name in _plan.py or add tracks under %s" % (folder_name, BGM_ROOT))
    return cands


def _resolve_bgm(spec: dict, visual_plan: dict, folder_bgm: str) -> tuple[str, str]:
    """Respect an explicit editorial music lock; otherwise use Asset Hub ranking."""
    policy = str(spec.get("bgm_policy", "asset_hub"))
    if policy not in {"asset_hub", "folder"}:
        raise AssertionError("unknown bgm_policy %r; expected asset_hub/folder" % policy)
    if policy == "folder":
        return folder_bgm, "folder_lock"
    selected = (visual_plan.get("asset_intelligence") or {}).get("selected_bgm")
    if selected:
        selected_path = selected if os.path.isabs(selected) \
            else os.path.join(PROJECT_ROOT, selected.replace("/", os.sep))
        if os.path.isfile(selected_path):
            return selected_path, "asset_hub"
    return folder_bgm, "folder_fallback"


def _load_plan(folder_id: str) -> tuple[str, dict]:
    src_dir = os.path.join(INBOX, folder_id)
    plan_path = os.path.join(src_dir, "_plan.py")
    assert os.path.exists(plan_path), "還沒有 _plan.py，先跑 scan：" + plan_path
    import importlib.util
    spec_mod = importlib.util.spec_from_file_location("plan_%s" % folder_id, plan_path)
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    spec = mod.SPEC
    assert "TODO" not in json.dumps(spec, default=str), \
        "%s/_plan.py 還有 TODO 未填" % folder_id
    return src_dir, spec


def _editorial_payload(spec: dict, ready: dict, visual_plan: dict) -> dict:
    """Canonical proof of editorial decisions, not render/cache metadata."""
    segs = [{
        "source": os.path.basename(str(path)),
        "in": round(float(start), 3),
        "duration": round(float(duration), 3),
    } for path, start, duration in spec.get("segs", [])]
    captions = [{
        "segment": int(index), "kind": str(kind),
        "text": "".join(str(text) for text, _color in pieces),
    } for index, pieces, kind in spec.get("caps_by_seg", [])]
    return {
        "schema": "hao.editorial-fingerprint/v1",
        "segment_sequence": segs,
        "captions": captions,
        "opening": {
            "place": spec.get("place"), "what": spec.get("what"),
            "first_cut": segs[0]["duration"] if segs else None,
            "promise": (visual_plan.get("story") or {}).get("opening_promise"),
        },
        "identity": {
            "niche": spec.get("niche"), "platform": spec.get("platform"),
            "label_policy": spec.get("persistent_label_policy", "required"),
        },
        "visual_language": {
            "theme": visual_plan.get("theme"), "domain": visual_plan.get("domain"),
            "color_profile": spec.get("color_profile"),
            "color_strength": spec.get("color_strength"),
            "caption_system": visual_plan.get("caption_system"),
        },
        "effects": {
            "tracked_graphics": spec.get("tracked_graphics"),
            "motion_asset_policy": spec.get("motion_asset_policy"),
            "motion_cues": (visual_plan.get("motion_assets") or {}).get("cues"),
            "runtime": visual_plan.get("programmatic_runtime"),
        },
    }


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fingerprint_paths(src_dir: str) -> tuple[str, str]:
    out_dir = os.path.join(src_dir, "_out")
    return (os.path.join(out_dir, "editorial_baseline.json"),
            os.path.join(out_dir, "current_editorial_fingerprint.json"))


def _read_json(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def snapshot_editorial_baseline(folder_id: str) -> dict:
    """Freeze the existing edit before a requested true recut."""
    from shorts_gate import assert_shorts
    src_dir, spec = _load_plan(folder_id)
    ready = assert_shorts(spec)
    out_dir = os.path.join(src_dir, "_out")
    os.makedirs(out_dir, exist_ok=True)
    visual = _read_json(os.path.join(out_dir, "current_visual_plan.json")) or {}
    payload = _editorial_payload(spec, ready, visual)
    baseline_path, _current_path = _fingerprint_paths(src_dir)
    receipt = {"schema": "hao.editorial-baseline/v1", "sha256": _fingerprint(payload),
               "payload": payload, "status": "FROZEN_BEFORE_RECUT"}
    if not os.path.isfile(baseline_path):
        with open(baseline_path, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return receipt


def _true_recut_receipt(src_dir: str, spec: dict, ready: dict, visual_plan: dict) -> dict:
    payload = _editorial_payload(spec, ready, visual_plan)
    current_sha = _fingerprint(payload)
    baseline_path, _current_path = _fingerprint_paths(src_dir)
    baseline = _read_json(baseline_path)
    if spec.get("require_true_recut") and not baseline:
        raise AssertionError("TRUE_RECUT_BASELINE_REQUIRED: snapshot the previous edit first")
    previous_sha = (baseline or {}).get("sha256")
    old_payload = (baseline or {}).get("payload") or {}
    dimensions = sorted(key for key in payload if old_payload.get(key) != payload.get(key))
    if spec.get("require_true_recut") and current_sha == previous_sha:
        raise AssertionError("FAKE_RECUT_BLOCKED: editorial fingerprint did not change")
    if spec.get("require_true_recut") and not {"segment_sequence", "captions", "opening"}.intersection(dimensions):
        raise AssertionError("FAKE_RECUT_BLOCKED: no shot/rhythm/opening decision changed")
    return {"schema": "hao.editorial-recut-receipt/v1", "previous_sha256": previous_sha,
            "current_sha256": current_sha, "changed_dimensions": dimensions,
            "payload": payload, "status": "TRUE_RECUT_CHANGED" if previous_sha else "NEW_EDIT"}


def _persist_editorial_receipt(src_dir: str, receipt: dict) -> str:
    _baseline, current_path = _fingerprint_paths(src_dir)
    with open(current_path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return current_path


def _prepare_visual_plan(folder_id: str, spec: dict, ready: dict, out_dir: str) -> tuple:
    from autonomy_standard import prepare_unattended_plan
    from caption_director import apply_caption_system
    from visual_director import write_visual_plan

    tracked = spec.get("tracked_graphics") or {}
    tracked_intervals = []
    for bucket in ("tracked_labels", "mask_sheens", "telemetry_callouts"):
        for item in tracked.get(bucket) or []:
            tracked_intervals.append((float(item.get("start", 0)),
                                      float(item.get("end", 0))))

    def _tracked_overlap(start: float, end: float) -> bool:
        return any(float(start) < right and float(end) > left
                   for left, right in tracked_intervals)

    caption_rows = [{
        "start": start, "end": end,
        "text": "".join(str(text) for text, _color in pieces), "kind": kind,
        "tracked_subject_overlaps": _tracked_overlap(start, end),
    } for start, end, pieces, kind in ready["caps"]]
    theme_text = " ".join(str(spec.get(key, "")) for key in
                          ("name", "place", "what", "bgm_folder")) + " " + \
                 " ".join(row["text"] for row in caption_rows)
    visual_plan_path = os.path.join(out_dir, "current_visual_plan.json")
    visual_plan = write_visual_plan(
        visual_plan_path, duration=ready["_dur"], captions=caption_rows,
        genre=spec.get("niche", "auto"), context_text=theme_text, format="short",
        seed=folder_id, color_profile=spec.get("color_profile"),
        color_strength=spec.get("color_strength"),
    )
    if spec.get("motion_asset_policy") == "tracked_only":
        visual_plan.setdefault("motion_assets", {})["cues"] = []
        visual_plan["motion_assets"]["policy"] = "tracked_only"
    visual_plan, unattended_repairs = prepare_unattended_plan(visual_plan)
    with open(visual_plan_path, "w", encoding="utf-8") as handle:
        json.dump(visual_plan, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    routed_ready = dict(ready, caps=apply_caption_system(
        ready["caps"], visual_plan["caption_system"]))
    return routed_ready, visual_plan, visual_plan_path, unattended_repairs


def _latest_runtime_receipt(visual_plan: dict, out_dir: str) -> dict:
    """Fail closed when an old planner/runtime tries to produce a new master."""
    runtime = visual_plan.get("programmatic_runtime") or {}
    composition_path = os.path.join(out_dir, str(runtime.get("composition") or ""))
    graph_path = os.path.join(out_dir, str(runtime.get("render_graph") or ""))
    failures = []
    if int(visual_plan.get("version") or 0) < LATEST_VISUAL_PLAN_VERSION:
        failures.append("visual plan version is older than the current release")
    if runtime.get("schema") != LATEST_COMPOSITION_SCHEMA or runtime.get("status") != "GREEN":
        failures.append("programmatic runtime is not compiled GREEN on the canonical schema")
    for label, path in (("composition", composition_path), ("render_graph", graph_path)):
        if not path or not os.path.isfile(path):
            failures.append("missing " + label)
            continue
        try:
            payload = json.loads(open(path, encoding="utf-8").read())
        except (OSError, ValueError):
            failures.append("invalid " + label)
            continue
        if payload.get("schema") != LATEST_COMPOSITION_SCHEMA:
            failures.append(label + " schema is stale")
        if label == "render_graph" and payload.get("status") != "GREEN":
            failures.append("render graph did not compile GREEN")
    if failures:
        raise AssertionError("LATEST_RUNTIME_REQUIRED: " + "; ".join(failures))
    return {
        "release": LATEST_PIPELINE_RELEASE,
        "visual_plan_version": int(visual_plan["version"]),
        "composition_schema": LATEST_COMPOSITION_SCHEMA,
        "composition": os.path.basename(composition_path),
        "render_graph": os.path.basename(graph_path),
        "legacy_master_allowed": False,
        "status": "GREEN",
    }


def _persist_runtime_receipt(out_dir: str, receipt: dict) -> str:
    """Persist the latest-only proof only after the rendered master passed QA."""
    path = os.path.join(out_dir, "current_runtime_receipt.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)
    return path


def _collect_short_qa(
    spec: dict, ready: dict, out: str, out_dir: str, visual_plan: dict,
    visual_plan_path: str, bgm: str, unattended_repairs: list,
    runtime_receipt: dict,
) -> tuple[dict, dict | None]:
    tracked_report = apply_tracked_graphics(spec, ready, out, out_dir, os.path.join(out_dir, "_work"))
    qa = run_short_qa(out, ready, out_dir)
    color_report_path = os.path.join(out_dir, "current_color_report.json")
    if os.path.isfile(color_report_path):
        with open(color_report_path, encoding="utf-8") as handle:
            qa["color_grade"] = json.load(handle)
    if tracked_report:
        qa["tracked_graphics"] = tracked_report
    runtime_receipt_path = None
    if qa.get("all_green"):
        runtime_receipt_path = _persist_runtime_receipt(out_dir, runtime_receipt)
    qa.update({
        "visual_theme": visual_plan["theme"], "editing_domain": visual_plan["domain"],
        "visual_plan": visual_plan_path,
        "asset_plan": os.path.join(out_dir, "current_asset_plan.json"),
        "selected_bgm": bgm,
        "runtime_release": runtime_receipt,
        "runtime_receipt": runtime_receipt_path,
        "unattended_preflight": {
            "status": "AUTO_REPAIRED" if unattended_repairs else "NO_REPAIR_NEEDED",
            "repairs": unattended_repairs,
        },
    })
    return qa, tracked_report


def _quality_review_short(
    folder_id: str, spec: dict, ready: dict, qa: dict, visual_plan: dict,
    tracked_report: dict | None, out: str, out_dir: str,
) -> dict:
    from autonomy_standard import assess_and_enqueue
    from quality_95 import short_evidence, write_report as write_quality_report
    from review_loop import create_bundle as create_review_bundle

    quality_evidence = short_evidence(
        content_id="shorts-" + str(folder_id), spec=spec, ready=ready, qa=qa,
        visual_plan=visual_plan, tracked_report=tracked_report, project_root=PROJECT_ROOT,
    )
    quality = write_quality_report(os.path.join(out_dir, "_qa"), quality_evidence)
    qa["quality_95"] = {
        "status": quality["status"], "score": quality["score"], "report": quality["json"],
    }
    qa["hao_review"] = create_review_bundle(out, "shorts-" + str(folder_id), quality["json"])
    qa["autonomy"] = assess_and_enqueue(
        content_id=_short_content_id(folder_id), format="shorts", artifact=out,
        qa=qa, visual_plan=visual_plan, quality_report=quality,
    )
    return qa


def _short_content_id(folder_id: str) -> str:
    """Return a stable publish/review id for base and split-battle Shorts."""
    raw = str(folder_id).strip()
    if raw.isdigit():
        return "S%03d" % int(raw)
    head, sep, tail = raw.partition("-")
    if sep and head.isdigit() and tail and all(part.isdigit() for part in tail.split("-")):
        return "S%03d-%s" % (int(head), tail)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)
    return "S" + safe


def _finalize_short(
    folder_id: str, src_dir: str, spec: dict, ready: dict, qa: dict,
    visual_plan: dict, bgm: str, out: str, work_dir: str, policy: dict,
) -> dict:
    if qa.get("all_green") and ready.get("_editorial_receipt"):
        qa["editorial_fingerprint"] = {
            "status": ready["_editorial_receipt"]["status"],
            "changed_dimensions": ready["_editorial_receipt"]["changed_dimensions"],
            "path": _persist_editorial_receipt(src_dir, ready["_editorial_receipt"]),
        }
    if qa.get("all_green"):
        from asset_registry import record_asset_paths
        used_assets = [bgm] + [
            cue["path"] for cue in ((visual_plan.get("motion_assets") or {}).get("cues") or [])
            if cue.get("role") in ("overlay", "transition") and cue.get("path")
        ]
        qa["asset_usage_recorded"] = record_asset_paths(
            used_assets, content_id="shorts-" + str(folder_id), project_root=PROJECT_ROOT)
    qa["storage"] = finalize_success(src_dir, out, work_dir, qa)
    qa["storage"]["grandfathered_legacy"] = len(policy.get("legacy_files") or [])
    write_short_report(src_dir, spec, ready, qa, out)
    qa["publishing"] = publish_hub.register_completed_short(folder_id, qa)
    write_short_report(src_dir, spec, ready, qa, out)
    return qa


def build(folder_id: str) -> dict:
    raise RuntimeError("Retired Shorts build entrypoint. Create an Editkin v4 run with workflow_contract.py; audit, atomic apply, render and artifact-bound visual review are required.")


def main():
    # Public-kit installs include a bounded, compatibility-gated updater.  The
    # private canonical workspace intentionally has no startup_update module,
    # so development runs remain local and deterministic.
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] != "selftest":
        try:
            from startup_update import ensure_current  # type: ignore
        except ImportError:
            pass
        else:
            ensure_current()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "snapshot", "selftest"])
    ap.add_argument("folders", nargs="*")
    a = ap.parse_args()
    if a.cmd == "selftest":
        six = _wave_segment_durations(6, 12.4)
        assert len(six) == 6 and abs(sum(six) - 12.4) < .08
        assert max(six) - min(six) >= .8 and six[3] == max(six) and six[4] == min(six)
        four = _wave_segment_durations(4, 10.4)
        assert all(1.8 <= d <= 3.6 for d in four) and abs(sum(four) - 10.4) < .08
        locked, source = _resolve_bgm(
            {"bgm_policy": "folder"},
            {"asset_intelligence": {"selected_bgm": "assets/bgm/wrong.wav"}},
            "chosen-folder.wav",
        )
        assert locked == "chosen-folder.wav" and source == "folder_lock"
        assert LATEST_VISUAL_PLAN_VERSION == 9
        assert LATEST_COMPOSITION_SCHEMA == "hao.motion-composition/v1"
        print("shorts_autopilot self-test OK")
        return 0
    if not a.folders:
        ap.error("scan/snapshot requires at least one folder id")
    for fid in a.folders:
        if a.cmd == "scan":
            scan(fid)
        elif a.cmd == "snapshot":
            rec = snapshot_editorial_baseline(fid)
            print("[snapshot] %s %s" % (fid, rec["sha256"][:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
