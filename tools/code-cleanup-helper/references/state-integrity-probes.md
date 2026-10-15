# Durable state, money and account audit

Apply to checkout, refunds, prepaid credit, orders, login migration, backup/restore and cloud replacement. This is a read-only measurement topic; existing task authorization separately governs repairs. Exclude presentation-only changes.

- commit ack: trace the actual UI → adapter → persistence → reply → UI chain. An unresolved Promise, rejected save or incomplete acknowledgement must preserve the cart and cannot display success. Test the real caller as well as the pure helper.
- replay rollback: freeze a durable request ID before mutation. Inject a lost reply after commit, reopen storage and retry that ID; money, stock and points change exactly once. Reject the same ID with different contents. Inject a mid-transaction fault and compare the complete before/after snapshot. Derive financial deltas from current persisted data inside the transaction.
- account continuity: version markers never authorize replacing accounts. Test a custom existing owner, missing/stale marker, malformed credentials and failed migration. Preserve identities, roles and hashes; bootstrap only an empty account store. Upgrade known weak passwords only after verification.
- native authority: caller/frame/origin admission and role validation belong at the privileged boundary. A renderer role or hidden button is insufficient. Test a legitimate staff journey plus forged role/frame, expired/revoked identity and private order access by another caller. Browser-local access is not a boundary against a user controlling that device.

At native child and public markup boundaries, keep untrusted names as literal data in a fixed program and escape for the exact output context. Pair legitimate printer/search/cart behavior with command metacharacters, quoted identifiers, rejected child exit and missing acknowledgement. A mocked printer proves boundary behavior, not physical printing.
- history backup: distinguish paid sales from fulfilment; retain every dated signed refund, including several partial refunds ending in full return. Freeze historical costs. Round cumulative refunds then subtract amounts already returned. Backups must inventory all collections and exceed every UI pagination limit; failed restore preserves the full original snapshot. Guard cloud replacement against a local mutation during fetch.

Run `scripts/state_integrity_regression.py` for generalized positive/negative evaluator calibration, then run the target's actual UI, native transaction and backup journeys. The replay is not a target scanner or security certification. Preserve target/runtime hashes, child exit, success marker and open boundaries in project-local evidence.

For an explicitly shared multi-device store, verify one authoritative commit path; remote clients must not silently use independent local replicas when disconnected. Test two real transport clients against the last item, desktop-to-phone invalidation, interrupted replies, device revocation, credential change and expiry. Pin the fixture certificate rather than disabling TLS validation globally. An opened browser at phone size does not establish real-phone certificate trust or sleep/background behavior.

Inventory receiving must commit stock, purchase progress, catalogue links and its receipt together. Replays return current stock without applying another delta; stale stocktake/catalogue edits require reconciliation. A known historical receipt that becomes unreadable cannot be labelled uncommitted. Verify request identity and material records before clearing its journal; bind remote journals to the persistent store identity, including fragment-only pairing links opened in an existing tab.

Include prepaid cash in the original shift, excluding gift credit; retain that shift identity in backup and optional sync. Preserve explicit zero settings and business configuration during restore. UI completion and batch counts follow acknowledgement, and must not disappear merely because the retry button changes to a saving state.

Dependency remediation needs the resolved tree and real native build/startup; a zero advisory count does not justify a forced downgrade or demonstrate release safety. Remote RLS requires owner, anonymous, second-identity and forged-owner write controls. Local SQL replay cannot certify a deployed provider.

For reserved or prepared inventory, audit availability, consumption, cancellation and signed accounting together. Unstarted cancellation may release resources; consumed cancellation retains loss and capacity. Freeze unit cost rather than confusing it with total loss, and include that loss after sales and cost reversals. Split mixed tenders by their actual payment records. Keep linked inventory/financial evidence; a generic history delete must not erase an already committed loss.

Backup fidelity includes original timestamps and deterministic collection ordering, especially tied times; otherwise a restore can drift the content revision. Probe a historical date rather than relying on a same-second run. Shared caller journeys also cover pagehide/pageshow and a departed network address. UI probes wait for loaded data, persisted status and original journal clearance; button labels or an unhydrated list are not acknowledgement.

R&D counterpart: `../../run-benchmark-driven-rd/references/topics/state-integrity.md`. Raw project paths, metrics and logs stay in the project's `.rd/`; shared guidance contains generalized rules only.

Quantity normalization must preserve supported fractional inventory units at the real form boundary; test a value below one unit alongside an integer, excessive precision, invalid sign and unavailable stock. Pending guards cover both normal and quick actions. A confirmed original-ID recovery must finish the original form, so its unchanged input cannot accidentally become a second action.

Calendar checks span the local midnight and month boundary across inputs, saved timestamps, journal dates and report filters. Compare parsed instants for offset-bearing and historical local timestamps; reject reversed intervals. Calibrate the runtime clock after the target page loads and wait for actual viewport resize geometry before testing a touch control.

Transfer evidence: [sanitized promotion receipt](../../run-benchmark-driven-rd/profiles/state-integrity-promotion.json).
