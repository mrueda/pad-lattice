from __future__ import annotations

import contextlib
import io
from unittest import TestCase

from pad_lattice import __version__
from pad_lattice.cli import build_parser


class CliTest(TestCase):
    def test_version_is_available_without_a_subcommand(self) -> None:
        output = io.StringIO()

        with (
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            build_parser().parse_args(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue(), f"pad-lattice {__version__}\n")

    def test_demo_accepts_greeting_delay(self) -> None:
        args = build_parser().parse_args(
            [
                "demo",
                "--profile",
                "novation/launchpad/pro-mk1",
                "--greeting-delay",
                "0.12",
                "--no-greeting",
            ]
        )

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.greeting_delay, 0.12)
        self.assertTrue(args.no_greeting)
        self.assertEqual(args.profile_id, "novation/launchpad/pro-mk1")

    def test_daemon_accepts_socket_and_no_greeting(self) -> None:
        args = build_parser().parse_args(
            [
                "daemon",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--no-greeting",
                "--terminal-hold",
                "1.5",
            ]
        )

        self.assertEqual(args.command, "daemon")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertTrue(args.no_greeting)
        self.assertEqual(args.terminal_hold, 1.5)

    def test_send_state_accepts_agent_state(self) -> None:
        args = build_parser().parse_args(["send-state", "waiting_for_reply"])

        self.assertEqual(args.command, "send-state")
        self.assertEqual(args.state, "waiting_for_reply")

    def test_hook_state_accepts_agent_state(self) -> None:
        args = build_parser().parse_args(["hook-state", "running"])

        self.assertEqual(args.command, "hook-state")
        self.assertEqual(args.state, "running")

    def test_codex_hook_accepts_socket(self) -> None:
        args = build_parser().parse_args(
            ["codex-hook", "--socket", "/tmp/pad-lattice.sock"]
        )

        self.assertEqual(args.command, "codex-hook")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")

    def test_install_codex_hooks_accepts_path(self) -> None:
        args = build_parser().parse_args(
            ["install-codex-hooks", "--path", "/tmp/hooks.json"]
        )

        self.assertEqual(args.command, "install-codex-hooks")
        self.assertEqual(str(args.path), "/tmp/hooks.json")

    def test_listen_actions_accepts_socket(self) -> None:
        args = build_parser().parse_args(
            [
                "listen-actions",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--backend",
                "codex",
                "--session-id",
                "session-123",
            ]
        )

        self.assertEqual(args.command, "listen-actions")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertEqual(args.backend, "codex")
        self.assertEqual(args.session_id, "session-123")

    def test_codex_exec_accepts_prompt(self) -> None:
        args = build_parser().parse_args(
            ["codex-exec", "--socket", "/tmp/pad-lattice.sock", "say", "hello"]
        )

        self.assertEqual(args.command, "codex-exec")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertEqual(args.prompt, ["say", "hello"])

    def test_monitor_midi_accepts_input_and_timeout(self) -> None:
        args = build_parser().parse_args(
            ["monitor-midi", "--input", "Launchpad Pro", "--seconds", "3"]
        )

        self.assertEqual(args.command, "monitor-midi")
        self.assertEqual(args.input, "Launchpad Pro")
        self.assertEqual(args.seconds, 3.0)

    def test_profile_test_accepts_experimental_profile_and_report(self) -> None:
        args = build_parser().parse_args(
            [
                "profile",
                "test",
                "novation/launchpad/mini-mk3",
                "--report",
                "/tmp/mini-report.json",
            ]
        )

        self.assertEqual(args.profile_command, "test")
        self.assertEqual(args.profile_id, "novation/launchpad/mini-mk3")
        self.assertEqual(str(args.report), "/tmp/mini-report.json")

    def test_profile_validate_accepts_json_path(self) -> None:
        args = build_parser().parse_args(["profile", "validate", "profile.json"])

        self.assertEqual(args.profile_command, "validate")
        self.assertEqual(str(args.path), "profile.json")
