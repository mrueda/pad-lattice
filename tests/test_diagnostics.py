from __future__ import annotations

import contextlib
import io
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.codex_hooks import HOOK_EVENTS
from pad_lattice.devices.profiles import ProfileCatalog, ProfileError
from pad_lattice.diagnostics import (
    collect_diagnostics,
    diagnostics_exit_code,
    print_diagnostics,
)


class DiagnosticsTest(TestCase):
    def test_healthy_report_is_concise_and_privacy_safe(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)
        status = {
            "protocol": 1,
            "type": "status",
            "profile": "novation/launchpad/pro-mk1",
            "sessions": [
                {"session_id": "private-session-id", "metadata": {"cwd": "/private"}}
            ],
        }
        with (
            patch("pad_lattice.diagnostics.ProfileCatalog.load", return_value=catalog),
            patch(
                "pad_lattice.diagnostics.list_midi_ports",
                return_value=(
                    ["Launchpad Pro Standalone Port"],
                    ["Launchpad Pro Standalone Port"],
                ),
            ),
            patch("pad_lattice.diagnostics.request_message", return_value=status),
            patch(
                "pad_lattice.diagnostics.installed_codex_hook_events",
                return_value=HOOK_EVENTS,
            ),
        ):
            report = collect_diagnostics(
                socket_path="/missing-test.sock",
                hooks_path=Path("/tmp/hooks.json"),
            )

        self.assertEqual(report["overall"], "ok")
        self.assertEqual(diagnostics_exit_code(report), 0)
        self.assertNotIn("private-session-id", str(report))
        daemon = next(
            check for check in report["checks"] if check["name"] == "daemon"
        )
        self.assertEqual(daemon["details"]["sessions"], 1)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_diagnostics(report)
        self.assertIn("[OK", output.getvalue())
        self.assertIn("Overall: OK", output.getvalue())

    def test_broken_dependencies_produce_error_report(self) -> None:
        with (
            patch(
                "pad_lattice.diagnostics.ProfileCatalog.load",
                side_effect=ProfileError("bad profile"),
            ),
            patch(
                "pad_lattice.diagnostics.list_midi_ports",
                side_effect=RuntimeError("MIDI backend unavailable"),
            ),
            patch(
                "pad_lattice.diagnostics.request_message",
                side_effect=FileNotFoundError("missing socket"),
            ),
            patch(
                "pad_lattice.diagnostics.installed_codex_hook_events",
                side_effect=ValueError("invalid hooks"),
            ),
        ):
            report = collect_diagnostics()

        self.assertEqual(report["overall"], "error")
        self.assertEqual(diagnostics_exit_code(report), 1)

    def test_report_redacts_home_and_runtime_paths(self) -> None:
        with (
            patch("pad_lattice.diagnostics.Path.home", return_value=Path("/home/alice")),
            patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/run/user/123"}),
            patch(
                "pad_lattice.diagnostics.ProfileCatalog.load",
                side_effect=ProfileError("/home/alice/profile.json is invalid"),
            ),
            patch(
                "pad_lattice.diagnostics.list_midi_ports",
                return_value=([], []),
            ),
            patch(
                "pad_lattice.diagnostics.request_message",
                side_effect=FileNotFoundError("/run/user/123/pad-lattice.sock"),
            ),
            patch(
                "pad_lattice.diagnostics.installed_codex_hook_events",
                return_value=(),
            ),
        ):
            report = collect_diagnostics(
                socket_path="/run/user/123/pad-lattice.sock",
                hooks_path=Path("/home/alice/.codex/hooks.json"),
            )

        serialized = str(report)
        self.assertNotIn("/home/alice", serialized)
        self.assertNotIn("/run/user/123", serialized)
        self.assertIn("~/.codex/hooks.json", serialized)
        self.assertIn("$XDG_RUNTIME_DIR/pad-lattice.sock", serialized)
