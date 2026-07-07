"""Pad-Lattice local JSON-line protocol."""

from __future__ import annotations

import json
import os
import socket
from typing import Any

from pad_lattice.events import AgentState, ControlAction


class ProtocolError(ValueError):
    """Raised for invalid Pad-Lattice protocol messages."""


def default_socket_path() -> str:
    if path := os.environ.get("PAD_LATTICE_SOCKET"):
        return path
    if runtime_dir := os.environ.get("XDG_RUNTIME_DIR"):
        return os.path.join(runtime_dir, "pad-lattice.sock")
    return os.path.join("/tmp", f"pad-lattice-{os.getuid()}.sock")


def encode_message(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(line: bytes) -> dict[str, Any]:
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid JSON message") from exc
    if not isinstance(message, dict):
        raise ProtocolError("protocol message must be a JSON object")
    return message


def state_message(state: AgentState) -> dict[str, str]:
    return {"type": "state", "state": state.value}


def action_message(action: ControlAction) -> dict[str, str]:
    return {"type": "action", "action": action.value}


def subscribe_actions_message() -> dict[str, str]:
    return {"type": "subscribe_actions"}


def parse_state(value: Any) -> AgentState:
    try:
        return AgentState(value)
    except ValueError as exc:
        raise ProtocolError(f"unknown state: {value}") from exc


def parse_action(value: Any) -> ControlAction:
    try:
        return ControlAction(value)
    except ValueError as exc:
        raise ProtocolError(f"unknown action: {value}") from exc


def send_message(socket_path: str, message: dict[str, Any]) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(encode_message(message))
