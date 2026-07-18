"""Typed Pad-Lattice JSON-line wire protocol."""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
from typing import Any, TypeAlias

from pad_lattice.events import DEFAULT_AGENT, AgentIdentity, AgentState, ControlAction

WIRE_PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 64 * 1024
MAX_PREVIEW_TTL = 30.0


class ProtocolError(ValueError):
    """Raised for invalid Pad-Lattice protocol messages."""

    def __init__(self, message: str, *, code: str = "invalid_message") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StateCommand:
    agent: AgentIdentity
    state: AgentState
    metadata: dict[str, str]
    lease_id: str | None
    reply: bool


@dataclass(frozen=True)
class SessionEndCommand:
    agent: AgentIdentity


@dataclass(frozen=True)
class StatusCommand:
    pass


@dataclass(frozen=True)
class PingCommand:
    pass


@dataclass(frozen=True)
class SessionLeaseCommand:
    lease_id: str
    agent: AgentIdentity | None
    metadata: dict[str, str]


@dataclass(frozen=True)
class SubscribeActionsCommand:
    agent: AgentIdentity
    actions: frozenset[ControlAction]
    request_id: str | None
    one_shot: bool


@dataclass(frozen=True)
class PreviewCommand:
    preview_id: str
    state: AgentState
    ttl: float


@dataclass(frozen=True)
class PreviewEndCommand:
    preview_id: str


@dataclass(frozen=True)
class ActionEvent:
    agent: AgentIdentity
    action: ControlAction
    request_id: str | None


ClientCommand: TypeAlias = (
    StateCommand
    | SessionEndCommand
    | StatusCommand
    | PingCommand
    | SessionLeaseCommand
    | SubscribeActionsCommand
    | PreviewCommand
    | PreviewEndCommand
)


class JsonLineConnection:
    """Blocking, bounded JSON-line connection for long-lived clients."""

    def __init__(
        self,
        client: socket.socket,
        *,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ) -> None:
        if max_message_bytes < 1:
            raise ValueError("max_message_bytes must be positive")
        self.client = client
        self.max_message_bytes = max_message_bytes
        self._buffer = b""

    def send(self, message: dict[str, Any]) -> None:
        self.client.sendall(encode_message(message))

    def receive(self) -> dict[str, Any]:
        while b"\n" not in self._buffer:
            data = self.client.recv(4096)
            if not data:
                raise ConnectionError("daemon closed the connection without a response")
            self._buffer += data
            if len(self._buffer) > self.max_message_bytes:
                raise ProtocolError(
                    "protocol message exceeds the size limit",
                    code="frame_too_large",
                )
        line, self._buffer = self._buffer.split(b"\n", 1)
        if len(line) > self.max_message_bytes:
            raise ProtocolError(
                "protocol message exceeds the size limit",
                code="frame_too_large",
            )
        return decode_message(line)

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.send(message)
        return self.receive()


@contextmanager
def open_message_connection(
    socket_path: str,
    *,
    timeout: float | None = 2.0,
) -> Iterator[JsonLineConnection]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        yield JsonLineConnection(client)


def default_socket_path() -> str:
    if path := os.environ.get("PAD_LATTICE_SOCKET"):
        return path
    if runtime_dir := os.environ.get("XDG_RUNTIME_DIR"):
        return os.path.join(runtime_dir, "pad-lattice.sock")
    return os.path.join("/tmp", f"pad-lattice-{os.getuid()}.sock")


def load_protocol_schema() -> dict[str, Any]:
    """Load the packaged machine-readable socket protocol schema."""

    schema = resources.files("pad_lattice").joinpath(
        "schemas", "socket-protocol-v1.json"
    )
    return json.loads(schema.read_text(encoding="utf-8"))


def wire_message(message_type: str, **fields: Any) -> dict[str, Any]:
    return {
        "protocol": WIRE_PROTOCOL_VERSION,
        "type": message_type,
        **fields,
    }


def encode_message(message: dict[str, Any]) -> bytes:
    validate_protocol_version(message)
    encoded = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES + 1:
        raise ProtocolError(
            "protocol message exceeds the size limit",
            code="frame_too_large",
        )
    return encoded


