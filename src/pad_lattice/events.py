"""Agent-agnostic event and control types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentState(str, Enum):
    """High-level states rendered by the Launchpad MVP."""

    RUNNING = "running"
    WAITING_FOR_REPLY = "waiting_for_reply"
    USER_TYPING = "user_typing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    SUCCESS = "success"
    ERROR = "error"


class ControlAction(str, Enum):
    """Hardware controls emitted by the Launchpad MVP."""

    APPROVE = "approve"
    REJECT = "reject"
    STOP = "stop"
    RETRY = "retry"


@dataclass(frozen=True)
class AgentIdentity:
    """Stable identity supplied by an agent integration."""

    backend: str
    session_id: str


DEFAULT_AGENT = AgentIdentity("local", "default")


@dataclass(frozen=True)
class AgentEvent:
    """A state update from any supported coding agent backend."""

    state: AgentState
    agent: AgentIdentity = DEFAULT_AGENT
    detail: str = ""
