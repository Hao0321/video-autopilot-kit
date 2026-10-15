"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import json
import math
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


_READINESS_FAILURE_CODES = frozenset({
    "DNS_RESOLUTION_FAILED", "TLS_VERIFICATION_FAILED", "ENDPOINT_TIMEOUT",
    "ENDPOINT_HTTP_ERROR", "ENDPOINT_UNAVAILABLE", "INVALID_ENDPOINT_RESPONSE",
    "HEALTH_IDENTITY_FAILED", "PAGE_IDENTITY_FAILED", "MEDIA_AUTH_GATE_FAILED",
})


class _RemoteReadinessError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.failure_code = code if code in _READINESS_FAILURE_CODES else "ENDPOINT_UNAVAILABLE"
        super().__init__("remote review verification failed: " + self.failure_code)


def _readiness_failure_code(exc: Exception) -> str:
    if isinstance(exc, _RemoteReadinessError):
        return exc.failure_code
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, socket.gaierror):
        return "DNS_RESOLUTION_FAILED"
    if isinstance(reason, ssl.SSLError):
        return "TLS_VERIFICATION_FAILED"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "ENDPOINT_TIMEOUT"
    if isinstance(exc, HTTPError):
        return "ENDPOINT_HTTP_ERROR"
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)):
        return "INVALID_ENDPOINT_RESPONSE"
    return "ENDPOINT_UNAVAILABLE"


def _validated_readiness_origin(attempts, retry_delay, timeout, total_timeout, url):
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("remote review delivery requires an HTTPS origin")
    if parsed.fragment or parsed.query or parsed.username or parsed.password:
        raise ValueError("remote readiness verification refuses secret-bearing URLs")
    if (not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= 64
            or any(not math.isfinite(value) or value <= 0 for value in (timeout, total_timeout))
            or total_timeout > 30 or not math.isfinite(retry_delay) or retry_delay < 0):
        raise ValueError("invalid bounded remote readiness budget")
    public_origin = "%s://%s" % (parsed.scheme.lower(), parsed.netloc.lower())
    return public_origin


def verify_remote_review(url: str, *, timeout: float = 12.0,
                         attempts: int = 32, retry_delay: float = 1.0,
                         total_timeout: float = 30.0) -> dict[str, Any]:
    """Verify the public origin only; secrets never cross this API boundary."""
    public_origin = _validated_readiness_origin(attempts, retry_delay, timeout, total_timeout, url)
    page_url = urljoin(public_origin + "/", "review.html")
    health_url = urljoin(public_origin + "/", "healthz")
    media_url = urljoin(public_origin + "/", "media/0")
    deadline = time.monotonic() + total_timeout
    last_code = "ENDPOINT_TIMEOUT"

    def remaining_timeout() -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        return min(timeout, remaining)

    for attempt in range(1, attempts + 1):
        if time.monotonic() >= deadline:
            break
        try:
            health = urlopen(Request(health_url, headers={
                "User-Agent": "creator-Mobile-Review-QA/2.0",
            }), timeout=remaining_timeout())
            try:
                health_status = int(getattr(health, "status", health.getcode()))
                health_body = json.loads(health.read(64_000).decode("utf-8"))
            finally:
                health.close()
            if (health_status != 200 or not isinstance(health_body, dict)
                    or health_body.get("service") != "hao-remote-review"
                    or health_body.get("authentication") != "required"):
                raise _RemoteReadinessError("HEALTH_IDENTITY_FAILED")
            page = urlopen(Request(page_url, headers={
                "User-Agent": "creator-Mobile-Review-QA/2.0",
            }), timeout=remaining_timeout())
            try:
                page_status = int(getattr(page, "status", page.getcode()))
                page_body = page.read(1_000_000).decode("utf-8", errors="replace")
            finally:
                page.close()
            if page_status != 200 or "安全連線中" not in page_body:
                raise _RemoteReadinessError("PAGE_IDENTITY_FAILED")
            try:
                media_probe = urlopen(Request(media_url, headers={
                    "User-Agent": "creator-Mobile-Review-QA/2.0",
                    "Range": "bytes=0-0", "Cache-Control": "no-store",
                }), timeout=remaining_timeout())
                try:
                    media_status = int(getattr(media_probe, "status", media_probe.getcode()))
                finally:
                    media_probe.close()
            except HTTPError as exc:
                media_status = int(exc.code)
                exc.close()
            if media_status != 401:
                raise _RemoteReadinessError("MEDIA_AUTH_GATE_FAILED")
            remaining_timeout()  # A late response cannot turn expired readiness green.
            return {
                "status": "VERIFIED", "health_status": health_status,
                "page_status": page_status, "media_status": media_status,
                "media_gate": "AUTH_GATED",
                "pairing_required": True,
                "attempts": attempt,
                "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        except Exception as exc:  # DNS/tunnel startup is eventually consistent.
            last_code = _readiness_failure_code(exc)
            if isinstance(exc, HTTPError):
                exc.close()
            # Identity/authentication failures are not propagation delays.
            if isinstance(exc, _RemoteReadinessError) or last_code == "TLS_VERIFICATION_FAILED":
                break
            remaining = deadline - time.monotonic()
            if attempt < attempts and remaining > 0:
                time.sleep(min(retry_delay * 2 ** min(attempt - 1, 3), 3.0, remaining))
    # URL-bearing urllib errors never reach disk, CLI, or the parent daemon.
    raise _RemoteReadinessError(last_code) from None
