# Editkin batch workflow

Use this contract whenever new footage is imported into Editkin for unattended or batch auto-editing.

## Ingestion

All new-footage entry points—file picker, drag-and-drop, watched folder, removable media copy, mobile upload or a structured MCP call—must normalize to the same versioned ingestion record. Preserve the absolute source identity, media probe, user grouping, rights/provenance metadata and a pre-run SHA-256. Source media is read-only; generated proxies, waveforms, transcripts and thumbnails live in managed derivative storage.

One-off editing may place several selected clips on one timeline. Batch auto-editing has a different contract: one source or explicit user group creates one stable job. A multi-select action is not batch evidence unless it fans out to independent jobs.

## Per-job closure

Every job owns an isolated output directory and must end in exactly one of these durable states: `completed`, `failed`, `cancelled` or `review_required`. A completed/review-required job provides:

- an editable current-schema EditGraph project;
- a decodable rendered video;
- a machine-readable receipt binding job ID, source SHA-256 before/after, Skill and inference provenance, current schema, editorial fingerprint, warnings and artifact identities;
- an `open-in-editor` path that loads the same project into the normal timeline without flattening it;
- explicit machine-review state; only recorded human action may promote human acceptance.

Failure is isolated. Remaining jobs continue, and retry mutates only the selected job. Shared caches may be content-addressed, but writable project, render and receipt paths cannot be shared across jobs.

## Durability and recovery

Persist the queue after every state transition. On restart, `running` is not trusted as completed: recover it to `queued` with an interruption note, then allow deterministic resume. Never infer success only because a file exists; validate the receipt and artifact identities.

Keep `PUBLISHED` artifacts immutable. A batch rebuild skips them unless Hao explicitly starts the correction workflow. The original footage hash after processing must equal the pre-run hash; mismatch is a hard failure.

## Required evidence

Promotion needs positive and negative evidence on the delivered desktop artifact:

1. Select at least two fixtures and prove N independent jobs, projects, renders and receipts.
2. Reopen one result, make an undoable timeline edit and save it without touching the rendered sibling job.
3. Force one invalid/corrupt input; prove other jobs complete and only the failed job retries.
4. Interrupt one job, restart the app and prove durable queued recovery.
5. Re-hash every source after the run and prove byte identity.
6. Reject unsafe job IDs, output traversal, stale receipts, shared mutable output paths and fake human-approval fields.

Passing an import test, a CLI unit test or one synthetic render alone is not delivered batch closure.
