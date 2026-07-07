"""Codex CLI JSONL adapter for Pad-Lattice."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from pad_lattice.events import AgentState
from pad_lattice.protocol import send_message, state_message

StateSender = Callable[[str, dict[str, str]], None]


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
