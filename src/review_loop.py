"""Human review CLI facade; implementation owners retain the HTTP/auth protocol."""
from __future__ import annotations
import argparse
import json
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from review_remote import _RemoteReadinessError, _remote_cli_summary, deliver_remote, remote_status, serve_remote, start_remote_background, stop_remote
from review_http import _handler_factory
from review_bundle import _manifest_media, create_bundle, finalize
from review_auth import AUTH_RATE_ATTEMPTS, AUTH_RATE_WINDOW_SECONDS, BOOTSTRAP_TTL_SECONDS, IMAGE_EXTENSIONS, MAX_BOOTSTRAP_BODY_BYTES, MAX_REVIEW_BODY_BYTES, MAX_REVIEW_MEDIA, MEDIA_EXTENSIONS, MEDIA_RATE_ATTEMPTS, QUICK_TUNNEL_HOST, QUICK_TUNNEL_ORIGIN, REMOTE_IDLE_TIMEOUT_SECONDS, REMOTE_SESSION_TTL_SECONDS, REMOTE_STOP_WAIT_SECONDS, REVIEW_RATE_ATTEMPTS, SESSION_COOKIE, VIDEO_EXTENSIONS, _RemoteReviewAuth, _normalized_origin, _review_payload_valid, _sha256, _utc_iso
from review_page import BOOTSTRAP_HTML, HTML, HTML_TEMPLATE, _csp_for_html, render_review_html
from review_bundle import CATEGORY_SIGNALS, _atomic_json, _browser_media, _discover_media, _kind, _manifest_media, _without_secret_metadata, create_bundle, finalize
from review_http import _MediaReviewHandler, _handler_factory, _parse_byte_range
from review_pairing import _NativePairingWindow, _load_pairing_ui_runtime, _load_qr_runtime, _render_pairing_qr
from review_remote import _READINESS_FAILURE_CODES, _RemoteReadinessError, _find_cloudflared, _pid_alive, _process_identity, _process_identity_matches, _read_bootstrap_pipe, _readiness_failure_code, _remote_cli_summary, _remote_daemon_command, _remote_session_payload, _safe_remote_announcements, _terminate_pid, deliver_remote, remote_status, serve_remote, start_remote_background, stop_remote, verify_remote_review
from review_loop_selftest import _self_test_bundle, _self_test_http, _self_test_pairing_ui, _self_test_remote_lifecycle, _self_test_secret_surfaces

def serve(bundle_dir: str | Path, port: int = 8765) -> None:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    print("僅限本機開啟：http://127.0.0.1:%d/review.html" % port)
    ThreadingHTTPServer(("127.0.0.1", port),
                        _handler_factory(bundle, media, None, can_finalize)).serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("video", help="browser-viewable video, image, or media directory")
    create.add_argument("--content-id", required=True)
    create.add_argument("--quality-json", default="")
    create.add_argument("--bundle-dir", default="")
    server = sub.add_parser("serve"); server.add_argument("bundle"); server.add_argument("--port", type=int, default=8765)
    remote = sub.add_parser("remote"); remote.add_argument("bundle"); remote.add_argument("--port", type=int, default=0)
    remote.add_argument("--cloudflared", default="")
    remote.add_argument("--bootstrap-digest", default="", help=argparse.SUPPRESS)
    remote.add_argument("--bootstrap-expires-epoch", type=float, default=0.0,
                        help=argparse.SUPPRESS)
    remote_start = sub.add_parser("remote-start"); remote_start.add_argument("bundle")
    remote_start.add_argument("--port", type=int, default=0); remote_start.add_argument("--cloudflared", default="")
    deliver = sub.add_parser("deliver")
    deliver.add_argument("source", help="finished visual asset, video, or media directory")
    deliver.add_argument("--content-id", required=True)
    deliver.add_argument("--quality-json", default="")
    deliver.add_argument("--bundle-dir", default="")
    deliver.add_argument("--port", type=int, default=0)
    deliver.add_argument("--cloudflared", default="")
    status = sub.add_parser("remote-status"); status.add_argument("bundle")
    stop = sub.add_parser("remote-stop"); stop.add_argument("bundle")
    final = sub.add_parser("finalize"); final.add_argument("bundle"); final.add_argument("--no-learn", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "create":
        print(json.dumps(create_bundle(args.video, args.content_id, args.quality_json or None,
                                       args.bundle_dir or None), ensure_ascii=False, indent=2)); return 0
    if args.command == "serve":
        serve(args.bundle, args.port); return 0
    if args.command == "remote":
        if not args.bootstrap_digest or not args.bootstrap_expires_epoch:
            raise RuntimeError("direct remote mode is disabled; use remote-start")
        serve_remote(args.bundle, args.port, args.cloudflared,
                     bootstrap_digest=args.bootstrap_digest,
                     bootstrap_expires_epoch=args.bootstrap_expires_epoch,
                     bootstrap_stream=sys.stdin.buffer); return 0
    if args.command == "remote-start":
        try:
            started = start_remote_background(args.bundle, args.port, args.cloudflared)
        except _RemoteReadinessError as exc:
            print(json.dumps({"status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                              "failure_code": exc.failure_code})); return 1
        print(json.dumps(_remote_cli_summary(started), ensure_ascii=False, indent=2)); return 0
    if args.command == "deliver":
        try:
            delivered = deliver_remote(
                args.source, args.content_id, quality_json=args.quality_json or None,
                bundle_dir=args.bundle_dir or None, port=args.port, cloudflared=args.cloudflared)
        except _RemoteReadinessError as exc:
            print(json.dumps({"status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                              "failure_code": exc.failure_code})); return 1
        print(json.dumps(_remote_cli_summary(delivered), ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-status":
        print(json.dumps(_remote_cli_summary(remote_status(args.bundle)),
                         ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-stop":
        print(json.dumps(_remote_cli_summary(stop_remote(args.bundle)),
                         ensure_ascii=False, indent=2)); return 0
    if args.command == "finalize":
        print(json.dumps(finalize(args.bundle, learn=not args.no_learn), ensure_ascii=False, indent=2)); return 0
    self_test(); return 0


def self_test() -> None:
    """Run owned local fixtures through the actual CLI facade."""
    from review_loop_selftest import self_test as run_tests
    run_tests(sys.modules[__name__])


if __name__ == "__main__":
    raise SystemExit(main())
