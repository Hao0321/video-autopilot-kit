"""Validate per-task execution, finding, and coverage records."""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath
from typing import Any

from security_assessment_network import canonical_network_destination
from security_assessment_shared import (
    CONFIDENCE,
    DIGEST_RE,
    FINDING_STATUSES,
    LIMIT_FIELDS,
    SEVERITIES,
    SECURITY_CONTROL_IDS,
    SHA256_RE,
    TASK_STATUSES,
    TERMINAL_COMPLETE,
    FailureSink,
    GapSink,
    bounded_limits,
    closed_fields,
    relative_path,
    string_list,
)


def _canonical_egress(values: list[str], task_id: str, fail: FailureSink) -> list[str]:
    canonical_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical, error = canonical_network_destination(value)
        if error or canonical is None:
            fail("unauthorized-egress", "task egress contains an unsafe destination", taskId=task_id)
            continue
        if canonical in seen:
            fail("duplicate-network-destination", "task egress contains equivalent duplicate destinations", taskId=task_id)
            continue
        seen.add(canonical)
        canonical_values.append(canonical)
    return canonical_values


def validate_execution(
    value: Any,
    task_id: str,
    target_snapshot: Any,
    authorization: dict[str, Any],
    fail: FailureSink,
    *,
    status: Any,
    schema_version: int,
) -> None:
    if not isinstance(value, dict):
        fail("execution", "task execution must be an object", taskId=task_id)
        return
    closed_fields(value, {
        "inputReadOnly", "outputIsolated", "unprivileged", "shell", "runtimeSocket",
        "broadHomeMount", "snapshotSha256", "commandSha256", "environmentSha256",
        "credentialMode", "networkMode", "egressAllowlist", "limits", "exitCode",
        "successMarker",
    }, f"tasks.{task_id}.execution", fail)
    exact_true = ("inputReadOnly", "outputIsolated", "unprivileged")
    for field in exact_true:
        if value.get(field) is not True:
            fail("unsafe-execution-isolation", f"execution.{field} must be true", taskId=task_id)
    for field in ("shell", "runtimeSocket", "broadHomeMount"):
        if value.get(field) is not False:
            fail("unsafe-execution-isolation", f"execution.{field} must be false", taskId=task_id)
    if value.get("snapshotSha256") != target_snapshot:
        fail("snapshot-drift", "task snapshot differs from target snapshot", taskId=task_id)
    for field in ("commandSha256", "environmentSha256"):
        if not isinstance(value.get(field), str) or not SHA256_RE.fullmatch(value[field]):
            fail("execution-provenance", f"execution.{field} must be lowercase SHA-256", taskId=task_id)
    authorized_credential = authorization.get("credentialMode")
    permitted_credentials = (
        {"none", "read-only-task-scoped"}
        if authorized_credential == "read-only-task-scoped"
        else {"none"}
    )
    if value.get("credentialMode") not in permitted_credentials:
        fail("credential-scope-drift", "task credential mode differs from authorization", taskId=task_id)
    network_mode = value.get("networkMode")
    raw_egress = string_list(
        value.get("egressAllowlist"),
        f"tasks.{task_id}.execution.egressAllowlist",
        fail,
        allow_empty=True,
    )
    egress = _canonical_egress(raw_egress, task_id, fail)
    if authorization.get("externalContact") is False:
        if network_mode != "disabled" or egress:
            fail("unauthorized-egress", "local-static task must disable network and have no egress", taskId=task_id)
    elif network_mode == "disabled":
        if egress:
            fail("unauthorized-egress", "disabled network cannot declare egress", taskId=task_id)
    elif network_mode == "exact-allowlist":
        if not egress or not set(egress).issubset(set(authorization.get("networkScope", []))):
            fail("unauthorized-egress", "task egress must be a non-empty subset of authorized scope", taskId=task_id)
    else:
        fail("network-mode", "task networkMode must be disabled or exact-allowlist", taskId=task_id)
    bounded_limits(value.get("limits"), LIMIT_FIELDS, f"tasks.{task_id}.execution.limits", fail)
    exit_code = value.get("exitCode")
    nullable_exit = schema_version == 2 and status in {"timed_out", "cancelled"}
    if (
        isinstance(exit_code, bool)
        or (not isinstance(exit_code, int) and not (nullable_exit and exit_code is None))
    ):
        fail("child-exit", "execution.exitCode must be an integer", taskId=task_id)
    marker = value.get("successMarker")
    if marker is not None and (not isinstance(marker, str) or not marker.strip() or len(marker) > 200):
        fail("success-marker", "successMarker must be null or a bounded non-empty string", taskId=task_id)


