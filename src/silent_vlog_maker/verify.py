"""Editkin v4 plan/receipt and rendered-media verification.

The legacy editor JSON checks have been replaced by fail-closed validation of
the canonical v4 plan, its material-intelligence evidence, the durable workflow
ledger, and the final rendered media.  No external editor helper is imported.
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from .checklists import get_pre_build_checklist


_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)
_SUSPECT_PATTERNS = (
    (re.compile(r"\b(?:clouds?|clear|crowd)\b", re.I), "likely Claude"),
    (re.compile(r"\bstudio\b"), "likely Studio case"),
    (re.compile(r"\bRN\b"), "likely Render"),
    (re.compile(r"扣的"), "likely Code"),
    (re.compile(r"網易"), "likely 網域"),
    (re.compile(r"克[拉勞]奧?|可好"), "likely Claude"),
    (re.compile(r"加過"), "likely 架過"),
    (re.compile(r"迪\s*[bB]ug"), "likely Debug"),
    (re.compile(r"(?<!掰)拜拜"), "likely 掰掰"),
    (re.compile(r"磕出"), "likely 刻出"),
)
_SIMPLIFIED_ONLY = frozenset("这为发后里么过说们还对时会让从实现进开关视频画质学习统软编辑帧设计网络题应该与专业")


def _caption_strings(value: Any, key_hint: str = "") -> list[str]:
    """Collect caption/text payloads from a renderer-neutral Editkin plan."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_caption_strings(child, str(key)))
    elif isinstance(value, list):
        for child in value:
            found.extend(_caption_strings(child, key_hint))
    elif isinstance(value, str) and any(token in key_hint.lower()
                                         for token in ("caption", "subtitle", "text", "title")):
        found.append(value)
    return found


def _scan_caption_text(plan: dict) -> list[dict[str, str]]:
    suspects = []
    for text in _caption_strings(plan):
        simplified = sorted(set(text) & _SIMPLIFIED_ONLY)
        if simplified:
            suspects.append({"text": text[:80], "reason": "simplified-only chars: " + "".join(simplified)})
        for pattern, note in _SUSPECT_PATTERNS:
            if pattern.search(text):
                suspects.append({"text": text[:80], "reason": note})
    return suspects


def _validate_edit_plan(plan: dict) -> tuple[list[str], int]:
    """Validate the renderer-neutral portion of edit-plan/v4 before receipt binding."""
    errors: list[str] = []
    if plan.get("schema") != "hao.video-autopilot.edit-plan/v4":
        errors.append("schema must be hao.video-autopilot.edit-plan/v4")
    source = plan.get("source") if isinstance(plan.get("source"), dict) else {}
    for key in ("skillSha256", "knowledgeSha256"):
        if not _SHA256.fullmatch(str(source.get(key, ""))):
            errors.append(f"source.{key} must be sha256")
    evidence = plan.get("materialEvidence") if isinstance(plan.get("materialEvidence"), dict) else {}
    if evidence.get("schema") != "hao.editkin.material-intelligence/v1":
        errors.append("materialEvidence schema missing/current mismatch")
    receipts = evidence.get("receipts") if isinstance(evidence.get("receipts"), list) else []
    if not receipts:
        errors.append("materialEvidence.receipts must contain every bound material")
    ids: list[str] = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            errors.append(f"materialEvidence.receipts[{index}] is not an object")
            continue
        material_id = str(receipt.get("materialId", ""))
        ids.append(material_id)
        if not material_id:
            errors.append(f"materialEvidence.receipts[{index}].materialId missing")
        for key in ("sourceSha256", "semanticReceiptSha256"):
            if not _SHA256.fullmatch(str(receipt.get(key, ""))):
                errors.append(f"materialEvidence.receipts[{index}].{key} must be sha256")
        for key in ("assetId", "clipId"):
            if not receipt.get(key):
                errors.append(f"materialEvidence.receipts[{index}].{key} missing")
    if len(ids) != len(set(ids)):
        errors.append("materialEvidence contains duplicate materialId")
    context = ((plan.get("inference") or {}).get("context") or {}) \
        if isinstance(plan.get("inference"), dict) else {}
    if not _SHA256.fullmatch(str(context.get("markdownRouterSha256", ""))):
        errors.append("inference.context.markdownRouterSha256 must be sha256")
    return errors, len(receipts)


def _verify_workflow_ledger(state_path: str) -> tuple[dict, dict]:
    """Load through the canonical controller and verify every durable receipt hash."""
    candidate = Path(state_path).expanduser().resolve()
    run_dir = candidate.parent if candidate.is_file() else candidate
    raw = json.loads((run_dir / "workflow-state.json").read_text(encoding="utf-8"))
    workspace = Path(raw["workspace"]).resolve()
    autopilot = Path(__file__).resolve().parents[1]
    if str(autopilot) not in sys.path:
        sys.path.insert(0, str(autopilot))
    from workflow_receipts import verify_run
    from workflow_state import load_state
    state = load_state(run_dir, workspace)
    return state, verify_run(state, workspace)


def _plan_from_workflow_state(state_path: str) -> dict:
    candidate = Path(state_path).expanduser().resolve()
    run_dir = candidate.parent if candidate.is_file() else candidate
    raw = json.loads((run_dir / "workflow-state.json").read_text(encoding="utf-8"))
    artifact = (raw.get("plan") or {}).get("artifact")
    if not artifact:
        raise ValueError("workflow has no completed v4 plan artifact")
    return json.loads((Path(raw["workspace"]) / artifact).read_text(encoding="utf-8"))


