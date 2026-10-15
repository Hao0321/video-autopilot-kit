from __future__ import annotations
import hmac
import json
import math
import os
import queue
import re
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from review_auth import BOOTSTRAP_TTL_SECONDS, QUICK_TUNNEL_ORIGIN, REMOTE_IDLE_TIMEOUT_SECONDS, REMOTE_SESSION_TTL_SECONDS, REMOTE_STOP_WAIT_SECONDS, _RemoteReviewAuth, _normalized_origin, _sha256, _utc_iso
from review_pairing import _NativePairingWindow, _load_pairing_ui_runtime, _load_qr_runtime, _render_pairing_qr
from review_bundle import _atomic_json, _manifest_media, _without_secret_metadata, create_bundle
from review_http import _handler_factory

from review_process import (
    _find_cloudflared,
    _pid_alive,
    _process_identity,
    _process_identity_matches,
    _terminate_pid,
)


def remote_status(bundle_dir: str | Path) -> dict[str, Any]:
    session_path = Path(bundle_dir).resolve() / "remote_session.json"
    if not session_path.is_file():
        return {"status": "INACTIVE"}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    server_alive = _process_identity_matches(session.get("server_identity"))
    tunnel_alive = _process_identity_matches(session.get("tunnel_identity"))
    try:
        expiry = float(session.get("expires_epoch", 0))
        expired = not math.isfinite(expiry) or time.time() >= expiry
    except (TypeError, ValueError):
        expired = True
    recorded_status = str(session.get("status", "")).upper()
    any_alive = server_alive or tunnel_alive
    if any_alive and recorded_status in {"STOPPED", "STOP_FAILED"}:
        effective_status = "STOP_FAILED"
    elif any_alive and recorded_status == "STARTING":
        effective_status = "STARTING"
    elif any_alive and expired:
        effective_status = "EXPIRED_RUNNING"
    elif server_alive and tunnel_alive:
        effective_status = "ACTIVE"
    elif any_alive:
        effective_status = "DEGRADED"
    elif recorded_status in {"STOPPED", "EXPIRED"}:
        effective_status = recorded_status
    else:
        effective_status = "INACTIVE"
    session.update(server_alive=server_alive, tunnel_alive=tunnel_alive,
                   process_identity_verified=server_alive and tunnel_alive,
                   status=effective_status)
    return _without_secret_metadata(session)


def stop_remote(bundle_dir: str | Path, *,
                wait_timeout: float = REMOTE_STOP_WAIT_SECONDS) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    session_path = bundle / "remote_session.json"
    if not session_path.is_file():
        return {"status": "INACTIVE"}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    stopped = []
    skipped = []
    requested: list[tuple[int, dict[str, Any]]] = []
    for pid_key, identity_key in (("tunnel_pid", "tunnel_identity"),
                                  ("server_pid", "server_identity")):
        try:
            pid = int(session.get(pid_key, 0))
        except (TypeError, ValueError):
            pid = 0
        expected = session.get(identity_key)
        if _process_identity_matches(expected):
            first_request = not any(
                existing_pid == pid and existing_identity == expected
                for existing_pid, existing_identity in requested)
            if first_request:
                requested.append((pid, expected))
            if first_request and not _terminate_pid(pid):
                skipped.append({"pid": pid, "reason": "terminate_request_failed"})
        elif _pid_alive(pid):
            skipped.append({"pid": pid, "reason": "process_identity_not_verified"})
    deadline = time.monotonic() + max(0.0, min(float(wait_timeout),
                                                REMOTE_STOP_WAIT_SECONDS))
    while requested and time.monotonic() < deadline:
        if not any(_process_identity_matches(expected) for _, expected in requested):
            break
        time.sleep(0.05)
    lingering = [pid for pid, expected in requested
                 if _process_identity_matches(expected)]
    stopped = [pid for pid, expected in requested
               if not _process_identity_matches(expected)]
    status = "STOP_FAILED" if lingering else "STOPPED"
    session.update(status=status, stopped_pids=stopped,
                   skipped_pids=skipped,
                   lingering_pids=lingering)
    stop_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if status == "STOPPED":
        session["stopped_at"] = stop_timestamp
        session.pop("stop_attempted_at", None)
    else:
        session["stop_attempted_at"] = stop_timestamp
        session.pop("stopped_at", None)
    session = _without_secret_metadata(session)
    _atomic_json(session_path, session)
    return session


from review_daemon import (
    _remote_daemon_command,
    _spawn_review_daemon,
)


