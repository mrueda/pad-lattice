"""Persistent, privacy-preserving session accent preferences."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pad_lattice.events import AgentIdentity

STORE_VERSION = 1
DEFAULT_MAX_ENTRIES = 256


def default_identity_store_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return root / "pad-lattice" / "identities.json"


class IdentityStore:
    """Remember accent names without writing raw session identifiers to disk."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.path = path or default_identity_store_path()
        self.max_entries = max_entries
        self._clock = clock
        self._records = self._load()

    def preferred_accent(self, identity: AgentIdentity) -> str | None:
        record = self._records.get(_identity_key(identity))
        if not isinstance(record, dict):
            return None
        accent = record.get("accent")
        return accent if isinstance(accent, str) and accent else None

    def remember(self, identity: AgentIdentity, accent: str) -> None:
        if not accent:
            raise ValueError("accent must be non-empty")
        self._records[_identity_key(identity)] = {
            "accent": accent,
            "last_used": self._clock(),
        }
        self._trim()
        self._write()

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeError):
            return {}
        if not isinstance(data, dict) or data.get("version") != STORE_VERSION:
            return {}
        records = data.get("identities")
        if not isinstance(records, dict):
            return {}
        return {
            key: value
            for key, value in records.items()
            if isinstance(key, str)
            and isinstance(value, dict)
            and isinstance(value.get("accent"), str)
            and isinstance(value.get("last_used"), (int, float))
        }

    def _trim(self) -> None:
        if len(self._records) <= self.max_entries:
            return
        oldest = sorted(
            self._records,
            key=lambda key: float(self._records[key].get("last_used", 0.0)),
        )
        for key in oldest[: len(self._records) - self.max_entries]:
            del self._records[key]

    def _write(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        payload = json.dumps(
            {"version": STORE_VERSION, "identities": self._records},
            indent=2,
            sort_keys=True,
        ) + "\n"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            self.path.chmod(0o600)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _identity_key(identity: AgentIdentity) -> str:
    value = f"{identity.backend}\0{identity.session_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()
