"""silent_vlog_maker.verify — Editkin build/export 後 verify_steps 執行器。

Project-state checks consume Editkin's editable project and the immutable result
returned by audit_autopilot_plan. External-editor draft schemas are not evidence.
"""
from typing import Optional

from .checklists import get_pre_build_checklist


def run_verify_steps(
    content_type: str,
    mp4_path: Optional[str] = None,
    editkin_project: Optional[dict] = None,
    editkin_audit: Optional[dict] = None,
    timeline_fps: int = 30,
) -> dict:
    """🆕 2026-05-27 — Runtime execute verify_steps that have callable check.

    Verify steps fall in 3 categories:
      (A) Pure data invariant (no ffmpeg/file) — runs immediately
      (B) Needs mp4 path (ffprobe / ffmpeg) — runs if mp4_path given
      (C) Needs Editkin project / audit receipt
      (D) Manual / observational — always returned as "skipped: manual"

    Returns: {
        "results": [{"step": str, "category": str, "status": str, "detail": str}, ...],
        "passed": int, "failed": int, "manual": int,
    }
    """
    import shutil
    import subprocess as _sp

    results = []
    checklist = get_pre_build_checklist(content_type)
    if checklist is None:
        return {"results": [], "passed": 0, "failed": 0, "manual": 0,
                "error": f"no checklist for {content_type}"}

    has_ffprobe = shutil.which("ffprobe") is not None

    if editkin_project is not None:
        captions = editkin_project.get("captions", [])
        violations = []
        previous_end = -1.0
        for i, caption in enumerate(captions):
            text = str(caption.get("text", "")).strip()
            start = float(caption.get("start", 0) or 0)
            duration = float(caption.get("duration", 0) or 0)
            if not text:
                violations.append(f"caption[{i}] empty")
            if start < 0 or duration <= 0:
                violations.append(f"caption[{i}] invalid timing")
            if start + 1e-6 < previous_end:
                violations.append(f"caption[{i}] overlaps previous")
            previous_end = max(previous_end, start + duration)
        results.append({
            "step": "VERIFY 4 (subtitle integrity — Editkin project schema)",
            "category": "C",
            "status": "pass" if captions and not violations else "fail",
            "detail": f"{len(captions)} captions valid" if captions and not violations
                      else f"{len(violations)} violation(s): {violations[:3]}",
        })
        results.append({
            "step": "VERIFY 7 (M73 Editkin caption invariants)",
            "category": "C",
            "status": "pass" if captions and not violations else "fail",
            "detail": "text/timing/order schema valid" if captions and not violations
                      else "caption schema has blockers",
        })

    if editkin_audit is not None:
        audit_status = str(editkin_audit.get("status", "")).upper()
        blockers = editkin_audit.get("blockers", [])
        blocked = audit_status in {"BLOCK", "BLOCKED", "FAIL", "FAILED"} or bool(blockers)
        results.append({
            "step": "VERIFY 6 (AP15 Editkin audit_autopilot_plan)",
            "category": "C",
            "status": "fail" if blocked or not audit_status else "pass",
            "detail": f"status={audit_status or 'MISSING'} blockers={len(blockers)}",
        })

    # M81 fps check, M82 timeline trim, audio duration — all need mp4 + ffprobe
    if mp4_path and has_ffprobe:
        try:
            # M81 — fps must = timeline_fps
            r = _sp.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                         "-show_entries", "stream=avg_frame_rate",
                         "-of", "default=nw=1:nk=1", mp4_path],
                        capture_output=True, text=True, timeout=10)
            fps_str = r.stdout.strip()
            results.append({
                "step": "VERIFY 0b (M81 fps conformance)",
                "category": "B",
                "status": "pass" if fps_str == f"{timeline_fps}/1" else "fail",
                "detail": f"avg_frame_rate={fps_str} (expected {timeline_fps}/1)",
            })

            # M82 — no extended silence at tail (> 5s = ship blocker)
            r = _sp.run(["ffmpeg", "-i", mp4_path, "-af",
                         "silencedetect=noise=-30dB:d=5", "-f", "null", "-"],
                        capture_output=True, text=True, timeout=60)
            silence_lines = [l for l in r.stderr.splitlines() if "silence_" in l]
            # Find any silence whose duration > 8 seconds (allow 6s outro card)
            big_tail_silence = False
            for line in silence_lines:
                if "silence_duration" in line:
                    try:
                        dur = float(line.split("silence_duration:")[1].strip().split()[0])
                        if dur > 8.0:
                            big_tail_silence = True
                            break
                    except Exception:
                        pass
            results.append({
                "step": "VERIFY 0c (M82 timeline trim — no >8s silence)",
                "category": "B",
                "status": "fail" if big_tail_silence else "pass",
                "detail": "extended silence detected (timeline > voice end?)"
                          if big_tail_silence
                          else "no excessive silence at tail",
            })
        except _sp.TimeoutExpired:
            results.append({"step": "ffprobe checks", "category": "B",
                            "status": "error", "detail": "ffprobe timeout"})
        except Exception as e:
            results.append({"step": "ffprobe checks", "category": "B",
                            "status": "error", "detail": str(e)[:80]})

    # 🆕 2026-06-20 (rank2 強化): 全覆蓋標記 — 任何 verify_step 沒被自動跑就標 manual。
    # 原本只認 5 個字串前綴 → VERIFY 4 / 6b(M86) 等既不跑也不標 = 純消失。改成「每個 step
    # 都要在 results 出現」+ coverage guard，杜絕未來新增 verify_step 被靜默漏掉。
    import re as _re

    def _vid(s):
        m = _re.search(r'VERIFY\s+(\S+)', s)
        return ("VERIFY " + m.group(1)) if m else s.split(":")[0].split("(")[0].strip()

    covered = {_vid(r["step"]) for r in results}
    for s in checklist["verify_steps"]:
        vid = _vid(s)
        if vid not in covered:
            results.append({
                "step": vid,
                "category": "D",
                "status": "manual",
                "detail": "人工確認 — 需肉眼/build-time 資料(如 M86 占比需 segments，M91 chrome 接觸表)",
            })
            covered.add(vid)

    # regression guard：每個 verify_step 都有對應 result（不可靜默消失）
    all_ids = {_vid(s) for s in checklist["verify_steps"]}
    uncovered = sorted(all_ids - covered)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    manual = sum(1 for r in results if r["status"] == "manual")
    return {"results": results, "passed": passed, "failed": failed, "manual": manual,
            "coverage": f"{len(all_ids) - len(uncovered)}/{len(all_ids)} verify_steps represented",
            "uncovered": uncovered}