def decode_message(line: bytes) -> dict[str, Any]:
    if len(line) > MAX_MESSAGE_BYTES:
        raise ProtocolError(
            "protocol message exceeds the size limit",
            code="frame_too_large",
        )
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid JSON message") from exc
    if not isinstance(message, dict):
        raise ProtocolError("protocol message must be a JSON object")
    validate_protocol_version(message)
    return message


def validate_protocol_version(message: dict[str, Any]) -> None:
    version = message.get("protocol")
    if version != WIRE_PROTOCOL_VERSION or isinstance(version, bool):
        raise ProtocolError(
            f"unsupported wire protocol {version!r}; expected {WIRE_PROTOCOL_VERSION}",
            code="unsupported_protocol",
        )


def state_message(
    state: AgentState,
    *,
    agent: AgentIdentity | dict[str, str] | None = None,
    lease_id: str | None = None,
    reply: bool = False,
) -> dict[str, Any]:
    fields: dict[str, Any] = {"state": state.value}
    if agent:
        fields["agent"] = encode_agent(agent)
    if lease_id:
        fields["lease_id"] = lease_id
    if reply:
        fields["reply"] = True
    return wire_message("state", **fields)


def session_end_message(
    agent: AgentIdentity | dict[str, str],
) -> dict[str, Any]:
    return wire_message("session_end", agent=encode_agent(agent))


def status_message() -> dict[str, Any]:
    return wire_message("status")


def ping_message() -> dict[str, Any]:
    return wire_message("ping")


