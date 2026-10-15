from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import hmac
import math
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp"}


MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


MAX_REVIEW_MEDIA = 300


MAX_REVIEW_BODY_BYTES = 256 * 1024


MAX_BOOTSTRAP_BODY_BYTES = 4 * 1024


BOOTSTRAP_TTL_SECONDS = 10 * 60


REMOTE_SESSION_TTL_SECONDS = 60 * 60


REMOTE_IDLE_TIMEOUT_SECONDS = 15 * 60


REMOTE_STOP_WAIT_SECONDS = 5.0


SESSION_COOKIE = "__Host-hao_review_session"


AUTH_RATE_WINDOW_SECONDS = 60


AUTH_RATE_ATTEMPTS = 12


REVIEW_RATE_ATTEMPTS = 120


MEDIA_RATE_ATTEMPTS = 600


QUICK_TUNNEL_HOST = "trycloud" + "flare.com"


QUICK_TUNNEL_ORIGIN = re.compile(
    r"https://[-a-z0-9]+\." + re.escape(QUICK_TUNNEL_HOST), re.I)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


def _normalized_origin(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return "%s://%s" % (parsed.scheme.lower(), parsed.netloc.lower())


@dataclass
class _RemoteReviewAuth:
    """In-memory capability state. Only non-secret fingerprints go to disk."""

    bootstrap_digest: str
    bootstrap_expires_epoch: float
    public_origin: str
    session_ttl_seconds: int = REMOTE_SESSION_TTL_SECONDS
    idle_timeout_seconds: int = REMOTE_IDLE_TIMEOUT_SECONDS
    created_epoch: float = field(default_factory=time.time)
    created_monotonic: float = field(default_factory=time.monotonic)
    bootstrap_used: bool = False
    session_digest: str = ""
    last_activity_monotonic: float = field(default_factory=time.monotonic)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _rate_hits: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(deque), repr=False)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.bootstrap_digest):
            raise ValueError("bootstrap digest must be a SHA-256 hex digest")
        self.public_origin = _normalized_origin(self.public_origin)
        if not self.public_origin:
            raise ValueError("remote review requires an explicit public origin")
        requested_expiry = float(self.bootstrap_expires_epoch)
        if not math.isfinite(requested_expiry):
            raise ValueError("bootstrap expiry must be finite")
        self.bootstrap_expires_epoch = min(
            requested_expiry, self.created_epoch + BOOTSTRAP_TTL_SECONDS)
        self.session_ttl_seconds = min(REMOTE_SESSION_TTL_SECONDS,
                                       max(1, int(self.session_ttl_seconds)))
        self.idle_timeout_seconds = min(REMOTE_IDLE_TIMEOUT_SECONDS,
                                        max(1, int(self.idle_timeout_seconds)))

    @property
    def session_expires_epoch(self) -> float:
        return self.created_epoch + self.session_ttl_seconds

    @property
    def fingerprint(self) -> str:
        return self.bootstrap_digest[:16]

    def allow_request(self, bucket: str, limit: int) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._rate_hits[bucket]
            while hits and now - hits[0] >= AUTH_RATE_WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def exchange(self, bootstrap: str) -> tuple[int, str]:
        """Consume the bootstrap once and return a new browser credential."""
        with self._lock:
            if self.bootstrap_used:
                return 409, ""
            if time.time() >= self.bootstrap_expires_epoch:
                return 410, ""
            if not bootstrap or not hmac.compare_digest(_sha256(bootstrap),
                                                        self.bootstrap_digest):
                return 401, ""
            credential = secrets.token_urlsafe(32)
            self.session_digest = _sha256(credential)
            self.bootstrap_used = True
            self.last_activity_monotonic = time.monotonic()
            return 200, credential

    def authorized(self, credential: str) -> bool:
        with self._lock:
            if (time.time() >= self.session_expires_epoch
                    or time.monotonic() - self.last_activity_monotonic >=
                    self.idle_timeout_seconds or not self.session_digest):
                return False
            if not credential or not hmac.compare_digest(_sha256(credential),
                                                         self.session_digest):
                return False
            self.last_activity_monotonic = time.monotonic()
            return True

    def shutdown_due(self) -> str:
        with self._lock:
            now_epoch, now_mono = time.time(), time.monotonic()
            if now_epoch >= self.session_expires_epoch:
                return "session_ttl_expired"
            if not self.bootstrap_used and now_epoch >= self.bootstrap_expires_epoch:
                return "bootstrap_expired"
            if now_mono - self.last_activity_monotonic >= self.idle_timeout_seconds:
                return "idle_timeout"
            return ""


def _review_payload_valid(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    issues = payload.get("issues", [])
    ratings = payload.get("ratings", {})
    decisions = payload.get("decisions", {})
    if not isinstance(issues, list) or len(issues) > 1000:
        return False
    if not isinstance(ratings, dict) or len(ratings) > 64:
        return False
    if not isinstance(decisions, dict) or len(decisions) > MAX_REVIEW_MEDIA:
        return False
    stack: list[tuple[Any, int]] = [(payload, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > 8:
            return False
        if isinstance(value, str) and len(value) > 10_000:
            return False
        if isinstance(value, dict):
            if len(value) > 2_000:
                return False
            stack.extend((key, depth + 1) for key in value)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            if len(value) > 2_000:
                return False
            stack.extend((item, depth + 1) for item in value)
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            return False
    return True
