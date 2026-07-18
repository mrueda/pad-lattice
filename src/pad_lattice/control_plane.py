"""Deterministic multi-agent state machine for Pad-Lattice."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

from pad_lattice.devices.base import SessionIndicator, SurfaceView
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.visual_protocol import IDENTITY_ACCENTS

DEFAULT_SESSION_TTL = 24 * 60 * 60.0
TERMINAL_STATES = frozenset(
    {AgentState.SUCCESS, AgentState.ERROR, AgentState.CANCELLED}
)
ACTION_STATES: dict[ControlAction, frozenset[AgentState]] = {
    ControlAction.APPROVE: frozenset({AgentState.WAITING_FOR_APPROVAL}),
    ControlAction.REJECT: frozenset({AgentState.WAITING_FOR_APPROVAL}),
    ControlAction.RETRY: frozenset({AgentState.ERROR, AgentState.CANCELLED}),
    ControlAction.STOP: frozenset({AgentState.RUNNING}),
}


class AccentPreferenceStore(Protocol):
    def preferred_accent(self, identity: AgentIdentity) -> str | None: ...

    def remember(self, identity: AgentIdentity, accent: str) -> None: ...


class ControlPlaneError(ValueError):
    """Raised when a domain command conflicts with current ownership."""

    def __init__(self, message: str, *, code: str = "invalid_operation") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class AgentSession:
    identity: AgentIdentity
    state: AgentState = AgentState.WAITING_FOR_REPLY
    slot: int | None = None
    accent: str | None = None
    last_seen: int = 0
    last_activity_at: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)
    terminal_state_until: float | None = None


@dataclass
class ActionSubscription:
    client_id: int
    agent: AgentIdentity
    actions: frozenset[ControlAction]
    request_id: str | None
    one_shot: bool
    subscribed_at: int


@dataclass(frozen=True)
class ActionDispatch:
    client_id: int
    agent: AgentIdentity
    action: ControlAction
    request_id: str | None


@dataclass(frozen=True)
class Preview:
    client_id: int
    preview_id: str
    state: AgentState
    expires_at: float


class ControlPlane:
    """Apply agent and surface events without performing socket or MIDI I/O."""

    def __init__(
        self,
        selector_capacity: int,
        accent_names: tuple[str, ...],
        *,
        terminal_hold: float = 2.0,
        action_debounce: float = 0.25,
        session_ttl: float = DEFAULT_SESSION_TTL,
        identity_store: AccentPreferenceStore | None = None,
    ) -> None:
        if selector_capacity < 1:
            raise ValueError("selector_capacity must be positive")
        if len(accent_names) != selector_capacity:
            raise ValueError("provide one accent per selector slot")
        if len(set(accent_names)) != len(accent_names):
            raise ValueError("accent names must be unique")
        if accent_names != IDENTITY_ACCENTS[:selector_capacity]:
            raise ValueError(
                "accent names must use the Visual Protocol identity order"
            )
        if terminal_hold < 0:
            raise ValueError("terminal_hold must be zero or positive")
        if action_debounce < 0:
            raise ValueError("action_debounce must be zero or positive")
        if session_ttl < 0:
            raise ValueError("session_ttl must be zero or positive")

        self.selector_capacity = selector_capacity
        self.accent_names = accent_names
        self.terminal_hold = terminal_hold
        self.action_debounce = action_debounce
        self.session_ttl = session_ttl
        self.identity_store = identity_store
        self._sessions: dict[AgentIdentity, AgentSession] = {}
        self._slots: list[AgentIdentity | None] = [None] * selector_capacity
        self._selected_agent: AgentIdentity | None = None
        self._subscriptions: dict[int, ActionSubscription] = {}
        self._lease_clients: dict[str, int] = {}
        self._client_leases: dict[int, str] = {}
        self._lease_agents: dict[str, AgentIdentity] = {}
        self._lease_metadata: dict[str, dict[str, str]] = {}
        self._last_action_at: dict[tuple[AgentIdentity, ControlAction], float] = {}
        self._preview: Preview | None = None
        self._sequence = 0
        self._revision = 0

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def state(self) -> AgentState | None:
        session = self.selected_session
        return session.state if session is not None else None

    @property
    def selected_agent(self) -> AgentIdentity | None:
        return self._selected_agent

    @property
    def selected_session(self) -> AgentSession | None:
        if self._selected_agent is None:
            return None
        return self._sessions.get(self._selected_agent)

    @property
    def sessions(self) -> tuple[AgentSession, ...]:
        return tuple(
            sorted(self._sessions.values(), key=lambda session: session.last_seen)
        )

    @property
    def preview(self) -> Preview | None:
        return self._preview

    @property
    def overflow_count(self) -> int:
        return sum(session.slot is None for session in self._sessions.values())

    def update_agent(
        self,
        identity: AgentIdentity,
        state: AgentState,
        *,
        now: float,
        metadata: dict[str, str] | None = None,
    ) -> AgentSession:
        session = self._ensure_session(identity, now)
        self._sequence += 1
        session.last_seen = self._sequence
        session.last_activity_at = now
        session.state = (
            AgentState.WAITING_FOR_APPROVAL
            if state is not AgentState.WAITING_FOR_APPROVAL
            and self._has_pending_approval(identity)
            else state
        )
        if metadata:
            session.metadata.update(metadata)
        session.terminal_state_until = (
            now + self.terminal_hold if session.state in TERMINAL_STATES else None
        )
        if session.slot is None:
            self._assign_slot(session)
        self._changed()
        return session

    def end_agent(self, identity: AgentIdentity) -> bool:
        changed = self._end_agent(identity)
        if changed:
            self._changed()
        return changed

    def select_slot(self, slot: int, *, now: float) -> bool:
        if not 0 <= slot < len(self._slots):
            return False
        identity = self._slots[slot]
        if identity is None:
            return False
        self._selected_agent = identity
        self._sequence += 1
        session = self._sessions[identity]
        session.last_seen = self._sequence
        session.last_activity_at = now
        self._changed()
        return True

    def subscribe(
        self,
        client_id: int,
        agent: AgentIdentity,
        actions: frozenset[ControlAction],
        *,
        request_id: str | None,
        one_shot: bool,
        now: float,
    ) -> None:
        session = self._ensure_session(agent, now)
        self._sequence += 1
        session.last_seen = self._sequence
        session.last_activity_at = now
        self._subscriptions[client_id] = ActionSubscription(
            client_id=client_id,
            agent=agent,
            actions=actions,
            request_id=request_id,
            one_shot=one_shot,
            subscribed_at=self._sequence,
        )
        self._changed()

    def register_lease(
        self,
        client_id: int,
        lease_id: str,
        *,
        agent: AgentIdentity | None,
        metadata: dict[str, str],
        now: float,
    ) -> AgentSession | None:
        previous_lease = self._client_leases.get(client_id)
        if previous_lease is not None and previous_lease != lease_id:
            self._release_lease(previous_lease, client_id)

        previous_client = self._lease_clients.get(lease_id)
        if previous_client is not None and previous_client != client_id:
            self._client_leases.pop(previous_client, None)
        self._lease_clients[lease_id] = client_id
        self._client_leases[client_id] = lease_id
        self._lease_metadata[lease_id] = dict(metadata)

        session: AgentSession | None = None
        if agent is not None:
            session = self._bind_lease(lease_id, agent, metadata, now=now)
        elif identity := self._lease_agents.get(lease_id):
            session = self._sessions.get(identity)
            if session is not None and metadata:
                session.metadata.update(metadata)
                session.last_activity_at = now
        self._changed()
        return session

    def bind_lease(
        self,
        lease_id: str,
        identity: AgentIdentity,
        metadata: dict[str, str],
        *,
        now: float,
    ) -> tuple[AgentSession, int | None]:
        session = self._bind_lease(lease_id, identity, metadata, now=now)
        self._changed()
        return session, self._lease_clients.get(lease_id)

    def set_preview(
        self,
        client_id: int,
        preview_id: str,
        state: AgentState,
        *,
        expires_at: float,
    ) -> None:
        if self._preview is not None and self._preview.client_id != client_id:
            raise ControlPlaneError(
                "surface preview is already owned by another client",
                code="preview_conflict",
            )
        if self._preview is not None and self._preview.preview_id != preview_id:
            raise ControlPlaneError(
                "client already owns a different surface preview",
                code="preview_conflict",
            )
        self._preview = Preview(client_id, preview_id, state, expires_at)
        self._changed()

    def end_preview(self, client_id: int, preview_id: str) -> None:
        if (
            self._preview is None
            or self._preview.client_id != client_id
            or self._preview.preview_id != preview_id
        ):
            raise ControlPlaneError(
                "surface preview is not owned by this client",
                code="preview_not_owned",
            )
        self._preview = None
        self._changed()

    def disconnect(self, client_id: int) -> None:
        changed = self._subscriptions.pop(client_id, None) is not None
        lease_id = self._client_leases.pop(client_id, None)
        if lease_id is not None and self._lease_clients.get(lease_id) == client_id:
            changed = self._release_lease(lease_id, client_id) or changed
        if self._preview is not None and self._preview.client_id == client_id:
            self._preview = None
            changed = True
        if changed:
            self._changed()

    def dispatch_action(
        self,
        action: ControlAction,
        *,
        now: float,
    ) -> ActionDispatch | None:
        identity = self._selected_agent
        if identity is None or action not in self.available_actions():
            return None
        recipients = sorted(
            (
                subscription
                for subscription in self._subscriptions.values()
                if subscription.agent == identity
                and action in subscription.actions
            ),
            key=lambda subscription: (
                subscription.request_id is None,
                subscription.subscribed_at,
            ),
        )
        if not recipients:
            return None

        debounce_key = (identity, action)
        last_action_at = self._last_action_at.get(debounce_key)
        if (
            last_action_at is not None
            and now - last_action_at < self.action_debounce
        ):
            return None
        self._last_action_at[debounce_key] = now
        session = self._sessions.get(identity)
        if session is not None:
            self._sequence += 1
            session.last_seen = self._sequence
            session.last_activity_at = now

        recipient = recipients[0]
        dispatch = ActionDispatch(
            client_id=recipient.client_id,
            agent=identity,
            action=action,
            request_id=recipient.request_id,
        )
        if recipient.one_shot:
            recipient.actions = frozenset()
            recipient.request_id = None
            recipient.one_shot = False
        self._changed()
        return dispatch

    def available_actions(self) -> frozenset[ControlAction]:
        if self._preview is not None:
            return frozenset()
        identity = self._selected_agent
        session = self.selected_session
        if identity is None or session is None:
            return frozenset()
        return frozenset(
            action
            for subscription in self._subscriptions.values()
            if subscription.agent == identity
            for action in subscription.actions
            if session.state in ACTION_STATES[action]
        )

    def tick(self, *, now: float) -> bool:
        changed = False
        if self._preview is not None and now >= self._preview.expires_at:
            self._preview = None
            changed = True

        for session in self._sessions.values():
            if (
                session.terminal_state_until is not None
                and now >= session.terminal_state_until
            ):
                session.state = AgentState.WAITING_FOR_REPLY
                session.terminal_state_until = None
                changed = True

        if self.session_ttl:
            expired = [
                session.identity
                for session in self._sessions.values()
                if not self.is_leased(session.identity)
                and now - session.last_activity_at >= self.session_ttl
            ]
            for identity in expired:
                changed = self._end_agent(identity) or changed

        if changed:
            self._changed()
        return changed

    def is_leased(self, identity: AgentIdentity) -> bool:
        return any(
            agent == identity and lease_id in self._lease_clients
            for lease_id, agent in self._lease_agents.items()
        )

    def surface_view(
        self,
        *,
        frame: int,
        activity_motion: bool,
    ) -> SurfaceView:
        indicators = tuple(
            SessionIndicator(
                slot=session.slot,
                state=session.state,
                selected=session.identity == self._selected_agent,
                accent=session.accent or self.accent_names[session.slot],
            )
            for session in sorted(
                (
                    session
                    for session in self._sessions.values()
                    if session.slot is not None
                ),
                key=lambda session: (
                    session.slot if session.slot is not None else -1
                ),
            )
            if session.slot is not None
        )
        preview_state = self._preview.state if self._preview is not None else None
        return SurfaceView(
            selected_state=preview_state if preview_state is not None else self.state,
            frame=frame,
            sessions=indicators,
            available_actions=self.available_actions(),
            overflow_count=self.overflow_count,
            activity_motion=activity_motion and self._preview is None,
        )

    def session_label(self, session: AgentSession) -> str:
        if label := session.metadata.get("label"):
            return label
        if cwd := session.metadata.get("cwd"):
            name = os.path.basename(os.path.normpath(cwd))
            if name:
                return name
        return session.identity.session_id[:8]

    def _ensure_session(self, identity: AgentIdentity, now: float) -> AgentSession:
        session = self._sessions.get(identity)
        if session is not None:
            return session
        self._sequence += 1
        session = AgentSession(
            identity=identity,
            last_seen=self._sequence,
            last_activity_at=now,
        )
        self._sessions[identity] = session
        self._assign_slot(session)
        if self._selected_agent is None and len(self._sessions) == 1:
            self._selected_agent = identity
        return session

    def _end_agent(self, identity: AgentIdentity) -> bool:
        session = self._sessions.pop(identity, None)
        if session is None:
            return False
        if session.slot is not None:
            self._slots[session.slot] = None
        if identity == self._selected_agent:
            self._selected_agent = None
        for client_id, subscription in list(self._subscriptions.items()):
            if subscription.agent == identity:
                del self._subscriptions[client_id]
        for lease_id, agent in list(self._lease_agents.items()):
            if agent == identity:
                del self._lease_agents[lease_id]
        self._last_action_at = {
            key: value
            for key, value in self._last_action_at.items()
            if key[0] != identity
        }
        self._fill_empty_slots()
        return True

    def _bind_lease(
        self,
        lease_id: str,
        identity: AgentIdentity,
        metadata: dict[str, str],
        *,
        now: float,
    ) -> AgentSession:
        previous_identity = self._lease_agents.get(lease_id)
        self._lease_agents[lease_id] = identity
        combined_metadata = dict(self._lease_metadata.get(lease_id, {}))
        combined_metadata.update(metadata)
        session = self._ensure_session(identity, now)
        session.last_activity_at = now
        if combined_metadata:
            session.metadata.update(combined_metadata)

        if (
            previous_identity is not None
            and previous_identity != identity
            and not self.is_leased(previous_identity)
        ):
            self._end_agent(previous_identity)
        return session

    def _release_lease(self, lease_id: str, client_id: int) -> bool:
        if self._lease_clients.get(lease_id) != client_id:
            return False
        del self._lease_clients[lease_id]
        self._client_leases.pop(client_id, None)
        identity = self._lease_agents.pop(lease_id, None)
        self._lease_metadata.pop(lease_id, None)
        if identity is not None and not self.is_leased(identity):
            self._end_agent(identity)
        return True

    def _has_pending_approval(self, identity: AgentIdentity) -> bool:
        approval_actions = {ControlAction.APPROVE, ControlAction.REJECT}
        return any(
            subscription.agent == identity
            and subscription.request_id is not None
            and bool(subscription.actions & approval_actions)
            for subscription in self._subscriptions.values()
        )

    def _assign_slot(self, session: AgentSession) -> None:
        if session.slot is not None:
            return
        try:
            slot = self._slots.index(None)
        except ValueError:
            candidates = [
                candidate
                for candidate in self._sessions.values()
                if candidate.slot is not None
                and candidate.identity != self._selected_agent
                and candidate.state is not AgentState.WAITING_FOR_APPROVAL
            ]
            if not candidates:
                return
            evicted = min(candidates, key=lambda candidate: candidate.last_seen)
            assert evicted.slot is not None
            slot = evicted.slot
            evicted.slot = None
        self._slots[slot] = session.identity
        session.slot = slot
        self._assign_accent(session)

    def _assign_accent(self, session: AgentSession) -> None:
        if session.slot is None:
            return
        used = {
            candidate.accent
            for candidate in self._sessions.values()
            if candidate is not session
            and candidate.slot is not None
            and candidate.accent is not None
        }
        preferred = session.accent
        if preferred is None and self.identity_store is not None:
            preferred = self.identity_store.preferred_accent(session.identity)
        if preferred not in self.accent_names or preferred in used:
            preferred = next(
                (name for name in self.accent_names if name not in used),
                None,
            )
        session.accent = preferred
        if preferred is not None and self.identity_store is not None:
            try:
                self.identity_store.remember(session.identity, preferred)
            except OSError:
                pass

    def _fill_empty_slots(self) -> None:
        waiting = sorted(
            (
                session
                for session in self._sessions.values()
                if session.slot is None
            ),
            key=lambda session: (
                session.state is AgentState.WAITING_FOR_APPROVAL,
                session.last_seen,
            ),
            reverse=True,
        )
        for session in waiting:
            if None not in self._slots:
                break
            self._assign_slot(session)

    def _changed(self) -> None:
        self._revision += 1
