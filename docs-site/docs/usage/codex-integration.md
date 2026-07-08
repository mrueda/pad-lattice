# Codex Integration

Pad-Lattice has two Codex paths today.

## Non-interactive Codex

Use `codex-exec` for real Codex CLI runs that expose JSON-line events:

```bash
pad-lattice codex-exec "summarize this repository"
```

The adapter runs:

```bash
codex exec --json ...
```

and maps Codex events to Pad-Lattice states:

| Codex event | Pad-Lattice state |
| --- | --- |
| `thread.started` | `running` |
| `turn.started` | `running` |
| `item.started` | `running` |
| `turn.completed` | `success` |
| `turn.failed` | `error` |
| `error` | `error` |

`success` and `error` are transient. The daemon shows them briefly and then
returns to `waiting_for_reply`.

## Interactive Codex

Normal `codex` and `codex resume` sessions do not automatically emit
Pad-Lattice states yet.

The next integration step is a sample Codex `hooks.json` that users can copy
into Codex config. Hooks can update turn-level states such as:

- prompt submitted
- running
- approval needed
- waiting again

Hooks do not expose every keystroke while the user is typing.
