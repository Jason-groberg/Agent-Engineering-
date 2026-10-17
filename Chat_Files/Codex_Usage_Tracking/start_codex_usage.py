"""Start one Codex usage tracker terminal per conversation on Windows.

Run from Chat_Files: python Codex_Usage_Tracking/start_codex_usage.py
Use --session SESSION_ID to attach to a specific Codex conversation.
Use --status to check whether the tracker is already running without opening one.
"""

import ctypes
import hashlib
import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

from codex_usage_tracker import CODEX_DIR, PROJECT, TRACKING_DIR, find_session, session_meta


RUNTIME_DIR = TRACKING_DIR / ".runtime"


def process_identity(pid):
    if not isinstance(pid, int) or pid <= 0:
        return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
            return None
        return (created.dwHighDateTime << 32) | created.dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def tracker_running(state):
    identity = process_identity(state.get("pid"))
    return identity is not None and identity == state.get("created")


def start_tracker(session, status_only=False):
    if os.name != "nt":
        raise ValueError("Automatic terminal launching requires Windows. Run codex_usage_tracker.py manually on other systems.")
    import msvcrt
    meta = session_meta(session)
    session_id = meta.get("id", meta.get("session_id")) or str(session.resolve())
    key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    state_file = RUNTIME_DIR / (key + ".json")
    lock_file = RUNTIME_DIR / (key + ".lock")
    # Hold a short file lock so simultaneous startup calls cannot open two windows.
    with lock_file.open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return "Usage tracker startup check already in progress."
        try:
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
            if isinstance(state, dict) and tracker_running(state):
                return f"Usage tracker already running for session {session_id} (PID {state['pid']})."
            if status_only:
                return f"Usage tracker is not running for session {session_id}."
            command = [sys.executable, "-B", "-u", str(TRACKING_DIR / "codex_usage_tracker.py"),
                       "--session", str(session.resolve()), "--workspace", str(PROJECT)]
            # A separate visible console lets the user press Ctrl+C and enter a filename.
            child = subprocess.Popen(command, cwd=PROJECT, creationflags=subprocess.CREATE_NEW_CONSOLE,
                                     close_fds=True)
            created = process_identity(child.pid)
            if created is None:
                raise OSError("Tracker process exited before startup could be confirmed.")
            state_file.write_text(json.dumps({"session_id": session_id, "pid": child.pid,
                                             "created": created, "log": str(session)}), encoding="utf-8")
            return f"Started usage tracker terminal for session {session_id} (PID {child.pid})."
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="Exact Codex session ID or JSONL path")
    parser.add_argument("--workspace", type=Path, default=PROJECT)
    parser.add_argument("--status", action="store_true", help="Check tracking without starting a new terminal")
    args = parser.parse_args()
    try:
        selection = args.session or os.environ.get("CODEX_THREAD_ID")
        session = find_session(CODEX_DIR / "sessions", args.workspace, selection)
        print(start_tracker(session, args.status))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"Usage tracker could not start: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
