# Desktop Architecture

The desktop app uses the same React pad and Python control plane as the browser
and CLI. Tauri supplies the native window, executable picker, single-instance
behavior, and ownership of the bundled Python process.

| Component | Location | Responsibility |
| --- | --- | --- |
| Native shell | `web-app/src-tauri/src/` | Start the engine, relay bounded requests/events, stop its process on exit. |
| Desktop UI | `web-app/src/DesktopControls.tsx`, `OpenConversations.tsx` | Loaded-conversation discovery and attachment, executable settings, MIDI selection, LAN settings. |
| Codex discovery | `codex_discovery.py` | Read-only summary metadata from an existing, same-user Codex app-server. |
| Live attachment | `codex_attachment.py` | Join selected live threads, translate events, and route single-request approvals and turn-specific interruption. |
| Surface transport | `web-app/src/desktop.ts`, `live.ts` | Deliver the existing surface messages through native IPC or browser WebSockets. |
| Desktop service | `desktop_service.py` | Adapt private stdio requests to the existing daemon and optional MIDI output. |
| Runtime helpers | `desktop_tools.py`, `desktop_entry.py` | Inspect the installed Codex version and start the bundled service. |
| Python bundle | `scripts/build_desktop_engine.py` | Package the interpreter, runtime, profiles, and web/audio assets. |

## Process Ownership

Tauri starts one engine with piped stdin/stdout. The engine reports readiness
after acquiring the Unix socket and starting its browser surface. Closing
stdin requests a graceful shutdown; the shell waits before terminating a stuck
process. An existing daemon causes startup to fail with an error, rather than
replacing its socket or controller.

The desktop channel carries JSON requests and responses with IDs and streamed
surface events. It is private to the parent and child processes. Native
conversation attachment and settings operations are not browser protocol commands.
The public app and paired devices receive no native shell permissions.

Desktop audio is fetched from the bundled assets and played through cached
blob URLs. WebKit's media pipeline cannot play the `tauri://` asset URLs
directly. Blob URLs are released when the player closes, and playback failures
are displayed in the interface. Linux packages require GStreamer's good
plugins for WAV decoding and audio output.

Agent routing remains in `ControlPlane`. Desktop events enter the same daemon
loop as browser and MIDI events. Slow Codex discovery and attachment
run on a worker so the pad keeps responding. MIDI output can be replaced in
the daemon loop; losing it leaves browser state and session leases intact.

The optional LAN listener can start or stop without resetting the control
plane. Reconfiguration revokes paired clients. It uses the existing pairing,
host checks, and browser message validation.

## Conversation Lifetime

The desktop lists loaded CLI conversations through Codex's
local WebSocket-over-Unix-socket endpoint under `$CODEX_HOME` (default
`~/.codex/app-server-control/app-server-control.sock`). It checks socket ownership,
initializes a short-lived connection, pages `thread/loaded/list`, and fetches
`thread/read` summaries with `includeTurns: false`. Only IDs, names, working
folders, and normalized status reach the UI; previews and conversation contents
are discarded. Discovery is bounded to 64 threads and a six-second request
budget, and never starts a Codex server.

