# Visual Protocol

import {StateLegend} from '@site/src/components/SurfaceVisuals';

Pad-Lattice Visual Protocol **1** defines how agent identity, state,
selection, action availability, and capacity appear on any conforming surface.

:::important A protocol, not decoration

Position, hue, shape, brightness, and motion carry defined information. The
virtual surface and device profiles translate these semantics into pixels or
hardware lights; they do not invent new meanings for them.

:::

## Reference Surface

LCD-key controllers use the same state glyphs inside individual keys rather
than spreading one glyph across the whole device. The experimental
[Stream Deck layout](../usage/stream-deck.md) shows one Codex session per Session
key: its name and color strip identify it, its glyph reports state whether
selected or not, and a white border marks selection. Separate action keys name
and control only the selected session. Key positions are configurable; a top
row of sessions is an example, not a protocol requirement. No new alphabet is
defined. A compact alphabet for smaller LED grids has not yet been specified.

The reference topology is the common Launchpad arrangement: an **8x8 matrix,
eight top controls, and eight right-side controls**. The browser uses the same
geometry, so knowledge transfers directly between virtual and physical pads:

- the top rail carries actions and system state;
- the right rail contains eight **Agent Scenes**;
- the rightmost matrix column reports the eight visible agents;
- the remaining 7x8 matrix renders the selected agent.

:::note Show temporarily changes the rails

