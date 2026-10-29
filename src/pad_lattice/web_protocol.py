"""Versioned browser control-surface message contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any, TypeAlias

from pad_lattice.devices.base import (
    ExperienceKind,
    ExperienceView,
    ShowFrame,
    SurfaceView,
)
from pad_lattice.events import ControlAction
from pad_lattice.visual_protocol import VISUAL_PROTOCOL_VERSION, compile_visual_frame

WEB_PROTOCOL_VERSION = 1
MAX_WEB_MESSAGE_BYTES = 16 * 1024
MAX_WEB_LABEL_LENGTH = 80


class WebProtocolError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_message") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AuthenticateCommand:
    credential: str | None


@dataclass(frozen=True)
class ActionCommand:
    action: ControlAction
    expected_revision: int | None = None


@dataclass(frozen=True)
class SelectSessionCommand:
    slot: int
    expected_revision: int | None = None


@dataclass(frozen=True)
class CreatePairingCommand:
    pass


@dataclass(frozen=True)
class RevokeRemoteCommand:
    pass


@dataclass(frozen=True)
class StartExperienceCommand:
    kind: ExperienceKind


@dataclass(frozen=True)
class StopExperienceCommand:
    pass


@dataclass(frozen=True)
class QuestionCommand:
    request_id: str
    operation: str
    slot: int | None = None
    revision: int | None = None
    token: str | None = None
    answers: dict[str, int] | None = None


WebCommand: TypeAlias = (
    AuthenticateCommand
    | ActionCommand
    | SelectSessionCommand
    | CreatePairingCommand
    | RevokeRemoteCommand
    | StartExperienceCommand
    | StopExperienceCommand
    | QuestionCommand
)


def decode_web_message(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        size = len(raw)
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WebProtocolError(
                "message must be UTF-8",
                code="invalid_encoding",
            ) from exc
    else:
        size = len(raw.encode("utf-8"))
    if size > MAX_WEB_MESSAGE_BYTES:
        raise WebProtocolError("message exceeds size limit", code="frame_too_large")
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WebProtocolError(
            "message must be valid JSON",
            code="invalid_json",
        ) from exc
    if not isinstance(message, dict):
        raise WebProtocolError("message must be a JSON object")
    if message.get("protocol") != WEB_PROTOCOL_VERSION:
        raise WebProtocolError("unsupported web protocol", code="unsupported_protocol")
    return message


def parse_web_command(message: dict[str, Any]) -> WebCommand:
    message_type = message.get("type")
    if message_type == "authenticate":
        _require_keys(message, required={"protocol", "type"}, optional={"credential"})
        credential = message.get("credential")
        if credential is not None and (
            not isinstance(credential, str) or not credential or len(credential) > 256
        ):
            raise WebProtocolError("credential must be a non-empty string")
        return AuthenticateCommand(credential)
    if message_type == "action":
        _require_keys(message, required={"protocol", "type", "action"}, optional={"expected_revision"})
        revision = _expected_revision(message)
        try:
            return ActionCommand(ControlAction(message.get("action")), revision)
        except (TypeError, ValueError) as exc:
            raise WebProtocolError("unknown action") from exc
    if message_type == "select_session":
        _require_keys(message, required={"protocol", "type", "slot"}, optional={"expected_revision"})
        slot = message.get("slot")
        if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < 8:
            raise WebProtocolError("slot must be an integer from 0 to 7")
        return SelectSessionCommand(slot, _expected_revision(message))
    if message_type == "create_pairing":
        _require_keys(message, required={"protocol", "type"})
        return CreatePairingCommand()
    if message_type == "revoke_remote":
        _require_keys(message, required={"protocol", "type"})
        return RevokeRemoteCommand()
    if message_type == "start_experience":
        _require_keys(message, required={"protocol", "type", "kind"})
        kind = message.get("kind")
        if kind not in {"demo", "show"}:
            raise WebProtocolError("experience kind must be demo or show")
        return StartExperienceCommand(kind)
    if message_type == "stop_experience":
        _require_keys(message, required={"protocol", "type"})
        return StopExperienceCommand()
    if message_type == "question_request":
        operation, request_id = message.get("operation"), message.get("request_id")
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 64:
            raise WebProtocolError("invalid request identifier")
        if operation == "status":
            _require_keys(message, required={"protocol", "type", "request_id", "operation"})
            return QuestionCommand(request_id, operation)
        if operation == "answer":
            _require_keys(message, required={"protocol", "type", "request_id", "operation", "slot", "revision", "token", "answers"})
            slot, revision, token, answers = (message.get("slot"), message.get("revision"),
                                               message.get("token"), message.get("answers"))
            if (type(slot) is not int or not 0 <= slot < 8 or type(revision) is not int or revision < 0
                    or not isinstance(token, str) or len(token) != 32 or any(c not in "0123456789abcdef" for c in token)
                    or not isinstance(answers, dict) or not 1 <= len(answers) <= 3
                    or any(not isinstance(k, str) or not 1 <= len(k) <= 128 or type(v) is not int or not 0 <= v < 9
                           for k, v in answers.items())):
                raise WebProtocolError("invalid question answer")
            return QuestionCommand(request_id, operation, slot, revision, token, answers)
        raise WebProtocolError("unknown question operation")
    raise WebProtocolError("unknown message type")


def surface_message(view: SurfaceView, selector_capacity: int) -> dict[str, Any]:
    visual = compile_visual_frame(view, selector_capacity)
    return web_message(
        "surface",
        visual_protocol=VISUAL_PROTOCOL_VERSION,
        view={
            "selected_state": (
                view.selected_state.value if view.selected_state is not None else None
            ),
            "frame": view.frame,
            "sessions": [
                {
                    "slot": session.slot,
                    "state": session.state.value,
                    "selected": session.selected,
                    "accent": session.accent,
                    "label": _display_label(session.label, slot=session.slot),
                }
                for session in view.sessions
            ],
            "available_actions": sorted(
                action.value for action in view.available_actions
            ),
            "overflow_count": view.overflow_count,
            "activity_motion": view.activity_motion,
            "control_revision": view.control_revision,
        },
        visual_frame={
            "state": [list(row) for row in visual.state],
            "selectors": list(visual.selectors),
            "statuses": list(visual.statuses),
            "actions": {
                action.value: token for action, token in visual.actions.items()
            },
            "overflow": visual.overflow,
        },
    )


def experience_message(view: ExperienceView) -> dict[str, Any]:
    return web_message(
        "experience_state",
        status=view.status,
        kind=view.kind,
        title=view.title,
        cue_index=view.cue_index,
        caption=view.caption,
        detail=view.detail,
        elapsed_ms=view.elapsed_ms,
        duration_ms=view.duration_ms,
        tempo=view.tempo,
        audio_asset=view.audio_asset,
        audio_cue=view.audio_cue,
        audio_slot=view.audio_slot,
        audio_sequence=view.audio_sequence,
        start_delay_ms=view.start_delay_ms,
        reason=view.reason,
    )


def performance_frame_message(frame: ShowFrame) -> dict[str, Any]:
    return web_message(
        "performance_frame",
        grid=[[_rgb_hex(color.rgb) for color in row] for row in frame.grid],
        top=[_rgb_hex(color.rgb) for color in frame.top],
        right=[_rgb_hex(color.rgb) for color in frame.right],
    )


def web_message(message_type: str, **fields: Any) -> dict[str, Any]:
    return {"protocol": WEB_PROTOCOL_VERSION, "type": message_type, **fields}


def encode_web_message(message: dict[str, Any]) -> str:
    encoded = json.dumps(message, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_WEB_MESSAGE_BYTES:
        raise WebProtocolError("message exceeds size limit", code="frame_too_large")
    return encoded


def web_error(error: WebProtocolError) -> dict[str, Any]:
    return web_message("error", code=error.code, error=str(error))


def load_web_protocol_schema() -> dict[str, Any]:
    schema = resources.files("pad_lattice").joinpath(
        "schemas", "web-surface-protocol-v1.json"
    )
    return json.loads(schema.read_text(encoding="utf-8"))


def _expected_revision(message: dict[str, Any]) -> int | None:
    if "expected_revision" not in message:
        return None
    value = message["expected_revision"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WebProtocolError("expected_revision must be a non-negative integer")
    return value


def _require_keys(
    message: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    keys = set(message)
    if missing := required - keys:
        raise WebProtocolError(f"missing field: {sorted(missing)[0]}")
    if extra := keys - required - optional:
        raise WebProtocolError(f"unknown field: {sorted(extra)[0]}")


def _display_label(value: str, *, slot: int) -> str:
    normalized = " ".join(value.split())
    return (normalized or f"Session {slot + 1}")[:MAX_WEB_LABEL_LENGTH]


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in rgb)
