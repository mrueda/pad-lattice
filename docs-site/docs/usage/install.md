# Install

**Desktop is recommended for interactive use.** The Python CLI is an
independent alternative for terminal workflows and automation. Both use the
same Pad-Lattice engine; neither requires a MIDI controller.

## Desktop Preview

Desktop bundles Python and the local service. You do not need Python, Node.js,
or Rust to run an installer. **Codex CLI is installed and authenticated
separately**, on the same computer as Pad-Lattice.

:::note Preview availability

Desktop installers are currently build artifacts, not a published desktop
release. The PyPI release does not include the desktop app.
Use a successful build from the official repository; if none is available,
use the CLI or the developer source-build instructions linked below.

:::

### Choose a Build

1. Open [Build desktop installers](https://github.com/mrueda/pad-lattice/actions/workflows/build-desktop.yml).
2. Choose a successful run and scroll to **Artifacts**. GitHub may ask you to sign in.
3. Download the `pad-lattice-<platform>-<commit>` artifact matching your computer,
   not the `desktop-checks` screenshots. Extract the archive.

| Computer | Platform | Installer |
| --- | --- | --- |
| Mac with Apple Silicon (M-series) | `macos-arm64` | `.dmg` |
| Mac with Intel processor | `macos-x64` | `.dmg` |
| Linux with Intel/AMD processor | `linux-x64` | `.AppImage` or `.deb` |
| Linux with ARM64 processor | `linux-arm64` | `.AppImage` or `.deb` |

Each installer includes a matching `.sha256` checksum and a `source.json`
record identifying its source commit. Native Windows installers are not yet
supported. In a VM, choose the guest operating system and processor type.

### Open the App

- **macOS:** open the DMG, copy Pad-Lattice to Applications, then open it there.
- **Linux AppImage:** allow the file to run as a program in its file properties,
  then open it. Keep the file where you want to run the app.
- **Ubuntu/Debian:** install the matching DEB with your package installer, then
  open Pad-Lattice from the applications menu. The builds use Ubuntu 24.04.

Signing and notarization remain release work. Follow your operating system's
security prompts and your organization's software policy; do not disable
security protections or install a build from an unknown source.

Continue with [Quick Start](./quickstart.md) to connect your first chat.
For source builds, see [Desktop Architecture](../technical-details/desktop.md#build-from-source).

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

## Try Without Installing

The [public virtual pad](pathname:///play/) has a guided Demo, Sandbox, and
audiovisual Show. It uses simulated agents and never connects to your local
Codex conversations.
