# Multi-Agent Design

Multi-agent operation is a core Pad-Lattice requirement. A single MIDI device
must represent several independent Codex CLI sessions without mixing their
states or sending an action to the wrong session.

This page defines the target architecture. The passive Codex hook already
forwards session identity, but the registry, selectors, and targeted action
routing described here are not implemented yet.

## Design invariants

- Agent state is keyed by **backend plus session ID**, never by terminal,
  working directory, or arrival order alone.
- The surface always has one **explicitly selected agent**.
- State shape and color describe what the selected agent is doing.
- A separate accent color identifies each visible session.
- Approve, reject, retry, and stop are sent only to the selected session.
- No action is broadcast, and an action without a matching live capability is
  ignored.
- All indicators remain steady; multi-agent awareness does not require
  flashing LEDs.
- The core registry is device-agnostic. A device profile decides how its
  available controls represent slots and selection.

## Agent identity

The daemon registry uses a compound key:

```text
(backend, session_id)
```

For Codex, `session_id` comes directly from lifecycle hook input. A registry
record needs at least:

| Field | Purpose |
| --- | --- |
| `backend` | Integration name, initially `codex`. |
| `session_id` | Stable identity supplied by the agent backend. |
| `label` | Human-readable workspace or user-defined name. |
| `state` | Latest semantic agent state. |
| `slot` | Current visible device slot, if any. |
| `accent` | Stable identity color while the session occupies a slot. |
| `last_seen` | Last lifecycle update for ordering and stale-session handling. |
| `capabilities` | Currently connected action sinks, such as approval or stop. |

The working directory is useful as a default label, but it is not an identity:
several Codex sessions can operate in the same repository.

## Launchpad Pro layout

The first multi-agent profile exposes four sessions. It reserves bottom pads
`13` through `16` as selectors and pads `23` through `26` as their steady state
indicators.

```text
81  82  83  84  85  86  87  88   selected agent state
71  72  73  74  75  76  77  78   selected agent state
61  62  63  64  65  66  67  68   selected agent state
51  52  53  54  55  56  57  58   selected agent state
41  42  43  44  45  46  47  48   selected agent state
31  32  33  34  35  36  37  38   selected agent state
21  22 [S1][S2][S3][S4] 27  28   semantic state indicators
AP  NO [A1][A2][A3][A4] RE  ST   actions and agent selectors
11  12  13  14  15  16  17  18
```

Each `A` pad keeps its assigned session accent color. The selected pad is
bright and other occupied slots are dim. Each `S` pad uses the existing state
color language: blue for running, white for waiting, yellow for approval,
green for success, and red for error. The center continues to use both shape
and semantic color for the selected session.

Using a dedicated status pad avoids overloading the accent color and makes an
approval request in an unselected session visible without changing selection.

## Slot policy

The registry may know more sessions than a device can display. The first
Launchpad profile has four visible slots.

1. The first observed session is assigned a slot and selected.
2. Later sessions take free slots without stealing selection.
3. The selected session and sessions waiting for approval stay visible.
4. When all slots are occupied, the least recently active unselected session
   that is not waiting for approval becomes overflow.
5. Activity from an overflow session brings it back into a visible slot using
   the same rule.
6. Restarting the daemon clears ephemeral slot assignments; the next lifecycle
   event registers each session again.

Codex hooks currently provide no session-close event. Recency-based overflow
therefore avoids pretending that the daemon can reliably distinguish a quiet
session from a closed terminal. A later action bridge can provide stronger
liveness while it remains connected.

## State flow

```text
Codex session A -- lifecycle hook --\
Codex session B -- lifecycle hook ----> agent registry -> selected state -> MIDI
Codex session C -- lifecycle hook --/          |
                                             slot LEDs
```

An update always changes the matching registry record. It changes the center
display only when that record is selected. This prevents background activity
from replacing the state of the agent the user intends to control.

## Action flow

```text
MIDI press -> device profile -> daemon -> selected agent -> live action sink
```

Action subscribers must identify their agent key and supported capabilities.
The daemon must not broadcast actions. Before emitting an action, it verifies:

1. The target slot is selected.
2. The selected session advertises that action as currently available.
3. Any request-scoped action, such as approval, still has a live correlation
   ID.

The action pads should be bright only when the selected session can consume
them. For example, approve and reject become active only while that session has
a pending permission request.

## Codex integration boundary

Lifecycle hooks are a reliable **state input** for normal `codex` and
`codex resume` terminal sessions. A `PermissionRequest` hook can also return an
approval decision, but doing so requires a bounded wait and a keyboard fallback
so unavailable hardware never traps the CLI.

Stop and retry require a separate live action sink because lifecycle hooks do
not provide a general external-interrupt channel. That sink must operate in the
same terminal process model; Pad-Lattice should not reintroduce terminal
scraping, synthetic typing, or a second pseudo-terminal.

## Implementation order

1. Add the daemon agent registry and selected-agent state rendering.
2. Add four Launchpad selector pads and their paired status indicators.
3. Make action subscriptions agent-scoped and remove broadcast routing.
4. Add session inspection and explicit selection commands for debugging.
5. Implement bounded hardware approval with a normal Codex prompt fallback.
6. Add a direct, non-PTY action bridge for interruption and retry.
7. Generalize slot capabilities through the device-profile API.
