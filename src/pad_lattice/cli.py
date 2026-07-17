"""Command-line entrypoint for Pad-Lattice."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

from pad_lattice import __version__
from pad_lattice.codex_hooks import (
    default_codex_hooks_path,
    install_codex_hooks,
    run_codex_hook,
)
from pad_lattice.codex_exec import run_codex_exec
from pad_lattice.daemon import PadLatticeDaemon
from pad_lattice.demo_agent import DemoAgent, run_demo_surface
from pad_lattice.devices.factory import (
    discover_devices,
    open_resolved_surface,
    resolve_device,
)
from pad_lattice.devices.midi_grid import (
    MidiDeviceError,
    list_midi_ports,
    monitor_midi_input,
)
from pad_lattice.devices.profiles import (
    DeviceProfile,
    ProfileCatalog,
    ProfileError,
    load_profile_file,
)
from pad_lattice.devices.testing import run_profile_test
from pad_lattice.events import AgentIdentity, AgentState
from pad_lattice.identity_store import IdentityStore, default_identity_store_path
from pad_lattice.protocol import (
    default_socket_path,
    decode_message,
    encode_message,
    request_message,
    send_message,
    session_end_message,
    state_message,
    status_message,
    subscribe_actions_message,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pad-lattice",
        description="Use a MIDI grid controller as a coding-agent control surface.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ports", help="list MIDI input and output ports")

    subparsers.add_parser("devices", help="detect supported and experimental devices")

    demo = subparsers.add_parser("demo", help="run the hardware demo loop")
    _add_device_arguments(demo)
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
    demo.add_argument(
        "--no-greeting",
        action="store_true",
        help="skip the device startup greeting",
    )

    daemon = subparsers.add_parser("daemon", help="run the hardware sidecar daemon")
    daemon.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    _add_device_arguments(daemon)
    daemon.add_argument(
        "--greeting-delay",
        type=float,
        default=0.08,
        help="seconds between greeting scroll frames",
    )
    daemon.add_argument(
        "--no-greeting",
        action="store_true",
        help="skip the device startup greeting",
    )
    daemon.add_argument(
        "--terminal-hold",
        type=float,
        default=2.0,
        help="seconds to show success/error before returning to waiting",
    )
    daemon.add_argument(
        "--session-ttl",
        type=float,
        default=24 * 60 * 60.0,
        help="seconds before quiet background sessions expire; 0 disables expiry",
    )
    daemon.add_argument(
        "--activity-motion",
        action="store_true",
        help="enable the optional slow running-state activity marker",
    )
    daemon.add_argument(
        "--identity-store",
        type=Path,
        default=default_identity_store_path(),
        help="path for persistent session accent preferences",
    )

    status = subparsers.add_parser("status", help="show daemon and session status")
    status.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    status.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    send_state = subparsers.add_parser("send-state", help="send a state to the daemon")
    send_state.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    send_state.add_argument(
        "state",
        choices=[state.value for state in AgentState],
        help="state to render on the control surface",
    )
    _add_agent_arguments(send_state)

    hook_state = subparsers.add_parser(
        "hook-state", help="send a state from a Codex hook without failing the hook"
    )
    hook_state.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    hook_state.add_argument(
        "state",
        choices=[state.value for state in AgentState],
        help="state to render on the control surface",
    )
    _add_agent_arguments(hook_state)

    end_session = subparsers.add_parser(
        "end-session", help="remove one agent session from the daemon"
    )
    end_session.add_argument(
        "--socket", default=default_socket_path(), help="Unix socket path"
    )
    _add_agent_arguments(end_session)

    codex_hook = subparsers.add_parser(
        "codex-hook", help="process one Codex lifecycle hook event from stdin"
    )
    codex_hook.add_argument("--socket", default=default_socket_path(), help="Unix socket path")

    install_hooks = subparsers.add_parser(
        "install-codex-hooks", help="install lifecycle hooks for interactive Codex"
    )
    install_hooks.add_argument(
        "--path",
        type=Path,
        default=default_codex_hooks_path(),
        help="hooks.json path (default: ~/.codex/hooks.json)",
    )

    listen_actions = subparsers.add_parser(
        "listen-actions", help="print hardware actions from the daemon"
    )
    listen_actions.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    _add_agent_arguments(listen_actions)

    monitor_midi = subparsers.add_parser(
        "monitor-midi", help="print raw MIDI input messages for pad mapping"
    )
    monitor_midi.add_argument("--input", help="MIDI input port name")
    monitor_midi.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="seconds to monitor before exiting",
    )

    codex_exec = subparsers.add_parser(
        "codex-exec", help="run `codex exec --json` and mirror state to the daemon"
    )
    codex_exec.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    codex_exec.add_argument("--codex", default="codex", help="Codex CLI executable")
    codex_exec.add_argument("prompt", nargs=argparse.REMAINDER, help="prompt passed to Codex")

    profile = subparsers.add_parser("profile", help="inspect and test device profiles")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser("list", help="list installed device profiles")

    profile_show = profile_commands.add_parser("show", help="show a device profile")
    profile_show.add_argument("profile_id", help="manufacturer/family/model profile ID")

    profile_validate = profile_commands.add_parser(
        "validate", help="validate a device profile JSON file"
    )
    profile_validate.add_argument("path", type=Path, help="profile JSON file")

    profile_test = profile_commands.add_parser(
        "test", help="run an interactive hardware profile verification"
    )
    profile_test.add_argument(
        "profile_id",
        nargs="?",
        help="manufacturer/family/model profile ID",
    )
    profile_test.add_argument("--profile-file", type=Path, help="profile JSON file")
    profile_test.add_argument("--input", help="MIDI input port name")
    profile_test.add_argument("--output", help="MIDI output port name")
    profile_test.add_argument(
        "--report",
        required=True,
        type=Path,
        help="path for the sanitized JSON test report",
    )
    profile_test.add_argument(
        "--event-timeout",
        type=float,
        default=15.0,
        help="seconds to wait for each requested pad press",
    )
    profile_test.add_argument(
        "--settle-delay",
        type=float,
        default=0.15,
        help="seconds to wait after rendering each visual",
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

        if args.command == "devices":
            candidates = discover_devices()
            if not candidates:
                print("No matching MIDI devices found.")
                return 0
            for candidate in candidates:
                print(
                    f"{candidate.profile.id} [{candidate.profile.status}]\n"
                    f"  input:  {candidate.input_name}\n"
                    f"  output: {candidate.output_name}"
                )
            return 0

        if args.command == "demo":
            agent = DemoAgent(seconds_per_state=args.seconds_per_state)
            device = resolve_device(
                profile_id=args.profile_id,
                profile_file=args.profile_file,
                input_name=args.input,
                output_name=args.output,
            )
            surface = open_resolved_surface(
                device,
                startup_greeting=None if args.no_greeting else "HELLO FROM CODEX CLI",
                scroll_delay=args.greeting_delay,
            )
            run_demo_surface(surface, agent)
            return 0

        if args.command == "daemon":
            device = resolve_device(
                profile_id=args.profile_id,
                profile_file=args.profile_file,
                input_name=args.input,
                output_name=args.output,
            )
            surface = open_resolved_surface(
                device,
                startup_greeting=None if args.no_greeting else "HELLO FROM CODEX CLI",
                scroll_delay=args.greeting_delay,
            )
            PadLatticeDaemon(
                surface,
                args.socket,
                terminal_hold=args.terminal_hold,
                session_ttl=args.session_ttl,
                activity_motion=args.activity_motion,
                identity_store=IdentityStore(args.identity_store),
            ).run()
            return 0

        if args.command == "status":
            status_payload = request_message(args.socket, status_message())
            if args.json:
                print(json.dumps(status_payload, indent=2, sort_keys=True))
            else:
                _print_status(status_payload)
            return 0

        if args.command == "send-state":
            send_message(
                args.socket,
                state_message(AgentState(args.state), agent=_agent_from_args(args)),
            )
            return 0

        if args.command == "hook-state":
            try:
                send_message(
                    args.socket,
                    state_message(AgentState(args.state), agent=_agent_from_args(args)),
                )
            except (ConnectionError, FileNotFoundError, OSError):
                pass
            return 0

        if args.command == "end-session":
            send_message(args.socket, session_end_message(_agent_from_args(args)))
            return 0

        if args.command == "codex-hook":
            return run_codex_hook(args.socket, sys.stdin, sys.stdout)

        if args.command == "install-codex-hooks":
            changed = install_codex_hooks(args.path)
            status = "Installed" if changed else "Already installed"
            print(f"{status}: {args.path}")
            print("Review and trust the hooks with /hooks in Codex.")
            return 0

        if args.command == "listen-actions":
            return listen_actions(args.socket, _agent_from_args(args))

        if args.command == "monitor-midi":
            monitor_midi_input(input_name=args.input, timeout=args.seconds)
            return 0

        if args.command == "codex-exec":
            prompt = args.prompt
            if prompt and prompt[0] == "--":
                prompt = prompt[1:]
            return run_codex_exec(prompt, args.socket, codex_binary=args.codex)

        if args.command == "profile":
            if args.profile_command == "validate":
                validated = load_profile_file(args.path)
                print(f"Valid profile: {validated.id} [{validated.status}]")
                return 0

            if args.profile_command == "test":
                if args.profile_id is None and args.profile_file is None:
                    raise ProfileError(
                        "profile test requires a profile ID or --profile-file"
                    )
                catalog = None if args.profile_file else ProfileCatalog.load()
                device = resolve_device(
                    profile_id=args.profile_id,
                    profile_file=args.profile_file,
                    input_name=args.input,
                    output_name=args.output,
                    catalog=catalog,
                )
                surface = open_resolved_surface(
                    device,
                    startup_greeting=None,
                    scroll_delay=0.0,
                )
                report = run_profile_test(
                    surface,
                    device.profile,
                    args.report,
                    event_timeout=args.event_timeout,
                    settle_delay=args.settle_delay,
                )
                print(f"Profile test report: {args.report}")
                return 0 if report["passed"] else 1

            catalog = ProfileCatalog.load()
            if args.profile_command == "list":
                for installed_profile in catalog.profiles:
                    print(
                        f"{installed_profile.id}\t{installed_profile.status}\t"
                        f"{installed_profile.name}"
                    )
                return 0
            if args.profile_command == "show":
                print(
                    json.dumps(
                        _profile_summary(catalog.get(args.profile_id)),
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
    except (MidiDeviceError, ProfileError) as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except (ConnectionError, FileNotFoundError, OSError) as exc:
        print(f"pad-lattice: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(f"unhandled command: {args.command}")


def listen_actions(socket_path: str, agent: AgentIdentity) -> int:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(encode_message(subscribe_actions_message(agent)))
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


def _add_device_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        dest="profile_id",
        help="manufacturer/family/model device profile ID",
    )
    parser.add_argument("--profile-file", type=Path, help="device profile JSON file")
    parser.add_argument("--input", help="MIDI input port name")
    parser.add_argument("--output", help="MIDI output port name")


def _add_agent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", default="local", help="agent backend identity")
    parser.add_argument("--session-id", default="default", help="agent session identity")


def _agent_from_args(args: argparse.Namespace) -> AgentIdentity:
    return AgentIdentity(args.backend, args.session_id)


def _profile_summary(profile: DeviceProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "manufacturer": profile.manufacturer,
        "family": profile.family,
        "model": profile.model,
        "status": profile.status,
        "driver": profile.driver,
        "visual_protocol": profile.visual_protocol,
        "conformance": sorted(profile.conformance),
        "input_patterns": profile.input_patterns,
        "output_patterns": profile.output_patterns,
        "selector_slots": profile.selector_capacity,
        "text_scroll": profile.text_scroll,
    }


def _print_status(payload: dict[str, object]) -> None:
    selected = payload.get("selected")
    selected_label = "none"
    if isinstance(selected, dict):
        selected_label = f"{selected.get('backend')}/{selected.get('session_id')}"
    print(f"Device: {payload.get('profile')} (Visual Protocol {payload.get('visual_protocol')})")
    print(f"Selected: {selected_label}")
    print(f"Overflow: {payload.get('overflow_count', 0)}")
    sessions = payload.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        print("Sessions: none")
        return
    print("Sessions:")
    for session in sessions:
        if not isinstance(session, dict):
            continue
        marker = "*" if session.get("selected") else "-"
        slot = session.get("slot")
        slot_label = str(int(slot) + 1) if isinstance(slot, int) else "overflow"
        print(
            f"  {marker} slot={slot_label} accent={session.get('accent')} "
            f"state={session.get('state')} "
            f"agent={session.get('backend')}/{session.get('session_id')}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
