# FAQ


<details>
<summary>Do I Need a MIDI Controller?</summary>

:::tip No hardware needed

**No.** Use the pad in the desktop app or pair a phone, tablet, or laptop browser.
Physical controllers are optional. See the [Device Catalog](../usage/device-catalog.md).

:::

</details>

<details>
<summary>Does It Control Codex CLI or Codex Desktop?</summary>

**Codex CLI.** The Pad-Lattice desktop app connects to open CLI conversations;
it is not an integration with the Codex desktop app or ChatGPT.

</details>

<details>
<summary>Can I Connect a Conversation Already Running?</summary>

Yes. Open Pad-Lattice, find the chat, and select **Connect**. Codex must run on
the same computer and operating-system account as the Pad-Lattice service.
To use saved history, resume that conversation in Codex first.

</details>

<details>
<summary>Do I Need Python, Hooks, or a Separate Daemon?</summary>

Not with the desktop app: its engine is bundled, its local service starts
automatically, and desktop attachment does not require hooks. Do not launch a
second daemon alongside it. The independent [CLI setup](../usage/cli.md) is
available for terminal-based use.

</details>

<details>
<summary>Does the Public Playground Control My Agents?</summary>

No. The website is a simulation. For real control, run Pad-Lattice locally and
connect your chats. A paired browser then controls that running instance.

</details>

<details>
<summary>Can I Use Several Screens or Controllers Together?</summary>

Yes. They share the same selected conversation and available actions. Selecting
a different session on one surface changes the selection on the others. Up to
eight sessions have visible slots. See [Connect Screens](../usage/connect-browsers.md).

</details>

<details>
<summary>Can I Answer Any Question or Approve Everything From the Pad?</summary>

No. Ordinary prompts and replies stay in Codex. Desktop attachment exposes
supported single-request Approve/Reject decisions and Stop for a known running
turn. Read the request in Codex before approving. Dark controls are unavailable,
not broken. See [How It Works](../usage/control-codex.md).

</details>

<details>
<summary>Why Does My Phone Not Connect With the QR Code?</summary>

Enable network pairing and keep both devices on the same trusted network.
A localhost address only works on the computer running Pad-Lattice. PINs and QR
codes are single-use and expire after five minutes; create a fresh one if needed.
A VM may need port forwarding. Follow [Connect Screens](../usage/connect-browsers.md).

</details>

<details>
<summary>Which Hardware Is Tested?</summary>

The Launchpad Pro Mk1 is physically tested. Mini Mk3, Pro Mk3, and the Stream
Deck plugin remain experimental. The [Device Catalog](../usage/device-catalog.md)
lists their requirements, limitations, and how to help test or add a device.

</details>

<details>
<summary>Is Pairing Safe to Expose to the Internet?</summary>

:::warning Trusted networks only

No. Keep the default local connection unless you need trusted-LAN access.
LAN traffic is unencrypted, and paired devices can invoke available actions,
including approvals. Never expose the service through your router. Use
**Revoke paired devices** when access is no longer needed.
See the [Security Model](../technical-details/security-model.md).

:::

</details>

<details>
<summary>Where Can I Get Help or Report a Problem?</summary>

Start with [Troubleshooting](../usage/troubleshooting.md). If the problem remains,
open a [GitHub issue](https://github.com/mrueda/pad-lattice/issues) with your
Pad-Lattice version, operating system, surface, and steps to reproduce it.
Do not include pairing credentials or private conversations. Report security
issues through the [security policy](https://github.com/mrueda/pad-lattice/security/policy).

</details>
