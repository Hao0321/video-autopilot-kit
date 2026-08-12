"""silent_vlog_maker.verify — build/export 後 verify_steps 執行器 (2026-05-27)。

2026-06-20 從 content_routing 拆出。run_verify_steps 內的 capcut_helpers import 刻意保持
function-local + ImportError-guarded（hoist 到 module top 會在 capcut_helpers 不在 path 時炸；
正是 2026-06-10 audit 修掉的 bug）。
"""
from typing import Optional

from .checklists import get_pre_build_checklist


def run_verify_steps(
    content_type: str,
    mp4_path: Optional[str] = None,
    draft: Optional[dict] = None,
    timeline_fps: int = 30,
) -> dict:
    """🆕 2026-05-27 — Runtime execute verify_steps that have callable check.

    Verify steps fall in 3 categories:
      (A) Pure data invariant (no ffmpeg/file) — runs immediately
      (B) Needs mp4 path (ffprobe / ffmpeg) — runs if mp4_path given
      (C) Needs draft dict — runs if draft given
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

    # M73 — TEXT_MATERIAL invariants check (no ffmpeg needed)
    if draft is not None:
        # capcut_helpers 在另一個 skill root — import 必須 guard（2026-06-10 audit:
        # 之前裸 import，不在 sys.path 時整個 verify run 直接 ModuleNotFoundError 炸掉）
        try:
            from capcut_helpers import TEXT_MATERIAL_INVARIANTS
        except ImportError:
            TEXT_MATERIAL_INVARIANTS = None
            results.append({
                "step": "VERIFY 7 (M73 styles range invariants)",
                "category": "C", "status": "error",
                "detail": "capcut_helpers not importable (add its skill root to sys.path)",
            })
        if TEXT_MATERIAL_INVARIANTS is not None:
            import json as _json
            texts = draft.get("materials", {}).get("texts", [])
            violations = []
            for i, t in enumerate(texts):
                try:
                    co = _json.loads(t.get("content", "{}"))
                except Exception:
                    continue
                for name, check_fn in TEXT_MATERIAL_INVARIANTS.items():
                    try:
                        if not check_fn(co):
                            violations.append(f"text[{i}] {name}")
                    except Exception:
                        pass
            results.append({
                "step": "VERIFY 7 (M73 styles range invariants)",
                "category": "C",
                "status": "pass" if not violations else "fail",
                "detail": "all styles[].range[1] == len(text)" if not violations
                          else f"{len(violations)} violation(s): {violations[:3]}",
            })

        # AP15 caption-broll mismatch audit
        try:
            from capcut_helpers import audit_caption_broll_mismatch
            audit = audit_caption_broll_mismatch(draft)
            high = audit["summary_by_severity"]["high"]
            results.append({
                "step": "VERIFY 6 (AP15 caption-broll match)",
                "category": "C",
                "status": "pass" if high == 0 else "fail",
                "detail": f"high={high} / medium={audit['summary_by_severity']['medium']} / "
                          f"matched={audit['matched_ok']}/{audit['total_captions']}",
            })
        except Exception as e:
            results.append({
                "step": "VERIFY 6 (AP15 caption-broll match)",
                "category": "C", "status": "error", "detail": str(e)[:80],
            })

        # VERIFY 4 — M69 字幕潛在誤字掃描 (2026-06-20 rank2 接上：原本 helper 存在卻沒人呼叫=孤兒)
        try:
            try:
                from capcut_helpers import scan_potential_errors
            except ImportError:
                # scan_potential_errors 住在隔壁 skill (capcut-agent-ops)；自己定位、不靠呼叫端設 path
                import sys as _sys, os as _os
                _skills = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
                _cap = _os.path.join(_skills, "capcut-agent-ops")
                if _cap not in _sys.path:
                    _sys.path.insert(0, _cap)
                from capcut_helpers import scan_potential_errors
            scan = scan_potential_errors(draft)
            n = scan.get("total_suspects", 0)
            results.append({
                "step": "VERIFY 4 (subtitle integrity — M69 scan_potential_errors)",
                "category": "C",
                "status": "pass" if n == 0 else "fail",
                "detail": "0 suspects" if n == 0
                          else f"{n} suspect(s): {[s.get('text','')[:12] for s in scan.get('suspects', [])[:3]]}",
            })
        except Exception as e:
            results.append({
                "step": "VERIFY 4 (subtitle integrity)",
                "category": "C", "status": "error", "detail": str(e)[:80],
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
