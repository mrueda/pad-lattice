# Desktop Pad

import useBaseUrl from '@docusaurus/useBaseUrl';

Connect your open Codex CLI chats and control them from the on-screen pad.
[Install](./install.md) includes Python and the local service; install and
authenticate Codex CLI separately on the same computer.

<video controls preload="none" playsInline style={{width: '100%', borderRadius: 8}}
  poster={useBaseUrl('/media/desktop-workflow-poster.png')}
  src={useBaseUrl('/media/desktop-workflow.mp4')}
  aria-label="Desktop walkthrough: select a Codex session and approve its request" />

Illustrated walkthrough with **simulated chats**, not a physical hardware recording.

## Find Open Conversations

Select **Connect** beside a chat under **Open Codex conversations**.
Its Scene number and color appear on the pad. Codex stays in its original
terminal; no restart or hooks are needed.

Use **Refresh chats** to update the list. It shows conversations loaded by Codex
on this computer and OS account, not saved history or chats on another host.
Resume a saved chat in Codex first. A VM cannot discover chats on its Mac host.

**Disconnect** releases the pad slot without stopping Codex. Codex may keep a
thread loaded after its terminal closes; see [Troubleshooting](./troubleshooting.md)
if the list differs from your open windows.

## Use the Live Pad

1. Select the chat's colored Scene button on the right.
2. Check **Selected conversation** and read the request in Codex.
3. Press a lit action when you want to approve, reject, or stop.

Only supported actions light up. Ordinary replies stay in Codex.
[How It Works](./control-codex.md#read-the-surface) shows the glyphs and controls.

| Control | What it does |
| --- | --- |
| **Maximize pad** | Hides setup panels and enlarges the pad. |
| **Restore workspace** or Escape | Returns to the full view. |
| **Refresh chats** | Updates the conversation list. |
| **Settings > Reload interface** | Reloads the window without disconnecting chats. |

## Connect a Launchpad

Connect it over USB, then choose **Settings > MIDI controller > Connect**.
If automatic detection cannot choose a device, select its profile and ports.
Experimental profiles must be selected explicitly.

See [Novation Launchpad](./launchpad.md) for models and the control diagram.
Disconnecting MIDI does not end your chats; the virtual pad keeps working.

## Connect a Phone

Enable **Settings > Phone and tablet**, then choose **Pair device** beside the
pad. Both devices must be on the same trusted network.
Follow [Connect Screens](./connect-browsers.md) for the QR/PIN steps.

## Try Demo and Show

Disconnect real sessions, then choose **Demo & Show > Demo** or **Demo & Show > Show**.
Enable **Sound** for audio. **Back to live pad** ends playback.

Demo & Show is disabled while real sessions are connected. Connecting a session
during playback also returns the pad to live control.

## Preferences and Closing

Sound, pad size, MIDI selections, and the Codex executable path save automatically
in the app's settings folder, not your project. Connections and network pairing
are not restored automatically.

If Codex is not found, choose it under **Settings > Codex**. The app reports
whether the installed version has been tested with this integration.

Minimize the window to leave Pad-Lattice running. Closing it stops its service
and releases MIDI; your Codex terminals remain open. Do not run a separate
Pad-Lattice daemon alongside the desktop app.