def validate_finding(
    raw: Any,
    task_id: str,
    index: int,
    evidence: dict[str, dict[str, Any]],
    task_evidence: set[str],
    seen_findings: set[tuple[str, str]],
    fail: FailureSink,
    gap: GapSink,
) -> bool:
    label = f"tasks.{task_id}.findings[{index}]"
    if not isinstance(raw, dict):
        fail("invalid-finding", f"{label} must be an object", taskId=task_id)
        return False
    closed_fields(raw, {
        "id", "ruleId", "fingerprint", "severity", "confidence", "location",
        "evidenceIds", "status", "resolution",
    }, label, fail)
    finding_id, rule_id = raw.get("id"), raw.get("ruleId")
    if not isinstance(finding_id, str) or not finding_id or not isinstance(rule_id, str) or not rule_id:
        fail("finding-identity", "finding needs id and ruleId", taskId=task_id)
        return False
    finding_key = (task_id.casefold(), finding_id.casefold())
    if finding_key in seen_findings:
        fail("duplicate-finding", "finding IDs must be unique within a task", taskId=task_id)
    seen_findings.add(finding_key)
    if not isinstance(raw.get("fingerprint"), str) or not DIGEST_RE.fullmatch(raw["fingerprint"]):
        fail("finding-fingerprint", "finding fingerprint must be sha256:<lowercase hex>", taskId=task_id, findingId=finding_id)
    if raw.get("severity") not in SEVERITIES or raw.get("confidence") not in CONFIDENCE:
        fail("finding-classification", "severity and confidence must use separate supported enums", taskId=task_id, findingId=finding_id)
    location = raw.get("location")
    if not isinstance(location, dict):
        fail("finding-location", "finding location must be an object", taskId=task_id, findingId=finding_id)
    else:
        closed_fields(location, {"path", "line"}, f"{label}.location", fail)
        if not relative_path(location.get("path")):
            fail("finding-location", "finding path must be a safe relative POSIX path", taskId=task_id, findingId=finding_id)
        line = location.get("line")
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            fail("finding-location", "finding line must be a positive integer", taskId=task_id, findingId=finding_id)
    evidence_ids = string_list(raw.get("evidenceIds"), f"{label}.evidenceIds", fail)
    normalized_evidence = {item.casefold() for item in evidence_ids}
    if not normalized_evidence.issubset(task_evidence) or not normalized_evidence.issubset(evidence):
        fail("finding-evidence", "finding evidence must belong to the task and global evidence registry", taskId=task_id, findingId=finding_id)
    status = raw.get("status")
    if status not in FINDING_STATUSES:
        fail("finding-status", "finding status is unsupported", taskId=task_id, findingId=finding_id)
        return False
    if status in {"resolved", "false_positive"}:
        resolution = raw.get("resolution")
        if not isinstance(resolution, dict):
            fail("finding-resolution", "closed finding needs a resolution object", taskId=task_id, findingId=finding_id)
        else:
            closed_fields(resolution, {"owner", "reason", "evidenceIds"}, f"{label}.resolution", fail)
            for field in ("owner", "reason"):
                if not isinstance(resolution.get(field), str) or not resolution[field].strip():
                    fail("finding-resolution", f"resolution.{field} is required", taskId=task_id, findingId=finding_id)
            proof = string_list(resolution.get("evidenceIds"), f"{label}.resolution.evidenceIds", fail)
            proof_keys = {item.casefold() for item in proof}
            if not proof_keys.issubset(task_evidence) or not proof_keys.issubset(evidence):
                fail("finding-resolution", "resolution evidence must belong to the task", taskId=task_id, findingId=finding_id)
        gap(
            "finding-disposition-untrusted",
            "closed findings need an independently trusted waiver or retest attestation",
            taskId=task_id,
            findingId=finding_id,
        )
    return status == "open"


