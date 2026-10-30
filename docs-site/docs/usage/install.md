# Install

**Desktop is recommended for interactive use.** The Python CLI is an
independent alternative for terminal workflows and automation. Both use the
same Pad-Lattice engine; neither requires a MIDI controller.

## Desktop App

Desktop bundles Python and the local service. You do not need Python, Node.js,
or Rust to run an installer. **Codex CLI is installed and authenticated
separately**, on the same computer as Pad-Lattice.

### Download the App

1. Open the [Pad-Lattice v0.2.0 release](https://github.com/mrueda/pad-lattice/releases/tag/v0.2.0).
2. Under **Assets**, download the `.dmg` or `.AppImage` matching your computer.
   No GitHub account is required.

| Computer | Platform | Installer |
| --- | --- | --- |
| Mac with Apple Silicon (M-series) | `macos-arm64` | `.dmg` |
| Mac with Intel processor | `macos-x64` | `.dmg` |
| Linux with Intel/AMD processor | `linux-x64` | `.AppImage` |
| Linux with ARM64 processor | `linux-arm64` | `.AppImage` |

Each installer has a matching `.sha256` checksum available in the release assets.
Native Windows installers are not yet
supported. In a VM, choose the guest operating system and processor type.

### Open the App

- **macOS:** open the DMG, copy Pad-Lattice to Applications, then open it there.
- **Linux AppImage:** allow the file to run as a program in its file properties,
  then open it. Keep the file where you want to run the app.

Linux builds use Ubuntu 24.04.

Follow your operating system's security prompts; do not disable
security protections or install a build from an unknown source.

Continue with [Quick Start](./quickstart.md) to connect your first chat.
For source builds, see [Desktop Architecture](../technical-details/desktop.md#build-from-source).

### Storage and Removal

<details className="alert alert--info">
<summary><strong>Where Pad-Lattice stores application data</strong></summary>

Preferences are stored separately from the installed app:

- **Linux:** `~/.local/share/com.mrueda.pad-lattice/`, or `$XDG_DATA_HOME/com.mrueda.pad-lattice/` when configured. Use **Ctrl+H** in the file manager to show hidden folders.
- **macOS:** `~/Library/Application Support/com.mrueda.pad-lattice/`. In Finder, use **Go > Go to Folder** to enter the path.

`settings.json` stores theme, sound, surface layout, pad size, MIDI selections, the Codex executable
path, and network addresses. Connections, pairing PINs, and the service's device
credentials live in memory and are cleared when Desktop closes. A paired browser
keeps its own credential in site storage.

Custom MIDI profiles are separate: `~/.config/pad-lattice/profiles/`, or
`$XDG_CONFIG_HOME/pad-lattice/profiles/`. Additional locations can be configured
with `PAD_LATTICE_PROFILE_PATH`.

The temporary local connection file is `$XDG_RUNTIME_DIR/pad-lattice.sock` on
systems with that runtime directory, otherwise `/tmp/pad-lattice-<uid>.sock`.
`PAD_LATTICE_SOCKET` can override it. It is normally removed when the service stops.

Codex owns your conversations and authentication; these are not saved in
Pad-Lattice's settings folder. Your repositories remain in their original locations.

</details>

#### Update Desktop

Quit Pad-Lattice first. On macOS, replace the app in Applications with the copy
from the new DMG. On Linux, replace the AppImage and allow execution again if needed.
Saved preferences remain; reconnect conversations and pair remote devices again.

#### Uninstall or Reset

1. Quit Pad-Lattice. This stops its local service, not your Codex terminals.
2. Delete the AppImage on Linux, or remove Pad-Lattice from Applications on macOS.
3. To also reset preferences, move the application-data folder above to a backup
   location, or delete it when no longer needed. Keeping it preserves preferences
   for a later reinstall. Moving it without uninstalling resets the app on its next launch.
4. Remove custom MIDI profiles separately only if you no longer need them. On a
   paired phone or tablet, clear site data for the Pad-Lattice address to remove
   its saved pairing credential.

:::caution Keep Codex and your projects

Do not delete your repositories or Codex's data directory (`~/.codex`, unless
you configured another location). Neither is Pad-Lattice application storage.
Uninstalling Desktop does not uninstall Codex or a separately installed Python CLI.

:::

## Python CLI

Install the CLI from PyPI in an isolated environment:

```bash
pipx install pad-lattice
pad-lattice --version
```

With an active Python virtual environment, use
`python -m pip install pad-lattice` instead. Python 3.10 or newer is required.
This installs the command-line tools, browser service, and MIDI support,
**not the desktop window**. Continue with [CLI Setup](./cli.md).

Upgrade with `pipx upgrade pad-lattice`; remove it with `pipx uninstall pad-lattice`.
For a pip installation, use `python -m pip install --upgrade pad-lattice` or
`python -m pip uninstall pad-lattice` in the same environment.

Desktop does not install global Codex hooks. If you previously installed global
Pad-Lattice hooks separately, run `pad-lattice uninstall-codex-hooks` before
removing the CLI. This removes Pad-Lattice entries, not other tools' hooks.

## Try Without Installing

The [public virtual pad](pathname:///play/) has an autoplay Demo, Sandbox, and
audiovisual Show. It uses simulated agents and never connects to your local
Codex conversations.