def _read_bootstrap_pipe(stream: Any, expected_digest: str) -> str:
    """Read one bounded token from an inherited anonymous pipe."""
    raw = stream.readline(1025)
    if not raw or len(raw) > 1024:
        raise RuntimeError("secure bootstrap pipe was empty or oversized")
    if isinstance(raw, str):
        raw = raw.encode("ascii", errors="strict")
    token_bytes = raw.rstrip(b"\r\n")
    if not re.fullmatch(rb"[A-Za-z0-9_-]{43,128}", token_bytes):
        raise RuntimeError("secure bootstrap pipe contained an invalid token")
    token = token_bytes.decode("ascii")
    if not hmac.compare_digest(_sha256(token), expected_digest):
        raise RuntimeError("secure bootstrap pipe integrity check failed")
    return token


def _safe_remote_announcements(auth: _RemoteReviewAuth) -> tuple[str, str]:
    return (
        "REMOTE_REVIEW_STATUS=READY_FOR_LOCAL_SCAN",
        "REMOTE_REVIEW_FINGERPRINT=" + auth.fingerprint,
    )


def _remote_cli_summary(payload: dict[str, Any]) -> dict[str, str]:
    """Keep remote command output safe for terminals and conversation capture."""
    safe = _without_secret_metadata(payload)
    summary = {"status": str(safe.get("status") or "UNKNOWN")}
    fingerprint = str(safe.get("url_fingerprint") or "")
    if re.fullmatch(r"[0-9a-f]{16}", fingerprint):
        summary["url_fingerprint"] = fingerprint
    return summary


def _remote_session_payload(auth: _RemoteReviewAuth, tunnel_pid: int,
                            media: list[dict[str, str]],
                            server_identity: dict[str, Any],
                            tunnel_identity: dict[str, Any],
                            verification: dict[str, Any],
                            pairing_status: str = "NATIVE_WINDOW_DISPLAYED",
                            status: str = "ACTIVE") -> dict[str, Any]:
    return {
        "schema_version": 4, "status": status,
        "url_fingerprint": auth.fingerprint,
        "server_pid": os.getpid(), "tunnel_pid": tunnel_pid,
        "server_identity": server_identity, "tunnel_identity": tunnel_identity,
        "media_count": len(media), "media_kinds": sorted({item["kind"] for item in media}),
        "started_at": _utc_iso(auth.created_epoch),
        "bootstrap_expires_at": _utc_iso(auth.bootstrap_expires_epoch),
        "expires_at": _utc_iso(auth.session_expires_epoch),
        "expires_epoch": auth.session_expires_epoch,
        "idle_timeout_seconds": auth.idle_timeout_seconds,
        "pairing_status": pairing_status,
        "verification": _without_secret_metadata(verification),
        "access": "native_memory_qr_then_one_time_fragment_and_browser_session_cookie",
    }


def start_remote_background(bundle_dir: str | Path, port: int = 0,
                            cloudflared: str = "", startup_timeout: float = 75.0) -> dict[str, Any]:
    """Start a detached review daemon that survives the launching Codex shell."""
    bundle = Path(bundle_dir).resolve()
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("review manifest is missing: %s" % manifest_path)
    current = remote_status(bundle)
    if current.get("status") in {"ACTIVE", "STARTING"}:
        raise RuntimeError("remote review is already active; stop it to mint a new one-time link")
    if (bundle / "remote_session.json").is_file():
        stopped = stop_remote(bundle)
        if (stopped.get("status") != "STOPPED" or stopped.get("skipped_pids")
                or stopped.get("lingering_pids")):
            raise RuntimeError("refusing to replace a session whose process identity cannot be verified")
        (bundle / "remote_session.json").unlink(missing_ok=True)
    process, bootstrap_digest = _spawn_review_daemon(bundle, port, cloudflared)
    session_path = bundle / "remote_session.json"
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if session_path.is_file():
            session = json.loads(session_path.read_text(encoding="utf-8"))
            if (int(session.get("server_pid", 0)) == process.pid
                    and int(session.get("schema_version", 0)) >= 4
                    and session.get("status") == "ACTIVE"
                    and session.get("url_fingerprint") == bootstrap_digest[:16]
                    and session.get("pairing_status") in {
                        "NATIVE_WINDOW_DISPLAYED", "SESSION_AUTHORIZED"}
                    and isinstance(session.get("verification"), dict)
                    and session["verification"].get("status") == "VERIFIED"
                    and _process_identity_matches(session.get("server_identity"))
                    and _process_identity_matches(session.get("tunnel_identity"))):
                return _without_secret_metadata(dict(session))
        if process.poll() is not None:
            if session_path.is_file():
                failed = json.loads(session_path.read_text(encoding="utf-8"))
                code = (failed.get("verification") or {}).get("failure_code")
                if (failed.get("url_fingerprint") == bootstrap_digest[:16]
                        and int(failed.get("server_pid", 0)) == process.pid
                        and code in _READINESS_FAILURE_CODES):
                    raise _RemoteReadinessError(code)
            raise RuntimeError(
                "remote review daemon exited before secure native pairing was ready")
        time.sleep(0.25)
    if session_path.is_file():
        stopped = stop_remote(bundle)
        if stopped.get("status") != "STOPPED":
            _terminate_pid(process.pid)
    else:
        _terminate_pid(process.pid)
    raise TimeoutError("remote review daemon did not open secure native pairing in time")