def validate_security_control_coverage(
    value: Any,
    target_ids: Any,
    fail: FailureSink,
    gap: GapSink,
    schema_version: int,
) -> tuple[int, int]:
    """Require the canonical route-level controls in the executed v2 plan."""
    if schema_version != 2:
        return 0, 0
    tasks = value if isinstance(value, list) else []
    required = set(SECURITY_CONTROL_IDS)
    required_folded = {item.casefold() for item in required}
    authorized_targets = target_ids if isinstance(target_ids, list) else []
    observed = [
        item
        for task in tasks
        if isinstance(task, dict)
        for field in ("plannedCheckIds", "executedCheckIds")
        for item in (task.get(field) if isinstance(task.get(field), list) else [])
        if isinstance(item, str)
    ]
    if any(item.casefold() in required_folded and item not in required for item in observed):
        fail(
            "security-control-case-drift",
            "canonical security control IDs must use exact case",
        )
    planned_cells = 0
    executed_cells = 0
    for target_id in authorized_targets:
        target_tasks = [task for task in tasks if isinstance(task, dict) and task.get("targetId") == target_id]
        planned_values = {
            item
            for task in target_tasks
            for item in (
                task.get("plannedCheckIds")
                if isinstance(task.get("plannedCheckIds"), list)
                else []
            )
            if isinstance(item, str)
        }
        executed_values = {
            item
            for task in target_tasks
            if task.get("status") in TERMINAL_COMPLETE
            for item in (
                task.get("executedCheckIds")
                if isinstance(task.get("executedCheckIds"), list)
                else []
            )
            if isinstance(item, str)
        }
        planned_controls = required.intersection(planned_values)
        executed_controls = required.intersection(executed_values)
        planned_cells += len(planned_controls)
        executed_cells += len(executed_controls)
        if planned_controls != required:
            fail(
                "security-control-plan",
                "a target plan does not cover every canonical security control",
            )
        if executed_controls != required:
            gap(
                "security-control-not-executed",
                "a target lacks execution evidence for canonical security controls",
            )
    return planned_cells, executed_cells


def _validate_task_output_bounds(
    raw: dict[str, Any],
    task_evidence: set[str],
    evidence: dict[str, dict[str, Any]],
    execution: dict[str, Any],
    fail: FailureSink,
) -> None:
    output_ids = set(task_evidence)
    adapter_id = raw.get("adapterResultEvidenceId")
    if isinstance(adapter_id, str):
        output_ids.add(adapter_id.casefold())
    output_records = [evidence[key] for key in output_ids if key in evidence]
    limits = execution.get("limits") if isinstance(execution.get("limits"), dict) else {}
    output_bytes = sum(
        record.get("bytes", 0)
        for record in output_records
        if isinstance(record.get("bytes"), int) and not isinstance(record.get("bytes"), bool)
    )
    output_depth = max(
        (
            max(1, len(PurePosixPath(record.get("path", "")).parts) - 2)
            for record in output_records
        ),
        default=0,
    )
    output_file_limit = limits.get("outputFiles")
    output_byte_limit = limits.get("outputBytes")
    output_depth_limit = limits.get("outputDepth")
    if isinstance(output_file_limit, int) and len(output_records) > output_file_limit:
        fail("execution-output-files", "task evidence exceeds declared output file bounds")
    if isinstance(output_byte_limit, int) and output_bytes > output_byte_limit:
        fail("execution-output-bytes", "task evidence exceeds declared output byte bounds")
    if isinstance(output_depth_limit, int) and output_depth > output_depth_limit:
        fail("execution-output-depth", "task evidence exceeds declared output depth bounds")


