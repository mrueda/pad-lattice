from __future__ import annotations

import io
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.codex_session import (
    SessionLease,
    normalize_session_label,
    run_codex_session,
)
from pad_lattice.events import AgentIdentity


class CodexSessionTest(TestCase):
    def test_label_validation_rejects_empty_long_and_control_text(self) -> None:
        self.assertEqual(normalize_session_label("  docs  "), "docs")
        with self.assertRaises(ValueError):
            normalize_session_label("   ")
        with self.assertRaises(ValueError):
            normalize_session_label("x" * 65)
        with self.assertRaises(ValueError):
            normalize_session_label("docs\nrelease")

    def test_launcher_inherits_stdio_and_passes_codex_arguments(self) -> None:
        lease = SimpleNamespace(
            start=lambda: None,
            wait_for_first_attempt=lambda: True,
            close=lambda: None,
        )
        process = SimpleNamespace(wait=lambda: 17)

        with (
            patch("pad_lattice.codex_session.SessionLease", return_value=lease),
            patch(
                "pad_lattice.codex_session.uuid.uuid4",
                return_value=SimpleNamespace(hex="lease-123"),
            ),
            patch(
                "pad_lattice.codex_session.subprocess.Popen",
                return_value=process,
            ) as popen,
        ):
            result = run_codex_session(
                ["resume", "session-123"],
                "/tmp/pad-lattice.sock",
                label="docs",
                codex_binary="/opt/codex",
            )

        self.assertEqual(result, 17)
        command = popen.call_args.args[0]
        options = popen.call_args.kwargs
        self.assertEqual(
            command,
            [
                "/opt/codex",
                "-c",
                "tui.terminal_title=[]",
                "resume",
                "session-123",
            ],
        )
        self.assertNotIn("stdin", options)
        self.assertNotIn("stdout", options)
        self.assertNotIn("stderr", options)
        self.assertEqual(options["env"]["PAD_LATTICE_LEASE_ID"], "lease-123")
        self.assertEqual(options["env"]["PAD_LATTICE_LABEL"], "docs")
        self.assertEqual(
            options["env"]["PAD_LATTICE_SOCKET"],
            "/tmp/pad-lattice.sock",
        )

    def test_launcher_closes_lease_when_codex_spawn_fails(self) -> None:
        closed = []
        lease = SimpleNamespace(
            start=lambda: None,
            wait_for_first_attempt=lambda: True,
            close=lambda: closed.append(True),
        )

        with (
            patch("pad_lattice.codex_session.SessionLease", return_value=lease),
            patch(
                "pad_lattice.codex_session.subprocess.Popen",
                side_effect=FileNotFoundError("codex"),
            ),
            self.assertRaises(FileNotFoundError),
        ):
            run_codex_session([], "/tmp/pad-lattice.sock")

        self.assertEqual(closed, [True])

    def test_unavailable_daemon_warns_but_still_launches_codex(self) -> None:
        lease = SimpleNamespace(
            start=lambda: None,
            wait_for_first_attempt=lambda: False,
            close=lambda: None,
        )
        process = SimpleNamespace(wait=lambda: 0)
        stderr = io.StringIO()

        with (
            patch("pad_lattice.codex_session.SessionLease", return_value=lease),
            patch("pad_lattice.codex_session.subprocess.Popen", return_value=process),
        ):
            result = run_codex_session(
                [],
                "/tmp/missing.sock",
                terminal_title=False,
                stderr=stderr,
            )

        self.assertEqual(result, 0)
        self.assertIn("daemon unavailable", stderr.getvalue())

    def test_launcher_does_not_inherit_label_or_title_flags(self) -> None:
        lease = SimpleNamespace(
            start=lambda: None,
            wait_for_first_attempt=lambda: True,
            close=lambda: None,
        )
        process = SimpleNamespace(wait=lambda: 0)

        with (
            patch.dict(
                "os.environ",
                {
                    "PAD_LATTICE_LABEL": "stale",
                    "PAD_LATTICE_TERMINAL_TITLE": "1",
                },
                clear=False,
            ),
            patch("pad_lattice.codex_session.SessionLease", return_value=lease),
            patch(
                "pad_lattice.codex_session.subprocess.Popen",
                return_value=process,
            ) as popen,
        ):
            run_codex_session(
                [],
                "/tmp/pad-lattice.sock",
                terminal_title=False,
            )

        environment = popen.call_args.kwargs["env"]
        self.assertNotIn("PAD_LATTICE_LABEL", environment)
        self.assertNotIn("PAD_LATTICE_TERMINAL_TITLE", environment)

    def test_lease_remembers_bound_agent_for_reconnect(self) -> None:
        lease = SessionLease("/tmp/pad-lattice.sock", "lease-1", {})

        lease._remember_binding(
            {
                "type": "session_lease_bound",
                "session": {
                    "backend": "codex",
                    "session_id": "session-123",
                },
            }
        )

        self.assertEqual(
            lease._known_agent,
            AgentIdentity("codex", "session-123"),
        )
