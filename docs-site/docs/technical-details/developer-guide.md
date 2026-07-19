# Developer Guide

This page is the shortest path from the product model to the implementation.
It explains which process owns each responsibility, how data moves in both
directions, and where a change belongs.

Module paths on this page are relative to `src/pad_lattice/`; test paths are
relative to `tests/`.

## Four Rules

Most of the architecture follows from four rules:

1. **The daemon owns policy and live surfaces during normal operation.** Agent
   integrations communicate through a local Unix socket; they never open MIDI
   ports or connect directly to browser clients. Standalone hardware demos and
   profile tests require the MIDI daemon to be stopped.
2. **Integrations report semantics, not lights.** They emit an agent identity,
   state, and supported actions. The visual layer decides what those semantics
   look like.
3. **Identity is `(backend, session_id)`.** Labels, terminal names, working
   directories, slots, and colors are metadata or presentation.
4. **A lit action is a promise.** An action is visible only when the selected
   session is in a valid state and a live subscriber can consume that action.

These rules prevent competing surface writers, device-specific agent adapters,
accidental cross-session actions, and controls that appear available but do
nothing.

## Runtime Processes

| Process | Responsibility | Lifetime |
| --- | --- | --- |
| `pad-lattice web` | Owns the socket and a browser surface around one deterministic `ControlPlane`. | Long-lived; one per socket. |
| `pad-lattice daemon` | Owns the socket, MIDI surface, and optional browser surface around one `ControlPlane`. | Long-lived; one per controller and socket. |
| `pad-lattice-hook` | Silently ignores events without a daemon, otherwise converts one Codex lifecycle event into state and may await one permission decision. | One lightweight Codex-managed process per hook event. |
| `pad-lattice codex` | Launches Codex on the real terminal and holds a reconnecting session lease. | Same lifetime as the child Codex process. |
| `pad-lattice codex-exec` | Converts a non-interactive Codex JSONL stream and subscribes to Stop. | Same lifetime as one non-interactive task. |
| Other CLI clients | Send a state, inspect status, end a session, or subscribe diagnostically. | Usually short-lived; action subscribers remain connected. |

The launcher is deliberately **not** a terminal emulator. Codex inherits the
terminal's stdin, stdout, and stderr. The launcher adds environment metadata,
a daemon lease, and child-only Codex hook configuration.

## The Contracts

Pad-Lattice keeps its contracts separate:

| Contract | Main code | What it defines |
| --- | --- | --- |
| Agent semantics | `events.py` | `AgentState`, `ControlAction`, and stable `AgentIdentity`. |
| Local IPC | `protocol.py`, `client.py` | Wire Protocol 1 and the public typed integration API. |
| Surface semantics | `devices/base.py`, `visual_protocol.py` | A hardware-independent `SurfaceView` and its semantic light tokens. |
| Browser transport | `web_protocol.py`, `web_surface.py` | Authenticated, sanitized browser rendering and input. |
| Audio semantics | `audio.py` | Optional earcons, Scene pitch identity, authored score, and playback lifecycle. |
| Hardware translation | `devices/profiles.py`, `devices/midi_grid.py` | Validated profile data, MIDI addresses, palette values, and physical events. |

`daemon_runtime.py` joins these contracts at the I/O boundary.
`control_plane.py` owns the policy transitions and creates a `SurfaceView`
without importing sockets, browser servers, MIDI, or a system clock.

The packaged JSON Schemas mirror the three machine-facing data contracts: Wire
Protocol 1, Web Surface Protocol 1, and Device Profile Schema 1. Runtime code
uses direct typed parsers. Optional device-profile JSON Schema validation is an
authoring-time dry run.

The [Socket Protocol](../reference/socket-protocol.md), [Visual
Language](../usage/visual-language.md), [Audio
Feedback](../usage/audio-feedback.md), and [Device
Profiles](./device-profiles.md) pages define each boundary in more detail.

## State Update Path

An interactive Codex state update follows this path:

