# Connect a Phone, Tablet, or Laptop

A browser can control the chats connected to Pad-Lattice. It does not start
another agent: every surface shares the same selected conversation.

![A phone, laptop, and local administrator browser connected to the same Pad-Lattice service](/img/multi-browser-setup.svg)

## Connect the First Device

1. Keep Pad-Lattice open on the computer running Codex. Connect both computers
   or devices to the same **trusted private network**.
2. Open **Settings > Phone and tablet**, enter the computer's private IPv4
   address, and choose **Enable pairing**.
3. Choose **Pair device** beside the pad.
4. Scan the QR code, or open the displayed address and enter its PIN.
5. Wait for **Pad connected**. If no sessions appear, connect a chat in the
   desktop app.

Each code works **once** and expires after **five minutes**. A localhost address
only works on the computer running Pad-Lattice, not on your phone.

:::warning Keep it on your private network

Pairing allows available actions, including approvals. Network traffic is not
encrypted. Do not expose the service to the internet or use public Wi-Fi.

:::

## Add More Browsers

Up to **eight remote browser connections** can use the service at once.
Choose **New code** for each additional device; a used PIN cannot pair another one.

Selection is shared. Check the selected chat before acting, especially if
someone else is using another surface.

## Share Demo and Show

Disconnect real sessions, then choose **Demo & Show > Demo** or **Demo & Show > Show**
in the desktop app. Paired browsers follow the experience. Each browser has its
own **Sound** toggle, initially muted.

Only the desktop or local administrator page starts and stops playback.
Paired browsers can answer Demo prompts; Show is read-only.

## Disconnect and Revoke

**Revoke paired devices** disconnects all paired browsers and the Stream Deck
plugin. Per-device revocation is not available. Restarting Pad-Lattice also
invalidates pairings; create new codes to reconnect.

## Running Inside Parallels Desktop

Shared Network can prevent your phone from reaching the VM directly. Use bridged
networking or the port-forwarding setup below.

<details>
<summary>Port forwarding with Parallels Pro and the CLI</summary>

Close the desktop app first. Its settings do not expose a fixed port or a
separate advertised host address; this setup uses the independent CLI.

1. Find the VM's private address with `hostname -I`.
2. Find the Mac's private address in **System Settings > Wi-Fi > Details > TCP/IP**.
3. Under **Parallels Desktop > Preferences > Network > Shared**, add a rule:

| Field | Example |
| --- | --- |
| Protocol | TCP |
| Source port | 8001 |
| Forward to | VM address: 10.211.55.4 |
| Destination port | 8001 |

Replace the example addresses with your own, then run inside the VM:

```bash
pad-lattice web --lan --port 8001 \
  --bind-host 10.211.55.4 \
  --advertise-host 192.168.1.45
```

Here, `--bind-host` is the VM address and `--advertise-host` is the Mac address
your phone can reach. Open `http://192.168.1.45:8001` on the phone and enter
the PIN. Follow [CLI Setup](./cli.md) to connect Codex.

Keep source and destination ports the same. **Do not add router forwarding**:
this rule should connect only your trusted LAN to the VM. See
[Parallels network settings](https://docs.parallels.com/landing/pdfm-ug/parallels-desktop-for-mac-26-users-guide/parallels-desktop-preferences-and-virtual-machine-settings/parallels-desktop-preferences/network-preferences).

</details>

## Quick Troubleshooting

| Problem | Check |
| --- | --- |
| Page does not open | Address, Wi-Fi, firewall, and VPN settings. A VM may need forwarding. |
| PIN rejected | Generate a fresh code; it may be expired or already used. |
| Connected, but no agents | Connect a chat in Desktop, or follow [CLI Setup](./cli.md). |
| Previously paired device disconnected | The service may have restarted or its pairings been revoked. |

See [Troubleshooting](./troubleshooting.md) for other problems.
