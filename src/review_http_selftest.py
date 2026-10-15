"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from review_auth import BOOTSTRAP_TTL_SECONDS, MAX_REVIEW_BODY_BYTES, SESSION_COOKIE, _RemoteReviewAuth, _sha256
from review_remote import _RemoteReadinessError, verify_remote_review
from review_http import _handler_factory
import review_readiness as readiness_runtime


def _self_test_remote_readiness(base):
    original_urlopen = readiness_runtime.urlopen
    probed_urls: list[str] = []

    def routed_urlopen(probe: Any, timeout: float = 0) -> Any:
        original_url = str(getattr(probe, "full_url", probe))
        probed_urls.append(original_url)
        return original_urlopen(
            Request(original_url.replace("https://local.test", base),
                    headers=dict(getattr(probe, "headers", {}))), timeout=timeout)

    readiness_runtime.urlopen = routed_urlopen
    try:
        verified = verify_remote_review("https://local.test", attempts=1)
        assert verified["page_status"] == 200
        assert verified["media_status"] == 401
        assert verified["media_gate"] == "AUTH_GATED"
        assert verified["pairing_required"]
        assert probed_urls and all("bootstrap" not in item for item in probed_urls)
        assert any(item.endswith("/media/0") for item in probed_urls)

        class UngatedMedia:
            def __init__(self, status: int) -> None:
                self.status = status
            def getcode(self) -> int: return self.status
            def read(self, _limit: int = -1) -> bytes: return b"leaked"
            def close(self) -> None: pass

        for leaked_status in (200, 206):
            def ungated_urlopen(probe: Any, timeout: float = 0,
                                 status: int = leaked_status) -> Any:
                probe_url = str(getattr(probe, "full_url", probe))
                if probe_url.endswith("/media/0"):
                    return UngatedMedia(status)
                return routed_urlopen(probe, timeout=timeout)

            readiness_runtime.urlopen = ungated_urlopen
            try:
                verify_remote_review("https://local.test", attempts=1)
                raise AssertionError(
                    "public media status %d unexpectedly passed readiness" %
                    leaked_status)
            except RuntimeError as exc:
                assert isinstance(exc, _RemoteReadinessError)
                assert exc.failure_code == "MEDIA_AUTH_GATE_FAILED"
    finally:
        readiness_runtime.urlopen = original_urlopen


def _self_test_unknown_credentials(base, post_headers, request):
    unknown_cookie = {"Cookie": SESSION_COOKIE + "=" + secrets.token_urlsafe(32)}
    assert request("/media/0", headers=unknown_cookie)[0] == 401

    wrong_origin = dict(post_headers, Origin="https://evil.invalid")
    unknown = json.dumps({"bootstrap": "wrong"}).encode("utf-8")
    assert request("/api/bootstrap", data=b"", headers=wrong_origin)[0] == 403
    assert request("/api/bootstrap", data=b"",
                   headers=dict(post_headers, **{"Sec-Fetch-Site": "cross-site"}))[0] == 403
    assert request("/api/bootstrap", data=b"",
                   headers={"Content-Type": "application/json",
                            "Origin": base})[0] == 403
    assert request("/api/bootstrap", data=unknown, headers=post_headers)[0] == 401
    return unknown_cookie


def _self_test_http(bundle: dict[str, Any], media: list[dict[str, Any]]) -> None:
    token = secrets.token_urlsafe(32)
    auth = _RemoteReviewAuth(_sha256(token), time.time() + BOOTSTRAP_TTL_SECONDS,
                             "http://127.0.0.1")
    assert auth.bootstrap_expires_epoch <= auth.created_epoch + BOOTSTRAP_TTL_SECONDS
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 _handler_factory(Path(bundle["bundle"]), media, auth))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    auth.public_origin = base

    def request(path: str, *, data: bytes | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, bytes, Any]:
        try:
            response = urlopen(Request(base + path, data=data, headers=headers or {}), timeout=3)
            return int(response.status), response.read(), response.headers
        except HTTPError as exc:
            return int(exc.code), exc.read(), exc.headers

    post_headers = {"Content-Type": "application/json", "Origin": base,
                    "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
    forbidden_inline_csp = "unsafe" + "-inline"
    try:
        status, page, page_headers = request("/review.html")
        assert status == 200 and "安全連線中" in page.decode("utf-8")
        bootstrap_csp = str(page_headers.get("Content-Security-Policy", ""))
        assert "sha256-" in bootstrap_csp and forbidden_inline_csp not in bootstrap_csp
        assert request("/media/0")[0] == 401  # no cookie cannot read media
        unknown_cookie = _self_test_unknown_credentials(base, post_headers, request)

        bootstrap_body = json.dumps({"bootstrap": token}).encode("utf-8")
        status, _, response_headers = request(
            "/api/bootstrap", data=bootstrap_body, headers=post_headers)
        assert status == 200
        set_cookie = str(response_headers.get("Set-Cookie", ""))
        assert (SESSION_COOKIE + "=") in set_cookie
        assert "HttpOnly" in set_cookie and "Secure" in set_cookie
        assert "SameSite=Strict" in set_cookie
        cookie = set_cookie.split(";", 1)[0]
        assert len(cookie.split("=", 1)[1]) >= 43
        assert token not in cookie and token not in repr(auth)
        assert request("/api/bootstrap", data=bootstrap_body,
                       headers=post_headers)[0] == 409  # one-time replay

        auth_headers = {"Cookie": cookie}
        status, page, page_headers = request("/review.html", headers=auth_headers)
        assert status == 200 and b"/media/0" in page and b"/media/1" in page
        assert b" onclick=\"" not in page
        app_csp = str(page_headers.get("Content-Security-Policy", ""))
        assert "sha256-" in app_csp and forbidden_inline_csp not in app_csp
        range_headers = {"Cookie": cookie, "Range": "bytes=2-5"}
        status, body, _ = request("/media/0", headers=range_headers)
        assert status == 206 and body == b"2345"
        assert request("/media/1", headers=auth_headers)[1] == b"fake-png"

        payload = json.dumps({"issues": [], "decisions": {"m1": "approved"}}).encode("utf-8")
        review_headers = dict(post_headers, Cookie=cookie)
        assert request("/api/review", data=b"", headers=post_headers)[0] == 401
        assert request("/api/review", data=b"",
                       headers=dict(post_headers, **unknown_cookie))[0] == 401
        assert request("/api/review", data=b"",
                       headers=dict(review_headers, Origin="https://evil.invalid"))[0] == 403
        assert request("/api/review", data=b"",
                       headers={key: value for key, value in review_headers.items()
                                if key != "Content-Type"})[0] == 415
        declared_oversize = dict(
            review_headers, **{"Content-Length": str(MAX_REVIEW_BODY_BYTES + 1)})
        assert request("/api/review", data=b"x",
                       headers=declared_oversize)[0] == 413
        assert request("/api/review", data=payload, headers=review_headers)[0] == 200
        assert (Path(bundle["bundle"]) / "review.json").is_file()

        _self_test_remote_readiness(base)
    finally:
        server.shutdown(); server.server_close()
