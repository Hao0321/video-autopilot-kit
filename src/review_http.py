from __future__ import annotations
from http.cookies import SimpleCookie
import json
import mimetypes
import re
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from review_auth import AUTH_RATE_ATTEMPTS, MAX_BOOTSTRAP_BODY_BYTES, MAX_REVIEW_BODY_BYTES, MEDIA_RATE_ATTEMPTS, REVIEW_RATE_ATTEMPTS, SESSION_COOKIE, _RemoteReviewAuth, _normalized_origin, _review_payload_valid
from review_page import BOOTSTRAP_HTML, _csp_for_html, render_review_html
from review_bundle import _atomic_json, _browser_media

def _parse_byte_range(value: str, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    if not value.startswith("bytes=") or "," in value:
        raise ValueError("unsupported byte range")
    start_text, end_text = value[6:].split("-", 1)
    if not start_text:
        length = int(end_text)
        if length <= 0:
            raise ValueError("invalid suffix range")
        return max(0, size - length), size - 1
    start = int(start_text)
    end = int(end_text) if end_text else size - 1
    if start < 0 or start >= size or end < start:
        raise ValueError("invalid byte range")
    return start, min(end, size - 1)


class _MediaReviewHandler(BaseHTTPRequestHandler):
    bundle: Path
    media: list[dict[str, str]]
    auth: _RemoteReviewAuth | None
    can_finalize: bool
    protocol_version = "HTTP/1.1"

    def _send_bytes(self, payload: bytes, content_type: str, *, status: int = 200,
                    headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if self.auth is not None and self.auth.public_origin.startswith("https://"):
            self.send_header("Strict-Transport-Security", "max-age=86400")
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", _csp_for_html(payload))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)
            self.wfile.flush()

    def _send_json(self, payload: dict[str, Any], *, status: int = 200,
                   headers: dict[str, str] | None = None) -> None:
        self._send_bytes(json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                         "application/json; charset=utf-8", status=status, headers=headers)

    def _fail(self, status: int, code: str) -> None:
        self._send_json({"ok": False, "error": code}, status=status,
                        headers={"Connection": "close"})
        self.close_connection = True

    def _credential(self) -> str:
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            morsel = cookie.get(SESSION_COOKIE)
            return morsel.value if morsel else ""
        except Exception:
            return ""

    def _authenticated(self) -> bool:
        return self.auth is None or self.auth.authorized(self._credential())

    def _same_origin_post(self) -> bool:
        if self.auth is None:
            return True
        origin = _normalized_origin(self.headers.get("Origin", ""))
        fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        fetch_mode = self.headers.get("Sec-Fetch-Mode", "").lower()
        return (origin == self.auth.public_origin and fetch_site == "same-origin"
                and fetch_mode in {"cors", "same-origin"})

    def _read_json(self, limit: int) -> tuple[int, Any]:
        if self.headers.get("Transfer-Encoding"):
            return 400, None
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return 415, None
        try:
            length = int(self.headers.get("Content-Length", ""))
        except (TypeError, ValueError):
            return 411, None
        if length <= 0:
            return 400, None
        if length > limit:
            return 413, None
        try:
            previous_timeout = self.connection.gettimeout()
            self.connection.settimeout(5.0)
            raw = self.rfile.read(length)
            if len(raw) != length:
                return 400, None
            return 200, json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return 400, None
        finally:
            try:
                self.connection.settimeout(previous_timeout)
            except (NameError, OSError):
                pass

    def _send_media(self, index: int) -> None:
        if index < 0 or index >= len(self.media):
            self._fail(404, "not_found")
            return
        path = Path(self.media[index]["path"])
        if not path.is_file():
            self._fail(404, "media_missing")
            return
        size = path.stat().st_size
        try:
            byte_range = _parse_byte_range(self.headers.get("Range", ""), size)
        except (ValueError, TypeError):
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        start, end = byte_range or (0, size - 1)
        self.send_response(206 if byte_range else 200)
        fallback = "video/mp4" if self.media[index]["kind"] == "video" else "image/jpeg"
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or fallback)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if byte_range:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if self.auth is not None and self.auth.public_origin.startswith("https://"):
            self.send_header("Strict-Transport-Security", "max-age=86400")
        self.end_headers()
        if self.command == "HEAD":
            return
        remaining = end - start + 1
        with path.open("rb") as handle:
            handle.seek(start)
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz" and self.auth is not None:
            self._send_json({"ok": True, "service": "hao-remote-review",
                             "authentication": "required"})
        elif path in {"/", "/review.html"}:
            if not self._authenticated():
                self._send_bytes(BOOTSTRAP_HTML.encode("utf-8"),
                                 "text/html; charset=utf-8")
                return
            client_media = _browser_media(self.media, remote=True)
            self._send_bytes(render_review_html(client_media, "/api/review",
                                                can_finalize=self.can_finalize).encode("utf-8"),
                             "text/html; charset=utf-8")
        elif re.fullmatch(r"/media/\d+", path):
            if not self._authenticated():
                self._fail(401, "authentication_required")
                return
            if self.auth is not None and not self.auth.allow_request(
                    "media", MEDIA_RATE_ATTEMPTS):
                self._fail(429, "rate_limited")
                return
            self._send_media(int(path.rsplit("/", 1)[1]))
        elif path == "/api/ping" and self.auth is not None:
            if not self._authenticated():
                self._fail(401, "authentication_required")
                return
            self._send_json({"ok": True})
        else:
            self._fail(404, "not_found")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if self.auth is None and path != "/api/review":
            self._fail(404, "not_found")
            return
        if self.auth is not None and path not in {"/api/bootstrap", "/api/review"}:
            self._fail(404, "not_found")
            return
        if not self._same_origin_post():
            self._fail(403, "cross_origin_request_blocked")
            return

        if path == "/api/bootstrap":
            assert self.auth is not None
            if not self.auth.allow_request("bootstrap", AUTH_RATE_ATTEMPTS):
                self._fail(429, "rate_limited")
                return
            status, payload = self._read_json(MAX_BOOTSTRAP_BODY_BYTES)
            if status != 200:
                self._fail(status, "invalid_bootstrap_request")
                return
            if not isinstance(payload, dict) or set(payload) != {"bootstrap"} or not isinstance(
                    payload.get("bootstrap"), str):
                self._fail(400, "invalid_bootstrap_request")
                return
            status, credential = self.auth.exchange(payload["bootstrap"])
            if status != 200:
                reason = {401: "invalid_bootstrap", 409: "bootstrap_already_used",
                          410: "bootstrap_expired"}.get(status, "bootstrap_failed")
                self._fail(status, reason)
                return
            max_age = max(1, int(self.auth.session_expires_epoch - time.time()))
            cookie = ("%s=%s; Path=/; Max-Age=%d; HttpOnly; Secure; SameSite=Strict" %
                      (SESSION_COOKIE, credential, max_age))
            self._send_json({"ok": True}, headers={"Set-Cookie": cookie})
            return

        assert path == "/api/review"
        if not self._authenticated():
            self._fail(401, "authentication_required")
            return
        if self.auth is not None and not self.auth.allow_request("review", REVIEW_RATE_ATTEMPTS):
            self._fail(429, "rate_limited")
            return
        status, payload = self._read_json(MAX_REVIEW_BODY_BYTES)
        if status != 200:
            self._fail(status, "invalid_review_request")
            return
        if not _review_payload_valid(payload):
            self._fail(400, "invalid_review_payload")
            return

        def write_review() -> None:
            _atomic_json(self.bundle / "review.json", payload)

        if self.auth is None:
            write_review()
        elif not self.auth.perform_authorized(self._credential(), write_review):
            self._fail(401, "authentication_required")
            return
        self._send_json({"ok": True})

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _handler_factory(bundle: Path, media: list[dict[str, str]],
                     auth: _RemoteReviewAuth | None,
                     can_finalize: bool = False):
    class Bound(_MediaReviewHandler):
        pass
    Bound.bundle, Bound.media, Bound.auth = bundle, media, auth
    Bound.can_finalize = can_finalize
    return Bound
