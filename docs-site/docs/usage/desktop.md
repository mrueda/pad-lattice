# Desktop App

import useBaseUrl from '@docusaurus/useBaseUrl';

**Pad-Lattice shows which Codex session needs you and lets you respond from a
virtual pad or a connected Launchpad.** Codex continues to run in your terminal.
Colors identify sessions; symbols show their state. Select a session, then use
its illuminated Approve or Reject control when a permission request arrives.

**Desktop is the recommended interface for interactive use.**
Start with [Install](./install.md) and [Quick Start](./quickstart.md).

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

## Find Open Conversations

The desktop opens with **Open Codex conversations**: names, working folders,
short IDs, and status from the local Codex app-server. The list refreshes every
ten seconds while the window is visible; the refresh button checks immediately.
It does not open another terminal or restart your conversation.

Use the **Connect** plug icon beside a conversation. Pad-Lattice joins that
conversation and selects its Scene on the pad. **Connected, Scene 1** (or another
number) identifies its pad slot. Your terminal stays open: no restart, new
terminal, or hook installation is needed for this connection.

Conversation titles come from Codex. Once connected, use **Maximize pad** beside
the pad to hide the setup, header, footer, and side panels. The selected
conversation remains visible below the enlarged pad. Use **Restore workspace** or
press Escape to return to the full view.
The desktop hides the WebView's right-click menu. **Settings > Reload interface**
refreshes the window without restarting the service or disconnecting your
conversations. **Refresh chats**, beside the conversation list, only updates
that list.

The pad updates from live Codex events. **Approve** and **Reject** appear for a
single pending command or file-change approval; review the request in your
Codex terminal before pressing either. Approval applies to that request only,
not future requests. **Stop** appears while a known turn is running. Ordinary
replies, permission-profile changes, identity verification, and other unsupported
prompts remain in Codex. Retry is not available through this connection.

Use **Disconnect** to release the pad slot without stopping Codex. Closing
Pad-Lattice also disconnects its attachments. If Codex disconnects, the controls
and slot disappear. Refresh drops ended connections; connect again when ready.

Discovery covers Codex CLI threads loaded on **this computer**, not saved
history or conversations running on another host. A VM cannot discover Codex
on its Mac host. Codex may keep a thread loaded after its terminal
closes, so this is not an exact list of open terminal windows. An attached
conversation remains connected until you disconnect it or Codex unloads it.

## Use the Live Pad

Select a session's colored Scene button on the right before responding.
**Selected conversation** shows its name, state, and available actions.
All connected surfaces share the same selection. Prompts and ordinary replies
stay in the Codex terminal.

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

Choose **Explore > Demo** for simulated agents and their controls, or
**Explore > Show** for the audiovisual story. Both work without Codex or MIDI
hardware. The header marks these experiences as **Simulation**.
Use **Back to live pad** to stop playback and return.

**Explore is disabled while any real session is connected**, even when idle.
Connecting a session during playback stops the experience and restores the live
pad. Enable **Sound** to hear audio; your choice is remembered.

## Preferences

Sound, maximized-pad view, MIDI selections, and the Codex executable path save
automatically in the app's standard settings folder, not in your project.
There is no Save button. Connections and network pairing are not restored
automatically, and credentials are not stored in preferences.

The desktop integration is tested with Codex CLI **0.164.0**. Newer versions
are identified as not yet tested. If Codex is not found, choose its executable
under **Settings > Codex**. Installation, authentication, and updates remain
under your control.

The [Python CLI](./control-codex.md) works independently of the desktop app and remains
available from PyPI.

Minimize the window to leave Pad-Lattice running. Closing the app stops its
service and releases the MIDI controller. Your Codex terminals remain open;
surface controls are unavailable until Pad-Lattice is running again. Stop a
separately launched Pad-Lattice daemon before opening the desktop app.
