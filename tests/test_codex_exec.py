from __future__ import annotations

from unittest import TestCase

from pad_lattice.codex_exec import state_for_codex_event
from pad_lattice.events import AgentState


class CodexExecTest(TestCase):
    def test_turn_started_maps_to_running(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "turn.started"}),
            AgentState.RUNNING,
        )

    def test_turn_completed_maps_to_success(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "turn.completed"}),
            AgentState.SUCCESS,
        )

    def test_error_maps_to_error(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "error"}),
            AgentState.ERROR,
        )

    def test_agent_message_does_not_change_state(self) -> None:
        self.assertIsNone(
            state_for_codex_event(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "done"},
                }
            )
        )
