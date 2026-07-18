"""Codex lifecycle hook integration for interactive sessions."""

from __future__ import annotations

import json
import math
import os
import shlex
import shutil
import socket
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    JsonLineConnection,
    ProtocolError,
    parse_action_event,
    request_message,
    send_message,
    state_message,
    subscribe_actions_message,
)

HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
)
DEFAULT_APPROVAL_TIMEOUT = 60.0
HOOK_TIMEOUT_MARGIN = 5

StateSender = Callable[[str, dict[str, Any]], None]
StateRequester = Callable[[str, dict[str, Any]], dict[str, Any]]
ActionWaiter = Callable[[str, AgentIdentity, float], ControlAction | None]


def state_for_codex_hook(event: dict[str, Any]) -> AgentState | None:
    """Map a stable Codex lifecycle hook event to a surface state."""

    return {
        "SessionStart": AgentState.WAITING_FOR_REPLY,
        "UserPromptSubmit": AgentState.RUNNING,
        "PermissionRequest": AgentState.WAITING_FOR_APPROVAL,
        "PostToolUse": AgentState.RUNNING,
        "Stop": AgentState.SUCCESS,
    }.get(event.get("hook_event_name"))


def run_codex_hook(
    socket_path: str,
    stdin: TextIO,
    stdout: TextIO,
    *,
    approval_timeout: float = DEFAULT_APPROVAL_TIMEOUT,
    sender: StateSender = send_message,
    requester: StateRequester = request_message,
    action_waiter: ActionWaiter | None = None,
) -> int:
    """Mirror one hook event and optionally await a hardware permission decision."""

    if approval_timeout <= 0:
        raise ValueError("approval_timeout must be positive")

    try:
        event = json.load(stdin)
    except (json.JSONDecodeError, UnicodeError):
        event = None

    response: dict[str, Any] = {}
    if isinstance(event, dict):
        socket_path = os.environ.get("PAD_LATTICE_SOCKET", socket_path)
        state = state_for_codex_hook(event)
        identity = _event_identity(event)
        if state is not None and identity is not None:
            assignment = _report_state(
                socket_path,
                state,
                event,
                sender=sender,
                requester=requester,
            )
            if assignment is not None:
                _set_terminal_title(assignment)

            if event.get("hook_event_name") == "PermissionRequest":
                waiter = action_waiter or wait_for_permission_action
                action = waiter(socket_path, identity, approval_timeout)
                if action in {ControlAction.APPROVE, ControlAction.REJECT}:
                    try:
                        sender(
                            socket_path,
                            state_message(
                                AgentState.RUNNING,
                                agent=_agent_metadata(event),
                                lease_id=_lease_id(),
                            ),
                        )
                    except (ConnectionError, FileNotFoundError, OSError):
                        pass
                    response = permission_decision(action)

    # Stop hooks require JSON output. An empty object is a no-op decision for
    # other events and restores Codex's keyboard approval prompt after timeout.
    print(json.dumps(response, separators=(",", ":")), file=stdout, flush=True)
    return 0


def wait_for_permission_action(
    socket_path: str,
    identity: AgentIdentity,
    timeout: float,
) -> ControlAction | None:
    """Wait for one request-scoped hardware approval decision."""

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(socket_path)
            return _wait_for_permission_action_client(client, identity, timeout)
    except (ConnectionError, FileNotFoundError, OSError):
        return None


def _wait_for_permission_action_client(
    client: socket.socket,
    identity: AgentIdentity,
    timeout: float,
) -> ControlAction | None:
    request_id = uuid.uuid4().hex
    deadline = time.monotonic() + timeout
    connection = JsonLineConnection(client)
    connection.send(
        subscribe_actions_message(
            identity,
            (ControlAction.APPROVE, ControlAction.REJECT),
            request_id=request_id,
            one_shot=True,
        )
    )
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        client.settimeout(remaining)
        try:
            event = parse_action_event(connection.receive())
        except ProtocolError:
            continue
        if (
            event.agent == identity
            and event.request_id == request_id
            and event.action in {ControlAction.APPROVE, ControlAction.REJECT}
        ):
            return event.action


def permission_decision(action: ControlAction) -> dict[str, Any]:
    if action is ControlAction.APPROVE:
        decision: dict[str, str] = {"behavior": "allow"}
    elif action is ControlAction.REJECT:
        decision = {
            "behavior": "deny",
            "message": "Rejected from Pad-Lattice.",
        }
    else:
        raise ValueError(f"unsupported permission action: {action.value}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": decision,
        }
    }


def default_codex_hooks_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "hooks.json"
    return Path.home() / ".codex" / "hooks.json"


def installed_codex_hook_events(path: Path) -> tuple[str, ...]:
    """Return lifecycle events containing a Pad-Lattice hook command."""

    config = _read_hooks_config(path)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return ()
    installed: list[str] = []
    for event_name in HOOK_EVENTS:
        groups = hooks.get(event_name)
        if not isinstance(groups, list):
            continue
        if any(
            isinstance(group, dict)
            and isinstance(group.get("hooks"), list)
            and any(
                isinstance(handler, dict)
                and _is_pad_lattice_hook_command(handler.get("command"))
                for handler in group["hooks"]
            )
            for group in groups
        ):
            installed.append(event_name)
    return tuple(installed)


