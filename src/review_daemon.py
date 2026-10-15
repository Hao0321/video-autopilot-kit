"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import os
import secrets
from typing import Any
import subprocess
import sys
import time
from pathlib import Path
from review_auth import BOOTSTRAP_TTL_SECONDS, _sha256
from review_process import _terminate_pid


def _remote_daemon_command(bundle: Path, port: int, cloudflared: str,
                           bootstrap_digest: str,
                           bootstrap_expires_epoch: float) -> list[str]:
    command = [sys.executable, str(Path(__file__).with_name("review_loop.py").resolve()), "remote", str(bundle),
               "--port", str(port), "--bootstrap-digest", bootstrap_digest,
               "--bootstrap-expires-epoch", str(bootstrap_expires_epoch)]
    if cloudflared:
        command.extend(("--cloudflared", cloudflared))
    return command


def _spawn_review_daemon(bundle, port, cloudflared):
    bootstrap = secrets.token_urlsafe(32)
    bootstrap_digest = _sha256(bootstrap)
    bootstrap_expires_epoch = time.time() + BOOTSTRAP_TTL_SECONDS
    command = _remote_daemon_command(bundle, port, cloudflared, bootstrap_digest,
                                     bootstrap_expires_epoch)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Remove legacy diagnostic surfaces. The detached daemon emits no URL-bearing logs.
    for legacy_name in ("remote_daemon.stdout.log", "remote_daemon.stderr.log",
                        "remote_tunnel.log"):
        (bundle / legacy_name).unlink(missing_ok=True)
    kwargs: dict[str, Any] = {
        "cwd": str(Path(__file__).resolve().parent), "env": env,
        "stdin": subprocess.PIPE, "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.CREATE_NO_WINDOW | 0x01000000 |
                                     subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    try:
        if process.stdin is None:
            raise RuntimeError("secure bootstrap pipe was not created")
        process.stdin.write((bootstrap + "\n").encode("ascii"))
        process.stdin.flush()
    except Exception:
        _terminate_pid(process.pid)
        raise
    finally:
        if process.stdin is not None:
            process.stdin.close()
        del bootstrap
    return process, bootstrap_digest
