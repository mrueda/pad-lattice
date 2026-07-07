from __future__ import annotations

from unittest import TestCase

from pad_lattice.cli import build_parser


class CliTest(TestCase):
    def test_demo_accepts_greeting_delay(self) -> None:
        args = build_parser().parse_args(["demo", "--greeting-delay", "0.12"])

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.greeting_delay, 0.12)

    def test_codex_accepts_pass_through_args(self) -> None:
        args = build_parser().parse_args(
            ["codex", "--approve-keys", "y\\n", "--no-greeting", "--", "resume", "--last"]
        )

        self.assertEqual(args.command, "codex")
        self.assertEqual(args.approve_keys, "y\\n")
        self.assertTrue(args.no_greeting)
        self.assertEqual(args.codex_args, ["--", "resume", "--last"])

    def test_codex_state_detection_is_explicit(self) -> None:
        args = build_parser().parse_args(["codex", "--detect-state"])

        self.assertTrue(args.detect_state)
