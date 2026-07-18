from __future__ import annotations

import contextlib
import io
from unittest import TestCase
from unittest.mock import Mock, patch

from pad_lattice import __version__
from pad_lattice.cli import _print_status, build_parser, cycle_symbols, main
from pad_lattice.events import AgentState


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

    def test_demo_accepts_device_and_greeting_options(self) -> None:
        args = build_parser().parse_args(
            [
                "demo",
                "--profile",
                "novation/launchpad/pro-mk1",
                "--greeting-delay",
                "0.12",
                "--no-greeting",
                "--audio",
            ]
        )

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.greeting_delay, 0.12)
        self.assertTrue(args.no_greeting)
        self.assertTrue(args.audio)
        self.assertEqual(args.profile_id, "novation/launchpad/pro-mk1")

    def test_demo_audio_speaks_the_visual_greeting(self) -> None:
        surface = Mock(
            startup_greeting="HELLO FROM CODEX CLI",
            startup_greeting_duration=10.32,
        )
        feedback = Mock()
        with (
            patch("pad_lattice.cli.resolve_device", return_value=object()),
            patch("pad_lattice.cli.open_resolved_surface", return_value=surface),
            patch("pad_lattice.cli.SystemAudioFeedback", return_value=feedback),
            patch("pad_lattice.cli.run_demo_surface") as run_demo,
        ):
            result = main(["demo", "--audio"])

        self.assertEqual(result, 0)
        feedback.speak.assert_called_once_with(
            "HELLO FROM CODEX CLI",
            duration=10.32,
        )
        run_demo.assert_called_once_with(surface, audio_feedback=feedback)

    def test_daemon_audio_speaks_the_visual_greeting(self) -> None:
        surface = Mock(
            startup_greeting="HELLO FROM CODEX CLI",
            startup_greeting_duration=10.32,
            selector_capacity=8,
            accent_names=("cyan",),
        )
        feedback = Mock()
        daemon = Mock()
        with (
            patch("pad_lattice.cli.resolve_device", return_value=object()),
            patch("pad_lattice.cli.open_resolved_surface", return_value=surface),
            patch("pad_lattice.cli.SystemAudioFeedback", return_value=feedback),
            patch("pad_lattice.cli.PadLatticeDaemon", return_value=daemon),
        ):
            result = main(["daemon", "--audio-feedback"])

        self.assertEqual(result, 0)
        feedback.speak.assert_called_once_with(
            "HELLO FROM CODEX CLI",
            duration=10.32,
        )
        daemon.run.assert_called_once_with()

    def test_show_accepts_device_and_tempo_options(self) -> None:
        args = build_parser().parse_args(
            [
                "show",
                "--profile",
                "novation/launchpad/pro-mk1",
                "--tempo",
                "1.25",
                "--audio",
            ]
        )

        self.assertEqual(args.command, "show")
        self.assertEqual(args.tempo, 1.25)
        self.assertTrue(args.audio)
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
                "--session-ttl",
                "3600",
                "--activity-motion",
                "--audio-feedback",
            ]
        )

        self.assertEqual(args.command, "daemon")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertTrue(args.no_greeting)
        self.assertEqual(args.terminal_hold, 1.5)
        self.assertEqual(args.session_ttl, 3600.0)
        self.assertTrue(args.activity_motion)
        self.assertTrue(args.audio_feedback)

    def test_status_supports_json_output(self) -> None:
        args = build_parser().parse_args(
            ["status", "--socket", "/tmp/pad-lattice.sock", "--json"]
        )

        self.assertEqual(args.command, "status")
        self.assertTrue(args.json)

    def test_doctor_supports_machine_readable_output(self) -> None:
        args = build_parser().parse_args(
            [
                "doctor",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--hooks-path",
                "/tmp/hooks.json",
                "--json",
            ]
        )

        self.assertEqual(args.command, "doctor")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertEqual(str(args.hooks_path), "/tmp/hooks.json")
        self.assertTrue(args.json)

    def test_status_supports_a_live_legend(self) -> None:
        args = build_parser().parse_args(
            ["status", "--watch", "--interval", "0.25"]
        )

        self.assertTrue(args.watch)
        self.assertEqual(args.interval, 0.25)

    def test_symbols_supports_a_custom_hold(self) -> None:
        args = build_parser().parse_args(["symbols", "--hold", "0.5"])

        self.assertEqual(args.command, "symbols")
        self.assertEqual(args.hold, 0.5)

    def test_end_session_accepts_agent_identity(self) -> None:
        args = build_parser().parse_args(
            [
                "end-session",
                "--backend",
                "codex",
                "--session-id",
                "session-123",
            ]
        )

        self.assertEqual(args.command, "end-session")
        self.assertEqual(args.backend, "codex")
        self.assertEqual(args.session_id, "session-123")

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
            [
                "codex-hook",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--approval-timeout",
                "30",
            ]
        )

        self.assertEqual(args.command, "codex-hook")
        self.assertEqual(args.socket, "/tmp/pad-lattice.sock")
        self.assertEqual(args.approval_timeout, 30.0)

    def test_install_codex_hooks_accepts_path(self) -> None:
        args = build_parser().parse_args(
            [
                "install-codex-hooks",
                "--path",
                "/tmp/hooks.json",
                "--socket",
                "/tmp/custom.sock",
            ]
        )

        self.assertEqual(args.command, "install-codex-hooks")
        self.assertEqual(str(args.path), "/tmp/hooks.json")
        self.assertEqual(args.socket, "/tmp/custom.sock")

    def test_codex_launcher_passes_resume_arguments_after_separator(self) -> None:
        args = build_parser().parse_args(
            [
                "codex",
                "--label",
                "docs",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--",
                "resume",
                "session-123",
            ]
        )

        self.assertEqual(args.command, "codex")
        self.assertEqual(args.label, "docs")
        self.assertEqual(args.codex_args, ["--", "resume", "session-123"])

    def test_listen_actions_accepts_socket(self) -> None:
        args = build_parser().parse_args(
            [
                "listen-actions",
                "--once",
                "--socket",
                "/tmp/pad-lattice.sock",
                "--backend",
                "codex",
                "--session-id",
                "session-123",
            ]
        )

        self.assertEqual(args.command, "listen-actions")
        self.assertTrue(args.once)
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
        args = build_parser().parse_args(
            [
                "profile",
                "validate",
                "profile.json",
                "--validate-schema",
            ]
        )

        self.assertEqual(args.profile_command, "validate")
        self.assertEqual(str(args.path), "profile.json")
        self.assertTrue(args.validate_schema)

    def test_status_legend_includes_scene_label_and_lease(self) -> None:
        output = io.StringIO()

        _print_status(
            {
                "profile": "test/grid",
                "visual_protocol": 1,
                "selected": {"backend": "codex", "session_id": "session-123"},
                "overflow_count": 0,
                "sessions": [
                    {
                        "backend": "codex",
                        "session_id": "session-123",
                        "slot": 1,
                        "accent": "magenta",
                        "state": "waiting_for_approval",
                        "selected": True,
                        "leased": True,
                        "label": "docs",
                        "metadata": {"cwd": "/work/pad-lattice"},
                    }
                ],
            },
            stream=output,
            color=False,
        )

        legend = output.getvalue()
        self.assertIn("S2", legend)
        self.assertIn("magenta", legend)
        self.assertIn("docs", legend)
        self.assertIn("pad-lattice", legend)
        self.assertIn("live", legend)

    def test_symbol_cycle_uses_a_temporary_display_preview(self) -> None:
        sent = []
        output = io.StringIO()

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def request(self, message):
                sent.append(message)
                if message["type"] == "preview":
                    return {
                        "type": "preview_ack",
                        "preview_id": message["preview_id"],
                    }
                return {
                    "type": "preview_end_ack",
                    "preview_id": message["preview_id"],
                }

        result = cycle_symbols(
            "/tmp/pad-lattice.sock",
            hold=0.5,
            sleep=lambda delay: None,
            stream=output,
            connector=lambda path: FakeConnection(),
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            [message["state"] for message in sent[:-1]],
            [state.value for state in AgentState],
        )
        self.assertTrue(all(message["type"] == "preview" for message in sent[:-1]))
        self.assertEqual(sent[-1]["type"], "preview_end")
        self.assertEqual(
            {message["preview_id"] for message in sent},
            {sent[0]["preview_id"]},
        )