from review_readiness import (
    _READINESS_FAILURE_CODES,
    _RemoteReadinessError,
    _readiness_failure_code,
    verify_remote_review,
)


def deliver_remote(source: str | Path, content_id: str, *,
                   quality_json: str | Path | None = None,
                   bundle_dir: str | Path | None = None, port: int = 0,
                   cloudflared: str = "") -> dict[str, Any]:
    """Create, launch and verify the mobile review required for visual delivery."""
    bundle_result = create_bundle(source, content_id, quality_json, bundle_dir)
    bundle = Path(bundle_result["bundle"])
    _atomic_json(bundle / "remote_delivery.json", {
        "schema_version": 4, "status": "STARTING", "content_id": content_id,
        "bundle": str(bundle), "media_count": bundle_result["media_count"],
    })
    if remote_status(bundle).get("status") == "ACTIVE":
        stop_remote(bundle)
    try:
        session = start_remote_background(bundle, port, cloudflared)
        verification = dict(session.get("verification") or {})
        if verification.get("status") != "VERIFIED":
            raise RuntimeError("remote review daemon did not report verified readiness")
    except Exception as exc:
        stop_remote(bundle)
        if isinstance(exc, _RemoteReadinessError):
            _atomic_json(bundle / "remote_delivery.json", {
                "schema_version": 4, "status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                "failure_code": exc.failure_code,
            })
        raise
    result = {
        "status": "READY_FOR_SECURE_NATIVE_PAIRING",
        "content_id": content_id,
        "url_fingerprint": session["url_fingerprint"],
        "bootstrap_expires_at": session["bootstrap_expires_at"],
        "expires_at": session["expires_at"],
        "bundle": str(bundle),
        "media_count": bundle_result["media_count"],
        "verification": verification,
        "temporary_public_url": True,
        "computer_must_remain_online": True,
        "pairing_status": session["pairing_status"],
        "pairing_qr_storage": "MEMORY_ONLY_NATIVE_WINDOW",
    }
    persisted = dict(result, schema_version=4)
    _atomic_json(bundle / "remote_delivery.json", persisted)
    return result


def _open_local_review_server(bootstrap_digest, bootstrap_expires_epoch, bundle, idle_timeout_seconds, manifest, media, port, session_ttl_seconds):
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    auth = _RemoteReviewAuth(
        bootstrap_digest=bootstrap_digest,
        bootstrap_expires_epoch=bootstrap_expires_epoch,
        public_origin="http://127.0.0.1",
        session_ttl_seconds=session_ttl_seconds,
        idle_timeout_seconds=idle_timeout_seconds,
    )
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 _handler_factory(bundle, media, auth, can_finalize))
    server.daemon_threads = True
    local_port = int(server.server_address[1])
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return auth, server, local_port


def _ready_pairing_session(auth, bootstrap_token, bundle, media, process, qr_module, tk_module, verification):
    remote_url = "%s/review.html#%s" % (
        auth.public_origin, urlencode({"bootstrap": bootstrap_token}))
    qr_png = _render_pairing_qr(remote_url, lambda _name: qr_module)
    del remote_url
    pairing_window = _NativePairingWindow(
        qr_png, auth.fingerprint, _utc_iso(auth.bootstrap_expires_epoch), tk_module)
    qr_png = b""
    server_identity = _process_identity(os.getpid())
    tunnel_identity = _process_identity(process.pid)
    if not server_identity or not tunnel_identity:
        raise RuntimeError("could not establish immutable process identity; refusing remote access")
    session = _remote_session_payload(
        auth, process.pid, media, server_identity, tunnel_identity, verification)
    _atomic_json(bundle / "remote_session.json", session)
    for announcement in _safe_remote_announcements(auth):
        print(announcement, flush=True)
    return pairing_window, session


