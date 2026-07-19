# Security Model

Pad-Lattice is a **local control channel for agent actions**, not only a status
display. A paired browser or physical controller can approve or reject a live
Codex permission request. Treat every enabled surface as an authorized operator.

## Trust Boundaries

| Boundary | Protection | Trust assumption |
| --- | --- | --- |
| Codex lifecycle hooks | Hooks are scoped to `pad-lattice codex`; Codex requires review of each exact definition. Pad-Lattice never bypasses hook trust. | The reviewed Pad-Lattice executable and its installation path are trusted. |
| Local Unix socket | The socket is mode `0600`. Linux also rejects peers whose kernel-reported UID differs from the daemon UID. | Other processes running as the same OS user are trusted. |
| Local browser | Every daemon generates a random 256-bit administrator token. The startup URL carries it in the fragment, which is not sent in the HTTP request. | The tokenized local URL and browser profile are private to the operator. |
| LAN browser | A one-use QR secret or six-digit PIN expires after five minutes. Reconnect tokens live only until daemon shutdown or explicit revocation. | The paired device and local network are trusted. |
| MIDI input | Only mapped positive Note On or Control Change events become semantic surface events. | The selected MIDI port, physical access, and user-supplied profile are trusted. |

The same-user assumption matters. A process already running as your account can
connect to the local socket, report agent state, inspect the registry, or
subscribe to actions. Pad-Lattice does not attempt to isolate mutually hostile
programs running under one OS account.

## Action Authorization

Browser and MIDI surfaces never choose an agent identity directly. They emit a
semantic selection or action, and the daemon applies all of these gates:

1. an Agent Scene must be explicitly selected;
2. the selected agent must be in a compatible state;
3. a live integration must advertise that action;
4. permission decisions must match one pending request;
5. one-shot subscriptions are disabled before delivery;
6. repeated actions are debounced;
7. an action is delivered to one matching subscriber, never broadcast.

Approve and Reject therefore apply to the selected, current permission request.
They do not create a persistent Codex permission rule. Codex still owns its
sandbox and approval policy.

## Browser Defenses

The live bridge binds to loopback by default. `--lan` adds a second listener on
only the selected private IPv4 interface rather than every interface. A NATed
VM may advertise a different private address when its host forwards the same
TCP port to that listener. The server also provides:

- exact Host and same-origin WebSocket checks;
- token authentication before any state is sent;
- separate local-administrator and remote-device credentials;
- local-administrator authorization for Demo/Show start and stop;
- typed command allowlists and bounded JSON messages;
- browser, remote-client, command-rate, and event-queue limits;
- disabled WebSocket compression;
- a restrictive Content Security Policy and no third-party scripts;
- sanitized browser state without prompts, responses, terminal output, raw
  working directories, or full Codex event payloads.

These controls follow the main recommendations in the
[OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).

## Residual Risks

:::warning LAN mode is not encrypted

`pad-lattice web --lan` uses HTTP and WebSocket traffic. A hostile network can
observe or tamper with credentials and actions. Use it only on a trusted private
network. A host-to-VM forward must remain inside that trusted LAN; do not
forward it through a router or expose it to the internet. Use loopback mode
when this condition is not satisfied.

:::

- A paired browser can press any action currently exposed by the selected
  integration, including Approve. Revoke remote access when the device is no
  longer under your control.
- A paired browser can answer built-in Demo prompts but cannot start or stop
  Demo or Show. Real reply and approval waits preempt either experience.
- The local administrator URL is a bearer credential. Do not paste it into
  chat, logs, screenshots, or shared shell history.
- A malicious process under the same OS account is outside the isolation
  boundary. Use separate OS accounts or containers for mutually untrusted
  workloads.
- A device profile can emit raw MIDI and SysEx startup, clear, and shutdown
  commands. Load profile files only from a source you trust.
- Anyone with physical access to the selected controller, or software access to
  inject its MIDI input, can press available controls.
- Hook trust protects the command definition, not an executable that is later
  replaced in place. Keep the Pad-Lattice installation writable only by the
  intended OS user.

## Operator Checklist

1. Install Pad-Lattice in an isolated environment such as `pipx`.
2. Start integrated sessions with `pad-lattice codex` and review `/hooks`.
3. Keep the default loopback browser unless phone or tablet access is required.
4. Use `--lan` only on a trusted private network and never expose its port
   beyond that LAN.
5. Pair only devices you control and use **Revoke remote access** afterward.
6. Confirm the selected Scene and terminal title before approving a request.
7. Use only trusted device profiles and MIDI ports.
8. Keep Pad-Lattice and its dependencies current.

Report security issues through the repository's
[security policy](https://github.com/mrueda/pad-lattice/security/policy).
