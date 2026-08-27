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

## Availability boundary

Authorization and reachability are separate. A valid device credential cannot find a desktop whose origin changed or is offline. Prefer an owned stable HTTPS origin for cross-network access and a stable LAN hostname/port locally. An ephemeral-port fallback may preserve authorization but can require the current link. Public tunnel ownership, TLS certificates, background operation, browser storage eviction and real-device acceptance remain separate obligations.

## Promotion evidence

Run one frozen delivered journey: pair → URL fragment removed → command accepted → service/app restart → reconnect without QR → command accepted → exact-device revoke → old cookie rejected. Retain a store scan proving the raw credential is absent and a negative fixture that fails if a long in-memory session is mislabeled as permanent binding.