| Step | Code path | Data |
| --- | --- | --- |
| 1 | Codex invokes `pad-lattice-hook`. | One hook event as JSON on stdin. |
| 2 | `state_for_codex_hook()` maps the event. | A stable `AgentState`. |
| 3 | `run_codex_hook()` builds a `state` message. | Codex session identity, state, metadata, and optional lease ID. |
| 4 | `parse_client_command()` validates and types the message. | A `StateCommand`, not raw JSON values. |
| 5 | `ControlPlane.update_agent()` applies policy. | State, metadata, recency, slot, accent, and terminal-state hold. |
| 6 | `ControlPlane.surface_view()` takes a policy snapshot. | Selected state, visible sessions, available actions, and overflow. |
| 7 | `compile_visual_frame()` applies Visual Protocol 1. | Surface-independent color tokens and a 7x8 glyph. |
| 8 | The active `ControlSurface` renders the view. | Browser frames, MIDI palette values, or both through `CompositeSurface`. |

The equivalent pipeline for `codex-exec` starts with documented Codex JSONL
events in `codex_exec.py`. A future agent backend should begin with its own
adapter and converge on the same `AgentState` and socket message contract.

An update from a background session changes that session's registry record and
compact status indicator. It does not change `_selected_agent`, so it cannot steal
the center display or action target.

With `--audio-feedback`, the daemon also compares the effective state with the
last announced state for that identity. Important transitions enqueue one
semantic `Earcon`; repeated reports, running, and typing remain silent. Slot
number transposes the cue so multi-agent identity and meaning stay independent.

## Surface Action Path

Input travels in the reverse direction:

| Step | Code path | Decision |
| --- | --- | --- |
| 1 | `WebSurface` or `MidiGridSurface` | Converts an authenticated browser command or MIDI address into `ActionPressed` or `SessionSelected`. |
| 2 | `PadLatticeDaemon._handle_surface_event()` | Supplies the event and current time to the control plane. |
| 3 | `ControlPlane.available_actions()` | Intersects selected identity, state, and live subscriber capabilities. |
| 4 | `ControlPlane.dispatch_action()` | Debounces and chooses one matching client ID. |
| 5 | `daemon_runtime.py` sends an `action` message. | The subscriber verifies identity and optional request ID. |

For a Codex permission request, the hook first reports
`waiting_for_approval`, then opens a one-shot subscription for Approve and
Reject. The controls become bright only after that subscription exists.

Request-scoped subscribers are ordered before diagnostic subscribers. The
oldest matching request receives the action. A one-shot subscription is
disabled before delivery, so one tap or press cannot resolve two requests.
Actions are never broadcast.

`CompositeSurface` does not duplicate input. It concatenates child event
queues, and each semantic event is processed once by the same method. Browser
clients never send an agent identity with an action; the control plane adds the
currently selected identity after all routing gates pass.

## Session Lease Path

Codex hooks know the real Codex session ID, but there is no terminal-close
hook. The integrated launcher bridges that lifecycle gap:

1. `pad-lattice codex` creates a random lease ID and starts `SessionLease`.
2. The lease connection sends its label and working-directory metadata.
3. The launcher exports the lease ID and injects scoped lifecycle hooks into
   its child Codex process.
4. The first lifecycle hook sends both the real Codex identity and lease ID.
5. The daemon binds the lease to that identity and returns its Scene, accent,
   and label.
6. The lease remembers the binding and includes it when reconnecting after a
   daemon restart.
7. When Codex exits, the launcher closes the lease. The daemon removes the
   bound session immediately if no other live lease owns it.

Plain `codex` sessions load no Pad-Lattice hooks and remain outside the session
registry.

## Execution Model

The daemon runtime uses one synchronous `selectors` loop. On each iteration it:

1. expires terminal holds and stale unleased sessions;
2. renders only when state is dirty or optional activity motion is due;
3. handles readable Unix-socket clients;
4. polls pending events from every enabled surface.

The default poll interval is 30 ms. The runtime supplies `time.monotonic()` to
each control-plane transition. Registry mutation, selection, routing, and
render scheduling happen in one thread, so the core needs no cross-thread
locking and policy tests can supply an exact clock.

Threads are confined to adapters that must wait independently:

- `BrowserSurfaceServer` serves HTTP and WebSocket clients and places semantic
  events on a thread-safe queue for the daemon loop;
- `SessionLease` reconnects in a background thread while Codex owns the
  terminal;
- `codex-exec` waits for a Stop action while its main thread consumes Codex
  JSONL;
- a permission hook waits synchronously because Codex is waiting for that
  hook's decision.

Audio uses short-lived operating-system player processes. Synthesis and
playback are outside the control plane, and playback never blocks the selector
loop.

## State Ownership

