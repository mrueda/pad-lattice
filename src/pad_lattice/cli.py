"""Command-line entrypoint for Pad-Lattice."""

from __future__ import annotations

import argparse
import sys

from pad_lattice.codex_cli import (
    CodexKeymap,
    CodexSupervisor,
    build_codex_command,
    decode_key_sequence,
)
from pad_lattice.demo_agent import DemoAgent
from pad_lattice.launchpad import LaunchpadError, list_midi_ports, open_launchpad, run_surface


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pad-lattice",
        description="Use a Launchpad Pro as a coding-agent control surface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ports", help="list MIDI input and output ports")

    demo = subparsers.add_parser("demo", help="run the Launchpad MVP demo loop")
    demo.add_argument("--input", help="MIDI input port name")
    demo.add_argument("--output", help="MIDI output port name")
    demo.add_argument(
        "--seconds-per-state",
        type=float,
        default=4.0,
        help="seconds before the demo advances to the next state",
    )
    demo.add_argument(
        "--greeting-delay",
        type=float,
        default=0.08,
        help="seconds between greeting scroll frames",
    )

    codex = subparsers.add_parser("codex", help="run Codex CLI under Launchpad control")
    codex.add_argument("--input", help="MIDI input port name")
    codex.add_argument("--output", help="MIDI output port name")
    codex.add_argument(
        "--no-launchpad",
        action="store_true",
        help="run the Codex PTY bridge without opening MIDI hardware",
    )
    codex.add_argument(
        "--greeting-delay",
        type=float,
        default=0.08,
        help="seconds between greeting scroll frames",
    )
    codex.add_argument(
        "--no-greeting",
        action="store_true",
        help="skip the Launchpad startup greeting",
    )
    codex.add_argument(
        "--approve-keys",
        default="\\n",
        help="key sequence sent to Codex for approve, using Python escapes",
    )
    codex.add_argument(
        "--reject-keys",
        default="\\x1b",
        help="key sequence sent to Codex for reject, using Python escapes",
    )
    codex.add_argument(
        "--retry-keys",
        default="r\\n",
        help="key sequence sent to Codex for retry, using Python escapes",
    )
    codex.add_argument(
        "codex_args",
        nargs=argparse.REMAINDER,
        help="arguments passed to Codex CLI; prefix with -- before Codex flags",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "ports":
            inputs, outputs = list_midi_ports()
            print("MIDI inputs:")
            for name in inputs:
                print(f"  {name}")
            print("MIDI outputs:")
            for name in outputs:
                print(f"  {name}")
            return 0

        if args.command == "demo":
            agent = DemoAgent(seconds_per_state=args.seconds_per_state)
            surface = open_launchpad(
                input_name=args.input,
                output_name=args.output,
                scroll_delay=args.greeting_delay,
            )
            run_surface(surface, agent.current_state, agent.action_logger())
            return 0

        if args.command == "codex":
            surface = None
            if not args.no_launchpad:
                surface = open_launchpad(
                    input_name=args.input,
                    output_name=args.output,
                    startup_greeting=None if args.no_greeting else "HELLO FROM CODEX CLI",
                    scroll_delay=args.greeting_delay,
                )
            supervisor = CodexSupervisor(
                build_codex_command(args.codex_args),
                surface=surface,
                keymap=CodexKeymap(
                    approve=decode_key_sequence(args.approve_keys),
                    reject=decode_key_sequence(args.reject_keys),
                    retry=decode_key_sequence(args.retry_keys),
                ),
            )
            return supervisor.run()
    except KeyboardInterrupt:
        return 130
    except LaunchpadError as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