def run_verify_steps(
    content_type: str,
    mp4_path: Optional[str] = None,
    edit_plan: Optional[dict] = None,
    workflow_state_path: Optional[str] = None,
    timeline_fps: int = 30,
) -> dict:
    """🆕 2026-05-27 — Runtime execute verify_steps that have callable check.

    Verify steps fall in 3 categories:
      (A) Editkin v4 plan + workflow receipt invariant — runs immediately
      (B) Needs mp4 path (ffprobe / ffmpeg) — runs if mp4_path given
      (C) Needs edit_plan/workflow_state_path — fail closed when omitted
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

    plan_load_error = None
    if edit_plan is None and workflow_state_path:
        try:
            edit_plan = _plan_from_workflow_state(workflow_state_path)
        except Exception as exc:
            plan_load_error = str(exc)
    plan_errors, evidence_count = _validate_edit_plan(edit_plan or {})
    if plan_load_error:
        plan_errors.insert(0, plan_load_error)
    results.append({
        "step": "VERIFY 7 (Editkin v4 plan/material evidence invariants)",
        "category": "C", "status": "pass" if not plan_errors else "fail",
        "detail": f"v4 plan + {evidence_count} material semantic receipt(s)"
                  if not plan_errors else "; ".join(plan_errors[:4]),
    })
    if content_type in {"teaching", "teaching_longform", "screen_recording_teaching"}:
        suspects = _scan_caption_text(edit_plan or {})
        results.append({
            "step": "VERIFY 4 (subtitle integrity — Editkin v4 caption commands)",
            "category": "C", "status": "pass" if edit_plan is not None and not suspects else "fail",
            "detail": "0 suspects" if edit_plan is not None and not suspects
                      else (f"{len(suspects)} suspect(s): {suspects[:3]}" if suspects
                            else "edit_plan is required"),
        })

    semantic_step = "VERIFY 6" if content_type in {
        "teaching", "teaching_longform", "screen_recording_teaching"
    } else "VERIFY 5"
    try:
        if not workflow_state_path:
            raise ValueError("workflow_state_path is required for receipt-bound semantic audit")
        state, ledger = _verify_workflow_ledger(workflow_state_path)
        from workflow_state import plan_sha256
        audit = (state.get("steps") or {}).get("audit") or {}
        plan_step = (state.get("steps") or {}).get("plan") or {}
        apply_step = (state.get("steps") or {}).get("apply") or {}
        render_step = (state.get("steps") or {}).get("render") or {}
        plan_bound = edit_plan is not None and plan_sha256(edit_plan) == (state.get("plan") or {}).get("plan_sha256")
        ok = ledger.get("status") == "GREEN" and audit.get("status") == "completed" \
            and plan_step.get("status") == "completed" and plan_bound \
            and evidence_count > 0 and not plan_errors
        results.append({
            "step": f"{semantic_step} (AP15 material semantics + Editkin audit receipt)",
            "category": "C", "status": "pass" if ok else "fail",
            "detail": (f"ledger GREEN; audit receipt bound; material receipts={evidence_count}"
                       if ok else f"ledger={ledger.get('status')}; audit={audit.get('status')}; "
                                  f"plan={plan_step.get('status')}; bound={plan_bound}; "
                                  f"errors={ledger.get('errors', [])[:2]}"),
        })
        render_ok = ledger.get("status") == "GREEN" and apply_step.get("status") == "completed" \
            and render_step.get("status") == "completed" and plan_bound
        results.append({
            "step": "VERIFY R (Editkin atomic apply + render receipt chain)",
            "category": "C", "status": "pass" if render_ok else "fail",
            "detail": "committed apply and render receipts match the bound v4 plan"
                      if render_ok else f"apply={apply_step.get('status')}; "
                                        f"render={render_step.get('status')}; bound={plan_bound}",
        })
    except Exception as exc:
        results.append({
            "step": f"{semantic_step} (AP15 material semantics + Editkin audit receipt)",
            "category": "C", "status": "fail", "detail": str(exc)[:180],
        })
        results.append({
            "step": "VERIFY R (Editkin atomic apply + render receipt chain)",
            "category": "C", "status": "fail", "detail": str(exc)[:180],
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


def _selftest() -> int:
    sha = "a" * 64
    plan = {
        "schema": "hao.video-autopilot.edit-plan/v4",
        "source": {"skillSha256": sha, "knowledgeSha256": "b" * 64},
        "materialEvidence": {
            "schema": "hao.editkin.material-intelligence/v1",
            "receipts": [{
                "materialId": "m1", "sourceSha256": "c" * 64,
                "assetId": "a1", "clipId": "c1", "semanticReceiptSha256": "d" * 64,
            }],
        },
        "inference": {"context": {"markdownRouterSha256": "e" * 64}},
        "commands": [{"type": "caption", "text": "Claude Studio"}],
    }
    errors, count = _validate_edit_plan(plan)
    assert not errors and count == 1
    assert not _scan_caption_text(plan)
    plan["commands"][0]["text"] = "这段網易 cloud"
    assert len(_scan_caption_text(plan)) >= 2
    broken = dict(plan, schema="hao.video-autopilot.edit-plan/v3")
    assert _validate_edit_plan(broken)[0]
    print("silent_vlog_maker.verify self-test GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
