# Multi-Agent Design

Multi-agent selection and targeted routing are implemented in the daemon. One
MIDI controller can represent several Codex or other agent sessions without
letting a background update change the intended action target.

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

Both bundled profiles expose the common Launchpad topology: eight top
controls, an 8x8 matrix, and eight right-side Agent Scene controls. The right
rail selects agents; the rightmost matrix column retains their compact states.

```text
AP  NO  --  --  OV  --  RE  ST   common top action/system rail
CC91 CC92 CC93 CC94 CC95 CC96 CC97 CC98
glyph glyph glyph glyph glyph glyph glyph S1   A1 / CC89
glyph glyph glyph glyph glyph glyph glyph S2   A2 / CC79
glyph glyph glyph glyph glyph glyph glyph S3   A3 / CC69
glyph glyph glyph glyph glyph glyph glyph S4   A4 / CC59
glyph glyph glyph glyph glyph glyph glyph S5   A5 / CC49
glyph glyph glyph glyph glyph glyph glyph S6   A6 / CC39
glyph glyph glyph glyph glyph glyph glyph S7   A7 / CC29
glyph glyph glyph glyph glyph glyph glyph S8   A8 / CC19
```

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
8. Quiet unselected sessions expire after 24 hours by default. Approval
   sessions do not expire, and `--session-ttl 0` disables cleanup.

Codex hooks currently provide no session-close event. Pad-Lattice therefore
exposes `pad-lattice end-session` for explicit cleanup and uses TTL-based
retirement as the conservative fallback.

## State Flow

```text
Codex A -- lifecycle hook --\
Codex B -- lifecycle hook ----> registry -> selected state -> center LEDs
Codex C -- lifecycle hook --/       |
                                    +----> per-slot status LEDs
```

An update always changes the matching registry record. It affects the center
only when that record is selected.

## Action Flow

```text
pad press -> profile -> daemon -> selected identity -> matching live subscriber
```

Subscribers declare both identity and capabilities. For example,
`codex-exec` advertises only Stop. The daemon derives action brightness from
the selected session's state and currently connected subscribers, then
debounces presses per identity and action. Approve/Reject require approval,
Stop requires running, and Retry requires error or cancellation.

Request-scoped validity remains the integration's responsibility. A future
approval bridge must correlate a hardware decision with a still-pending Codex
permission request before advertising Approve or Reject.

## Current Codex Coverage

| Integration | Multi-session state | Targeted actions |
| --- | --- | --- |
| Interactive Codex hooks | Yes | None; state-only hooks |
| `codex-exec` | Yes | Stop |
| Manual `listen-actions` | Yes | Approve, reject, retry, stop for its chosen identity |

The architecture intentionally avoids terminal scraping, synthetic typing, and
nested pseudo-terminals. A broader interactive action set should wait for a
durable Codex integration point.

Inspect the live registry without touching MIDI ownership:

```bash
pad-lattice status
pad-lattice status --json
```
