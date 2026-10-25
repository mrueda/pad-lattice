# Connect a Phone, Tablet, or Laptop

You do not need a MIDI controller to use Pad-Lattice. A phone, tablet, or
laptop browser can become a live control surface for Codex.

:::info One control room, several remotes

Connecting another browser does **not** start another agent. Every connected
screen mirrors the same Pad-Lattice daemon, selected Agent Scene, state, and
available actions. Selecting a Scene on one screen changes it on all screens.

:::

![A phone, laptop, and local administrator browser connected to one Pad-Lattice daemon and its shared Codex Agent Scenes](/img/multi-browser-setup.svg)

[Open the connection diagram at full size](/img/multi-browser-setup.svg).

## Before You Start

You need:

- Pad-Lattice installed on the computer that runs Codex;
- the computer and remote devices on the same **trusted private network**;
- the Pad-Lattice desktop app (or the independent CLI service);
- a modern browser such as Chrome, Chromium, Firefox, or Safari.

Avoid public or guest Wi-Fi. Some guest networks prevent devices from seeing
one another.

## Connect the First Device

### 1. Open Desktop Settings

On the computer running Codex, open **Pad-Lattice > Settings > Phone and tablet**.
Enter this computer's private IPv4 address and choose **Enable pairing**.
Use the address of the trusted local network, not a public internet address.

The app displays the browser address, including its port. Keep the app open.
In a VM, read the [Parallels section](#running-inside-parallels-desktop) first.

### 2. Create a Pairing Code

Choose **Pair device** beside the pad. Pad-Lattice displays a QR code and a
six-digit PIN. Each code works once and expires after five minutes.

### 3. Open the Pad on the Other Device

Scan the QR code, or open the address shown in Settings and enter the PIN.
The screen should change to **Pad connected**.

### 4. Connect a Codex Conversation

In the desktop app, select **Connect** beside an open Codex chat.
Its Scene appears on every paired surface. A phone does not discover or launch
Codex itself; it controls the conversations connected on the host computer.

<details>
<summary>Alternative: pair browsers from the CLI</summary>

With the desktop app closed, run:

```bash
pad-lattice web --lan
```

Leave the process running. It opens a local administrator page and prints the
remote address and PIN. Treat the tokenized local administrator URL as a
credential; never share it.

Start or resume an integrated Codex session in another terminal:

```bash
pad-lattice codex --label work
```

Review `/hooks` on the first integrated session. See [CLI Setup](./cli.md)
for the complete independent workflow.

</details>

## Add More Browsers

Pad-Lattice supports the local administrator plus **up to eight remote browser
connections** at the same time.

For each additional phone, tablet, or laptop:

1. In the desktop app or local administrator page, choose **New code**.
2. Scan the new QR code or enter its new PIN on that device.
3. Wait for **Pad connected** before pairing the next device.

A code consumed by the first device cannot pair the second one. Generate one
fresh code per device.

All connected devices can select Agent Scenes and invoke currently lit actions,
including request-scoped Approve and Reject. Coordinate with anyone holding a
paired device; there is one shared selection and one shared action target.

## Share Demo and Show

Choose **Explore > Demo** or **Explore > Show** in the desktop app.
The same experience appears on connected browsers and the connected Launchpad.

- Disconnect real agent sessions first. Connecting one stops playback and restores the live pad.
- Only the desktop app or local CLI administrator page can start or stop playback.
- Paired devices can answer Demo prompts; Show is read-only.
- Each browser has its own **Sound** toggle, initially muted.

Pairings last only while the daemon is running. **Revoke remote** disconnects
every remote browser at once. Per-device revocation is not currently available,
so revoke all devices and pair the trusted ones again if a device is lost.

## Running Inside Parallels Desktop

Parallels **Shared Network** lets the virtual machine reach the network, but it
normally prevents phones and other computers from reaching the VM. Parallels
Desktop Pro can forward one TCP port from the Mac to Pad-Lattice without
putting the whole VM in bridged mode.

The example below uses the **CLI alternative** with a fixed port, `8001`.
Close the desktop app before using it. The desktop preview does not yet expose
fixed-port or advertised-host settings; use it directly on the LAN or use this
CLI setup for explicit VM port forwarding.

### 1. Find both private addresses

Inside the Linux VM, run:

```bash
hostname -I
```

The Shared Network address commonly starts with `10.211.55`. In this example,
the VM address is `10.211.55.4`.

On the Mac, open **System Settings > Wi-Fi > Details > TCP/IP** and note the
IPv4 address. In this example, the Mac address is `192.168.1.45`.

### 2. Add the Parallels forwarding rule

Open **Parallels Desktop > Preferences > Network > Shared**, then add a port
forwarding rule:

| Field | Value |
| --- | --- |
| Protocol | `TCP` |
| Source port | `8001` |
| Forward to | the Linux VM or its `10.211.55.4` address |
| Destination port | `8001` |

Use the same source and destination port. The official [Parallels Network
Preferences](https://docs.parallels.com/landing/pdfm-ug/parallels-desktop-for-mac-26-users-guide/parallels-desktop-preferences-and-virtual-machine-settings/parallels-desktop-preferences/network-preferences)
guide shows where these fields are located.

### 3. Start Pad-Lattice inside the VM

Replace the example addresses with your own:

```bash
pad-lattice web --lan --port 8001 \
  --bind-host 10.211.55.4 \
  --advertise-host 192.168.1.45
```

Here, `--bind-host` is the VM address where Pad-Lattice listens.
`--advertise-host` is the Mac address that phones can reach.

### 4. Open the Mac address on each device

For the example above, open:

```text
http://192.168.1.45:8001
```

Enter the printed PIN, then repeat [Add More Browsers](#add-more-browsers) for
each additional device.

:::warning Forward only inside your trusted LAN

The Parallels rule crosses only from the Mac to its VM. Do not add router port
forwarding, expose port `8001` to the internet, or use this setup on public
Wi-Fi. LAN traffic is authenticated but not encrypted.

:::

## What You Should See

| Screen | Meaning |
| --- | --- |
| **Pad connected** | Browser pairing and live synchronization work. |
| **No active agents** | Pairing works; connect a chat in Desktop (or launch one through the CLI integration). |
| An Agent Scene such as `work` | That Codex session is registered. |
| A lit Approve or Reject action | The selected session has a live permission request. |
| Dark actions | No compatible action is available for the selected session. |

## Quick Troubleshooting

| Problem | Check |
| --- | --- |
| The page does not open | Confirm both devices use the same private Wi-Fi; temporarily disconnect VPNs and check the computer firewall. |
| A VM address opens only inside the VM | Use the [Parallels forwarding setup](#running-inside-parallels-desktop) or bridged networking. |
| The PIN is rejected | Create a new code; codes are one-use and expire after five minutes. |
| The browser connects but shows no agents | Select **Connect** beside a chat in Desktop; CLI users should use `pad-lattice codex`. |
| The second device cannot use the first PIN | Generate a separate code for every device. |
| A previously paired browser stopped reconnecting | The daemon restarted; pair it again. |

For less common problems, see [Troubleshooting](./troubleshooting.md) and the
[Security Model](../technical-details/security-model.md).
