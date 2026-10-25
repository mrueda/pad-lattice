# Desktop Architecture

The desktop app uses the same React pad and Python control plane as the browser
and CLI. Tauri supplies the native window, folder picker, single-instance
behavior, and ownership of the bundled Python process.

| Component | Location | Responsibility |
| --- | --- | --- |
| Native shell | `web-app/src-tauri/src/` | Start the engine, relay bounded requests/events, stop its process on exit. |
| Desktop UI | `web-app/src/DesktopControls.tsx` | Session launcher, executable settings, MIDI selection, LAN settings. |
| Surface transport | `web-app/src/desktop.ts`, `live.ts` | Deliver the existing surface messages through native IPC or browser WebSockets. |
| Desktop service | `desktop_service.py` | Adapt private stdio requests to the existing daemon and optional MIDI output. |
| Terminal helpers | `desktop_tools.py`, `desktop_entry.py` | Locate Codex, check hooks, open a native terminal, invoke scoped hooks. |
| Python bundle | `scripts/build_desktop_engine.py` | Package the interpreter, runtime, profiles, and web/audio assets. |

## Process Ownership

Tauri starts one engine with piped stdin/stdout. The engine reports readiness
after acquiring the Unix socket and starting its browser surface. Closing
stdin requests a graceful shutdown; the shell waits before terminating a stuck
process. An existing daemon causes startup to fail with an error, rather than
replacing its socket or controller.

The desktop channel carries JSON requests and responses with IDs and streamed
surface events. It is private to the parent and child processes. Native
session-launch and settings operations are not browser protocol commands.
The public app and paired devices receive no native shell permissions.

Agent routing remains in `ControlPlane`. Desktop events enter the same daemon
loop as browser and MIDI events. Slow Codex discovery and terminal launching
run on a worker so the pad keeps responding. MIDI output can be replaced in
the daemon loop; losing it leaves browser state and session leases intact.

The optional LAN listener can start or stop without resetting the control
plane. Reconfiguration revokes paired clients. It uses the existing pairing,
host checks, and browser message validation.

## Terminal and Hook Lifetime

The launcher creates a private, quoted command script and opens a supported
terminal with it. The script deletes itself and invokes the bundled engine's
session helper. That helper uses `run_codex_session` with inherited terminal
I/O and the existing reconnecting lease.

The frozen engine doubles as the hook executable. Its absolute installed path
is used, not PyInstaller's extracted entry script. Native subprocesses receive
the host library environment so bundled libraries do not leak into Codex or
the terminal emulator. No terminal output is scraped.

Codex 0.164.0 supports the existing five hooks plus `Interrupt` and `SessionEnd`.
Interrupt displays cancellation; SessionEnd removes the session. Both use the
documented one-second timeout. The seven definitions remain scoped to the
launched Codex process. See the [official hook reference](https://learn.chatgpt.com/docs/hooks).

## Verification

### Reproduce the Walkthrough

`scripts/render_desktop_demo.mjs` records the desktop renderer using Playwright
and the real Python desktop service. It substitutes simulated agent events,
terminal launches, and MIDI connection status. The illustrated controller
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
two-session approval routing, settings permissions, terminal quoting, and
MIDI failure isolation. When Codex is installed, its configuration parser also
checks the generated hooks without running a model turn.

Set `PAD_LATTICE_TEST_ENGINE` to the bundled engine to run relocation tests,
including hook execution from a path containing spaces. Native smoke builds
exercise the actual WebView, render Demo/Show messages, and capture Linux
screenshots. They use a separate socket and settings directory.

Public installer publication, signing/notarization, physical hardware checks,
and an interactive end-to-end Codex approval remain release acceptance steps.