def resolve_hook_command(
    socket_path: str,
    argv0: str | None = None,
    *,
    approval_timeout: float = DEFAULT_APPROVAL_TIMEOUT,
) -> str:
    """Return a shell-safe hook command with stable executable and socket paths."""

    if approval_timeout <= 0:
        raise ValueError("approval_timeout must be positive")

    invocation = argv0 or sys.argv[0]
    candidate = Path(invocation).expanduser()
    if candidate.is_file():
        executable = candidate.resolve()
    else:
        located = shutil.which(invocation)
        if located is None:
            raise FileNotFoundError(f"could not resolve Pad-Lattice executable: {invocation}")
        executable = Path(located).resolve()
    resolved_socket = Path(socket_path).expanduser().resolve()
    return (
        f"{shlex.quote(str(executable))} codex-hook "
        f"--socket {shlex.quote(str(resolved_socket))} "
        f"--approval-timeout {approval_timeout:g}"
    )


def install_codex_hooks(
    path: Path,
    *,
    command: str,
    approval_timeout: float = DEFAULT_APPROVAL_TIMEOUT,
) -> bool:
    """Merge Pad-Lattice lifecycle hooks into a Codex hooks file.

    Returns ``True`` when the file changed and ``False`` when the same hooks
    were already installed.
    """

    if approval_timeout <= 0:
        raise ValueError("approval_timeout must be positive")
    config = _read_hooks_config(path)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path}: 'hooks' must be a JSON object")

    changed = False
    for event_name in HOOK_EVENTS:
        timeout = (
            math.ceil(approval_timeout) + HOOK_TIMEOUT_MARGIN
            if event_name == "PermissionRequest"
            else 5
        )
        groups = hooks.setdefault(event_name, [])
        if not isinstance(groups, list):
            raise ValueError(f"{path}: hooks.{event_name} must be a JSON array")
        groups, found, replaced = _replace_managed_commands(
            groups,
            command,
            timeout=timeout,
        )
        if replaced:
            hooks[event_name] = groups
            changed = True
        if not found:
            groups.append(
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command,
                            "timeout": timeout,
                        }
                    ]
                }
            )
            hooks[event_name] = groups
            changed = True

    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.tmp")
        temporary_path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    return changed


def _agent_metadata(event: dict[str, Any]) -> dict[str, str]:
    metadata = {"backend": "codex"}
    for field in ("session_id", "cwd", "model"):
        value = event.get(field)
        if isinstance(value, str) and value:
            metadata[field] = value
    if label := os.environ.get("PAD_LATTICE_LABEL"):
        metadata["label"] = label
    return metadata


def _event_identity(event: dict[str, Any]) -> AgentIdentity | None:
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return None
    return AgentIdentity("codex", session_id)


def _lease_id() -> str | None:
    value = os.environ.get("PAD_LATTICE_LEASE_ID")
    return value if value else None


def _report_state(
    socket_path: str,
    state: AgentState,
    event: dict[str, Any],
    *,
    sender: StateSender,
    requester: StateRequester,
) -> dict[str, Any] | None:
    wants_assignment = os.environ.get("PAD_LATTICE_TERMINAL_TITLE") == "1"
    message = state_message(
        state,
        agent=_agent_metadata(event),
        lease_id=_lease_id(),
        reply=wants_assignment,
    )
    try:
        if wants_assignment:
            return requester(socket_path, message)
        sender(socket_path, message)
    except (ConnectionError, FileNotFoundError, OSError, ProtocolError):
        pass
    return None


def _set_terminal_title(assignment: dict[str, Any]) -> None:
    if os.environ.get("PAD_LATTICE_TERMINAL_TITLE") != "1":
        return
    scene = assignment.get("scene")
    accent = assignment.get("accent")
    label = assignment.get("label")
    if (
        not isinstance(scene, int)
        or not isinstance(accent, str)
        or not isinstance(label, str)
    ):
        return
    safe_accent = _terminal_text(accent.upper(), limit=16)
    safe_label = _terminal_text(label, limit=64)
    title = f"[S{scene} {safe_accent}] {safe_label}"
    try:
        descriptor = os.open("/dev/tty", os.O_WRONLY | os.O_NOCTTY)
        try:
            os.write(descriptor, f"\x1b]0;{title}\x07".encode("utf-8"))
        finally:
            os.close(descriptor)
    except OSError:
        pass


def _terminal_text(value: str, *, limit: int) -> str:
    safe = "".join(
        character if ord(character) >= 32 and ord(character) != 127 else " "
        for character in value
    )
    return " ".join(safe.split())[:limit]


def _read_hooks_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(config, dict):
        raise ValueError(f"{path}: top-level value must be a JSON object")
    return config


def _replace_managed_commands(
    groups: list[Any],
    command: str,
    *,
    timeout: int,
) -> tuple[list[Any], bool, bool]:
    updated_groups: list[Any] = []
    found = False
    changed = False

    for group in groups:
        if not isinstance(group, dict):
            updated_groups.append(group)
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            updated_groups.append(group)
            continue

        updated_handlers: list[Any] = []
        group_changed = False
        for handler in handlers:
            managed = (
                isinstance(handler, dict)
                and _is_pad_lattice_hook_command(handler.get("command"))
            )
            if not managed:
                updated_handlers.append(handler)
                continue
            if found:
                group_changed = True
                changed = True
                continue

            found = True
            if (
                handler.get("command") == command
                and handler.get("timeout") == timeout
            ):
                updated_handlers.append(handler)
                continue
            updated_handler = dict(handler)
            updated_handler["command"] = command
            updated_handler["timeout"] = timeout
            updated_handlers.append(updated_handler)
            group_changed = True
            changed = True

        if not updated_handlers and group_changed:
            continue
        if group_changed:
            updated_group = dict(group)
            updated_group["hooks"] = updated_handlers
            updated_groups.append(updated_group)
        else:
            updated_groups.append(group)

    return updated_groups, found, changed


def _is_pad_lattice_hook_command(command: Any) -> bool:
    if not isinstance(command, str):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if len(parts) < 2 or parts[1] != "codex-hook":
        return False
    executable = Path(parts[0]).name
    return executable in {"pad-lattice", "pad-lattice.exe"}
