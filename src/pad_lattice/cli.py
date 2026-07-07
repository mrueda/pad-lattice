"""Command-line entrypoint for Pad-Lattice."""

from __future__ import annotations

import argparse
import json
import socket
import sys

from pad_lattice.demo_agent import DemoAgent
from pad_lattice.events import AgentState
from pad_lattice.daemon import PadLatticeDaemon
from pad_lattice.launchpad import LaunchpadError, list_midi_ports, open_launchpad, run_surface
from pad_lattice.protocol import (
    default_socket_path,
    decode_message,
    send_message,
    state_message,
    subscribe_actions_message,
)


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

    daemon = subparsers.add_parser("daemon", help="run the Launchpad sidecar daemon")
    daemon.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    daemon.add_argument("--input", help="MIDI input port name")
    daemon.add_argument("--output", help="MIDI output port name")
    daemon.add_argument(
        "--greeting-delay",
        type=float,
        default=0.08,
        help="seconds between greeting scroll frames",
    )
    daemon.add_argument(
        "--no-greeting",
        action="store_true",
        help="skip the Launchpad startup greeting",
    )

    send_state = subparsers.add_parser("send-state", help="send a state to the daemon")
    send_state.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    send_state.add_argument(
        "state",
        choices=[state.value for state in AgentState],
        help="state to render on the Launchpad",
    )

    listen_actions = subparsers.add_parser(
        "listen-actions", help="print Launchpad actions from the daemon"
    )
    listen_actions.add_argument("--socket", default=default_socket_path(), help="Unix socket path")

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

        if args.command == "daemon":
            surface = open_launchpad(
                input_name=args.input,
                output_name=args.output,
                startup_greeting=None if args.no_greeting else "HELLO FROM CODEX CLI",
                scroll_delay=args.greeting_delay,
            )
            PadLatticeDaemon(surface, args.socket).run()
            return 0

        if args.command == "send-state":
            send_message(args.socket, state_message(AgentState(args.state)))
            return 0

        if args.command == "listen-actions":
            return listen_actions(args.socket)
    except KeyboardInterrupt:
        return 130
    except (ConnectionError, FileNotFoundError, OSError) as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1
    except LaunchpadError as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(f"unhandled command: {args.command}")


def listen_actions(socket_path: str) -> int:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(json.dumps(subscribe_actions_message()).encode("utf-8") + b"\n")
        buffer = b""
        while True:
            data = client.recv(4096)
            if not data:
                return 0
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    print(json.dumps(decode_message(line), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