def _monitor_remote_session(process, auth, pairing_window, session, bundle):
    while process.poll() is None:
        if auth.bootstrap_used and pairing_window is not None:
            pairing_window.close()
            pairing_window = None
            session["pairing_status"] = "SESSION_AUTHORIZED"
            _atomic_json(bundle / "remote_session.json", session)
        elif pairing_window is not None and not pairing_window.pump():
            session.update(
                status="EXPIRED", stop_reason="pairing_window_closed",
                stopped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            _atomic_json(bundle / "remote_session.json", session)
            return pairing_window
        reason = auth.shutdown_due()
        if reason:
            session.update(status="EXPIRED", stop_reason=reason,
                           stopped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            _atomic_json(bundle / "remote_session.json", session)
            return pairing_window
        time.sleep(0.05)
    raise RuntimeError("cloudflared stopped unexpectedly")


def _review_bundle_media(bundle_dir):
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    missing = [item["path"] for item in media if not Path(item["path"]).is_file()]
    if missing:
        raise FileNotFoundError("review media is missing: %s" % missing[0])
    return bundle, manifest, media


def serve_remote(bundle_dir: str | Path, port: int = 0, cloudflared: str = "",
                 startup_timeout: float = 30.0, *, bootstrap_digest: str = "",
                 bootstrap_expires_epoch: float = 0.0, bootstrap_stream: Any = None,
                 session_ttl_seconds: int = REMOTE_SESSION_TTL_SECONDS,
                 idle_timeout_seconds: int = REMOTE_IDLE_TIMEOUT_SECONDS) -> None:
    if not bootstrap_digest or not bootstrap_expires_epoch or bootstrap_stream is None:
        raise RuntimeError(
            "direct remote mode is disabled: use remote-start for anonymous-pipe pairing")
    bootstrap_token = _read_bootstrap_pipe(bootstrap_stream, bootstrap_digest)
    bundle, manifest, media = _review_bundle_media(bundle_dir)
    qr_module = _load_qr_runtime()
    tk_module = _load_pairing_ui_runtime()
    binary = _find_cloudflared(cloudflared)
    auth, server, local_port = _open_local_review_server(bootstrap_digest, bootstrap_expires_epoch, bundle, idle_timeout_seconds, manifest, media, port, session_ttl_seconds)
    command = [str(binary), "tunnel", "--url", "http://127.0.0.1:%d" % local_port,
               "--no-autoupdate", "--loglevel", "info"]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=flags)
    starting_server_identity = _process_identity(os.getpid())
    starting_tunnel_identity = _process_identity(process.pid)
    if not starting_server_identity or not starting_tunnel_identity:
        if process.poll() is None:
            process.terminate()
        server.shutdown(); server.server_close()
        raise RuntimeError("could not establish immutable process identity; refusing remote access")
    _atomic_json(bundle / "remote_session.json", _remote_session_payload(
        auth, process.pid, media, starting_server_identity, starting_tunnel_identity,
        {"status": "PENDING"}, pairing_status="STARTING_NATIVE_WINDOW",
        status="STARTING"))
    lines: queue.Queue[str] = queue.Queue(maxsize=128)

    def pump() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            try:
                lines.put(line, timeout=0.1)
            except queue.Full:
                pass

    threading.Thread(target=pump, daemon=True).start()
    deadline, public_base = time.monotonic() + startup_timeout, ""
    pairing_window: _NativePairingWindow | None = None
    try:
        while time.monotonic() < deadline and process.poll() is None:
            try:
                line = lines.get(timeout=0.25)
            except queue.Empty:
                continue
            match = QUICK_TUNNEL_ORIGIN.search(line)
            if match:
                public_base = match.group(0)
                break
        if not public_base:
            raise RuntimeError("cloudflared did not produce a Quick Tunnel URL")
        with auth._lock:
            auth.public_origin = _normalized_origin(public_base)
        verification = verify_remote_review(auth.public_origin, timeout=5.0, attempts=32,
                                            retry_delay=1.0, total_timeout=30.0)
        pairing_window, session = _ready_pairing_session(auth, bootstrap_token, bundle, media, process, qr_module, tk_module, verification)
        del bootstrap_token
        pairing_window = _monitor_remote_session(process, auth, pairing_window, session, bundle)
        return
    except _RemoteReadinessError as exc:
        _atomic_json(bundle / "remote_session.json", _remote_session_payload(
            auth, process.pid, media, starting_server_identity, starting_tunnel_identity,
            {"status": "FAILED", "failure_code": exc.failure_code},
            pairing_status="NOT_READY", status="STARTUP_FAILED"))
        raise
    finally:
        server.shutdown(); server.server_close()
        if pairing_window is not None:
            pairing_window.close()
        if process.poll() is None:
            process.terminate()