During Show, the top and right buttons cannot issue actions. They become
read-only stage lights in an authored 80-light frame. This does not change
their operational Visual Protocol meanings, which return as soon as Show ends
or a real agent needs attention. See [Outer Rails During Show](../usage/visual-show.md#outer-rails-during-show)
for the choreography used by each story phase.

:::

The Launchpad Pro Mk1 has additional left and bottom rails. They are optional
hardware and remain reserved by this protocol. The virtual surface does not
add actions to those reserved positions.

:::tip Read each right-hand pair as WHAT / WHO

The square status pad answers **what is this agent doing?** The round Agent
Scene button directly beside it answers **who is this, and who will I select?**
Read the square; press the round button.

:::

<div className="matrixDiagram" aria-label="Pad-Lattice common Launchpad surface">
  <div className="surfaceTierLabel"><strong>ACTION</strong><span>top rail: selected-agent commands and system state</span></div>
  <div className="topRail" aria-label="Top action and system controls">
    <span className="externalPad approve">approve<br />CC91</span><span className="externalPad reject">reject<br />CC92</span><span className="externalPad">CC93</span><span className="externalPad">CC94</span><span className="externalPad">more<br />CC95</span><span className="externalPad">CC96</span><span className="externalPad">retry<br />CC97</span><span className="externalPad">stop<br />CC98</span>
  </div>
  <div className="surfaceTierLabel"><strong>STATE</strong><span>7x8 selected-agent glyph, status column, and Agent Scene strip</span></div>
  <div className="controllerBody">
    <div className="matrixGrid">
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticAmber">S1<br />88</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticBlue">S2<br />78</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticWhite">S3<br />68</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticGreen">S4<br />58</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticRed">S5<br />48</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticCyan">S6<br />38</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticGray">S7<br />28</span>
      <span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell semanticAmber"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell"></span><span className="matrixCell status semanticBlue">S8<br />18</span>
    </div>
    <div className="sideRail" aria-label="Right-side Agent Scene controls">
      <span className="selectorCell accentCyan">A1<br />CC89</span><span className="selectorCell accentMagenta unselected">A2<br />CC79</span><span className="selectorCell accentLime unselected">A3<br />CC69</span><span className="selectorCell accentOrange unselected">A4<br />CC59</span><span className="selectorCell accentViolet unselected">A5<br />CC49</span><span className="selectorCell accentTeal unselected">A6<br />CC39</span><span className="selectorCell accentRose unselected">A7<br />CC29</span><span className="selectorCell accentSky unselected">A8<br />CC19</span>
    </div>
  </div>
</div>

Agent Scene 1 is selected and waiting for approval. Its Scene button remains
cyan because cyan identifies agent 1. The adjacent S1 pad and the center
exclamation mark are amber because amber means approval is needed.

| Zone | Reference mapping | Meaning |
| --- | --- | --- |
| Top action/system rail | CC 91-98 | Approve, reject, overflow, retry, and stop; unassigned positions remain dark. |
| State canvas | matrix columns 1-7 | 7x8 glyph for the selected agent. |
| Status column | notes 88, 78, ..., 18 | WHAT: dim semantic state for each visible agent. |
| Right Agent Scene strip | CC 89, 79, ..., 19 | WHO: stable identity; brighter means selected. |

The CC values apply to the common Launchpad device profiles. Browser controls
occupy the corresponding visual positions without pretending to emit MIDI.
Printed musical labels are repurposed while Pad-Lattice owns hardware in
Programmer mode.

## Ableton Influence

Pad-Lattice borrows the Launchpad interaction language without pretending that
an agent is an audio clip:

- the right-side Scene strip provides eight direct context choices;
- selection is distinct from the state being controlled;
- a fixed eight-Scene window represents part of a larger session;
- unavailable controls are dark and selected controls are brighter.

In Ableton Session View, Scene buttons launch horizontal rows and tracks occupy
columns. The Launchpad Pro Sends page also uses the right strip as an
eight-choice contextual selector. Pad-Lattice adapts that behavior: an Agent
Scene changes the focused agent rather than launching audio.

See the official [Launchpad Pro Mk1 user guide](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/novation/downloads/10594/launchpad-pro-user-guide-en.pdf)
and [Ableton Session View manual](https://www.ableton.com/en/live-manual/11/session-view/).

## Identity Accents

An accent belongs to (backend, session_id), not to a slot. Pad-Lattice stores
only a hash of that identity with its preferred accent, so returning sessions
remain recognizable without writing raw session IDs to disk.

| Agent Scene | Reference color | Launchpad palette pair |
| --- | --- | --- |
| Cyan | 🩵 | 37 selected / 39 unselected |
| Magenta | 🟪 | 53 / 55 |
| Lime | 🟢 | 17 / 19 |
| Orange | 🟠 | 9 / 11 |
| Violet | 🟣 | 49 / 51 |
| Teal | 🔷 | 29 / 31 |
| Rose | 🩷 | 57 / 59 |
| Sky | 🔵 | 41 / 43 |

## State Glyphs

The selected-agent canvas is 7x8. These examples use the same renderer as the app.

<StateLegend all />

**Ready** (`idle`) is a dim three-pad dash: no question or approval is pending.
Success, error, and cancellation settle back to Ready after their brief display.
Only an actual input request uses the white question mark. With no selection,
the pad also shows a dim dash, but no Scene is highlighted.

Rapid flashing and pulsing are not used. Optional running motion is disabled
unless the daemon starts with `--activity-motion`.

## Action Semantics

| Top control | Action | Enabled state |
| --- | --- | --- |
| CC 91 | approve | Selected session is waiting for approval and advertises Approve. |
| CC 92 | reject | Selected session is waiting for approval and advertises Reject. |
| CC 97 | retry | Selected session is failed or cancelled and advertises Retry. |
| CC 98 | stop | Selected session is running and advertises Stop. |

On the reference LED surface, an enabled action is bright and an unavailable
action is dark. Stream Deck keeps unavailable action keys dim, with their
labels visible. Only enabled controls can issue actions. Presses are debounced
and routed only to the selected session's current request or turn, never
broadcast. CC 93, 94, and 96 remain unassigned. CC 95 is a steady amber overflow
indicator.

## Capacity and Device Independence

The reference surface shows eight Agent Scenes. When a ninth session arrives,
the daemon may move the least recently active unselected, non-approval session
to overflow. Selected and approval-waiting sessions are protected. Ending the
selected session clears selection and shows the idle dash; another agent is
never silently targeted.

Removing Scene 2 leaves its slot empty; Scene 3 retains its number and accent.
New connections can reuse free slots without renumbering existing sessions.

The common Launchpad mapping is a reference topology, not a requirement that
every implementation look like a Launchpad. Another browser presentation or
MIDI device may relocate these roles, but it must preserve separate identity
and state, selected-agent feedback, capability-gated targeted actions, visible
overflow, and distinguishable shapes and colors without rapid flashing.

## Conformance

| Level | Requirement |
| --- | --- |
| core-state | Render every protocol state with distinguishable shape and semantic hue. |
| multi-agent | Preserve selected identity, per-session status, distinct accents, and overflow. |
| actions | Expose capability-gated, selected-session action controls. |

The bundled Launchpad profiles declare all three levels.
