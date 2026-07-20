# Origin and Development

Pad-Lattice grew from [mrueda](https://github.com/mrueda)'s personal need for a
more direct way to work with Codex CLI. With several sessions open, he wanted
to see which agent needed attention and send a deliberate action without
replacing the terminal.

This is an **independent hobby project developed in mrueda's free time**.

## From Ableton Live To Agents

mrueda is also a musician and a member of the duo [The New
Assembly](https://www.thenewassembly.com/). He already used a Novation Launchpad
Pro with Ableton Live and owned other MIDI instruments. Its tactile RGB grid
and scene controls suggested a new use outside music: stable visual symbols for
agent states and illuminated controls for actions that were genuinely
available.

The physical controller came first. The Virtual Pad followed, preserving the
same visual language for people using a phone, tablet, or computer.

## Development

Public development began on 3 July 2026 with the [initial Pad-Lattice
scaffold](https://github.com/mrueda/pad-lattice/commit/cc0440b2d0bcdc49335c5a0e77e49996bf3f9c90).
By 7 July, commits had established [host
mode](https://github.com/mrueda/pad-lattice/commit/72152e997fa37132a78c91f636157e42d30bf596),
a [visual state
grammar](https://github.com/mrueda/pad-lattice/commit/f28a14918dbb54f992d1d40b949dec3fe5796601),
and a [Codex CLI control
bridge](https://github.com/mrueda/pad-lattice/commit/ce7c1682613adb92f6ac7db37286172117684701).
Further use added multi-agent Scenes, device profiles, virtual surfaces, audio,
and shared Demo and Show experiences.

Pad-Lattice was developed through repeated cycles of architecture,
implementation, automated testing, and evaluation on the physical Launchpad or
a paired browser. Codex CLI (OpenAI, GPT-5.6) assisted with implementation,
testing, documentation, and design exploration. mrueda set the product
direction and evaluated the interaction on real devices.