def validate_checklist_answers(content_type: str, user_answers: dict) -> dict:
    """Validate user answers against a checklist's required questions.

    Args:
        content_type: e.g. "teaching_longform"
        user_answers: dict with keys matching questions_for_user numbering

    Returns: {
        "valid": bool,
        "missing": list of unanswered question numbers,
        "extras": list of extra keys not in checklist,
        "merged_config": dict with defaults + user_answers,
    }
    """
    checklist = get_pre_build_checklist(content_type)
    if checklist is None:
        return {
            "valid": False,
            "missing": [],
            "extras": [],
            "merged_config": {},
            "error": f"Unknown content_type: {content_type}",
        }

    # 題號從題目字串的「N.」前綴推導 — teaching checklist 是 0-based（0.~4.），
    # 之前寫死 1..N 害「全答了還 valid=False」(2026-06-10 audit)
    q_nums = []
    for q in checklist["questions_for_user"]:
        head = str(q).strip().split(".", 1)[0]
        if head.strip().lstrip("🎥🎬📐🔊⚙️ ").isdigit():
            q_nums.append(int(head.strip().lstrip("🎥🎬📐🔊⚙️ ")))
    if len(q_nums) != len(checklist["questions_for_user"]):
        q_nums = list(range(1, len(checklist["questions_for_user"]) + 1))  # fallback
    expected_nums = set(q_nums)
    expected_keys = expected_nums | {f"q{i}" for i in expected_nums}
    answered_int = {int(k) for k in user_answers.keys() if isinstance(k, int) or (isinstance(k, str) and k.isdigit())}
    answered_q = {int(k[1:]) for k in user_answers.keys() if isinstance(k, str) and k.startswith("q") and k[1:].isdigit()}
    answered = answered_int | answered_q

    missing = sorted(expected_nums - answered)
    extras = sorted(k for k in user_answers.keys() if k not in expected_keys)

    merged = dict(checklist["defaults"])
    merged.update({f"user_q{k}": v for k, v in user_answers.items()})

    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "extras": extras,
        "merged_config": merged,
    }
