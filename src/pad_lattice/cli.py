"""Command-line entrypoint for Pad-Lattice."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
import uuid
import webbrowser
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TextIO

from pad_lattice import __version__
from pad_lattice.audio import SystemAudioFeedback
from pad_lattice.codex_hooks import (
    default_codex_hooks_path,
    remove_codex_hooks,
    run_codex_hook,
)
from pad_lattice.codex_exec import run_codex_exec
from pad_lattice.codex_session import run_codex_session
from pad_lattice.daemon_runtime import PadLatticeDaemon
from pad_lattice.demo_agent import run_demo_surface
from pad_lattice.diagnostics import (
    collect_diagnostics,
    diagnostics_exit_code,
    print_diagnostics,
)
from pad_lattice.devices.factory import (
    discover_devices,
    open_resolved_surface,
    resolve_device,
)
from pad_lattice.devices.composite import CompositeSurface
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
    JsonLineConnection,
    MAX_PREVIEW_TTL,
    default_socket_path,
    open_message_connection,
    preview_end_message,
    preview_message,
    request_message,
    send_message,
    session_end_message,
    state_message,
    status_message,
    subscribe_actions_message,
)
from pad_lattice.show import run_show_surface
from pad_lattice.visual_protocol import ACCENT_RGB
from pad_lattice.web_surface import WebSurface


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pad-lattice",
        description="Use physical and virtual pads as coding-agent control surfaces.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ports", help="list MIDI input and output ports")

    subparsers.add_parser("devices", help="detect supported and experimental devices")

    doctor = subparsers.add_parser("doctor", help="inspect the local installation")
    doctor.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    doctor.add_argument(
        "--hooks-path",
        type=Path,
        default=default_codex_hooks_path(),
        help="legacy Codex hooks.json path",
    )
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    demo = subparsers.add_parser("demo", help="run a guided hardware conversation")
    _add_device_arguments(demo)
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
    demo.add_argument(
        "--audio",
        action="store_true",
        help="play the default semantic sounds during the conversation",
    )

    show = subparsers.add_parser(
        "show",
        help="play an authored full-surface visual performance",
    )
    _add_device_arguments(show)
    show.add_argument(
        "--tempo",
        type=float,
        default=1.0,
        help="performance speed multiplier; default 1.0",
    )
    show.add_argument(
        "--audio",
        action="store_true",
        help="play the synchronized score through the computer",
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
        "--audio-feedback",
        action="store_true",
        help="play short semantic sounds for states and surface actions",
    )
    daemon.add_argument(
        "--identity-store",
        type=Path,
        default=default_identity_store_path(),
        help="path for persistent session accent preferences",
    )
    daemon.add_argument(
        "--web",
        action="store_true",
        help="mirror the physical surface in a local browser",
    )
    _add_web_arguments(daemon)

    web = subparsers.add_parser(
        "web",
        help="run a virtual browser surface without MIDI hardware",
    )
    web.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    web.add_argument(
        "--terminal-hold",
        type=float,
        default=2.0,
        help="seconds to show success/error before returning to waiting",
    )
    web.add_argument(
        "--session-ttl",
        type=float,
        default=24 * 60 * 60.0,
        help="seconds before quiet background sessions expire; 0 disables expiry",
    )
    web.add_argument(
        "--activity-motion",
        action="store_true",
        help="enable the optional slow running-state activity marker",
    )
    web.add_argument(
        "--audio-feedback",
        action="store_true",
        help="play short semantic sounds for states and browser actions",
    )
    web.add_argument(
        "--identity-store",
        type=Path,
        default=default_identity_store_path(),
        help="path for persistent session accent preferences",
    )
    _add_web_arguments(web)

    status = subparsers.add_parser("status", help="show daemon and session status")
    status.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    status_output = status.add_mutually_exclusive_group()
    status_output.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    status_output.add_argument(
        "--watch", action="store_true", help="continuously refresh the session legend"
    )
    status.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="seconds between --watch updates",
    )

    symbols = subparsers.add_parser(
        "symbols", help="cycle all state glyphs on the selected session"
    )
    symbols.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    symbols.add_argument(
        "--hold",
        type=float,
        default=0.7,
        help="seconds to display each glyph",
    )

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
    codex_hook.add_argument(
        "--approval-timeout",
        type=float,
        default=60.0,
        help="seconds to wait for a hardware approval decision",
    )

    uninstall_hooks = subparsers.add_parser(
        "uninstall-codex-hooks",
        help="remove legacy global Pad-Lattice hooks",
    )
    uninstall_hooks.add_argument(
        "--path",
        type=Path,
        default=default_codex_hooks_path(),
        help="legacy hooks.json path (default: ~/.codex/hooks.json)",
    )

    listen_actions = subparsers.add_parser(
        "listen-actions", help="print hardware actions from the daemon"
    )
    listen_actions.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    listen_actions.add_argument(
        "--once",
        action="store_true",
        help="exit after receiving one hardware action",
    )
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

    codex = subparsers.add_parser(
        "codex", help="run interactive Codex with labels and automatic cleanup"
    )
    codex.add_argument("--socket", default=default_socket_path(), help="Unix socket path")
    codex.add_argument("--codex", default="codex", help="Codex CLI executable")
    codex.add_argument("--label", help="human-readable session label")
    codex.add_argument(
        "--approval-timeout",
        type=float,
        default=60.0,
        help="seconds before falling back to Codex's keyboard approval prompt",
    )
    codex.add_argument(
        "--no-terminal-title",
        action="store_true",
        help="leave Codex's terminal title behavior unchanged",
    )
    codex.add_argument(
        "codex_args",
        nargs=argparse.REMAINDER,
        help="arguments passed unchanged to interactive Codex",
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
    profile_validate.add_argument(
        "--validate-schema",
        action="store_true",
        help="also run the optional JSON Schema dry-run check",
    )

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

        if args.command == "doctor":
            report = collect_diagnostics(
                socket_path=args.socket,
                hooks_path=args.hooks_path,
            )
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print_diagnostics(report)
            return diagnostics_exit_code(report)

        if args.command == "demo":
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
            audio_feedback = None
            try:
                audio_feedback = SystemAudioFeedback() if args.audio else None
                if audio_feedback is not None and surface.startup_greeting:
                    audio_feedback.speak(
                        surface.startup_greeting,
                        duration=surface.startup_greeting_duration,
                    )
            except BaseException:
                if audio_feedback is not None:
                    audio_feedback.close()
                surface.close()
                raise
            run_demo_surface(surface, audio_feedback=audio_feedback)
            return 0

        if args.command == "show":
            if args.tempo <= 0:
                raise ValueError("show tempo must be positive")
            device = resolve_device(
                profile_id=args.profile_id,
                profile_file=args.profile_file,
                input_name=args.input,
                output_name=args.output,
            )
            surface = open_resolved_surface(
                device,
                startup_greeting=None,
                scroll_delay=0.08,
            )
            run_show_surface(surface, tempo=args.tempo, audio=args.audio)
            return 0

        if args.command == "daemon":
            if (args.lan or args.advertise_host) and not args.web:
                raise ValueError("--lan and --advertise-host require --web")
            device = resolve_device(
                profile_id=args.profile_id,
                profile_file=args.profile_file,
                input_name=args.input,
                output_name=args.output,
            )
            midi_surface = open_resolved_surface(
                device,
                startup_greeting=None if args.no_greeting else "HELLO FROM CODEX CLI",
                scroll_delay=args.greeting_delay,
            )
            web_surface = None
            surface = midi_surface
            if args.web:
                try:
                    web_surface = _open_web_surface(args)
                    surface = CompositeSurface((web_surface, midi_surface))
                except BaseException:
                    midi_surface.close()
                    raise
            try:
                audio_feedback = (
                    SystemAudioFeedback() if args.audio_feedback else None
                )
            except BaseException:
                surface.close()
                raise
            daemon = PadLatticeDaemon(
                surface,
                args.socket,
                terminal_hold=args.terminal_hold,
                session_ttl=args.session_ttl,
                activity_motion=args.activity_motion,
                identity_store=IdentityStore(args.identity_store),
                audio_feedback=audio_feedback,
            )
            try:
                if audio_feedback is not None and midi_surface.startup_greeting:
                    audio_feedback.speak(
                        midi_surface.startup_greeting,
                        duration=midi_surface.startup_greeting_duration,
                    )
            except BaseException:
                daemon.close()
                raise
            daemon.run()
            return 0

        if args.command == "web":
            surface = _open_web_surface(args)
            try:
                audio_feedback = (
                    SystemAudioFeedback() if args.audio_feedback else None
                )
            except BaseException:
                surface.close()
                raise
            daemon = PadLatticeDaemon(
                surface,
                args.socket,
                terminal_hold=args.terminal_hold,
                session_ttl=args.session_ttl,
                activity_motion=args.activity_motion,
                identity_store=IdentityStore(args.identity_store),
                audio_feedback=audio_feedback,
            )
            daemon.run()
            return 0

        if args.command == "status":
            if args.interval <= 0:
                raise ValueError("status interval must be positive")
            if args.watch:
                return watch_status(args.socket, interval=args.interval)
            status_payload = request_message(args.socket, status_message())
            if args.json:
                print(json.dumps(status_payload, indent=2, sort_keys=True))
            else:
                _print_status(status_payload)
            return 0

        if args.command == "symbols":
            return cycle_symbols(args.socket, hold=args.hold)

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
            return run_codex_hook(
                args.socket,
                sys.stdin,
                sys.stdout,
                approval_timeout=args.approval_timeout,
            )

        if args.command == "uninstall-codex-hooks":
            changed = remove_codex_hooks(args.path)
            status = "Removed" if changed else "No Pad-Lattice hooks found"
            print(f"{status}: {args.path}")
            return 0

        if args.command == "listen-actions":
            return listen_actions(args.socket, _agent_from_args(args), once=args.once)

        if args.command == "monitor-midi":
            monitor_midi_input(input_name=args.input, timeout=args.seconds)
            return 0

        if args.command == "codex":
            codex_args = args.codex_args
            if codex_args and codex_args[0] == "--":
                codex_args = codex_args[1:]
            return run_codex_session(
                codex_args,
                args.socket,
                label=args.label,
                codex_binary=args.codex,
                terminal_title=not args.no_terminal_title,
                approval_timeout=args.approval_timeout,
            )

        if args.command == "codex-exec":
            prompt = args.prompt
            if prompt and prompt[0] == "--":
                prompt = prompt[1:]
            return run_codex_exec(prompt, args.socket, codex_binary=args.codex)

        if args.command == "profile":
            if args.profile_command == "validate":
                validated = load_profile_file(
                    args.path,
                    validate_schema=args.validate_schema,
                )
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


def listen_actions(
    socket_path: str,
    agent: AgentIdentity,
    *,
    once: bool = False,
) -> int:
    with open_message_connection(socket_path, timeout=None) as connection:
        connection.send(subscribe_actions_message(agent))
        while True:
            try:
                message = connection.receive()
            except ConnectionError:
                return 0
            print(json.dumps(message, separators=(",", ":")), flush=True)
            if once:
                return 0


def _add_device_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        dest="profile_id",
        help="manufacturer/family/model device profile ID",
    )
    parser.add_argument("--profile-file", type=Path, help="device profile JSON file")
    parser.add_argument("--input", help="MIDI input port name")
    parser.add_argument("--output", help="MIDI output port name")


def _add_web_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--lan",
        action="store_true",
        help="allow explicitly paired browsers on the trusted local network",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="browser surface TCP port; default 8765",
    )
    parser.add_argument(
        "--advertise-host",
        help="LAN hostname or address encoded in pairing links",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do not open the local browser automatically",
    )


def _open_web_surface(args: argparse.Namespace) -> WebSurface:
    if not 0 <= args.port <= 65535:
        raise ValueError("web port must be from 0 to 65535")
    if args.advertise_host and not args.lan:
        raise ValueError("--advertise-host requires --lan")
    surface = WebSurface(
        host="0.0.0.0" if args.lan else "127.0.0.1",
        port=args.port,
    )
    try:
        surface.initialize()
        if args.lan:
            advertised_host = args.advertise_host or _discover_lan_host()
            base_url = f"http://{advertised_host}:{surface.server.actual_port}"
            surface.configure_lan(base_url)
            pairing = surface.create_pairing()
            print(f"Virtual surface: {surface.local_url}")
            print(f"Phone/tablet:   {base_url}")
            print(f"Pairing PIN:   {pairing['pin']} (expires in 5 minutes)")
            print("Trusted LAN only. Do not expose or port-forward this server.")
        else:
            print(f"Virtual surface: {surface.local_url}")
        if not args.no_open:
            try:
                webbrowser.open(surface.local_url)
            except webbrowser.Error:
                pass
        return surface
    except BaseException:
        surface.close()
        raise


def _discover_lan_host() -> str:
    candidates: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            candidates.append(str(probe.getsockname()[0]))
    except OSError:
        pass
    try:
        candidates.extend(
            str(item[4][0])
            for item in socket.getaddrinfo(
                socket.gethostname(),
                None,
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
            )
        )
    except OSError:
        pass
    for candidate in dict.fromkeys(candidates):
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_private and not address.is_loopback and not address.is_link_local:
            return candidate
    raise ValueError("could not discover a private LAN address; pass --advertise-host")


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


def cycle_symbols(
    socket_path: str,
    *,
    hold: float = 0.7,
    sleep: Callable[[float], None] = time.sleep,
    stream: TextIO | None = None,
    connector: Callable[
        [str], AbstractContextManager[JsonLineConnection]
    ] = open_message_connection,
) -> int:
    """Preview every state glyph without changing authoritative agent state."""

    if hold <= 0:
        raise ValueError("symbol hold must be positive")
    if hold >= MAX_PREVIEW_TTL:
        raise ValueError(
            f"symbol hold must be less than {MAX_PREVIEW_TTL:g} seconds"
        )
    if stream is None:
        stream = sys.stdout

    preview_id = uuid.uuid4().hex
    ttl = hold + 1.0
    with connector(socket_path) as connection:
        active = False
        try:
            for state in AgentState:
                response = connection.request(
                    preview_message(state, preview_id, ttl=ttl)
                )
                _expect_response(response, "preview_ack")
                active = True
                print(state.value, file=stream, flush=True)
                sleep(hold)
        finally:
            if active:
                response = connection.request(
                    preview_end_message(preview_id)
                )
                _expect_response(response, "preview_end_ack")
    return 0


def _expect_response(response: object, expected_type: str) -> None:
    if not isinstance(response, dict):
        raise ValueError("daemon returned an invalid response")
    if response.get("type") == "error":
        raise ValueError(str(response.get("error", "daemon rejected the request")))
    if response.get("type") != expected_type:
        raise ValueError(
            f"daemon returned {response.get('type')!r}; expected {expected_type!r}"
        )


def watch_status(
    socket_path: str,
    *,
    interval: float = 0.5,
    stream: TextIO | None = None,
) -> int:
    """Render a stable, colorized multi-agent legend until interrupted."""

    if interval <= 0:
        raise ValueError("status interval must be positive")
    if stream is None:
        stream = sys.stdout
    while True:
        payload = request_message(socket_path, status_message())
        if _stream_is_tty(stream):
            stream.write("\x1b[H\x1b[J")
        _print_status(payload, stream=stream)
        stream.flush()
        time.sleep(interval)


def _print_status(
    payload: dict[str, object],
    *,
    stream: TextIO | None = None,
    color: bool | None = None,
) -> None:
    if stream is None:
        stream = sys.stdout
    selected = payload.get("selected")
    selected_label = "none"
    if isinstance(selected, dict):
        selected_label = f"{selected.get('backend')}/{selected.get('session_id')}"
    print(
        f"Surface profile: {payload.get('profile')} "
        f"(Visual Protocol {payload.get('visual_protocol')})",
        file=stream,
    )
    surfaces = payload.get("surfaces")
    if isinstance(surfaces, list) and surfaces:
        labels = [
            f"{item.get('kind')}:{item.get('profile')}"
            for item in surfaces
            if isinstance(item, dict)
        ]
        if labels:
            print(f"Surfaces: {', '.join(labels)}", file=stream)
    print(f"Selected: {selected_label}", file=stream)
    print(f"Overflow: {payload.get('overflow_count', 0)}", file=stream)
    print(
        "Audio feedback: "
        f"{'on' if payload.get('audio_feedback') else 'off'}",
        file=stream,
    )
    sessions = payload.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        print("Sessions: none", file=stream)
        return
    use_color = (
        _stream_is_tty(stream) and "NO_COLOR" not in os.environ
        if color is None
        else color
    )
    print("Sessions:", file=stream)
    print(
        "    Scene  Color       State                 Label                    "
        "Project              Session   Lease",
        file=stream,
    )
    for session in sessions:
        if not isinstance(session, dict):
            continue
        marker = ">" if session.get("selected") else " "
        slot = session.get("slot")
        slot_label = f"S{int(slot) + 1}" if isinstance(slot, int) else "overflow"
        accent = _safe_display(session.get("accent"), 8)
        state = _safe_display(session.get("state"), 20)
        label = _safe_display(session.get("label"), 24)
        session_id = _safe_display(session.get("session_id"), 8)
        metadata = session.get("metadata")
        project = "-"
        if isinstance(metadata, dict):
            cwd = metadata.get("cwd")
            if isinstance(cwd, str) and cwd:
                project = Path(cwd).name or cwd
        project = _safe_display(project, 20)
        swatch = _accent_swatch(accent, color=use_color)
        lease = "live" if session.get("leased") else "ttl"
        print(
            f"  {marker} {slot_label:<6} {swatch} {accent:<8} {state:<20} "
            f"{label:<24} {project:<20} {session_id:<8} {lease}",
            file=stream,
        )


def _accent_swatch(accent: str, *, color: bool) -> str:
    rgb = ACCENT_RGB.get(accent)
    if not color or rgb is None:
        return "[]"
    red, green, blue = rgb
    return f"\x1b[48;2;{red};{green};{blue}m  \x1b[0m"


def _safe_display(value: object, limit: int) -> str:
    text = value if isinstance(value, str) else "-"
    safe = "".join(
        character if ord(character) >= 32 and ord(character) != 127 else " "
        for character in text
    )
    compact = " ".join(safe.split())
    return compact[:limit] or "-"


def _stream_is_tty(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty()) if callable(isatty) else False


if __name__ == "__main__":
    raise SystemExit(main())
