"""Exercise production routing over real Unix sockets and browser WebSockets."""

from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
from unittest import TestCase

from websockets.sync.client import connect

from pad_lattice.client import PadLatticeClient
from pad_lattice.daemon_runtime import PadLatticeDaemon
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    open_message_connection,
    parse_action_event,
    ping_message,
    session_lease_message,
    state_message,
    subscribe_actions_message,
)
from pad_lattice.web_protocol import web_message
from pad_lattice.web_surface import WebSurface


TIMEOUT = 3.0
APPROVAL_ACTIONS = (ControlAction.APPROVE, ControlAction.REJECT)


class RuntimeHarness(TestCase):
    def setUp(self) -> None:
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        # Keep Unix socket addresses below macOS's 104-byte limit.
        root = self.resources.enter_context(TemporaryDirectory(prefix="pl-live-", dir="/tmp"))
        self.socket_path = str(Path(root) / "daemon.sock")
        self.client = PadLatticeClient(self.socket_path, timeout=TIMEOUT)
        self.start_daemon()

    def start_daemon(self) -> None:
        self.surface = WebSurface(port=0, admin_token="runtime-test-admin")
        # One-shot and revision safety must work even without a debounce delay.
        self.daemon = PadLatticeDaemon(
            self.surface, self.socket_path,
            poll_interval=0.005, action_debounce=0, terminal_hold=60,
        )
        self.stopped = threading.Event()
        self.errors: list[BaseException] = []

        def run():
            try:
                self.daemon.run(self.stopped)
            except BaseException as error:
                self.errors.append(error)

        self.thread = threading.Thread(target=run, name="test-pad-lattice-daemon", daemon=True)
        self.thread.start()
        self.resources.callback(self.stop_daemon)
        deadline = time.monotonic() + TIMEOUT
        while time.monotonic() < deadline:
            if self.errors:
                raise self.errors[0]
            try:
                self.client.ping()
                return
            except (FileNotFoundError, ConnectionRefusedError):
                self.stopped.wait(0.01)
        self.fail("The isolated daemon did not start")

    def stop_daemon(self) -> None:
        self.stopped.set()
        self.thread.join(timeout=TIMEOUT)
        self.assertFalse(self.thread.is_alive(), "Daemon thread did not stop")
        self.assertEqual(self.errors, [], "Daemon failed during the integration test")
        self.assertFalse(Path(self.socket_path).exists(), "Daemon left its socket behind")

    def connection(self):
        return self.resources.enter_context(open_message_connection(self.socket_path, timeout=TIMEOUT))

    def agent(self, label: str, *, lease: str | None = None):
        identity = AgentIdentity("test", label.lower())
        connection = self.connection()
        if lease is not None:
            ack = connection.request(session_lease_message(lease, agent=identity))
            self.assertEqual(ack["type"], "session_lease_ack")
        self.report(connection, identity, AgentState.WAITING_FOR_APPROVAL, label=label)
        return identity, connection

    def report(self, connection, identity, state, *, label=None):
        message = state_message(
            state,
            agent={"backend": identity.backend, "session_id": identity.session_id,
                   "label": label or identity.session_id.title()},
            reply=True,
        )
        ack = connection.request(message)
        self.assertEqual(ack["type"], "state_ack")
        return ack

    def subscribe(self, connection, identity, request_id):
        connection.send(subscribe_actions_message(
            identity, APPROVAL_ACTIONS, request_id=request_id, one_shot=True,
        ))
        # A pong on this same stream confirms the subscription was processed.
        self.assertEqual(connection.request(ping_message())["type"], "pong")

    def browser(self, credential="runtime-test-admin"):
        browser = self.resources.enter_context(connect(
            self.surface.local_url.replace("http://", "ws://") + "/ws",
            origin=self.surface.local_url, proxy=None, close_timeout=0.2,
            open_timeout=TIMEOUT,
        ))
        self.send(browser, "authenticate", credential=credential)
        auth = self.message(browser, "authenticated")
        return browser, auth

    def send(self, browser, message_type, **fields):
        browser.send(json.dumps(web_message(message_type, **fields)))

    def message(self, browser, kind, predicate=lambda message: True):
        deadline = time.monotonic() + TIMEOUT
        last = None
        while time.monotonic() < deadline:
            try:
                last = json.loads(browser.recv(timeout=max(0, deadline - time.monotonic())))
            except TimeoutError:
                break
            if last["type"] == kind and predicate(last):
                return last
            self.assertNotEqual(last["type"], "error", last)
        self.fail(f"Timed out waiting for {kind}; last message: {last!r}")

    def view(self, browser, predicate=lambda view: True):
        # Socket acknowledgements can precede rendering. Observe the revision
        # only to wait for that render; all mutations still cross real sockets.
        revision = self.daemon.control.revision
        return self.message(browser, "surface", lambda message: (
            message["view"]["control_revision"] >= revision and predicate(message["view"])
        ))["view"]

    def select(self, browser, view, slot):
        self.send(browser, "select_session", slot=slot, expected_revision=view["control_revision"])
        return self.view(browser, lambda current: (
            current["control_revision"] > view["control_revision"]
            and any(session["selected"] and session["slot"] == slot for session in current["sessions"])
        ))

    def press(self, browser, view, action="approve"):
        self.send(browser, "action", action=action, expected_revision=view["control_revision"])

    def received(self, connection, identity, request_id, action):
        event = parse_action_event(connection.receive())
        self.assertEqual((event.agent, event.request_id, event.action), (identity, request_id, action))

    def assert_silent(self, connection):
        previous = connection.client.gettimeout()
        connection.client.settimeout(0.1)
        try:
            with self.assertRaises(TimeoutError, msg="Unexpected action was delivered"):
                connection.receive()
        finally:
            connection.client.settimeout(previous)

