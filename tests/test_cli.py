from __future__ import annotations

from unittest import TestCase

from pad_lattice.cli import build_parser


class CliTest(TestCase):
    def test_demo_accepts_greeting_delay(self) -> None:
        args = build_parser().parse_args(["demo", "--greeting-delay", "0.12"])

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.greeting_delay, 0.12)

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

    def test_listen_actions_accepts_socket(self) -> None:
        args = build_parser().parse_args(
            ["listen-actions", "--socket", "/tmp/pad-lattice.sock"]
        )

        self.assertEqual(args.command, "listen-actions")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")

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
