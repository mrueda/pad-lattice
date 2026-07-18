from __future__ import annotations

import random
from unittest import TestCase

from pad_lattice.control_plane import ControlPlane, ControlPlaneError
from pad_lattice.events import AgentIdentity, AgentState, ControlAction

ACCENTS = ("cyan", "magenta", "lime", "orange")


class ControlPlaneTest(TestCase):
    def plane(self, **kwargs) -> ControlPlane:
        return ControlPlane(4, ACCENTS, **kwargs)

    def test_background_updates_do_not_steal_selection(self) -> None:
        plane = self.plane()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")

        plane.update_agent(first, AgentState.WAITING_FOR_REPLY, now=1.0)
        plane.update_agent(second, AgentState.RUNNING, now=2.0)

        self.assertEqual(plane.selected_agent, first)
        self.assertIs(plane.state, AgentState.WAITING_FOR_REPLY)

    def test_request_scoped_actions_are_deterministic_and_one_shot(self) -> None:
        plane = self.plane(action_debounce=0)
        identity = AgentIdentity("codex", "session")
        plane.update_agent(identity, AgentState.WAITING_FOR_APPROVAL, now=1.0)
        for client_id, request_id in ((10, "first"), (11, "second")):
            plane.subscribe(
                client_id,
                identity,
                frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
                request_id=request_id,
                one_shot=True,
                now=2.0,
            )

        first = plane.dispatch_action(ControlAction.APPROVE, now=3.0)
        second = plane.dispatch_action(ControlAction.REJECT, now=4.0)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None
        self.assertEqual((first.client_id, first.request_id), (10, "first"))
        self.assertEqual((second.client_id, second.request_id), (11, "second"))
        self.assertEqual(plane.available_actions(), frozenset())

    def test_pending_approval_wins_over_running_update(self) -> None:
        plane = self.plane()
        identity = AgentIdentity("codex", "session")
        plane.subscribe(
            10,
            identity,
            frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
            request_id="approval",
            one_shot=True,
            now=1.0,
        )

        plane.update_agent(identity, AgentState.RUNNING, now=2.0)

        self.assertIs(plane.state, AgentState.WAITING_FOR_APPROVAL)

    def test_lease_owner_replacement_ignores_old_disconnect(self) -> None:
        plane = self.plane()
        identity = AgentIdentity("codex", "session")
        plane.register_lease(
            10,
            "lease",
            agent=identity,
            metadata={"label": "first"},
            now=1.0,
        )
        plane.register_lease(
            11,
            "lease",
            agent=identity,
            metadata={"label": "second"},
            now=2.0,
        )

        plane.disconnect(10)
        self.assertTrue(plane.is_leased(identity))
        self.assertIn(identity, plane._sessions)

        plane.disconnect(11)
        self.assertFalse(plane.is_leased(identity))
        self.assertNotIn(identity, plane._sessions)

    def test_preview_is_an_expiring_display_override(self) -> None:
        plane = self.plane()
        identity = AgentIdentity("codex", "session")
        plane.update_agent(identity, AgentState.RUNNING, now=1.0)
        plane.subscribe(
            10,
            identity,
            frozenset({ControlAction.STOP}),
            request_id=None,
            one_shot=False,
            now=1.0,
        )

        plane.set_preview(
            20,
            "preview",
            AgentState.SUCCESS,
            expires_at=3.0,
        )

        self.assertIs(plane.state, AgentState.RUNNING)
        self.assertIs(
            plane.surface_view(frame=0, activity_motion=False).selected_state,
            AgentState.SUCCESS,
        )
        self.assertEqual(plane.available_actions(), frozenset())
        with self.assertRaises(ControlPlaneError):
            plane.set_preview(
                21,
                "other",
                AgentState.ERROR,
                expires_at=3.0,
            )

        plane.tick(now=3.0)
        self.assertIsNone(plane.preview)
        self.assertEqual(
            plane.available_actions(),
            frozenset({ControlAction.STOP}),
        )

    def test_expiry_uses_caller_supplied_clock(self) -> None:
        plane = self.plane(terminal_hold=2.0, session_ttl=10.0)
        identity = AgentIdentity("codex", "session")
        plane.update_agent(identity, AgentState.SUCCESS, now=1.0)

        plane.tick(now=2.9)
        self.assertIs(plane.state, AgentState.SUCCESS)
        plane.tick(now=3.0)
        self.assertIs(plane.state, AgentState.WAITING_FOR_REPLY)
        plane.tick(now=11.0)
        self.assertNotIn(identity, plane._sessions)

    def test_seeded_event_trace_preserves_core_invariants(self) -> None:
        randomizer = random.Random(20260718)
        plane = self.plane(
            terminal_hold=1.0,
            action_debounce=0.1,
            session_ttl=8.0,
        )
        agents = [AgentIdentity("codex", f"session-{index}") for index in range(8)]
        clients = list(range(10, 22))
        leases = [f"lease-{index}" for index in range(4)]
        now = 0.0

        for _ in range(500):
            now += randomizer.random()
            operation = randomizer.randrange(9)
            agent = randomizer.choice(agents)
            client_id = randomizer.choice(clients)
            if operation == 0:
                plane.update_agent(agent, randomizer.choice(list(AgentState)), now=now)
            elif operation == 1:
                action = randomizer.choice(list(ControlAction))
                plane.subscribe(
                    client_id,
                    agent,
                    frozenset({action}),
                    request_id=(
                        f"request-{client_id}" if action in {
                            ControlAction.APPROVE,
                            ControlAction.REJECT,
                        } else None
                    ),
                    one_shot=randomizer.choice((True, False)),
                    now=now,
                )
            elif operation == 2:
                plane.disconnect(client_id)
            elif operation == 3:
                plane.select_slot(randomizer.randrange(4), now=now)
            elif operation == 4:
                plane.end_agent(agent)
            elif operation == 5:
                plane.register_lease(
                    client_id,
                    randomizer.choice(leases),
                    agent=agent if randomizer.choice((True, False)) else None,
                    metadata={},
                    now=now,
                )
            elif operation == 6:
                plane.dispatch_action(randomizer.choice(list(ControlAction)), now=now)
            elif operation == 7:
                try:
                    plane.set_preview(
                        client_id,
                        f"preview-{client_id}",
                        randomizer.choice(list(AgentState)),
                        expires_at=now + 1.0,
                    )
                except ControlPlaneError:
                    pass
            else:
                plane.tick(now=now)
            self._assert_invariants(plane)

    def _assert_invariants(self, plane: ControlPlane) -> None:
        visible = [session for session in plane.sessions if session.slot is not None]
        slots = [session.slot for session in visible]
        accents = [session.accent for session in visible]
        self.assertEqual(len(slots), len(set(slots)))
        self.assertEqual(len(accents), len(set(accents)))
        self.assertLessEqual(len(visible), plane.selector_capacity)
        for session in visible:
            assert session.slot is not None
            self.assertEqual(plane._slots[session.slot], session.identity)
            self.assertIn(session.accent, plane.accent_names)
        for slot, identity in enumerate(plane._slots):
            if identity is not None:
                self.assertEqual(plane._sessions[identity].slot, slot)
        if plane.selected_agent is not None:
            self.assertIn(plane.selected_agent, plane._sessions)
        self.assertEqual(
            plane.overflow_count,
            sum(session.slot is None for session in plane.sessions),
        )
