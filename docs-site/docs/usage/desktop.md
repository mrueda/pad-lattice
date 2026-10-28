# Desktop Pad

import DesktopWalkthrough from '@site/src/components/DesktopWalkthrough';

Connect your open Codex CLI chats and control them from the on-screen pad.
[Install](./install.md) includes Python and the local service; install and
authenticate Codex CLI separately on the same computer.

<DesktopWalkthrough />

## Find Open Conversations

Select **Connect** beside a chat under **Open Codex conversations**.
Its Scene number and color appear on the pad. Codex stays in its original
terminal; no restart or hooks are needed.

Use **Refresh chats** to update the list. It shows conversations loaded by Codex
on this computer and OS account, not saved history or chats on another host.
Resume a saved chat in Codex first. A VM cannot discover chats on its Mac host.

The list separates **open** conversations from those **connected to the pad**.
If Codex is unavailable, click its status at the top to open settings, check the
executable, and select **Check again**. An empty conversation list is not an
installation error. Connection errors link to **Diagnostics** for a shareable report.

**Disconnect** releases the pad slot without stopping Codex. Codex may keep a
thread loaded after its terminal closes; see [Troubleshooting](./troubleshooting.md)
if the list differs from your open windows.

## Use the Live Pad

1. Select the chat's colored Scene button on the right.
2. Check **Selected conversation** and read the request in Codex.
3. Press a lit action when you want to approve, reject, or stop.

Only supported actions light up. Ordinary replies stay in Codex.
[How It Works](./control-codex.md#read-the-surface) shows the glyphs and controls.

**Needs attention** lists approvals first, then errors and conversations waiting
for a reply, with time in that state. Select a row to bring that chat onto the pad;
selection does not approve anything. **All conversations** keeps the usual Scene order.

| Control | What it does |
| --- | --- |
| **Maximize pad** | Hides setup panels and enlarges the pad. |
| **Restore workspace** or Escape | Returns to the full view. |
| **Refresh chats** | Updates the conversation list. |
| **Settings > Reload interface** | Reloads the window without disconnecting chats. |

## Connect a Launchpad

**Settings > Devices** groups connections into **Browsers**, **MIDI controllers**,
and **Stream Deck**, with a connected count for each. Browser and Stream Deck
pairing share one network configuration.

Connect it over USB, then choose **Settings > Devices > MIDI controllers > Connect**.
If automatic detection cannot choose a device, select its profile and ports.
Experimental profiles must be selected explicitly.

See [Novation Launchpad](./launchpad.md) for models and the control diagram.
Disconnecting MIDI does not end your chats; the virtual pad keeps working.

To check an unfamiliar controller, disconnect chats and MIDI, then select explicit
ports and use **Hardware test** in the same settings page. Compare the lights with
the preview and press each requested hardware control. You can stop at any time
and export a report. See [Device Testing](../technical-details/device-testing.md).

## Connect a Stream Deck

Open **Settings > Devices > Stream Deck** for the plugin download, pairing, and
connected plugins. The plugin includes an editable 15-key starter layout;
customize keys in Elgato's software, not the MIDI page. On the same computer,
pair with the displayed address and PIN; network access can stay off.
The plugin is experimental; a hardware-test wizard is not yet available for it.
See [Elgato Stream Deck](./stream-deck.md).

## Connect a Phone

Open **Pair device** in the toolbar, or **Settings > Devices > Browsers**.
Enable network access; a fresh QR/PIN window opens automatically.
Both devices must be on the same trusted network. The paired-device list lets
you disconnect a device or revoke its access without affecting the others.
The toolbar shows the live connected-device count; select it to open the list.
**Network enabled** means pairing is available, not that a phone is connected.
Follow [Connect Screens](./connect-browsers.md) for the QR/PIN steps.

## Try Demo and Show

Disconnect real sessions, then choose **Demo & Show > Demo** or **Demo & Show > Show**.
Enable **Sound** for audio. **Back to live pad** ends playback.

Demo & Show is disabled while real sessions are connected. Connecting a session
during playback also returns the pad to live control.

## Preferences and Closing

Choose **Light** or **Dark** under **Settings > Appearance**. The pad stays dark
in both themes to preserve its LED colors.

Theme, sound, pad size, MIDI selections, and the Codex executable path save automatically
in the app's settings folder, not your project. Connections and network pairing
are not restored automatically.

If Codex is not found, choose it under **Settings > Codex**. The app reports
whether the installed version has been tested with this integration.

**Settings > About** lists the app version, project links, license, and core
third-party library credits. **Bundled dependency notices** opens the collected
license texts. **Copy diagnostics** copies versions, connection counts, and failed
operation names, without prompts, tokens, device names, or private paths.

If the connection drops, stale actions clear and a status banner appears, including
in maximized mode. Select **Reconnect** when Desktop is available again;
the browser does not keep retrying. Revoked access requires pairing again.

Minimize the window to leave Pad-Lattice running. Closing it stops its service
and releases MIDI; your Codex terminals remain open. Do not run a separate
Pad-Lattice daemon alongside the desktop app.