def validate_tasks(
    value: Any,
    planned_ids: list[str],
    target: dict[str, Any],
    authorization: dict[str, Any],
    engines: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
    gap: GapSink,
    schema_version: int,
) -> tuple[bool, int, Counter[str]]:
    if not isinstance(value, list):
        fail("tasks", "tasks must be an array")
        return False, 0, Counter()
    tasks: dict[str, dict[str, Any]] = {}
    complete = True
    open_findings = 0
    status_counts: Counter[str] = Counter()
    seen_findings: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            fail("invalid-task", f"tasks[{index}] must be an object")
            continue
        task_fields = {
            "id", "targetId", "engineId", "status", "plannedCheckIds",
            "executedCheckIds", "reason", "rawFindingCount", "findings",
            "rawEvidenceId", "evidenceIds", "execution",
        }
        if schema_version == 2:
            task_fields.update({"adapterResultEvidenceId", "adapterResultSha256"})
        closed_fields(raw, task_fields, f"tasks[{index}]", fail)
        task_id = raw.get("id")
        if not isinstance(task_id, str) or not task_id:
            fail("task-id", f"tasks[{index}].id is required")
            continue
        key = task_id.casefold()
        if key in tasks:
            fail("duplicate-task", "task IDs must be case-insensitively unique", taskId=task_id)
        tasks[key] = raw
        status = raw.get("status")
        status_counts[status if status in TASK_STATUSES else "invalid"] += 1
        if status not in TASK_STATUSES:
            fail("task-status", "task status is unsupported", taskId=task_id)
            complete = False
        planned = string_list(
            raw.get("plannedCheckIds"),
            f"tasks.{task_id}.plannedCheckIds",
            fail,
            allow_empty=status not in TERMINAL_COMPLETE,
        )
        executed = string_list(raw.get("executedCheckIds"), f"tasks.{task_id}.executedCheckIds", fail, allow_empty=True)
        planned_keys, executed_keys = {item.casefold() for item in planned}, {item.casefold() for item in executed}
        if not executed_keys.issubset(planned_keys):
            fail("coverage-expansion", "executed checks must be a subset of the frozen plan", taskId=task_id)
        if status in TERMINAL_COMPLETE:
            if executed_keys != planned_keys:
                fail("false-complete-task", "completed task did not execute every planned check", taskId=task_id)
                complete = False
        else:
            complete = False
            if not isinstance(raw.get("reason"), str) or not raw["reason"].strip():
                fail("partial-task-reason", "non-complete task needs a reason", taskId=task_id)
            gap("security-task-not-complete", "planned security task did not complete", taskId=task_id, taskStatus=status)

        target_id = raw.get("targetId")
        if target_id not in authorization.get("targetIds", []):
            fail("unauthorized-target", "task target is outside frozen authorization", taskId=task_id)
        engine_id = raw.get("engineId")
        engine = engines.get(engine_id.casefold()) if isinstance(engine_id, str) else None
        if engine is None:
            fail("unknown-engine", "task references an unknown engine", taskId=task_id)
        elif status in TERMINAL_COMPLETE and engine.get("admissionStatus") != "admitted":
            fail("unadmitted-engine-executed", "completed task used an unadmitted engine", taskId=task_id, engineId=engine_id)
        elif engine.get("admissionStatus") != "admitted":
            gap("engine-not-admitted", "task engine is not admitted", taskId=task_id, engineId=engine_id)

        execution_value = raw.get("execution")
        if execution_value is None and schema_version == 2 and status not in TERMINAL_COMPLETE:
            execution = {}
        else:
            validate_execution(
                execution_value,
                task_id,
                target.get("snapshotSha256"),
                authorization,
                fail,
                status=status,
                schema_version=schema_version,
            )
            execution = execution_value if isinstance(execution_value, dict) else {}
        evidence_ids = string_list(raw.get("evidenceIds"), f"tasks.{task_id}.evidenceIds", fail, allow_empty=status not in TERMINAL_COMPLETE)
        task_evidence = {item.casefold() for item in evidence_ids}
        if not task_evidence.issubset(evidence):
            fail("task-evidence", "task references unknown evidence IDs", taskId=task_id)
        raw_evidence_id = raw.get("rawEvidenceId")
        if executed:
            if not isinstance(raw_evidence_id, str) or raw_evidence_id.casefold() not in task_evidence:
                fail("raw-evidence", "executed task must retain raw evidence in its evidence set", taskId=task_id)
            elif raw_evidence_id.casefold() not in evidence or evidence[raw_evidence_id.casefold()].get("kind") != "raw":
                fail("raw-evidence", "rawEvidenceId must resolve to kind=raw evidence", taskId=task_id)
        elif raw_evidence_id is not None:
            fail("raw-evidence", "unexecuted task must not claim raw evidence", taskId=task_id)

        findings = raw.get("findings")
        if not isinstance(findings, list):
            fail("task-findings", "task findings must be an array", taskId=task_id)
            findings = []
        count = raw.get("rawFindingCount")
        if isinstance(count, bool) or not isinstance(count, int) or count != len(findings):
            fail("finding-count-mismatch", "rawFindingCount must equal preserved finding records", taskId=task_id)
        if status == "completed" and findings:
            fail("task-status-mismatch", "completed task cannot contain findings", taskId=task_id)
        if status == "findings" and not findings:
            fail("task-status-mismatch", "findings task must preserve at least one finding", taskId=task_id)
        for finding_index, finding in enumerate(findings):
            if validate_finding(
                finding, task_id, finding_index, evidence, task_evidence,
                seen_findings, fail, gap,
            ):
                open_findings += 1
                fail("open-security-finding", "security finding remains open", taskId=task_id, findingId=finding.get("id"))

        if schema_version == 2 and execution:
            _validate_task_output_bounds(raw, task_evidence, evidence, execution, fail)
        if status in TERMINAL_COMPLETE and (execution.get("exitCode") != 0 or not execution.get("successMarker")):
            fail("false-provider-success", "complete task needs exit 0 and an explicit success marker", taskId=task_id)
        if status not in TERMINAL_COMPLETE and execution.get("exitCode") == 0 and execution.get("successMarker"):
            gap("provider-partial", "provider signalled success but coverage remained partial", taskId=task_id)

    planned_keys = {item.casefold() for item in planned_ids}
    missing = sorted(item for item in planned_ids if item.casefold() not in tasks)
    unexpected = sorted(raw.get("id") for key, raw in tasks.items() if key not in planned_keys)
    if missing:
        fail("missing-planned-task", "planned security tasks are missing terminal records", missing=missing)
        complete = False
    if unexpected:
        fail("unexpected-task", "tasks contains undeclared task IDs", unexpected=unexpected)
        complete = False
    return complete and set(tasks) == planned_keys, open_findings, status_counts
