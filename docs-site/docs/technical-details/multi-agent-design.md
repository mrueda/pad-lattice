# Multi-Agent Design

Multi-agent selection and targeted routing are implemented in the deterministic
`ControlPlane`. The daemon runtime supplies socket, clock, and MIDI events. One
controller can represent several agent sessions without letting a background
update change the intended action target.

## Invariants

- Identity is **backend plus session ID**, never terminal, working directory,
  or arrival order alone.
- The surface has one explicitly selected session.
- The center shape and semantic color describe only that session.
- Every visible slot has a distinct steady accent and a separate state LED.
- A physical action is routed only to the selected identity.
- The selected identity must have a live subscriber for that exact action.
- Actions are never broadcast.
- Session awareness does not require flashing or pulsing LEDs.
- Slot management remains independent of the device's MIDI map.

## Surface Layout

All bundled profiles expose the common Launchpad topology: eight top
controls, an 8x8 matrix, and eight right-side Agent Scene controls. The right
rail selects agents; the rightmost matrix column retains their compact states.

![Three agent sessions mapped through the daemon registry to one explicitly selected Launchpad view](/img/multi-agent-selection.svg)

_Session 2 is selected. Its amber approval state owns the center and enables
Approve/Reject, while sessions 1 and 3 remain visible through their compact
status pads and identity-colored Agent Scenes._

An occupied Agent Scene is bright when selected and dim otherwise. Its status
pad uses the state's semantic color. This makes a background approval request
visible without replacing the selected-agent glyph. `CC 95` is steady amber
while one or more registered sessions are in overflow.

The Pro Mk1's additional left `CC 80`-`10` and bottom `CC 1`-`8` controls remain
reserved. Keeping the core mapping on the common rails lets the same visual
protocol work on Launchpad models without those extra controls.

Accent assignment is independent of slot assignment. A privacy-preserving LRU
store remembers the preferred accent for a hash of `(backend, session_id)`,
while the daemon guarantees that currently visible accents are unique.

## Terminal Identity

The controller communicates identity by Scene and accent, not by rendering
arbitrary names. The leased launcher completes that visual protocol on screen:

```text
[S1 CYAN] implementation
[S2 MAGENTA] docs
```

`pad-lattice status --watch` is the live legend for larger setups. It matches
those titles to current state, project, short troubleshooting ID, and lease
status. Labels default to the Codex working-directory name and can be supplied
with `pad-lattice codex --label NAME` when several agents share a repository.

## Slot Policy

1. The first observed session takes the first slot and becomes selected.
2. Later sessions take free slots without stealing selection.
3. The selected session and approval-waiting sessions are protected.
4. When slots are full, the least recently active unselected session not
   waiting for approval becomes overflow.
5. New activity from an overflow session can assign it a visible slot using the
   same rule.
6. An explicit `session_end` removes that identity and fills any free slot.
7. Ending the selected session clears selection; another session is never
   silently targeted.
8. A live launcher lease prevents expiry and removes its session immediately
   when the Codex process exits.
9. Any inactive unleased session expires after 24 hours by default;
   `--session-ttl 0` disables cleanup.

Codex hooks provide no session-close event. `pad-lattice codex` therefore keeps
a persistent daemon lease while passing the real terminal directly to Codex.
Plain Codex remains supported through explicit `end-session` and TTL cleanup.

## State Flow

An update always changes the matching registry record. It affects the center
only when that record is selected. The selection diagram above shows both
outputs: every visible record has a compact state pad, while exactly one record
drives the 7x8 center glyph and available action rail.

## Action Flow

![One physical Approve press passing daemon routing gates and reaching only the oldest matching request for the selected agent](/img/multi-agent-action-routing.svg)

_The hardware emits a semantic action without choosing an agent. The daemon
adds the explicit selected identity, validates state and live capability, and
delivers to one matching subscriber._

Subscribers declare identity, capabilities, and optional request correlation.
For example, `codex-exec` advertises only Stop, while a Codex
`PermissionRequest` hook advertises one-shot Approve and Reject with a unique
request ID. The daemon derives action visibility from the selected session's
state and live subscribers, then debounces presses per identity and action.
Approve/Reject require approval, Stop requires running, and Retry requires
error or cancellation.

Request-scoped subscribers take priority over diagnostic session listeners.
Only the oldest matching request receives a press, and one-shot subscriptions
remove both approval capabilities before delivery. One physical press can
therefore never approve two pending operations.

## Current Codex Coverage

| Integration | Multi-session state | Targeted actions |
| --- | --- | --- |
| Interactive Codex hooks | Yes | Approve and Reject for permission requests |
| `codex-exec` | Yes | Stop |
| Manual `listen-actions` | Yes | Approve, reject, retry, stop for its chosen identity |

The architecture intentionally avoids terminal scraping, synthetic typing, and
nested pseudo-terminals. Interactive Stop, Retry, and ordinary chat replies
remain outside the permission-hook boundary and require a broader Codex
integration point.

Inspect the live registry without touching MIDI ownership:

```bash
pad-lattice status
pad-lattice status --watch
pad-lattice status --json
```
