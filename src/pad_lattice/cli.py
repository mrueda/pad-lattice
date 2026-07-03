"""Command-line entrypoint for PadLattice."""

from __future__ import annotations

import argparse
import sys

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
            surface = open_launchpad(input_name=args.input, output_name=args.output)
            run_surface(surface, agent.current_state, agent.action_logger())
            return 0
    except KeyboardInterrupt:
        return 130
    except LaunchpadError as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
