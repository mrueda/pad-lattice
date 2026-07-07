from __future__ import annotations

from unittest import TestCase

from pad_lattice.cli import build_parser


class CliTest(TestCase):
    def test_demo_accepts_greeting_delay(self) -> None:
        args = build_parser().parse_args(["demo", "--greeting-delay", "0.12"])

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.greeting_delay, 0.12)
