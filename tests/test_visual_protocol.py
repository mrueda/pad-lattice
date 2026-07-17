from __future__ import annotations

from unittest import TestCase

from pad_lattice.devices.base import SessionIndicator, SurfaceView
from pad_lattice.events import AgentState, ControlAction
from pad_lattice.visual_protocol import (
    ACTIVITY,
    IDLE,
    OFF,
    STATE_GLYPHS,
    STATE_HEIGHT,
    STATE_WIDTH,
    compile_visual_frame,
)


class VisualProtocolTest(TestCase):
    def test_every_state_glyph_fits_the_seven_by_eight_canvas(self) -> None:
        self.assertEqual(set(STATE_GLYPHS), set(AgentState))
        for state, points in STATE_GLYPHS.items():
            with self.subTest(state=state):
                self.assertTrue(points)
                self.assertTrue(
                    all(
                        0 <= x < STATE_WIDTH and 0 <= y < STATE_HEIGHT
                        for x, y in points
                    )
                )

    def test_no_selection_renders_a_quiet_idle_dash(self) -> None:
        frame = compile_visual_frame(SurfaceView(None), 8)

        lit = {
            (x, y): token
            for y, row in enumerate(frame.state)
            for x, token in enumerate(row)
            if token != OFF
        }
        self.assertEqual(
            lit,
            {(2, 4): IDLE, (3, 4): IDLE, (4, 4): IDLE},
        )

    def test_waiting_reply_and_approval_are_distinct(self) -> None:
        reply = compile_visual_frame(
            SurfaceView(AgentState.WAITING_FOR_REPLY),
            8,
        )
        approval = compile_visual_frame(
            SurfaceView(AgentState.WAITING_FOR_APPROVAL),
            8,
        )

        self.assertNotEqual(reply.state, approval.state)
        self.assertIn("state:waiting_for_reply:primary", sum(reply.state, ()))
        self.assertIn("state:waiting_for_approval:primary", sum(approval.state, ()))

    def test_running_motion_is_disabled_by_default(self) -> None:
        steady = compile_visual_frame(
            SurfaceView(AgentState.RUNNING, frame=2),
            8,
        )
        moving = compile_visual_frame(
            SurfaceView(AgentState.RUNNING, frame=2, activity_motion=True),
            8,
        )

        self.assertNotIn(ACTIVITY, sum(steady.state, ()))
        self.assertEqual(sum(moving.state, ()).count(ACTIVITY), 2)

    def test_sessions_actions_and_overflow_compile_to_semantic_tokens(self) -> None:
        frame = compile_visual_frame(
            SurfaceView(
                AgentState.WAITING_FOR_APPROVAL,
                sessions=(
                    SessionIndicator(
                        0,
                        AgentState.WAITING_FOR_APPROVAL,
                        selected=True,
                        accent="cyan",
                    ),
                ),
                available_actions=frozenset({ControlAction.APPROVE}),
                overflow_count=1,
            ),
            8,
        )

        self.assertEqual(frame.selectors[0], "accent:cyan:selected")
        self.assertEqual(
            frame.statuses[0],
            "state:waiting_for_approval:summary",
        )
        self.assertEqual(frame.actions[ControlAction.APPROVE], "action:approve:enabled")
        self.assertEqual(frame.actions[ControlAction.REJECT], "action:reject:disabled")
        self.assertEqual(frame.overflow, "system:overflow")
