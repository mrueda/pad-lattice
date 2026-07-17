"""Codex lifecycle hook integration for interactive sessions."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from pad_lattice.events import AgentState
from pad_lattice.protocol import send_message, state_message

HOOK_COMMAND = "pad-lattice codex-hook"
HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
)

StateSender = Callable[[str, dict[str, Any]], None]


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
    sender: StateSender = send_message,
) -> int:
    """Read one Codex hook event and mirror it without blocking Codex."""

    try:
        event = json.load(stdin)
    except (json.JSONDecodeError, UnicodeError):
        event = None

    if isinstance(event, dict):
        state = state_for_codex_hook(event)
        if state is not None:
            try:
                sender(
                    socket_path,
                    state_message(state, agent=_agent_metadata(event)),
                )
            except (ConnectionError, FileNotFoundError, OSError):
                pass

    # Stop hooks require JSON output. An empty object is also a no-op decision
    # for the other lifecycle events used by Pad-Lattice.
    print("{}", file=stdout, flush=True)
    return 0


def default_codex_hooks_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "hooks.json"
    return Path.home() / ".codex" / "hooks.json"


def install_codex_hooks(path: Path, *, command: str = HOOK_COMMAND) -> bool:
    """Merge Pad-Lattice lifecycle hooks into a Codex hooks file.

    Returns ``True`` when the file changed and ``False`` when the same hooks
    were already installed.
    """

    config = _read_hooks_config(path)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path}: 'hooks' must be a JSON object")

    changed = False
    for event_name in HOOK_EVENTS:
        groups = hooks.setdefault(event_name, [])
        if not isinstance(groups, list):
            raise ValueError(f"{path}: hooks.{event_name} must be a JSON array")
        if _contains_command(groups, command):
            continue
        groups.append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": 5,
                    }
                ]
            }
        )
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
    return metadata


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


def _contains_command(groups: list[Any], command: str) -> bool:
    for group in groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if isinstance(handler, dict) and handler.get("command") == command:
                return True
    return False
