"""Read-only discovery on an existing local Codex app-server.

Listing never starts a server, resumes a thread, or subscribes to approvals.
Only summary metadata crosses the desktop IPC boundary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import time

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from pad_lattice import __version__

MAX_CONVERSATIONS = 64
DISCOVERY_TIMEOUT = 6.0


def control_socket() -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    return home / "app-server-control" / "app-server-control.sock"


def _summaries(connection, deadline: float) -> dict:
    sequence = 0

    def request(method, params):
        nonlocal sequence
        sequence += 1
        connection.send(json.dumps({"id": sequence, "method": method, "params": params}))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex discovery timed out")
            message = json.loads(connection.recv(timeout=remaining))
            if not isinstance(message, dict):
                raise ValueError("Invalid Codex response")
            if message.get("id") == sequence and "method" not in message:
                if "error" in message:
                    raise RuntimeError("Codex does not support conversation discovery")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise ValueError("Invalid Codex response")
                return result

    request("initialize", {"clientInfo": {"name": "pad_lattice_discovery", "version": __version__}})
    connection.send(json.dumps({"method": "initialized"}))
    conversations = []
    seen_ids = set()
    seen_cursors = set()
    cursor = None
    truncated = False
    while True:
        params = {"limit": MAX_CONVERSATIONS}
        if cursor:
            params["cursor"] = cursor
        page = request("thread/loaded/list", params)
        ids = page.get("data")
        if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
            raise ValueError("Invalid Codex conversation list")
        for thread_id in ids:
            if thread_id in seen_ids:
                continue
            if len(seen_ids) >= MAX_CONVERSATIONS:
                truncated = True
                break
            seen_ids.add(thread_id)
            thread = request("thread/read", {"threadId": thread_id, "includeTurns": False}).get("thread")
            if not isinstance(thread, dict):
                raise ValueError("Invalid Codex conversation summary")
            # Subagents, editor sessions, and saved history aren't CLI conversations.
            if thread.get("source") != "cli":
                continue
            status = thread.get("status", {})
            kind = status.get("type") if isinstance(status, dict) else None
            if kind == "notLoaded":
                continue
            flags = status.get("activeFlags", []) if isinstance(status, dict) else []
            state = {"idle": "idle", "systemError": "error", "active": "running"}.get(kind, "unknown")
            if kind == "active" and isinstance(flags, list):
                if "waitingOnApproval" in flags:
                    state = "approval"
                elif "waitingOnUserInput" in flags:
                    state = "waiting"
            cwd = thread.get("cwd")
            name = thread.get("name")
            conversations.append({"id": thread_id,
                                  "name": name[:256] if isinstance(name, str) and name else "Untitled conversation",
                                  "cwd": cwd[:4096] if isinstance(cwd, str) else "",
                                  "state": state})
        cursor = page.get("nextCursor")
        if not cursor:
            break
        if not isinstance(cursor, str) or cursor in seen_cursors:
            raise ValueError("Invalid Codex discovery cursor")
        seen_cursors.add(cursor)
        if truncated or len(seen_ids) >= MAX_CONVERSATIONS:
            truncated = True
            break
    return {"available": True, "conversations": sorted(conversations, key=lambda item: (item["name"].casefold(), item["id"])),
            "truncated": truncated}


def discover_conversations() -> dict:
    path = control_socket()
    try:
        info = path.stat()
    except FileNotFoundError:
        return {"available": False, "conversations": [], "error": "No local Codex app-server is running."}
    except OSError as exc:
        return {"available": False, "conversations": [], "error": f"Conversation discovery unavailable: {exc}"}
    try:
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Codex control socket must belong to the current user")
        deadline = time.monotonic() + DISCOVERY_TIMEOUT
        with unix_connect(str(path), uri="ws://localhost/", open_timeout=2,
                          close_timeout=0.2, max_size=1024 * 1024, compression=None) as connection:
            return _summaries(connection, deadline)
    except (OSError, ValueError, RuntimeError, WebSocketException) as exc:
        return {"available": False, "conversations": [], "error": f"Conversation discovery unavailable: {exc}"}
