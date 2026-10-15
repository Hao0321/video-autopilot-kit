"""Public privacy review; canonical implementation."""
from __future__ import annotations

import re
from public_privacy_legacy import _function, _generalize_identity, _generalize_project_ids, _lf, _replace_lines, _replace_module_docstring


def _module_doc(title: str, purpose: str) -> str:
    return f'''"""{title} (public distribution).

{purpose}

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""'''


def _sanitize_comments(text: str) -> str:
    lines: list[str] = []
    for line in _lf(text).splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            sensitive_context = re.search(
                r"(?:creator|demo_longform|示範長片|實測|審片|評分|回測|淘汰|踩過|抓到)",
                line,
                re.I,
            )
            dated = re.search(r"20\d{2}[-/.]\d{2}[-/.]\d{2}", line)
            measured = re.search(r"(?:\d+(?:\.\d+)?%|\d+\s*/\s*\d+|AVP|CTR|cuts/min)", line, re.I)
            if sensitive_context and (dated or measured):
                indent = line[:len(line) - len(stripped)]
                line = indent + "# PUBLIC_FIXTURE: starter defaults require creator-owned calibration evidence."
            elif (re.search(r"(?:creator|user|使用者)", line, re.I)
                  and re.search(r"(?:回饋|批評|challenge|鐵則|嫌)", line, re.I)
                  and re.search(r"[「『\"'][^\r\n]+[」』\"']", line)):
                indent = line[:len(line) - len(stripped)]
                line = indent + "# PUBLIC_FIXTURE: verify project-specific caption choices with creator-owned source frames."
            elif sensitive_context and dated:
                line = re.sub(r"20\d{2}[-/.]\d{2}[-/.]\d{2}", "public calibration", line)
        lines.append(line)
    return "\n".join(lines) + "\n"


def _common(text: str, doc: str) -> str:
    public = _replace_module_docstring(_lf(text), doc)
    public = _generalize_project_ids(_generalize_identity(public))
    return _sanitize_comments(public)


def _replace_review_resolution(text: str) -> str:
    """Replace a maintainer-specific actor allowlist with explicit public config."""
    public = _lf(text)
    scope = _function(public, "resolve_review")
    return _replace_lines(
        public,
        scope.lineno,
        scope.end_lineno or scope.lineno,
        '''REVIEW_ACTORS_ENV = "VIDEO_AUTOPILOT_REVIEW_ACTORS"


def _configured_review_actors() -> set[str]:
    """Return the explicitly configured review actors; an empty set fails closed."""
    raw = os.environ.get(REVIEW_ACTORS_ENV, "")
    return {value.strip().casefold() for value in raw.split(",") if value.strip()}


def resolve_review(queue_id: str, *, actor: str, decision: str,
                   queue_path: str | Path = DEFAULT_QUEUE) -> dict[str, Any]:
    actor_name = str(actor).strip()
    if not actor_name or actor_name.casefold() not in _configured_review_actors():
        raise PermissionError(
            f"Actor is not authorized to resolve the subjective review queue; "
            f"configure {REVIEW_ACTORS_ENV} with a comma-separated allowlist"
        )
    queue = Path(queue_path).resolve()
    with _QueueLock(queue):
        state = _read_json(queue, {"schema_version": 1, "items": []})
        item = next((row for row in state.get("items", []) if row.get("queue_id") == queue_id), None)
        if not item:
            raise KeyError(queue_id)
        item.update(state="RESOLVED", decision=str(decision), resolved_by=actor_name,
                    resolved_at=_now(), updated_at=_now())
        state["updated_at"] = _now()
        _atomic_json(queue, state)
    return item''',
    )


def _replace_review_selftests(text: str) -> str:
    """Make actor authorization behavior executable public contract evidence."""
    public = _lf(text).replace("HAO_REVIEW_REQUIRED", "CREATOR_REVIEW_REQUIRED")
    scope = _function(public, "_selftest_queue")
    return _replace_lines(
        public,
        scope.lineno,
        scope.end_lineno or scope.lineno,
        '''def _selftest_queue(root: Path, artifact: Path, qa: dict, assessed: dict) -> None:
    queue = root / "queue.json"
    first = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    again = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert first["action"] == "ENQUEUED" and again["action"] == "IDEMPOTENT"
    artifact.write_bytes(b"revision-two")
    changed = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                             autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert changed["item"]["revision"] == 2
    errors: list[str] = []
    def worker(identifier: str) -> None:
        try:
            media = root / f"{identifier}.mp4"; media.write_bytes(identifier.encode("utf-8"))
            enqueue_review(content_id=identifier, format="shorts", artifact=media,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))
    threads = [threading.Thread(target=worker, args=(f"S10{i}",)) for i in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert not errors and queue_summary(queue)["counts"]["OPEN"] == 5

    previous = os.environ.pop(REVIEW_ACTORS_ENV, None)
    try:
        try:
            resolve_review(changed["item"]["queue_id"], actor="creator",
                           decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an empty actor allowlist must fail closed")

        os.environ[REVIEW_ACTORS_ENV] = "  CREATOR  "
        resolved = resolve_review(changed["item"]["queue_id"], actor=" creator ",
                                  decision="approve", queue_path=queue)
        assert resolved["state"] == "RESOLVED" and resolved["resolved_by"] == "creator"

        second = next(row for row in queue_summary(queue)["active"]
                      if row["content_id"] != "S001")
        os.environ[REVIEW_ACTORS_ENV] = "reviewer, EDITOR"
        resolved_second = resolve_review(second["queue_id"], actor=" editor ",
                                         decision="approve", queue_path=queue)
        assert resolved_second["resolved_by"] == "editor"

        os.environ[REVIEW_ACTORS_ENV] = "creator,reviewer"
        try:
            resolve_review(next(row["queue_id"] for row in queue_summary(queue)["active"]),
                           actor="bot", decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an unconfigured bot must not resolve creator review")
    finally:
        if previous is None:
            os.environ.pop(REVIEW_ACTORS_ENV, None)
        else:
            os.environ[REVIEW_ACTORS_ENV] = previous''',
    )


def _autonomy_standard(text: str) -> str:
    public = _common(text, _module_doc(
        "Fail-closed unattended editing standard and central review queue",
        "Allows reversible unattended work while keeping subjective approval and publishing human-owned.",
    ))
    return _replace_review_selftests(_replace_review_resolution(public))