| Data | Authority | Persistence |
| --- | --- | --- |
| Sessions, selection, slots, subscriptions, leases | `ControlPlane` memory | None; reconstructed by live clients. |
| Preferred identity accent | `IdentityStore` | Bounded local LRU containing hashed identities only. |
| Codex hook commands | `pad-lattice codex` command line | Child process only; not persisted globally. |
| Device definitions | Profile catalog | Packaged JSON plus optional user profile roots. |
| Visual meanings | `visual_protocol.py` and documentation | Versioned as Visual Protocol 1. |

Slots are presentation state, not identity. A session may move into or out of
overflow while retaining its identity and preferred accent.

## Failure Behavior

| Failure | Behavior |
| --- | --- |
| Daemon unavailable during a normal lifecycle hook | The hook remains a no-op for Codex; the agent session continues. |
| Daemon unavailable at launcher startup | Codex still starts and the lease retries once per second. |
| No surface permission response before timeout | The hook returns no decision and Codex restores its keyboard prompt. |
| Action subscriber disconnects | Its capabilities disappear and affected controls render dark. |
| Lease connection drops | The launcher reconnects with its remembered identity. |
| Leased process exits | Its session is removed immediately. |
| Unleased client disappears without cleanup | The session expires after the configured inactivity TTL. |
| Several MIDI ports or profiles match | Device resolution fails with a diagnostic instead of guessing. |
| Invalid protocol message | The daemon returns a protocol error on that client connection. |
| Browser fails authentication | It receives no surface state and must pair again. |
| Browser server cannot bind | Startup fails before the daemon claims normal operation. |
| One child surface fails to initialize | Composite initialization closes already-opened children. |
| Requested audio player unavailable | Explicit audio startup fails clearly; operation without an audio flag is unaffected. |
| Audio playback fails after startup | State, rendering, MIDI input, and action routing continue. |
| Clean daemon shutdown | Browser clients close; MIDI clears and returns to normal device mode. |

## Where To Make Changes

| Goal | Start here | Primary tests |
| --- | --- | --- |
| Add an agent backend | New adapter using `PadLatticeClient` and `events.py` | Adapter tests, `test_client.py` |
| Change session selection or routing | `control_plane.py` | `test_control_plane.py` |
| Change a glyph or semantic color role | `visual_protocol.py` | `test_visual_protocol.py`, `test_midi_grid.py` |
| Change browser commands or rendering | `web_protocol.py`, `web_surface.py`, `web-app/src/` | `test_web_protocol.py`, `test_web_surface.py`, Vitest, Playwright |
| Change multi-surface fan-out | `devices/composite.py` | `test_composite_surface.py`, `test_daemon.py` |
| Change an earcon or show score | `audio.py` | `test_audio.py`, `test_daemon.py` |
| Change the visual story | `show.py` | `test_show.py`, real-device performance test |
| Add a palette-grid controller | A profile JSON file | `test_device_profiles.py`, guided profile test |
| Add a new hardware driver | `devices/base.py`, `devices/factory.py`, new trusted driver | Driver tests and profile validation tests |
| Change Codex lifecycle mapping | `codex_hooks.py` or `codex_exec.py` | Matching Codex adapter tests |
| Change socket or surface adaptation | `daemon_runtime.py` | `test_daemon.py` |
| Change launcher cleanup or reconnect behavior | `codex_session.py`, lease handling in `control_plane.py` | `test_codex_session.py`, `test_control_plane.py` |

Adding a new state or action is intentionally cross-cutting. It changes agent
semantics, daemon gating, the visual protocol, every conforming profile, tests,
and documentation. Treat it as a protocol change rather than a local enum
addition.

## Validate a Change

Run the hardware-independent suite:

```bash
.venv/bin/python -m unittest discover -s tests
```

Validate the documentation:

```bash
cd docs-site
npm run typecheck
npm run build
```

Validate the virtual surface:

```bash
cd web-app
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Unit tests use fake surfaces and MIDI ports. A profile intended for real
hardware also needs the guided physical test described in [Test a
Device](../usage/device-testing.md).

## Recommended Reading Order

1. [Architecture](./architecture.md) for system boundaries.
2. [Socket Protocol](../reference/socket-protocol.md) for client behavior.
3. [Multi-Agent Design](./multi-agent-design.md) for routing invariants.
4. [Visual Language](../usage/visual-language.md) for surface semantics.
5. [Virtual Surface](../usage/virtual-surface.md) for browser transport and pairing.
6. [Audio Feedback](../usage/audio-feedback.md) for optional sonification.
7. [Device Profiles](./device-profiles.md) for hardware extension.
