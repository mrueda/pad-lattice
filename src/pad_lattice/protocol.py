"""Pad-Lattice local JSON-line protocol."""

from __future__ import annotations

import json
import os
import socket
from typing import Any

from pad_lattice.events import DEFAULT_AGENT, AgentIdentity, AgentState, ControlAction


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


def state_message(
    state: AgentState,
    *,
    agent: AgentIdentity | dict[str, str] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"type": "state", "state": state.value}
    if agent:
        message["agent"] = encode_agent(agent)
    return message


def session_end_message(
    agent: AgentIdentity | dict[str, str],
) -> dict[str, Any]:
    return {"type": "session_end", "agent": encode_agent(agent)}


def status_message() -> dict[str, str]:
    return {"type": "status"}


def action_message(
    action: ControlAction,
    agent: AgentIdentity,
) -> dict[str, Any]:
    return {
        "type": "action",
        "action": action.value,
        "agent": encode_agent(agent),
    }


def subscribe_actions_message(
    agent: AgentIdentity = DEFAULT_AGENT,
    actions: tuple[ControlAction, ...] | None = None,
) -> dict[str, Any]:
    selected_actions = actions or tuple(ControlAction)
    return {
        "type": "subscribe_actions",
        "agent": encode_agent(agent),
        "actions": [action.value for action in selected_actions],
    }


def parse_state(value: Any) -> AgentState:
    try:
        return AgentState(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"unknown state: {value}") from exc


def parse_action(value: Any) -> ControlAction:
    try:
        return ControlAction(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"unknown action: {value}") from exc


def encode_agent(agent: AgentIdentity | dict[str, str]) -> dict[str, str]:
    if isinstance(agent, AgentIdentity):
        return {"backend": agent.backend, "session_id": agent.session_id}
    return dict(agent)


def parse_agent(value: Any, *, default: AgentIdentity | None = DEFAULT_AGENT) -> AgentIdentity:
    if value is None and default is not None:
        return default
    if not isinstance(value, dict):
        raise ProtocolError("agent must be a JSON object")
    backend = value.get("backend")
    session_id = value.get("session_id")
    if not isinstance(backend, str) or not backend:
        raise ProtocolError("agent.backend must be a non-empty string")
    if not isinstance(session_id, str) or not session_id:
        raise ProtocolError("agent.session_id must be a non-empty string")
    return AgentIdentity(backend, session_id)


def parse_actions(value: Any) -> frozenset[ControlAction]:
    if not isinstance(value, list) or not value:
        raise ProtocolError("actions must be a non-empty JSON array")
    try:
        return frozenset(ControlAction(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("actions contains an unknown control action") from exc


def send_message(socket_path: str, message: dict[str, Any]) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(encode_message(message))


def request_message(
    socket_path: str,
    message: dict[str, Any],
    *,
    timeout: float = 2.0,
) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        client.sendall(encode_message(message))
        buffer = b""
        while b"\n" not in buffer:
            data = client.recv(4096)
            if not data:
                raise ConnectionError("daemon closed the connection without a response")
            buffer += data
        line, _ = buffer.split(b"\n", 1)
        return decode_message(line)
