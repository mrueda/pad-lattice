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

Both bundled profiles expose four sessions. Pads `13` through `16` are
selectors; pads `23` through `26` retain their states.

```text
81  82  83  84  85  86  87  88   selected session state
71  72  73  74  75  76  77  78   selected session state
61  62  63  64  65  66  67  68   selected session state
51  52  53  54  55  56  57  58   selected session state
41  42  43  44  45  46  47  48   selected session state
31  32  33  34  35  36  37  38   selected session state
21  22 [S1][S2][S3][S4] 27  28   semantic status LEDs
AP  NO [A1][A2][A3][A4] RE  ST   actions and selectors
11  12  13  14  15  16  17  18
```

An occupied selector is bright when selected and dim otherwise. Its status pad
uses blue for running, white for waiting, yellow for approval, green for
success, or red for error. This makes a background approval request visible
without replacing the center display.

## Slot Policy

1. The first observed session takes the first slot and becomes selected.
2. Later sessions take free slots without stealing selection.
3. The selected session and approval-waiting sessions remain visible.
4. When slots are full, the least recently active unselected session not
   waiting for approval becomes overflow.
5. New activity from an overflow session assigns it a visible slot using the
   same rule.
6. Restarting the daemon clears the ephemeral registry and slot assignments.

Codex hooks currently provide no session-close event. Recency-based overflow
avoids pretending that a quiet terminal is definitely closed.

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
the selected session's currently connected subscribers and debounces presses
per identity and action.

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
