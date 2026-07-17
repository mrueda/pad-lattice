"""Codex CLI JSONL adapter for Pad-Lattice."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.protocol import (
    decode_message,
    encode_message,
    parse_action,
    send_message,
    state_message,
    subscribe_actions_message,
)

StateSender = Callable[[str, dict[str, Any]], None]


def state_for_codex_event(event: dict[str, Any]) -> AgentState | None:
    """Map documented `codex exec --json` events to Pad-Lattice states."""

    event_type = event.get("type")
    if event_type in {"thread.started", "turn.started", "item.started"}:
        return AgentState.RUNNING
    if event_type == "turn.completed":
        return AgentState.SUCCESS
    if event_type in {"turn.failed", "error"}:
        return AgentState.ERROR
    return None


def run_codex_exec(
    prompt: Sequence[str],
    socket_path: str,
    *,
    codex_binary: str = "codex",
    sender: StateSender = send_message,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run `codex exec --json` and mirror its state to Pad-Lattice."""

    if not prompt:
        raise ValueError("codex-exec requires a prompt")

    sender(socket_path, state_message(AgentState.RUNNING))
    process = subprocess.Popen(
        [codex_binary, "exec", "--json", *prompt],
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=True,
    )
    action_thread = threading.Thread(
        target=_stop_process_on_pad_action,
        args=(socket_path, process, stderr),
        daemon=True,
    )
    action_thread.start()

    assert process.stdout is not None
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(line, file=stdout, flush=True)
            continue

        state = state_for_codex_event(event)
        if state is not None:
            sender(socket_path, state_message(state))

        if event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    print(text, file=stdout, flush=True)
        elif event.get("type") == "error":
            print(json.dumps(event, separators=(",", ":")), file=stderr, flush=True)

    return_code = process.wait()
    if return_code != 0:
        sender(socket_path, state_message(AgentState.ERROR))
    return return_code


def _stop_process_on_pad_action(
    socket_path: str,
    process: subprocess.Popen[str],
    stderr: TextIO,
) -> None:
    """Terminate Codex when the daemon emits a stop action."""

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(socket_path)
            client.sendall(encode_message(subscribe_actions_message()))
            buffer = b""
            while process.poll() is None:
                data = client.recv(4096)
                if not data:
                    return
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        message = decode_message(line)
                        action = parse_action(message.get("action"))
                    except ValueError:
                        continue
                    if action is ControlAction.STOP and process.poll() is None:
                        print("pad-lattice: stop requested from Launchpad", file=stderr)
                        process.terminate()
                        return
    except OSError:
        return
