"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any
from review_auth import _sha256


def _find_cloudflared(explicit: str = "") -> Path:
    candidates = [explicit, shutil.which("cloudflared") or ""]
    if os.name == "nt":
        candidates += [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "cloudflared", "cloudflared.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "cloudflared", "cloudflared.exe"),
        ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError("cloudflared not found; install it before using remote review")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p,
                                                ctypes.POINTER(ctypes.c_ulong)]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                        and exit_code.value == 259)  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, SystemError):
        return False
    return True


def _process_identity(pid: int) -> dict[str, Any]:
    """Return enough immutable process identity to reject recycled PIDs."""
    if not _pid_alive(pid):
        return {}
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.GetProcessTimes.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),
            ]
            kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return {}
            try:
                created, exited = wintypes.FILETIME(), wintypes.FILETIME()
                kernel, user = wintypes.FILETIME(), wintypes.FILETIME()
                if not kernel32.GetProcessTimes(handle, ctypes.byref(created),
                                                ctypes.byref(exited), ctypes.byref(kernel),
                                                ctypes.byref(user)):
                    return {}
                size = ctypes.c_ulong(32768)
                image = ctypes.create_unicode_buffer(size.value)
                if not kernel32.QueryFullProcessImageNameW(handle, 0, image,
                                                           ctypes.byref(size)):
                    return {}
                ticks = (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
                executable = os.path.normcase(os.path.realpath(image.value))
                return {"pid": pid, "start_marker": str(ticks),
                        "executable_fingerprint": _sha256(executable)[:32]}
            finally:
                kernel32.CloseHandle(handle)
        proc = Path("/proc") / str(pid)
        if proc.is_dir():
            stat = (proc / "stat").read_text(encoding="utf-8")
            tail = stat[stat.rfind(")") + 2:].split()
            executable = str((proc / "exe").resolve())
            return {"pid": pid, "start_marker": tail[19],
                    "executable_fingerprint": _sha256(executable)[:32]}
        marker = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "comm="],
            text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
        return {"pid": pid, "start_marker": marker,
                "executable_fingerprint": _sha256(marker.split()[-1])[:32]}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return {}


def _process_identity_matches(expected: Any) -> bool:
    if not isinstance(expected, dict):
        return False
    try:
        pid = int(expected.get("pid", 0))
    except (TypeError, ValueError):
        return False
    current = _process_identity(pid)
    return bool(current and str(current.get("start_marker")) == str(expected.get("start_marker"))
                and str(current.get("executable_fingerprint", "")) ==
                str(expected.get("executable_fingerprint", "")))


def _terminate_pid(pid: int) -> bool:
    if not _pid_alive(pid):
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if not handle:
            return False
        try:
            return bool(kernel32.TerminateProcess(handle, 0))
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except (OSError, SystemError):
        return False
