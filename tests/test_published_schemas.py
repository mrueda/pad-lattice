from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase, skipUnless

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - exercised by installations without the extra
    Draft202012Validator = None  # type: ignore[assignment]

from pad_lattice.daemon_runtime import PadLatticeDaemon
from pad_lattice.devices.base import SessionIndicator, SurfaceView
from pad_lattice.devices.profiles import load_profile_schema
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    error_message,
    load_protocol_schema,
    ping_message,
    preview_end_message,
    preview_message,
    session_end_message,
    session_lease_message,
    state_message,
    status_message,
    subscribe_actions_message,
    wire_message,
)
from pad_lattice.visual_protocol import IDENTITY_ACCENTS, VISUAL_PROTOCOL_VERSION
from pad_lattice.web_protocol import (
    WebProtocolError,
    load_web_protocol_schema,
    surface_message,
    web_error,
    web_message,
)
from pad_lattice.web_surface import BrowserSurfaceServer


class SchemaSurface:
    surface_kind = "midi"
    profile_id = "novation/launchpad/pro-mk1"
    input_name = "Test input"
    output_name = "Test output"
    selector_capacity = 8
    accent_names = IDENTITY_ACCENTS
    visual_protocol = VISUAL_PROTOCOL_VERSION

    def initialize(self) -> None:
        pass

    def render(self, view: SurfaceView) -> None:
        pass

    def poll_events(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


@skipUnless(Draft202012Validator is not None, "install pad-lattice[schema]")
class PublishedSchemaTest(TestCase):
    def test_published_schemas_and_builtin_profiles_validate(self) -> None:
        schemas = (
            load_profile_schema(),
            load_protocol_schema(),
            load_web_protocol_schema(),
        )
        for schema in schemas:
            with self.subTest(schema=schema["title"]):
                Draft202012Validator.check_schema(schema)

        profile_schema = Draft202012Validator(schemas[0])
        paths = sorted(
            Path("src/pad_lattice/device_profiles").glob("**/*.json")
        )
        self.assertGreater(len(paths), 0)
        for path in paths:
            with self.subTest(profile=str(path)):
                profile_schema.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_socket_implementation_matches_published_schema(self) -> None:
        identity = AgentIdentity("codex", "schema-test")
        daemon = PadLatticeDaemon(SchemaSurface(), "/tmp/schema-test.sock")
        self.addCleanup(daemon.close)
        session = daemon.control.update_agent(identity, AgentState.RUNNING, now=1.0)
        state_ack = daemon._state_ack(session)
        messages = (
            state_message(AgentState.RUNNING, agent=identity),
            session_end_message(identity),
            status_message(),
            ping_message(),
            session_lease_message("lease-1", agent=identity),
            subscribe_actions_message(identity),
            preview_message(AgentState.SUCCESS, "preview-1", ttl=2),
            preview_end_message("preview-1"),
            action_message(ControlAction.APPROVE, identity),
            error_message(ProtocolError("bad request")),
            state_ack,
            daemon.status_snapshot(),
            wire_message("pong"),
            wire_message("session_lease_ack", lease_id="lease-1"),
            wire_message(
                "session_lease_bound",
                lease_id="lease-1",
                session=state_ack,
            ),
            wire_message(
                "preview_ack",
                preview_id="preview-1",
                state=AgentState.SUCCESS.value,
            ),
            wire_message("preview_end_ack", preview_id="preview-1"),
        )
        validator = Draft202012Validator(load_protocol_schema())
        for message in messages:
            with self.subTest(message=message["type"]):
                validator.validate(message)

    def test_web_implementation_matches_published_schema(self) -> None:
        server = BrowserSurfaceServer(lambda event: None)
        server.configure_lan("http://192.168.1.10:8765")
        pairing = server.create_pairing()
        view = SurfaceView(
            selected_state=AgentState.WAITING_FOR_APPROVAL,
            sessions=(
                SessionIndicator(
                    slot=0,
                    state=AgentState.WAITING_FOR_APPROVAL,
                    selected=True,
                    accent="cyan",
                    label="Review agent",
                ),
            ),
            available_actions=frozenset(
                {ControlAction.APPROVE, ControlAction.REJECT}
            ),
        )
        messages = (
            web_message("authenticate"),
            web_message("action", action="approve"),
            web_message("select_session", slot=0),
            web_message("create_pairing"),
            web_message("revoke_remote"),
            web_message(
                "authenticated",
                admin=True,
                session_token=None,
                lan_enabled=True,
            ),
            pairing,
            surface_message(view, 8),
            web_message("remote_revoked"),
            web_error(WebProtocolError("bad request")),
        )
        validator = Draft202012Validator(load_web_protocol_schema())
        for message in messages:
            with self.subTest(message=message["type"]):
                validator.validate(message)