class RuntimeIntegrationTest(RuntimeHarness):
    def test_selected_request_receives_action_without_inventing_success(self):
        builder, first = self.agent("Builder")
        reviewer, second = self.agent("Reviewer")
        self.subscribe(first, builder, "build-request")
        self.subscribe(second, reviewer, "review-request")
        browser, _ = self.browser()
        view = self.view(browser, lambda v: len(v["sessions"]) == 2)
        view = self.select(browser, view, 1)
        self.press(browser, view)
        self.received(second, reviewer, "review-request", ControlAction.APPROVE)
        after = self.view(browser, lambda v: not v["available_actions"])
        self.assertEqual(after["selected_state"], "waiting_for_approval")
        self.assert_silent(first)
        self.assert_silent(second)

        self.report(second, reviewer, AgentState.RUNNING)
        after = self.view(browser, lambda v: v["selected_state"] == "running")
        self.assertEqual([s["label"] for s in after["sessions"]], ["Builder", "Reviewer"])
        self.assertEqual(after["sessions"][0]["state"], "waiting_for_approval")
        self.report(second, reviewer, AgentState.SUCCESS)
        self.view(browser, lambda v: v["selected_state"] == "success")

    def test_two_surfaces_cannot_answer_one_request_twice(self):
        identity, agent = self.agent("Reviewer")
        self.subscribe(agent, identity, "shared-request")
        first, _ = self.browser()
        second, _ = self.browser()
        view = self.view(first, lambda v: "approve" in v["available_actions"])
        other = self.view(second, lambda v: v["control_revision"] == view["control_revision"])
        self.press(first, view, "approve")
        self.press(second, other, "reject")
        event = parse_action_event(agent.receive())
        self.assertEqual((event.agent, event.request_id), (identity, "shared-request"))
        self.assertIn(event.action, APPROVAL_ACTIONS)
        self.view(first, lambda v: not v["available_actions"])
        self.view(second, lambda v: not v["available_actions"])
        self.assert_silent(agent)

    def test_duplicate_press_cannot_spill_into_a_second_pending_request(self):
        identity, first = self.agent("Reviewer")
        second = self.connection()
        self.subscribe(first, identity, "older-request")
        self.subscribe(second, identity, "newer-request")
        browser, _ = self.browser()
        view = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, view)
        self.press(browser, view, "reject")
        self.received(first, identity, "older-request", ControlAction.APPROVE)
        after = self.view(browser, lambda v: v["control_revision"] > view["control_revision"])
        self.assertEqual(after["available_actions"], ["approve", "reject"])
        self.assert_silent(second)
        self.press(browser, after, "reject")
        self.received(second, identity, "newer-request", ControlAction.REJECT)
        self.view(browser, lambda v: not v["available_actions"])
        self.assert_silent(first)
        self.assert_silent(second)

    def test_another_surface_selection_invalidates_old_actions_and_selections(self):
        builder, first = self.agent("Builder")
        reviewer, second = self.agent("Reviewer")
        self.subscribe(first, builder, "build-request")
        self.subscribe(second, reviewer, "review-request")
        desktop, _ = self.browser()
        phone, _ = self.browser()
        old = self.view(desktop, lambda v: len(v["sessions"]) == 2)
        current = self.view(phone, lambda v: v["control_revision"] == old["control_revision"])
        current = self.select(phone, current, 1)
        self.view(desktop, lambda v: v["control_revision"] == current["control_revision"])
        self.press(desktop, old)
        self.send(desktop, "select_session", slot=0, expected_revision=old["control_revision"])
        after = self.view(desktop, lambda v: v["frame"] > current["frame"])
        self.assertTrue(after["sessions"][1]["selected"])
        self.assertEqual(after["control_revision"], current["control_revision"])
        self.assert_silent(first)
        self.assert_silent(second)
        self.press(phone, current)
        self.received(second, reviewer, "review-request", ControlAction.APPROVE)

    def test_answered_request_loses_controls_and_cannot_approve_its_replacement(self):
        identity, old_request = self.agent("Reviewer")
        self.subscribe(old_request, identity, "answered-in-agent")
        browser, _ = self.browser()
        old = self.view(browser, lambda v: "approve" in v["available_actions"])
        old_request.client.close()
        self.view(browser, lambda v: not v["available_actions"])
        current = self.connection()
        self.report(current, identity, AgentState.RUNNING)
        running = self.view(browser, lambda v: v["selected_state"] == "running")
        self.press(browser, old)
        self.view(browser, lambda v: v["frame"] > running["frame"])
        self.assert_silent(current)

        self.report(current, identity, AgentState.WAITING_FOR_APPROVAL)
        self.subscribe(current, identity, "replacement-request")
        replacement = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, old)
        self.view(browser, lambda v: v["frame"] > replacement["frame"])
        self.assert_silent(current)
        self.press(browser, replacement)
        self.received(current, identity, "replacement-request", ControlAction.APPROVE)

    def test_lease_disconnect_clears_selection_and_reconnect_needs_fresh_subscription(self):
        builder, first = self.agent("Builder")
        reviewer, second = self.agent("Reviewer", lease="reviewer-lease")
        self.subscribe(first, builder, "build-request")
        self.subscribe(second, reviewer, "old-review-request")
        browser, _ = self.browser()
        view = self.view(browser, lambda v: len(v["sessions"]) == 2)
        old = self.select(browser, view, 1)
        second.client.close()
        after = self.view(browser, lambda v: len(v["sessions"]) == 1)
        self.assertIsNone(after["selected_state"])
        self.assertEqual(after["available_actions"], [])
        self.assertFalse(after["sessions"][0]["selected"])
        self.press(browser, old)
        self.view(browser, lambda v: v["frame"] > after["frame"])
        self.assert_silent(first)

        _, reconnected = self.agent("Reviewer", lease="reviewer-lease")
        after = self.view(browser, lambda v: len(v["sessions"]) == 2)
        self.assertIsNone(after["selected_state"])
        selected = self.select(browser, after, 1)
        self.assertEqual(selected["available_actions"], [])
        self.subscribe(reconnected, reviewer, "new-review-request")
        current = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, old)
        self.view(browser, lambda v: v["frame"] > current["frame"])
        self.assert_silent(reconnected)
        self.press(browser, current, "reject")
        self.received(reconnected, reviewer, "new-review-request", ControlAction.REJECT)
        self.assert_silent(first)

    def test_paired_browser_reconnects_to_current_state_not_its_old_request(self):
        identity, agent = self.agent("Reviewer")
        self.subscribe(agent, identity, "old-request")
        admin, _ = self.browser()
        self.view(admin, lambda v: "approve" in v["available_actions"])
        self.send(admin, "create_pairing")
        pin = self.message(admin, "pairing")["pin"]
        phone, auth = self.browser(pin)
        self.assertFalse(auth["admin"])
        old = self.view(phone, lambda v: "approve" in v["available_actions"])
        phone.close()

        self.subscribe(agent, identity, "new-request")
        current = self.view(admin, lambda v: v["control_revision"] > old["control_revision"])
        resumed, auth = self.browser(auth["session_token"])
        self.assertFalse(auth["admin"])
        snapshot = self.view(resumed, lambda v: v["control_revision"] == current["control_revision"])
        self.press(resumed, old)
        self.view(resumed, lambda v: v["frame"] > snapshot["frame"])
        self.assert_silent(agent)
        self.press(resumed, current)
        self.received(agent, identity, "new-request", ControlAction.APPROVE)
        self.view(admin, lambda v: not v["available_actions"])

    def test_replacement_lease_survives_its_previous_connection_closing(self):
        identity, old_owner = self.agent("Reviewer", lease="reviewer-lease")
        self.subscribe(old_owner, identity, "old-request")
        browser, _ = self.browser()
        old = self.view(browser, lambda v: "approve" in v["available_actions"])
        _, new_owner = self.agent("Reviewer", lease="reviewer-lease")
        old_owner.client.close()
        current = self.view(browser, lambda v: not v["available_actions"])
        self.assertEqual(len(current["sessions"]), 1)
        self.assertTrue(current["sessions"][0]["selected"])
        self.assertTrue(self.client.status()["sessions"][0]["leased"])
        self.subscribe(new_owner, identity, "new-request")
        current = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, old)
        self.view(browser, lambda v: v["frame"] > current["frame"])
        self.assert_silent(new_owner)
        self.press(browser, current)
        self.received(new_owner, identity, "new-request", ControlAction.APPROVE)

    def test_agent_connection_preempts_demo_and_blocks_new_playback(self):
        browser, _ = self.browser()
        self.view(browser)
        self.send(browser, "start_experience", kind="demo")
        self.message(browser, "experience_state", lambda m: m["status"] == "playing")
        identity, agent = self.agent("Reviewer")
        self.subscribe(agent, identity, "real-request")
        self.message(browser, "experience_state", lambda m: m["status"] == "idle")
        view = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.assertEqual(view["sessions"][0]["label"], "Reviewer")
        self.send(browser, "start_experience", kind="show")
        self.message(browser, "experience_state", lambda m: m["status"] == "blocked")
        self.press(browser, view)
        self.received(agent, identity, "real-request", ControlAction.APPROVE)

    def test_guarded_demo_click_cannot_reach_an_agent_after_preemption(self):
        browser, _ = self.browser()
        self.view(browser)
        self.send(browser, "start_experience", kind="demo")
        demo = self.view(browser, lambda v: len(v["sessions"]) == 3)
        self.assertIsInstance(demo["control_revision"], int)
        self.send(browser, "select_session", slot=1, expected_revision=demo["control_revision"])
        demo = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, demo)
        self.view(browser, lambda v: v["selected_state"] == "running")

        identity, agent = self.agent("Actual agent")
        self.subscribe(agent, identity, "actual-request")
        current = self.view(browser, lambda v: len(v["sessions"]) == 1 and "approve" in v["available_actions"])
        self.press(browser, demo)
        self.view(browser, lambda v: v["frame"] > current["frame"])
        self.assert_silent(agent)
        self.press(browser, current)
        self.received(agent, identity, "actual-request", ControlAction.APPROVE)
