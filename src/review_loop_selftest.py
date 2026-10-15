from __future__ import annotations
import base64
import contextlib
import io
import json
import os
import secrets
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from review_auth import AUTH_RATE_ATTEMPTS, BOOTSTRAP_TTL_SECONDS, MAX_REVIEW_BODY_BYTES, QUICK_TUNNEL_HOST, SESSION_COOKIE, _RemoteReviewAuth, _sha256
from review_page import HTML_TEMPLATE
from review_pairing import _NativePairingWindow, _load_pairing_ui_runtime, _render_pairing_qr
from review_remote import _RemoteReadinessError, _pid_alive, _process_identity, _process_identity_matches, _read_bootstrap_pipe, _remote_cli_summary, _remote_daemon_command, _remote_session_payload, _safe_remote_announcements, deliver_remote, remote_status, stop_remote, verify_remote_review
from review_bundle import _atomic_json, _manifest_media, create_bundle
from review_http import _handler_factory, _parse_byte_range
import review_remote as remote_runtime

def _self_test_bundle(temp: str, api: Any) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    source = Path(temp) / "assets"; source.mkdir()
    video = source / "current.mp4"
    video.write_bytes(b"0123456789")
    image = source / "taste-board.png"; image.write_bytes(b"fake-png")
    (source / "notes.txt").write_text("skip", encoding="utf-8")
    bundle = create_bundle(source, "demo")
    assert Path(bundle["page"]).is_file()
    assert bundle["media_count"] == 2
    assert create_bundle(source, "demo")["media_count"] == 2
    assert _manifest_media({"video": str(video)})[0]["path"] == str(video.resolve())
    assert _pid_alive(os.getpid()) and not _pid_alive(-1)
    cli_bundle = Path(temp) / "cli-review"
    assert api.main(["create", str(image), "--content-id", "cli-demo",
                 "--bundle-dir", str(cli_bundle)]) == 0
    assert json.loads((cli_bundle / "manifest.json").read_text(encoding="utf-8"))["media_count"] == 1
    assert "taste-board.png" in Path(bundle["page"]).read_text(encoding="utf-8")
    assert _parse_byte_range("bytes=2-5", 10) == (2, 5)
    manifest = json.loads((Path(bundle["bundle"]) / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    return bundle, media, image


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

        original_urlopen = remote_runtime.urlopen
        probed_urls: list[str] = []

        def routed_urlopen(probe: Any, timeout: float = 0) -> Any:
            original_url = str(getattr(probe, "full_url", probe))
            probed_urls.append(original_url)
            return original_urlopen(
                Request(original_url.replace("https://local.test", base),
                        headers=dict(getattr(probe, "headers", {}))), timeout=timeout)

        remote_runtime.urlopen = routed_urlopen
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

                remote_runtime.urlopen = ungated_urlopen
                try:
                    verify_remote_review("https://local.test", attempts=1)
                    raise AssertionError(
                        "public media status %d unexpectedly passed readiness" %
                        leaked_status)
                except RuntimeError as exc:
                    assert isinstance(exc, _RemoteReadinessError)
                    assert exc.failure_code == "MEDIA_AUTH_GATE_FAILED"
        finally:
            remote_runtime.urlopen = original_urlopen
    finally:
        server.shutdown(); server.server_close()


def _self_test_pairing_ui() -> None:
    pairing_token = secrets.token_urlsafe(32)
    pairing_remote_url = ("https://pairing.example.invalid/review.html#" +
                          urlencode({"bootstrap": pairing_token}))
    qr_png = _render_pairing_qr(pairing_remote_url)
    assert qr_png.startswith(b"\x89PNG\r\n\x1a\n") and len(qr_png) > 100

    def missing_qr_runtime(_name: str) -> Any:
        raise ModuleNotFoundError("qrcode")

    try:
        _render_pairing_qr(pairing_remote_url, missing_qr_runtime)
        raise AssertionError("missing qrcode runtime unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    def missing_ui_runtime(_name: str) -> Any:
        raise ModuleNotFoundError("tkinter")

    try:
        _load_pairing_ui_runtime(missing_ui_runtime)
        raise AssertionError("missing tkinter runtime unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    class BrokenTk:
        @staticmethod
        def Tk() -> Any:
            raise RuntimeError("no interactive desktop")

    try:
        _NativePairingWindow(qr_png, _sha256(pairing_token)[:16],
                             "2099-01-01T00:00:00+00:00", BrokenTk())
        raise AssertionError("unavailable native desktop unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    class FakeRoot:
        def __init__(self) -> None:
            self.visible = False
            self.destroyed = False
            self.protocols: dict[str, Any] = {}
            self.attributes_seen: list[tuple[Any, ...]] = []

        def withdraw(self) -> None: self.visible = False
        def title(self, _value: str) -> None: return
        def configure(self, **_kwargs: Any) -> None: return
        def resizable(self, *_args: Any) -> None: return
        def protocol(self, name: str, callback: Any) -> None:
            self.protocols[name] = callback
        def update_idletasks(self) -> None: return
        def deiconify(self) -> None: self.visible = True
        def lift(self) -> None: return
        def attributes(self, *args: Any) -> None: self.attributes_seen.append(args)
        def after(self, _delay: int, _callback: Any) -> None: return
        def update(self) -> None:
            if self.destroyed:
                raise RuntimeError("destroyed")
        def destroy(self) -> None: self.destroyed = True

    class FakeWidget:
        def __init__(self, _root: Any, **kwargs: Any) -> None:
            fake_tk.widget_kwargs.append(kwargs)
        def pack(self, **_kwargs: Any) -> None: return

    class FakePhoto:
        def __init__(self, **kwargs: Any) -> None:
            self.data = kwargs.get("data", "")
            self.format = kwargs.get("format", "")

    class FakeTk:
        def __init__(self) -> None:
            self.root = FakeRoot()
            self.widget_kwargs: list[dict[str, Any]] = []
            self.Label = FakeWidget
            self.PhotoImage = FakePhoto
        def Tk(self) -> FakeRoot: return self.root

    fake_tk = FakeTk()
    pairing_window = _NativePairingWindow(
        qr_png, _sha256(pairing_token)[:16],
        "2099-01-01T00:00:00+00:00", fake_tk)
    assert pairing_window.is_open and pairing_window.pump() and fake_tk.root.visible
    assert pairing_window._image.format == "png"
    assert base64.b64decode(pairing_window._image.data) == qr_png
    visible_text = "\n".join(
        str(item.get("text", "")) for item in fake_tk.widget_kwargs)
    assert pairing_token not in visible_text
    assert "pairing.example.invalid" not in visible_text
    fake_tk.root.protocols["WM_DELETE_WINDOW"]()
    assert not pairing_window.is_open and fake_tk.root.destroyed


def _self_test_remote_lifecycle(temp: str, bundle: dict[str, Any],
                                media: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    expired_token = secrets.token_urlsafe(32)
    expired_auth = _RemoteReviewAuth(_sha256(expired_token), time.time() - 1,
                                     "http://127.0.0.1")
    expired_server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _handler_factory(Path(bundle["bundle"]), media, expired_auth))
    expired_thread = threading.Thread(target=expired_server.serve_forever, daemon=True)
    expired_thread.start()
    expired_base = "http://127.0.0.1:%d" % expired_server.server_address[1]
    expired_auth.public_origin = expired_base
    try:
        expired_headers = {"Content-Type": "application/json", "Origin": expired_base,
                       "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
        expired_body = json.dumps({"bootstrap": expired_token}).encode("utf-8")
        try:
            urlopen(Request(expired_base + "/api/bootstrap", data=expired_body,
                            headers=expired_headers), timeout=3)
            raise AssertionError("expired bootstrap unexpectedly succeeded")
        except HTTPError as exc:
            assert exc.code == 410
    finally:
        expired_server.shutdown(); expired_server.server_close()

    idle_auth = _RemoteReviewAuth(_sha256("idle"), time.time() + 60,
                                  "https://local.test", idle_timeout_seconds=1)
    idle_auth.session_digest = _sha256("idle-credential")
    idle_auth.bootstrap_used = True
    idle_auth.last_activity_monotonic -= 2
    assert not idle_auth.authorized("idle-credential")
    assert idle_auth.shutdown_due() == "idle_timeout"
    ttl_auth = _RemoteReviewAuth(_sha256("ttl"), time.time() + 60,
                                 "https://local.test", session_ttl_seconds=1)
    ttl_auth.created_epoch -= 2
    assert ttl_auth.shutdown_due() == "session_ttl_expired"
    identity = _process_identity(os.getpid())
    assert identity and _process_identity_matches(identity)
    assert not _process_identity_matches(dict(identity, start_marker="reused-pid"))
    limiter = _RemoteReviewAuth(_sha256("limit"), time.time() + 60,
                                "https://local.test")
    assert all(limiter.allow_request("bootstrap", AUTH_RATE_ATTEMPTS)
               for _ in range(AUTH_RATE_ATTEMPTS))
    assert not limiter.allow_request("bootstrap", AUTH_RATE_ATTEMPTS)
    starting_bundle = Path(temp) / "starting-review"; starting_bundle.mkdir()
    _atomic_json(starting_bundle / "remote_session.json", {
        "schema_version": 4, "status": "STARTING",
        "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
        "url_fingerprint": "0" * 16,
    })
    assert remote_status(starting_bundle)["status"] == "STARTING"
    assert _remote_cli_summary(remote_status(starting_bundle)) == {
        "status": "STARTING", "url_fingerprint": "0" * 16}
    status_bundle = Path(temp) / "status-review"; status_bundle.mkdir()
    raw_url_key = "u" + "rl"
    forbidden_url_json = '"' + raw_url_key + '":'
    status_payload = {
        "schema_version": 2, "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
    }
    status_payload[raw_url_key] = (
        "https://legacy." + QUICK_TUNNEL_HOST + "/legacy-bearer/review.html")
    status_payload["public_origin"] = "https://legacy." + QUICK_TUNNEL_HOST
    status_payload["local_pairing_url"] = "http://127.0.0.1:43210/pair"
    status_payload["pairing_port"] = 43210
    status_payload["port"] = 8765
    status_payload["nested"] = {
        raw_url_key: "https://legacy." + QUICK_TUNNEL_HOST + "/nested-secret",
        "safe": "metadata",
    }
    _atomic_json(status_bundle / "remote_session.json", status_payload)
    safe_status = remote_status(status_bundle)
    assert safe_status["status"] == "ACTIVE" and raw_url_key not in safe_status
    assert "legacy-bearer" not in json.dumps(safe_status)
    assert safe_status["nested"] == {"safe": "metadata"}
    assert not ({"public_origin", "local_pairing_url", "pairing_port", "port"}
                & set(safe_status))
    status_payload["server_identity"] = dict(identity, start_marker="reused-pid")
    _atomic_json(status_bundle / "remote_session.json", status_payload)
    assert remote_status(status_bundle)["status"] == "DEGRADED"

    stop_failure_bundle = Path(temp) / "stop-failure-review"
    stop_failure_bundle.mkdir()
    stop_failure_payload = {
        "schema_version": 4, "status": "ACTIVE",
        "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
    }
    _atomic_json(stop_failure_bundle / "remote_session.json", stop_failure_payload)
    original_terminate = remote_runtime._terminate_pid
    remote_runtime._terminate_pid = lambda _pid: False
    try:
        failed_stop = stop_remote(stop_failure_bundle, wait_timeout=0.0)
    finally:
        remote_runtime._terminate_pid = original_terminate
    assert failed_stop["status"] == "STOP_FAILED"
    assert failed_stop["lingering_pids"] == [os.getpid()]
    assert failed_stop["skipped_pids"] == [
        {"pid": os.getpid(), "reason": "terminate_request_failed"}]
    assert "stop_attempted_at" in failed_stop and "stopped_at" not in failed_stop
    truthful_status = remote_status(stop_failure_bundle)
    assert truthful_status["status"] == "STOP_FAILED"
    assert truthful_status["server_alive"] and truthful_status["tunnel_alive"]

    stopped_bundle = Path(temp) / "already-stopped-review"
    stopped_bundle.mkdir()
    dead_pid = 2_000_000_000
    dead_identity = dict(identity, pid=dead_pid, start_marker="not-running")
    _atomic_json(stopped_bundle / "remote_session.json", {
        "schema_version": 4, "status": "ACTIVE",
        "server_pid": dead_pid, "tunnel_pid": dead_pid,
        "server_identity": dead_identity, "tunnel_identity": dead_identity,
        "expires_epoch": time.time() + 60,
    })
    stopped_result = stop_remote(stopped_bundle, wait_timeout=0.0)
    assert stopped_result["status"] == "STOPPED" and "stopped_at" in stopped_result
    assert remote_status(stopped_bundle)["status"] == "STOPPED"

    return identity, forbidden_url_json


def _self_test_secret_surfaces(temp: str, image: Path, media: list[dict[str, Any]],
                               identity: dict[str, Any], forbidden_url_json: str, api: Any) -> None:
    delivery_bundle = Path(temp) / "delivery-review"
    surface_token = secrets.token_urlsafe(32)
    surface_digest = _sha256(surface_token)
    command = _remote_daemon_command(delivery_bundle, 0, "", surface_digest,
                                     time.time() + BOOTSTRAP_TTL_SECONDS)
    assert surface_token not in "\0".join(command)
    assert _read_bootstrap_pipe(io.BytesIO((surface_token + "\n").encode("ascii")),
                                surface_digest) == surface_token
    surface_auth = _RemoteReviewAuth(surface_digest, time.time() + 60,
                                     "https://example.invalid")
    announcements = "\n".join(_safe_remote_announcements(surface_auth))
    assert surface_token not in announcements and "#bootstrap=" not in announcements
    assert "example.invalid" not in announcements and "127.0.0.1" not in announcements
    surface_verification = {
        "status": "VERIFIED", "health_status": 200, "page_status": 200,
        "media_status": 401, "media_gate": "AUTH_GATED",
        "pairing_required": True,
    }
    safe_session = _remote_session_payload(
        surface_auth, os.getpid(), media, identity, identity,
        surface_verification)
    session_text = json.dumps(safe_session, ensure_ascii=False)
    assert surface_token not in session_text and forbidden_url_json not in session_text
    forbidden_locator_keys = {
        "public_origin", "local_pairing_url", "pairing_url", "pairing_port", "port"}
    assert not (forbidden_locator_keys & set(safe_session))
    assert "example.invalid" not in session_text and "127.0.0.1" not in session_text
    safe_artifacts = Path(temp) / "safe-surfaces"; safe_artifacts.mkdir()
    _atomic_json(safe_artifacts / "remote_session.json", safe_session)
    original_start = remote_runtime.start_remote_background
    original_cli_start = api.start_remote_background
    remote_runtime.start_remote_background = lambda *_args, **_kwargs: dict(safe_session)
    api.start_remote_background = remote_runtime.start_remote_background
    try:
        cli_stdout = io.StringIO()
        with contextlib.redirect_stdout(cli_stdout):
            assert api.main(["remote-start", str(delivery_bundle)]) == 0
        cli_text = cli_stdout.getvalue()
        assert surface_token not in cli_text and forbidden_url_json not in cli_text
        assert set(json.loads(cli_text)) == {"status", "url_fingerprint"}
        deliver_stdout = io.StringIO()
        cli_delivery_bundle = Path(temp) / "cli-delivery-review"
        with contextlib.redirect_stdout(deliver_stdout):
            assert api.main(["deliver", str(image), "--content-id", "cli-secret-free",
                         "--bundle-dir", str(cli_delivery_bundle)]) == 0
        deliver_cli_text = deliver_stdout.getvalue()
        assert surface_token not in deliver_cli_text
        assert forbidden_url_json not in deliver_cli_text
        assert set(json.loads(deliver_cli_text)) == {"status", "url_fingerprint"}
        delivered = deliver_remote(image, "secret-free", bundle_dir=delivery_bundle)
        delivered_text = json.dumps(delivered, ensure_ascii=False)
        assert surface_token not in delivered_text and forbidden_url_json not in delivered_text
        assert delivered["pairing_status"] == "NATIVE_WINDOW_DISPLAYED"
        assert delivered["pairing_qr_storage"] == "MEMORY_ONLY_NATIVE_WINDOW"
        assert not (forbidden_locator_keys & set(delivered))
        assert "example.invalid" not in delivered_text and "127.0.0.1" not in delivered_text
        delivery_text = (delivery_bundle / "remote_delivery.json").read_text(encoding="utf-8")
        assert surface_token not in delivery_text and forbidden_url_json not in delivery_text
        assert all(key not in delivery_text for key in forbidden_locator_keys)
        for artifact in safe_artifacts.iterdir():
            text = artifact.read_text(encoding="utf-8", errors="replace")
            assert surface_token not in text and "#bootstrap=" not in text
            assert "example.invalid" not in text and "127.0.0.1" not in text
    finally:
        remote_runtime.start_remote_background = original_start
        api.start_remote_background = original_cli_start


def self_test(api: Any) -> None:
    assert '.viewer{display:block' in HTML_TEMPLATE
    assert 'placeholder="未評"' in HTML_TEMPLATE
    assert "data.ratings[k]||5" not in HTML_TEMPLATE
    assert "input.checkValidity()" in HTML_TEMPLATE
    with tempfile.TemporaryDirectory(prefix="review-loop-") as temp:
        bundle, media, image = _self_test_bundle(temp, api)
        _self_test_http(bundle, media)
        _self_test_pairing_ui()
        identity, forbidden_url_json = _self_test_remote_lifecycle(temp, bundle, media)
        _self_test_secret_surfaces(temp, image, media, identity, forbidden_url_json, api)
    print("review_loop self-test GREEN")
