"""A tiny fake agent backend for exercising the hardware loop."""

from __future__ import annotations

import time
from collections.abc import Callable

from pad_lattice.events import AgentState, ControlAction


class DemoAgent:
    """Cycle through the MVP states until a Launchpad control changes it."""

    def __init__(self, *, seconds_per_state: float = 4.0) -> None:
        self.seconds_per_state = seconds_per_state
        self._states = (
            AgentState.RUNNING,
            AgentState.WAITING_FOR_APPROVAL,
            AgentState.SUCCESS,
            AgentState.ERROR,
        )
        self._index = 0
        self._last_change = time.monotonic()

    def current_state(self) -> AgentState:
        now = time.monotonic()
        if now - self._last_change >= self.seconds_per_state:
            self._index = (self._index + 1) % len(self._states)
            self._last_change = now
        return self._states[self._index]

    def handle_action(self, action: ControlAction) -> None:
        if action is ControlAction.APPROVE:
            self._set_state(AgentState.RUNNING)
        elif action is ControlAction.REJECT:
            self._set_state(AgentState.ERROR)
        elif action is ControlAction.STOP:
            self._set_state(AgentState.ERROR)
        elif action is ControlAction.RETRY:
            self._set_state(AgentState.RUNNING)

    def action_logger(self) -> Callable[[ControlAction], None]:
        def log_and_handle(action: ControlAction) -> None:
            print(f"control: {action.value}", flush=True)
            self.handle_action(action)

        return log_and_handle

    def _set_state(self, state: AgentState) -> None:
        self._index = self._states.index(state)
        self._last_change = time.monotonic()
