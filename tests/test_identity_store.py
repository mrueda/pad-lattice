from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pad_lattice.events import AgentIdentity
from pad_lattice.identity_store import IdentityStore


class IdentityStoreTest(TestCase):
    def test_accent_round_trips_without_storing_raw_identity(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "identities.json"
            identity = AgentIdentity("codex", "private-session-id")
            store = IdentityStore(path, clock=lambda: 10.0)

            store.remember(identity, "magenta")

            self.assertEqual(
                IdentityStore(path).preferred_accent(identity),
                "magenta",
            )
            self.assertNotIn("private-session-id", path.read_text(encoding="utf-8"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_store_discards_least_recently_used_entries(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "identities.json"
            timestamps = iter((1.0, 2.0, 3.0))
            store = IdentityStore(path, max_entries=2, clock=lambda: next(timestamps))
            identities = [AgentIdentity("codex", str(index)) for index in range(3)]

            for identity in identities:
                store.remember(identity, "cyan")

            reloaded = IdentityStore(path, max_entries=2)
            self.assertIsNone(reloaded.preferred_accent(identities[0]))
            self.assertEqual(reloaded.preferred_accent(identities[1]), "cyan")
            self.assertEqual(reloaded.preferred_accent(identities[2]), "cyan")
            self.assertEqual(len(json.loads(path.read_text())["identities"]), 2)

    def test_invalid_store_is_treated_as_empty(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "identities.json"
            path.write_text("not-json", encoding="utf-8")

            store = IdentityStore(path)

            self.assertIsNone(
                store.preferred_accent(AgentIdentity("codex", "session"))
            )
