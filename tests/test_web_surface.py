from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from websockets.sync.client import connect

from pad_lattice.devices.base import ActionPressed, SessionSelected, SurfaceView
from pad_lattice.events import AgentState, ControlAction
from pad_lattice.web_surface import (
    COMMAND_RATE_LIMIT,
    MAX_PENDING_SURFACE_EVENTS,
    BrowserClient,
    BrowserSurfaceServer,
    WebSurface,
)


class BrowserSurfaceServerTest(TestCase):
    def test_pairing_is_one_use_and_session_tokens_are_ephemeral(self) -> None:
        now = [10.0]
        server = BrowserSurfaceServer(lambda event: None, clock=lambda: now[0])
        server.configure_lan("http://192.168.1.10:8765")
        pairing = server.create_pairing()

        authenticated, token = server._authenticate(
            "192.168.1.20", pairing["pin"], loopback=False
        )
        reused, _ = server._authenticate(
            "192.168.1.21", pairing["pin"], loopback=False
        )
        resumed, replacement = server._authenticate(
            "192.168.1.20", token, loopback=False
        )

        self.assertTrue(authenticated)
        self.assertIsNotNone(token)
        self.assertFalse(reused)
        self.assertTrue(resumed)
        self.assertIsNone(replacement)
        server.revoke_remote()
        revoked, _ = server._authenticate(
            "192.168.1.20", token, loopback=False
        )
        self.assertFalse(revoked)

    def test_expired_pairing_and_repeated_failures_are_rejected(self) -> None:
        now = [10.0]
        server = BrowserSurfaceServer(lambda event: None, clock=lambda: now[0])
        server.configure_lan("http://192.168.1.10:8765")
        pairing = server.create_pairing()
        now[0] += 301
        accepted, _ = server._authenticate(
            "192.168.1.20", pairing["pin"], loopback=False
        )
        self.assertFalse(accepted)
        for _ in range(5):
            server._authenticate("192.168.1.30", "wrong", loopback=False)
        self.assertTrue(server._rate_limited("192.168.1.30"))

    def test_concurrent_pairing_consumes_credential_once(self) -> None:
        server = BrowserSurfaceServer(lambda event: None)
        server.configure_lan("http://192.168.1.10:8765")
        pairing = server.create_pairing()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                executor.map(
                    lambda peer: server._authenticate(
                        peer,
                        pairing["pin"],
                        loopback=False,
                    ),
                    ("192.168.1.20", "192.168.1.21"),
                )
            )

        self.assertEqual(sum(accepted for accepted, token in results), 1)
        self.assertEqual(sum(token is not None for accepted, token in results), 1)

    def test_loopback_requires_no_pairing_credential(self) -> None:
        server = BrowserSurfaceServer(lambda event: None)
        self.assertEqual(
            server._authenticate("127.0.0.1", None, loopback=True),
            (True, None),
        )

    def test_lan_host_is_limited_to_advertised_origin(self) -> None:
        server = BrowserSurfaceServer(
            lambda event: None,
            host="0.0.0.0",
            port=8765,
        )
        server.configure_lan("http://pad-host.local:8765")

        self.assertTrue(server._host_is_allowed("pad-host.local:8765"))
        self.assertTrue(server._host_is_allowed("127.0.0.1:8765"))
        self.assertFalse(server._host_is_allowed("other.local:8765"))
        self.assertFalse(server._host_is_allowed("pad-host.local:9999"))

    def test_lan_rejects_public_literal_address_and_url_credentials(self) -> None:
        server = BrowserSurfaceServer(lambda event: None)
        with self.assertRaisesRegex(ValueError, "private address"):
            server.configure_lan("http://8.8.8.8:8765")
        with self.assertRaisesRegex(ValueError, "HTTP origin"):
            server.configure_lan("http://user@pad-host.local:8765")

    def test_browser_command_rate_is_bounded(self) -> None:
        client = BrowserClient(object(), admin=False, remote=True)
        self.assertTrue(
            all(client.allow_command(10.0) for _ in range(COMMAND_RATE_LIMIT))
        )
        self.assertFalse(client.allow_command(10.0))
        self.assertTrue(client.allow_command(11.1))


class WebSurfaceIntegrationTest(TestCase):
    def test_browser_event_queue_is_bounded(self) -> None:
        surface = WebSurface(port=0)
        event = ActionPressed(ControlAction.STOP)
        for _ in range(MAX_PENDING_SURFACE_EVENTS + 10):
            surface._enqueue_event(event)

        self.assertEqual(
            len(surface.poll_events()),
            MAX_PENDING_SURFACE_EVENTS,
        )

    def test_loopback_browser_receives_frames_and_emits_events(self) -> None:
        with TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("ok", encoding="utf-8")
            surface = WebSurface(port=0, asset_root=Path(directory))
            surface.initialize()
            try:
                surface.render(SurfaceView(AgentState.WAITING_FOR_REPLY))
                websocket_url = surface.local_url.replace("http://", "ws://") + "/ws"
                with connect(
                    websocket_url,
                    origin=surface.local_url,
                    proxy=None,
                    close_timeout=1,
                ) as client:
                    client.send(json.dumps({"protocol": 1, "type": "authenticate"}))
                    authenticated = json.loads(client.recv())
                    frame = json.loads(client.recv())
                    client.send(
                        json.dumps(
                            {"protocol": 1, "type": "select_session", "slot": 2}
                        )
                    )
                    client.send(
                        json.dumps(
                            {"protocol": 1, "type": "action", "action": "stop"}
                        )
                    )
                    deadline = time.monotonic() + 1.0
                    events = []
                    while time.monotonic() < deadline and len(events) < 2:
                        events.extend(surface.poll_events())
                        time.sleep(0.01)
                self.assertTrue(authenticated["admin"])
                self.assertEqual(frame["type"], "surface")
                self.assertEqual(
                    events,
                    [SessionSelected(2), ActionPressed(ControlAction.STOP)],
                )
            finally:
                surface.close()