Discovery itself sends no `thread/resume`, turn commands, or approval responses.
Each refresh replaces the discovered list and discards finished attachment
workers. Only active attachments can supplement the list during discovery failure. Loaded threads can outlive their
terminal while Codex retains them.
See the [Codex app-server reference](https://learn.chatgpt.com/docs/app-server).

### Attach to a Running Conversation

An explicit desktop **Connect** operation creates a `CodexAttachment`. It checks
that the thread is loaded and CLI-owned, then calls `thread/resume` with only
`threadId` and `excludeTurns: true`. For a loaded thread, Codex rejoins the running
conversation. No model, permission, sandbox, or configuration overrides are sent;
no `turn/start` is sent. Discovery and attachment are local-only, using the same
user-owned control socket.

Each attachment owns one WebSocket reader, a Pad-Lattice session lease, and a
short-lived action subscription. Thread/turn events update the existing daemon
through its ordinary protocol, so MIDI and browser surfaces share the same
selection and routing. `thread/turns/list` may fetch one metadata-only turn to
identify work already running at attachment time. Tool output and transcript
content are not retained or forwarded to the desktop.

The adapter exposes Approve/Reject only when exactly one pending request supports
the simple `accept`/`decline` decisions. It never grants a session-wide approval,
changes a saved policy, answers a question, or handles identity verification.
Stop includes the current `threadId` and `turnId`. Each subscription is one-shot
and has a fresh capability token; resolved requests, completion, and connection
loss invalidate controls. Server events are drained before dispatch, and Codex
remains the final arbiter of requests another client may have answered first.

Closing an attachment releases its lease and socket without interrupting Codex.
There is no automatic reconnection or silent replay of an action. The desktop
rejects attachment when the same thread is already connected by scoped hooks,
or when eight pad slots are occupied. An attached conversation needs no
Pad-Lattice hooks. The independent Python CLI uses its own scoped hook workflow.

## Preferences

The service accepts only named, typed preferences: the Codex executable,
MIDI profile and ports, sound, and pad focus. Updates merge with existing values
and replace `settings.json` atomically using a private temporary file.
The native shell provides the platform app-data directory. Credentials,
project data, and connection restoration are not part of these preferences.

## Verification

### Reproduce the Walkthrough

`scripts/render_desktop_demo.mjs` records the desktop renderer using Playwright
and the real Python desktop service. It substitutes simulated agent events,
conversation discovery and attachment, and MIDI connection status. The illustrated controller
mirrors the pad's state and forwards clicks through the native transport
adapter. Approval routing runs through the daemon's ordinary socket protocol.
The footage labels these substitutions explicitly.

After installing the project and web dependencies, install Playwright Chromium
and FFmpeg, then run:

```bash
npm --prefix web-app run build
node scripts/render_desktop_demo.mjs
```

The muted MP4 and poster are written to `docs-site/static/media/`. Set
`PLAYWRIGHT_CHROMIUM_PATH` to use an existing Chromium executable. The recording
uses an isolated temporary socket; it does not start real Codex sessions or
send commands to a connected MIDI controller.

### Automated Checks

`tests/test_desktop.py` exercises stdio startup/shutdown, request validation,
two-session approval routing, settings validation and persistence, and
MIDI failure isolation. When Codex is installed, its configuration parser also
checks the generated hooks without running a model turn.
`tests/test_codex_discovery.py` covers read-only discovery, pagination, state
mapping, thread filtering, ownership checks, bounded work, and failure handling.
`tests/test_codex_attachment.py` uses a local simulated Codex server with the
real Pad-Lattice daemon to check two-session routing, single-request decisions,
turn-specific Stop, stale approvals, unsupported prompts, and disconnection.
A live Codex 0.164.0 join/state/detach check succeeded without starting a turn
or sending an action. Interactive approval alongside the original terminal
remains a manual acceptance check.

Set `PAD_LATTICE_TEST_ENGINE` to the bundled engine to run relocation tests,
including service startup from a path containing spaces and rejection of removed helpers. Native smoke builds
exercise the actual WebView, render Demo/Show messages, and capture Linux
screenshots. They use a separate socket and settings directory.

Public installer publication, signing/notarization, physical hardware checks,
and an interactive end-to-end Codex approval remain release acceptance steps.

## Build From Source

Install Python 3.12, Node.js 24, Rust 1.90, and the
[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) for your platform.
From the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[desktop-build]'
npm --prefix web-app ci
npm --prefix web-app run build
.venv/bin/python scripts/build_desktop_engine.py
npm --prefix web-app run desktop
```

For installers, use `npm --prefix web-app run desktop:build` after bundling the
engine. Linux ARM64 is included for development on ARM virtual machines.
Native Windows support requires additional backend work.
