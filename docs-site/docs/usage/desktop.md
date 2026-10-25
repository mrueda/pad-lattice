# Desktop App

import useBaseUrl from '@docusaurus/useBaseUrl';

**Pad-Lattice shows which Codex session needs you and lets you respond from a
virtual pad or a connected Launchpad.** Codex continues to run in your terminal.
Colors identify sessions; symbols show their state. Select a session, then use
its illuminated Approve or Reject control when a permission request arrives.

You do not need a MIDI controller. The desktop pad works on its own, and you can
also pair a phone or tablet.

<video controls preload="none" playsInline style={{width: '100%', borderRadius: 8}}
  poster={useBaseUrl('/media/desktop-workflow-poster.png')}
  src={useBaseUrl('/media/desktop-workflow.mp4')}
  aria-label="Desktop walkthrough: select a Codex session and approve its request" />

This short walkthrough uses **simulated Codex sessions and an illustrated MIDI
controller** with the desktop interface. It shows session colors, shared state,
and a targeted approval, not a recording of physical hardware.

:::note Desktop preview

Desktop packaging is under development for Linux and macOS. Preview installers
come from the manually run **Build desktop installers** GitHub workflow; they
are not a new published release. Python is bundled. Codex CLI is installed and
authenticated separately.

:::

## Start a Session

1. Open **Pad-Lattice**. Its local service starts automatically.
2. Choose a **Project folder** and give the session a short label, such as
   `implementation` or `tests`.
3. Select **Start session**. Codex opens in a terminal.
4. When Codex asks, open `/hooks` and review the Pad-Lattice handlers.
5. Start working in Codex. The pad updates as the session runs or needs attention.

Repeat these steps for another session. Select its colored Scene button on the
right before responding. The same selected session appears on all connected
surfaces. Prompts and ordinary replies stay in the Codex terminal.

To reopen a conversation, enter its **Resume ID** before selecting **Resume
session**. Pad-Lattice keeps the integration scoped to the sessions it starts.

## Connect a Launchpad

Connect the controller over USB, then open **Settings > MIDI controller**.
Choose **Connect** for automatic detection of a supported device. When several
ports match, choose a profile, input, and output explicitly.

The Launchpad Pro Mk1 profile is physically tested. Mini Mk3 and Pro Mk3 profiles
remain experimental and require explicit selection. A disconnected controller
does not end Codex sessions; the virtual pad continues working. Reconnect it
through Settings when it is available again.

## Connect a Phone

In **Settings > Phone and tablet**, enter this computer's private IPv4 address
and select **Enable pairing**. Use the pairing controls beside the pad to
generate a QR code or PIN. Both devices must be on the same trusted network.

See [Phones, Tablets & Laptops](./connect-browsers.md) for network and Parallels
examples. Pairing is off when the app starts and is revoked when it exits.

## Try Demo and Show

**Start Demo** walks through simulated agents and their controls. **Start Show**
plays the audiovisual story. Both work without Codex or MIDI hardware. Enable
**Sound** to hear audio; it starts muted. A real agent requesting a reply or
approval takes priority over playback.

## Codex and Terminal Settings

The desktop integration targets Codex CLI **0.164.0**, verified against the
stable npm release on 25 October 2026. The app checks the installed version and
whether lifecycle hooks are available. Newer versions are identified as not
yet tested; this is not a guarantee of future compatibility.

If Codex is not found, choose its executable under **Settings > Codex and
terminal**. macOS uses Terminal.app. Linux supports GNOME Terminal, Konsole,
Xfce Terminal, and xterm. Codex installation, authentication, and updates remain
under your control.

Minimize the window to leave Pad-Lattice running. Closing the app stops its
service and releases the MIDI controller. Your Codex terminals remain open;
surface controls are unavailable until Pad-Lattice is running again. Stop a
separately launched Pad-Lattice daemon before opening the desktop app.

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
