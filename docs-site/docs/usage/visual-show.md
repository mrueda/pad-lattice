# Visual Show

**Show uses the pad creatively: as a canvas for light, movement, and music.**
It is separate from controlling agents. It explores what a small grid can
express beyond status indicators, on a Launchpad or a virtual pad.

The included story, **A Spark Becomes a Constellation**, follows a lone light
as it finds an idea, a friend, and eventually a community. It lasts about
43 seconds, with an optional original soundtrack.

## Play in Desktop

1. Disconnect real conversations.
2. Choose **Demo & Show > Show**.
3. Enable **Sound** for the music.

A connected Launchpad and paired browsers follow the performance.
Use **Back to live pad** to stop. Only the administrator can start or stop
playback; connecting a real agent ends the show.

No hardware is needed. You can also [watch in the public pad](pathname:///play/).

**Demo is different:** it lets you practice responding to simulated agents.
Show is a light-and-music performance, not a tutorial or a view of agent activity.

## The Story

![Eight scenes showing one spark becoming an idea, finding a friend, surviving a storm, calling a community, and forming the Pad-Lattice constellation](/img/visual-show-storyboard.svg)

A spark becomes an idea, searches for company, and finds a friend. A storm
breaks their connection. A call brings other lights together, ending in a
constellation and the letters **PL**.

Colors are chosen for the story, not the normal agent-state meanings.
The optional score combines piano, sustained strings, echoes, and a synthesized
voice saying "PAD LATTICE."

## Outer Rails During Show

The top and right buttons become part of the animation, **not controls**:

- Usually they show progress through the story.
- During the search, they follow the moving light's row and column.
- In the storm, they form a red border.
- In the finale, colors travel around the grid.

They do not simply copy the grid's colors. The Launchpad Pro Mk1's left and
bottom buttons stay unused.

## Play from the CLI

```bash
pad-lattice show --surface midi --audio
pad-lattice show --surface web
pad-lattice show --surface both --audio
```

MIDI playback starts immediately and opens the device directly; stop any daemon
using that device first. Web modes wait for **Start Show** on the local
administrator page. Browser sound is enabled separately on each device.

Use `--tempo 0.8` for slower playback or `--tempo 1.2` for faster playback.
Press `Ctrl-C` to stop.

## How It Is Made

The story and score are written once in Python, then compiled into shared
animation and audio files for physical and virtual playback. There is no
separate browser composition.

See the [experience asset compiler](../technical-details/developer-guide.md#experience-asset-compiler)
for the source files, schemas, and build commands, or
[Audio Feedback](./audio-feedback.md) for sound setup.