def session_lease_message(
    lease_id: str,
    *,
    agent: AgentIdentity | dict[str, str] | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {"lease_id": lease_id}
    if agent is not None:
        fields["agent"] = encode_agent(agent)
    if metadata:
        fields["metadata"] = dict(metadata)
    return wire_message("session_lease", **fields)


def action_message(
    action: ControlAction,
    agent: AgentIdentity,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "action": action.value,
        "agent": encode_agent(agent),
    }
    if request_id:
        fields["request_id"] = request_id
    return wire_message("action", **fields)


def subscribe_actions_message(
    agent: AgentIdentity = DEFAULT_AGENT,
    actions: tuple[ControlAction, ...] | None = None,
    *,
    request_id: str | None = None,
    one_shot: bool = False,
) -> dict[str, Any]:
    selected_actions = actions or tuple(ControlAction)
    fields: dict[str, Any] = {
        "agent": encode_agent(agent),
        "actions": [action.value for action in selected_actions],
    }
    if request_id:
        fields["request_id"] = request_id
    if one_shot:
        fields["one_shot"] = True
    return wire_message("subscribe_actions", **fields)


def preview_message(
    state: AgentState,
    preview_id: str,
    *,
    ttl: float,
) -> dict[str, Any]:
    return wire_message(
        "preview",
        preview_id=preview_id,
        state=state.value,
        ttl=ttl,
    )


def preview_end_message(preview_id: str) -> dict[str, Any]:
    return wire_message("preview_end", preview_id=preview_id)


def error_message(error: ProtocolError) -> dict[str, Any]:
    return wire_message("error", code=error.code, error=str(error))


def parse_client_command(message: dict[str, Any]) -> ClientCommand:
    validate_protocol_version(message)
    message_type = message.get("type")
    if message_type == "state":
        _reject_unknown_fields(
            message,
            {"protocol", "type", "state", "agent", "lease_id", "reply"},
        )
        agent_value = message.get("agent")
        return StateCommand(
            agent=parse_agent(agent_value),
            state=parse_state(message.get("state")),
            metadata=parse_agent_metadata(agent_value),
            lease_id=parse_identifier(
                message.get("lease_id"), field="lease_id", default=None
            ),
            reply=parse_boolean(message.get("reply"), field="reply"),
        )
    if message_type == "session_end":
        _reject_unknown_fields(message, {"protocol", "type", "agent"})
        return SessionEndCommand(parse_agent(message.get("agent"), default=None))
    if message_type == "status":
        _reject_unknown_fields(message, {"protocol", "type"})
        return StatusCommand()
    if message_type == "ping":
        _reject_unknown_fields(message, {"protocol", "type"})
        return PingCommand()
    if message_type == "session_lease":
        _reject_unknown_fields(
            message,
            {"protocol", "type", "lease_id", "agent", "metadata"},
        )
        lease_id = parse_identifier(message.get("lease_id"), field="lease_id")
        assert lease_id is not None
        agent = (
            parse_agent(message.get("agent"), default=None)
            if message.get("agent") is not None
            else None
        )
        return SessionLeaseCommand(
            lease_id=lease_id,
            agent=agent,
            metadata=parse_metadata(message.get("metadata")),
        )
    if message_type == "subscribe_actions":
        _reject_unknown_fields(
            message,
            {
                "protocol",
                "type",
                "agent",
                "actions",
                "request_id",
                "one_shot",
            },
        )
        return SubscribeActionsCommand(
            agent=parse_agent(message.get("agent")),
            actions=parse_actions(message.get("actions")),
            request_id=parse_identifier(
                message.get("request_id"), field="request_id", default=None
            ),
            one_shot=parse_boolean(message.get("one_shot"), field="one_shot"),
        )
    if message_type == "preview":
        _reject_unknown_fields(
            message,
            {"protocol", "type", "preview_id", "state", "ttl"},
        )
        preview_id = parse_identifier(message.get("preview_id"), field="preview_id")
        assert preview_id is not None
        return PreviewCommand(
            preview_id=preview_id,
            state=parse_state(message.get("state")),
            ttl=parse_preview_ttl(message.get("ttl")),
        )
    if message_type == "preview_end":
        _reject_unknown_fields(message, {"protocol", "type", "preview_id"})
        preview_id = parse_identifier(message.get("preview_id"), field="preview_id")
        assert preview_id is not None
        return PreviewEndCommand(preview_id)
    raise ProtocolError(
        f"unknown message type: {message_type}",
        code="unknown_message_type",
    )


def parse_action_event(message: dict[str, Any]) -> ActionEvent:
    validate_protocol_version(message)
    if message.get("type") != "action":
        raise ProtocolError(
            f"expected action message, got {message.get('type')!r}",
            code="unexpected_message_type",
        )
    _reject_unknown_fields(
        message,
        {"protocol", "type", "agent", "action", "request_id"},
    )
    return ActionEvent(
        agent=parse_agent(message.get("agent"), default=None),
        action=parse_action(message.get("action")),
        request_id=parse_identifier(
            message.get("request_id"), field="request_id", default=None
        ),
    )


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


def parse_agent(
    value: Any,
    *,
    default: AgentIdentity | None = DEFAULT_AGENT,
) -> AgentIdentity:
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


def parse_agent_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    metadata: dict[str, str] = {}
    for key, item in value.items():
        if key in {"backend", "session_id"}:
            continue
        if not isinstance(key, str) or not key:
            raise ProtocolError("agent metadata keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ProtocolError("agent metadata values must be non-empty strings")
        metadata[key] = item
    return metadata


def parse_actions(value: Any) -> frozenset[ControlAction]:
    if not isinstance(value, list) or not value:
        raise ProtocolError("actions must be a non-empty JSON array")
    try:
        return frozenset(ControlAction(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("actions contains an unknown control action") from exc


def parse_identifier(
    value: Any,
    *,
    field: str,
    default: str | None = None,
) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{field} must be a non-empty string")
    return value


def parse_metadata(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProtocolError("metadata must be a JSON object")
    metadata: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ProtocolError("metadata keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ProtocolError("metadata values must be non-empty strings")
        metadata[key] = item
    return metadata


def _reject_unknown_fields(message: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(message) - allowed)
    if unknown:
        raise ProtocolError(f"unknown field: {unknown[0]}")


def parse_boolean(value: Any, *, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ProtocolError(f"{field} must be a boolean")
    return value


def parse_preview_ttl(value: Any) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0 < float(value) <= MAX_PREVIEW_TTL
    ):
        raise ProtocolError(
            f"ttl must be greater than zero and at most {MAX_PREVIEW_TTL:g}"
        )
    return float(value)


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
    with open_message_connection(socket_path, timeout=timeout) as connection:
        return connection.request(message)
