# Editkin permanent mobile device binding

## Product promise

The user scans one QR once. Future Editkin Remote sessions recognize the same device automatically until that device is explicitly revoked, the browser clears site data, or the host trust store is reset. Ordinary Remote shutdown never means “forget all devices”.

## Trust exchange

1. Desktop creates a random 128-bit or stronger bootstrap token with a ten-minute maximum lifetime and places it only in the QR URL fragment.
2. The mobile page posts that token through the same-origin JSON pairing endpoint and immediately removes it from browser history.
3. Pairing returns a separate random 256-bit per-device credential in an HttpOnly, SameSite=Strict cookie; HTTPS adds Secure.
4. Desktop persists only SHA-256 of the device credential with bounded device ID/name, paired time and last-seen metadata. Raw credentials never enter disk, logs, receipts, URLs or installers.
5. Re-pairing the same device ID replaces the previous credential. A device ID or localStorage UUID is a label, not an authenticator.

## Required behavior

- Remote/app restart plus the old cookie reconnects without another QR.
- Temporary network loss and Remote stop preserve the binding.
- The desktop lists trusted devices separately from currently connected devices.
- Exact-device revoke removes the stored hash and makes the old cookie receive `401` on its next request.
- Device count, request body, headers, pairing attempts and command frequency remain bounded.
- Same-origin/Fetch Metadata/content type, hashed CSP, private-path omission and generic server errors remain enforced on both the positive client and negative probes.

## Review-session boundary

Visual review is not authorized by an obscure path or by possession of a shareable URL. A review delivery may reuse an explicitly trusted device binding, but every review still receives a separate, bounded authenticated session.

- If pairing is required, issue a one-time random bootstrap of at least 128 bits only in the URL fragment. It expires within ten minutes, is consumed exactly once, is removed with `history.replaceState`, and can exchange only for a session; it cannot read media or mutate review state directly.
- Return the review credential only as an `HttpOnly; SameSite=Strict` cookie and add `Secure` whenever HTTPS is used. Do not put credentials in query strings, paths, JSON responses, local storage or service-worker caches.
- Cap a review session at 60 minutes total and 15 minutes idle. Expiry, idle timeout, Remote stop, exact-session revoke or device revoke invalidates it immediately and stops the review listener/tunnel when no authorized review remains.
- Persist only credential hashes and bounded non-secret metadata needed for revocation. Raw bootstrap values, cookie credentials and complete capability URLs must never enter disk, logs, receipts, process command lines, clipboard automation or Codex/chat transcripts. CLI output may contain only a non-secret session fingerprint and status; show the one-time QR in a trusted local UI.
- Every mutation requires an authenticated session, exact same-origin `Origin`, `Content-Type: application/json`, `Sec-Fetch-Site: same-origin`, a bounded body and request rate. Missing or cross-site metadata, form/plain-text fallbacks and oversized bodies fail closed.
- Validate both successful authenticated page/media access (including byte-range media) and negative probes: bootstrap replay, bootstrap used as bearer authorization, missing/expired/revoked cookie, cross-origin mutation, wrong content type, non-same-origin Fetch Metadata, expiry and idle shutdown.
- If an owned or otherwise controlled HTTPS origin and this authentication runtime are unavailable, report `SECURE_REVIEW_RUNTIME_REQUIRED`. Never fall back to an unauthenticated Quick Tunnel, a bare LAN listener or a secret-path bearer link.

## Availability boundary

Authorization and reachability are separate. A valid device credential cannot find a desktop whose origin changed or is offline. Use an owned or otherwise controlled stable HTTPS origin for cross-network access and a stable LAN hostname/port locally; both paths still require the same authentication and mutation controls. Public tunnel ownership, TLS certificates, background operation, browser storage eviction and real-device acceptance remain separate obligations. A temporary tunnel may be used only when it is controlled by the authenticated runtime, inherits all review TTL/revocation controls and never emits a bearer URL; it is not a security fallback or permanent-connectivity claim.

## Promotion evidence

Run one frozen delivered journey: pair → URL fragment removed → authenticated media Range request and mutation accepted → bootstrap replay rejected → service/app restart → trusted-device reconnect without QR → new bounded review session accepted → exact-session revoke → old review cookie rejected → exact-device revoke → device credential rejected. Retain a disk/log/receipt/transcript scan proving raw credentials and complete capability URLs are absent, plus negative fixtures for cross-origin/wrong-content-type/Fetch-Metadata mutation and TTL/idle auto-stop.
