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
- one terminal window for Pad-Lattice and another for Codex;
- a modern browser such as Chrome, Chromium, Firefox, or Safari.

Avoid public or guest Wi-Fi. Some guest networks prevent devices from seeing
one another.

## Connect the First Device

### 1. Start Pad-Lattice

On the computer that runs Codex:

```bash
pad-lattice web --lan
```

Leave this terminal open. Pad-Lattice prints three useful items:

```text
Local admin:   http://127.0.0.1:8765/#admin=...
Phone/tablet:  http://192.168.1.20:8765
Pairing PIN:   123456 (expires in 5 minutes)
```

The exact address and PIN will be different on your computer.

### 2. Keep the local page open

Pad-Lattice opens its administrator page on the Codex computer. This page
shows a QR code and can create or revoke pairing codes.

Do not share the `Local admin` URL. It contains the administrator credential
for this daemon.

### 3. Pair the phone, tablet, or laptop

On the remote device, either:

- scan the QR code shown on the local administrator page; or
- open the printed `Phone/tablet` address and enter the six-digit PIN.

The screen should change to **Connected to Codex**. Each QR code or PIN can be
used once and expires after five minutes.

### 4. Start Codex through Pad-Lattice

In another terminal on the Codex computer:

```bash
pad-lattice codex --label work
```

The `work` Agent Scene appears on every connected surface. On the first launch,
use `/hooks` inside Codex to review and trust the scoped Pad-Lattice hooks.

:::tip Resuming an existing conversation

Use the normal Codex session ID after `resume`:

```bash
pad-lattice codex --label work -- resume <SESSION_ID>
```

An already-running plain `codex` process cannot be attached afterwards. Resume
it through `pad-lattice codex` instead.

:::

## Add More Browsers

Pad-Lattice supports the local administrator plus **up to eight remote browser
connections** at the same time.

For each additional phone, tablet, or laptop:

1. On the local administrator page, choose **New code**.
2. Scan the new QR code or enter its new PIN on that device.
3. Wait for **Connected to Codex** before pairing the next device.

A code consumed by the first device cannot pair the second one. Generate one
fresh code per device.

All connected devices can select Agent Scenes and invoke currently lit actions,
including request-scoped Approve and Reject. Coordinate with anyone holding a
paired device; there is one shared selection and one shared action target.

## Share Demo and Show

The local administrator page can start **Demo** or **Show** while the normal
live daemon is running. The same experience appears on every connected
browser and, with `pad-lattice daemon --web`, on the Launchpad too.

- Only the tokenized local administrator page can start or stop an experience.
- Paired phones, tablets, and laptops can answer Demo Scene/action prompts.
- Show is synchronized and read-only on paired devices.
- Sound is independent on each browser and starts muted; one device's toggle
  does not affect another device or the host `--audio-feedback` setting.
- A real agent waiting for a reply or approval immediately interrupts Demo or
  Show and restores the live agent display.

This ownership rule prevents a paired remote from replacing operational state
with a performance, while still allowing several people to experience the
surface together.

Pairings last only while the daemon is running. **Revoke remote** disconnects
every remote browser at once. Per-device revocation is not currently available,
so revoke all devices and pair the trusted ones again if a device is lost.

## Running Inside Parallels Desktop

Parallels **Shared Network** lets the virtual machine reach the network, but it
normally prevents phones and other computers from reaching the VM. Parallels
Desktop Pro can forward one TCP port from the Mac to Pad-Lattice without
putting the whole VM in bridged mode.

The example below uses port `8001`.

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
| **Connected to Codex** | Browser pairing and live synchronization work. |
| **No active agents** | Pairing works; start Codex with `pad-lattice codex`. |
| An Agent Scene such as `work` | That Codex session is registered. |
| A lit Approve or Reject action | The selected session has a live permission request. |
| Dark actions | No compatible action is available for the selected session. |

## Quick Troubleshooting

| Problem | Check |
| --- | --- |
| The page does not open | Confirm both devices use the same private Wi-Fi; temporarily disconnect VPNs and check the computer firewall. |
| A VM address opens only inside the VM | Use the [Parallels forwarding setup](#running-inside-parallels-desktop) or bridged networking. |
| The PIN is rejected | Create a new code; codes are one-use and expire after five minutes. |
| The browser connects but shows no agents | Launch or resume Codex with `pad-lattice codex`, not plain `codex`. |
| The second device cannot use the first PIN | Generate a separate code for every device. |
| A previously paired browser stopped reconnecting | The daemon restarted; pair it again. |

For less common problems, see [Troubleshooting](./troubleshooting.md) and the
[Security Model](../technical-details/security-model.md).
