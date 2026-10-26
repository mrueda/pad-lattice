"""Private stdio desktop bridge; routing remains in the ordinary daemon."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
import tempfile
from typing import Any
from urllib.parse import urlsplit

from pad_lattice import __version__
from pad_lattice.codex_discovery import discover_conversations
from pad_lattice.codex_attachment import AttachmentManager
from pad_lattice.client import PadLatticeClient
from pad_lattice.daemon_runtime import PadLatticeDaemon
from pad_lattice.desktop_tools import inspect_codex
from pad_lattice.devices.base import (ActionPressed, SessionSelected, ExperienceRequested,
                                     ExperienceStopRequested, SurfaceView, ExperienceView)
from pad_lattice.devices.factory import resolve_device, open_resolved_surface
from pad_lattice.devices.midi_grid import list_midi_ports
from pad_lattice.devices.profiles import ProfileCatalog
from pad_lattice.protocol import default_socket_path
from pad_lattice.web_protocol import (parse_web_command, ActionCommand, SelectSessionCommand,
    CreatePairingCommand, RevokeRemoteCommand, StartExperienceCommand, StopExperienceCommand,
    surface_message, experience_message, performance_frame_message, web_message)
from pad_lattice.web_surface import WebSurface

MAX_REQUEST = 64 * 1024
PREFERENCE_TYPES = {"codex": str, "midi_profile": str, "midi_input": str,
                    "midi_output": str, "pad_focused": bool, "audio_enabled": bool, "light_theme": bool,
                    "pairing_host": str, "pairing_port": str, "pairing_advertise_host": str}


def valid_preference(key, value):
    return key in PREFERENCE_TYPES and type(value) is PREFERENCE_TYPES[key] and (
        not isinstance(value, str) or len(value) <= 4096)


class DesktopSurface(WebSurface):
    def __init__(self, settings_dir: Path, socket_path: str, emit, stop: threading.Event):
        super().__init__(port=0)
        self.settings_dir = settings_dir
        self.socket_path = socket_path
        self.emit = emit
        self.stop = stop
        self.requests: queue.Queue = queue.Queue(maxsize=64)
        self.workers = ThreadPoolExecutor(max_workers=1, thread_name_prefix="desktop-tools")
        self.tool_pending = False
        self.discovery_future = None
        self.attachments = AttachmentManager(socket_path)
        self.midi = None
        self.midi_error = None
        self.last_view = SurfaceView(None)
        self.last_experience = ExperienceView("idle")
        self.last_frame = None
        self.last_port_check = 0.0

    def initialize(self):
        super().initialize()
        self.emit({"event": "ready", "version": __version__})

    def notify(self, message):
        self.emit({"event": "surface", "payload": message})

    def emit_audio(self, cue, slot):
        super().emit_audio(cue, slot)
        self.notify(web_message("audio_cue", cue=cue, slot=slot))

    def render(self, view):
        self.last_view = view
        super().render(view)
        self.notify(surface_message(view, self.selector_capacity))
        self._midi_call("render", view)

    def render_show_frame(self, frame):
        self.last_frame = frame
        super().render_show_frame(frame)
        self.notify(performance_frame_message(frame))
        self._midi_call("render_show_frame", frame)

    def set_experience(self, view):
        self.last_experience = view
        if view.status in {"idle", "blocked"}:
            self.last_frame = None
        super().set_experience(view)
        self.notify(experience_message(view))
        self._midi_call("set_experience", view)

    def _midi_call(self, method, *args):
        if self.midi is None:
            return []
        try:
            return getattr(self.midi, method)(*args)
        except (OSError, RuntimeError) as exc:
            self.midi_error = str(exc)
            self.disconnect_midi()
            self.emit({"event": "device", "error": self.midi_error})
            return []

    def disconnect_midi(self):
        midi, self.midi = self.midi, None
        if midi is not None:
            try:
                midi.close()
            except (OSError, RuntimeError):
                pass

    def snapshot(self):
        messages = [web_message("authenticated", admin=True,
                               lan_enabled=self.server.host != "127.0.0.1"),
                    surface_message(self.last_view, self.selector_capacity),
                    experience_message(self.last_experience)]
        if self.last_frame is not None:
            messages.append(performance_frame_message(self.last_frame))
        return {"messages": messages}

    def settings(self):
        try:
            value = json.loads((self.settings_dir / "settings.json").read_text())
            if isinstance(value, dict):
                return {key: item for key, item in value.items() if valid_preference(key, item)}
        except (OSError, ValueError):
            pass
        return {}

    def status(self):
        error = None
        try:
            inputs, outputs = list_midi_ports()
        except (OSError, RuntimeError) as exc:
            inputs, outputs, error = [], [], str(exc)
        profiles = [{"id": p.id, "status": p.status} for p in ProfileCatalog.load().profiles]
        return {"version": __version__, "settings": self.settings(),
                "inputs": inputs, "outputs": outputs, "profiles": profiles,
                "midi": self.midi.profile_id if self.midi else None,
                "midi_error": self.midi_error or error, "lan_host": self.server.host,
                "network_url": self.server.network_url,
                "port": self.server.actual_port, "socket": self.socket_path}

    def command(self, method: str, params: dict):
        if method == "snapshot":
            return self.snapshot()
        if method == "status":
            return self.status()
        if method == "paired_devices":
            return {"devices": self.server.paired_devices()}
        if method in {"disconnect_device", "revoke_device"}:
            device_id = params.get("device_id")
            if not isinstance(device_id, str) or not device_id:
                raise ValueError("Choose a paired device.")
            self.server.manage_device(device_id, revoke=method == "revoke_device")
            return {"devices": self.server.paired_devices()}
        if method == "settings":
            if any(not valid_preference(key, value) for key, value in params.items()):
                raise ValueError("Invalid settings")
            values = self.settings() | params
            if not params:
                return values
            target = self.settings_dir / "settings.json"
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.settings_dir,
                                             prefix="settings-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    json.dump(values, stream)
                    stream.flush()
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
            return values
        if method == "lan":
            self.server.set_lan(params.get("host") or None, port=params.get("port"),
                                advertise_host=params.get("advertise_host") or None)
            if params.get("host"):
                self.command("settings", {"pairing_host": params["host"],
                    "pairing_port": str(urlsplit(self.server.network_url).port),
                    "pairing_advertise_host": params.get("advertise_host") or ""})
            self.notify(web_message("remote_revoked"))
            self.notify(self.snapshot()["messages"][0])
            return self.status()
        if method == "disconnect_midi":
            self.disconnect_midi()
            return self.status()
        if method == "connect_midi":
            self.disconnect_midi()
            device = resolve_device(profile_id=params.get("profile") or None,
                                    input_name=params.get("input") or None, output_name=params.get("output") or None)
            midi = open_resolved_surface(device, startup_greeting=None, scroll_delay=0.1)
            try:
                if (midi.selector_capacity != self.selector_capacity or midi.accent_names != self.accent_names
                        or midi.visual_protocol != self.visual_protocol):
                    raise ValueError("This device does not match the desktop surface layout.")
                midi.initialize()
                midi.set_experience(self.last_experience)
                midi.render_show_frame(self.last_frame) if self.last_frame else midi.render(self.last_view)
            except BaseException:
                midi.close()
                raise
            self.midi = midi
            self.midi_error = None
            return self.status()
        if method == "surface":
            command = parse_web_command(params)
            if isinstance(command, ActionCommand):
                self._enqueue_event(ActionPressed(command.action, command.expected_revision))
            elif isinstance(command, SelectSessionCommand):
                self._enqueue_event(SessionSelected(command.slot, command.expected_revision))
            elif isinstance(command, StartExperienceCommand):
                self._enqueue_event(ExperienceRequested(command.kind))
            elif isinstance(command, StopExperienceCommand):
                self._enqueue_event(ExperienceStopRequested())
            elif isinstance(command, CreatePairingCommand):
                self.notify(self.create_pairing())
            elif isinstance(command, RevokeRemoteCommand):
                self.server.revoke_remote()
                self.notify(web_message("remote_revoked"))
            else:
                raise ValueError("Unsupported desktop surface command")
            return {}
        raise ValueError("Unknown desktop operation")

    def respond(self, request, work):
        try:
            self.emit({"id": request["id"], "result": work()})
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            self.emit({"id": request["id"], "error": str(exc)})

    def discover(self):
        result = discover_conversations()
        self.attachments.discard_disconnected()
        attachments = self.attachments.snapshot()
        sessions = {item["session_id"]: item for item in PadLatticeClient(self.socket_path).status()["sessions"]
                    if item["backend"] == "codex"}
        listed = {item["id"] for item in result["conversations"]}
        for thread_id, attachment in attachments.items():
            if thread_id not in listed:
                session = sessions.get(thread_id, {})
                result["conversations"].append({"id": thread_id, "name": session.get("label", thread_id),
                                              "cwd": session.get("metadata", {}).get("cwd", ""), "state": "unknown"})
        for item in result["conversations"]:
            attachment = attachments.get(item["id"], {})
            session = sessions.get(item["id"], {})
            item.update(connected=bool(attachment.get("connected")),
                        managed=item["id"] in attachments, error=attachment.get("error"),
                        launcher=bool(session) and item["id"] not in attachments,
                        slot=session.get("slot"), accent=session.get("accent"))
        return result

    def poll_events(self):
        for _ in range(16):
            try:
                request = self.requests.get_nowait()
            except queue.Empty:
                break
            method, params = request["method"], request["params"]
            if method == "list_conversations":
                if self.discovery_future is None or self.discovery_future.done():
                    self.discovery_future = self.workers.submit(self.discover)
                self.discovery_future.add_done_callback(
                    lambda future, request=request: self.respond(request, future.result))
                continue
            if method in {"inspect_codex", "attach_conversation", "detach_conversation"}:
                if self.tool_pending:
                    self.emit({"id": request["id"], "error": "A session operation is already running."})
                    continue
                self.tool_pending = True
                def task(request=request, method=method, params=params):
                    try:
                        options = self.settings() | params
                        if method == "attach_conversation":
                            self.respond(request, lambda: self.attachments.attach(params.get("thread_id")))
                        elif method == "detach_conversation":
                            self.respond(request, lambda: self.attachments.detach(params.get("thread_id")))
                        else:
                            self.respond(request, lambda: inspect_codex(options.get("codex", "")))
                    finally:
                        self.tool_pending = False
                self.workers.submit(task)
            else:
                self.respond(request, lambda: self.command(method, params))
        if self.midi and time.monotonic() - self.last_port_check > 2:
            self.last_port_check = time.monotonic()
            try:
                inputs, outputs = list_midi_ports()
                if self.midi.input_name not in inputs or self.midi.output_name not in outputs:
                    raise OSError("MIDI controller disconnected")
            except (OSError, RuntimeError) as exc:
                self.midi_error = str(exc)
                self.disconnect_midi()
                self.emit({"event": "device", "error": self.midi_error})
        return super().poll_events() + (self._midi_call("poll_events") or [])

    def close(self):
        self.stop.set()
        self.attachments.close()
        self.disconnect_midi()
        self.workers.shutdown(wait=False, cancel_futures=True)
        super().close()


def run(settings_dir: str, socket_path: str | None = None) -> int:
    directory = Path(settings_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stop = threading.Event()
    lock = threading.Lock()
    def emit(value):
        try:
            with lock:
                print(json.dumps(value, separators=(",", ":")), flush=True)
        except (BrokenPipeError, OSError):
            stop.set()
    surface = DesktopSurface(directory, socket_path or default_socket_path(), emit, stop)
    def read_commands():
        try:
            while not stop.is_set():
                line = sys.stdin.readline(MAX_REQUEST + 1)
                if not line:
                    break
                if len(line) > MAX_REQUEST:
                    break
                try:
                    value = json.loads(line)
                    if (not isinstance(value, dict) or not isinstance(value.get("id"), int)
                            or not isinstance(value.get("method"), str)
                            or not isinstance(value.get("params", {}), dict)):
                        break
                    value.setdefault("params", {})
                    surface.requests.put_nowait(value)
                except (ValueError, queue.Full):
                    break
        finally:
            stop.set()
    threading.Thread(target=read_commands, daemon=True, name="desktop-input").start()
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, lambda *_: stop.set())
    try:
        PadLatticeDaemon(surface, surface.socket_path).run(stop)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        emit({"event": "fatal", "error": str(exc)})
        return 1
