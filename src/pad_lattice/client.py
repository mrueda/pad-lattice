"""Public client API for agent integrations."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from types import TracebackType
from typing import Any

from pad_lattice.events import DEFAULT_AGENT, AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    ActionEvent,
    JsonLineConnection,
    ProtocolError,
    default_socket_path,
    parse_action_event,
    ping_message,
    request_message,
    send_message,
    session_end_message,
    state_message,
    status_message,
    subscribe_actions_message,
)


class PadLatticeClient:
    """Report agent state and inspect one local Pad-Lattice daemon."""

    def __init__(
        self,
        socket_path: str | None = None,
        *,
        timeout: float = 2.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.socket_path = socket_path or default_socket_path()
        self.timeout = timeout

    def report_state(
        self,
        state: AgentState,
        *,
        agent: AgentIdentity = DEFAULT_AGENT,
        metadata: dict[str, str] | None = None,
        lease_id: str | None = None,
        reply: bool = False,
    ) -> dict[str, Any] | None:
        agent_payload = {
            "backend": agent.backend,
            "session_id": agent.session_id,
            **(metadata or {}),
        }
        message = state_message(
            state,
            agent=agent_payload,
            lease_id=lease_id,
            reply=reply,
        )
        if reply:
            return request_message(
                self.socket_path,
                message,
                timeout=self.timeout,
            )
        send_message(self.socket_path, message)
        return None

    def end_session(self, agent: AgentIdentity = DEFAULT_AGENT) -> None:
        send_message(self.socket_path, session_end_message(agent))

    def status(self) -> dict[str, Any]:
        response = request_message(
            self.socket_path,
            status_message(),
            timeout=self.timeout,
        )
        _expect_type(response, "status")
        return response

    def ping(self) -> None:
        response = request_message(
            self.socket_path,
            ping_message(),
            timeout=self.timeout,
        )
        _expect_type(response, "pong")

    def subscribe_actions(
        self,
        agent: AgentIdentity = DEFAULT_AGENT,
        actions: tuple[ControlAction, ...] | None = None,
        *,
        request_id: str | None = None,
        one_shot: bool = False,
        timeout: float | None = None,
    ) -> "ActionSubscription":
        return ActionSubscription(
            self.socket_path,
            agent,
            actions,
            request_id=request_id,
            one_shot=one_shot,
            timeout=timeout,
        )


class ActionSubscription:
    """Context-managed stream of actions targeted to one agent identity."""

    def __init__(
        self,
        socket_path: str,
        agent: AgentIdentity,
        actions: tuple[ControlAction, ...] | None,
        *,
        request_id: str | None,
        one_shot: bool,
        timeout: float | None,
    ) -> None:
        self.socket_path = socket_path
        self.agent = agent
        self.actions = actions
        self.request_id = request_id
        self.one_shot = one_shot
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._connection: JsonLineConnection | None = None

    def __enter__(self) -> "ActionSubscription":
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(self.timeout)
            client.connect(self.socket_path)
            connection = JsonLineConnection(client)
            connection.send(
                subscribe_actions_message(
                    self.agent,
                    self.actions,
                    request_id=self.request_id,
                    one_shot=self.one_shot,
                )
            )
        except BaseException:
            client.close()
            raise
        self._socket = client
        self._connection = connection
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __iter__(self) -> Iterator[ActionEvent]:
        while True:
            yield self.receive()

    def receive(self) -> ActionEvent:
        if self._connection is None:
            raise RuntimeError("action subscription is not open")
        message = self._connection.receive()
        if message.get("type") == "error":
            raise ProtocolError(
                str(message.get("error", "daemon rejected the subscription")),
                code=str(message.get("code", "daemon_error")),
            )
        return parse_action_event(message)

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
        self._socket = None
        self._connection = None


def _expect_type(message: dict[str, Any], expected: str) -> None:
    if message.get("type") == "error":
        raise ProtocolError(
            str(message.get("error", "daemon rejected the request")),
            code=str(message.get("code", "daemon_error")),
        )
    if message.get("type") != expected:
        raise ProtocolError(
            f"expected {expected!r}, got {message.get('type')!r}",
            code="unexpected_message_type",
        )
