# Durable state and caller audit

Read-only provider for money, stock, accounts, recovery and shared stores; task authority separately governs repairs.

- `cleanup.state.commit-ack`: trace real UI -> adapter -> commit -> reply -> UI. Pending, rejected or incomplete acknowledgement preserves inputs/cart and cannot display success. Verify original ID and material records before clearing the journal; confirmed original-ID recovery finishes the old form.
- `cleanup.state.replay-rollback`: freeze durable ID before mutation. Lose reply after commit, reopen storage and retry once; money/points/stock change once. Reject changed contents; inject late failure and compare the full snapshot. Derive deltas from authoritative persisted data. An unreadable historical receipt remains uncertain.
- `cleanup.state.account-continuity`: custom owner plus missing/stale version marker, malformed credentials and failed migration. Preserve IDs, roles and hashes; bootstrap only an empty store; upgrade weak hashes only after verification. No marker authorizes account replacement.
- `cleanup.state.native-authority`: privilege belongs at native frame/origin and verified actor boundaries, not hidden buttons or renderer roles. Pair valid staff calls with forged caller/frame, private-order access, revoked/expired identity and password change. Browser-local control is no security boundary.
- `cleanup.state.history-backup`: distinguish payment from fulfilment; preserve dated signed cumulative/last-full refunds and historical costs. Backups exceed UI limits and retain all collections, receipts, zero settings, business identity, original timestamps and stable tied-row ordering. Failed restore rolls back; cloud replacement detects local changes during fetch.

Shared controls: two real transport clients versus last stock, native-to-phone refresh, lost reply, revocation/expiry, replacement store identity and fragment-only re-pair in an existing tab. No disconnected local replicas. Pin the fixture certificate; phone-size Chromium does not prove phone trust/sleep. Verify pagehide/pageshow and a departed address; wait for hydrated data, persisted status and journal clearance.

Receiving atomically binds stock, purchase, catalogue links and receipt; replays return current stock, stale counts/catalogues reconcile. Original-shift prepaid cash excludes gifts. Unstarted cancellation releases resources; consumed cancellation retains loss and capacity. Freeze unit cost, retain loss after sales reversal, split actual mixed tenders, and preserve committed inventory/financial evidence.

Caller controls: fractional and integer units, precision/sign/stock rejection, quick/normal pending guards and the original form after retry. Local midnight/month date inputs and filters match ledger dates; compare parsed local/offset timestamps and reject reversed intervals. Verify injected clocks after page load and actual resize geometry before touching.

Native/public boundaries: fixed program plus literal arguments/environment, context-correct quoting/attribute escaping, failed/missing child acknowledgement. Record executable identity, real exit and marker. Mock spooler or loopback is not physical printing. Dependency fixes need resolved tree and native startup; zero advisories never justify forced downgrade or certify release. Provider RLS needs owner/anonymous/second-identity/forged-owner controls; local SQL is not deployed evidence.

Run generalized replay, then actual target journeys; keep raw provenance local and measured gaps explicit. R&D: `../../../run-benchmark-driven-rd/references/topics/state-integrity.md`. [Detailed probes](../state-integrity-probes.md) retain family cases. [Transfer receipt](../../../run-benchmark-driven-rd/profiles/state-integrity-caller-calendar-promotion.json).
