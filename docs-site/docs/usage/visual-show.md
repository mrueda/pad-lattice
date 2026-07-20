# Visual Show

`pad-lattice show` turns a physical or virtual surface into a small stage. The reference
performance, **A Spark Becomes a Constellation**, is an emotional visual story
rather than a tour of Pad-Lattice features.

```bash
pad-lattice show --surface midi --audio
pad-lattice show --surface web
pad-lattice show --surface both --audio
```

`midi` is the default and starts immediately. It opens MIDI ports directly, so
stop a running MIDI daemon first. `web` and `both` open the tokenized local
administrator page and wait for that page to choose **Show**. A normal live
`pad-lattice web` or `pad-lattice daemon --web` also exposes Show from its
administrator page without stopping the daemon.

Every connected surface receives the same cue. Paired browsers can watch but
cannot start or stop playback. A real agent waiting for a reply or approval
preempts Show and restores operational state immediately.

## The Story

![Eight scenes showing one spark becoming an idea, finding a friend, surviving a storm, calling a community, and forming the Pad-Lattice constellation](/img/visual-show-storyboard.svg)

| Act | Emotion | Readable visual sequence |
| --- | --- | --- |
| Prelude - Alone | Loneliness | One cyan light appears in darkness. |
| Act I - An Idea | Wonder | The light grows into a warm light bulb. |
| Act II - The Search | Curiosity | A question mark becomes a magnifying glass. |
| Act III - A Friend | Hope | Cyan and magenta figures meet, connect, and form a heart. |
| Act IV - The Storm | Fear and loss | Red lightning breaks the heart; a sad face remains. |
| Act V - The Call | Courage | An exclamation becomes a signal; colored answers arrive and connect. |
| Act VI - Together | Belonging and joy | The community becomes a green solution, smile, and shared heart. |
| Finale - A Constellation | Celebration | Every light joins the constellation, which resolves into `PL`. |

The final cyan spark repeats the opening image with a different meaning:
**no light is alone once it belongs to a constellation**. The outer rails form
a quiet chapter-progress frame, then join the full-color finale.

At normal tempo the 80-frame performance lasts about 43 seconds:

```bash
pad-lattice show --tempo 0.8  # slower
pad-lattice show --tempo 1.2  # faster
```

Press `Ctrl-C` at any time. Cleanup still runs.

## Outer Rails During Show

The reference Show surface contains **80 authored lights**: the 64-pad matrix,
eight top-rail lights, and eight right-rail lights. While Show is playing, the
two rails stop acting as commands and Agent Scene selectors. Their buttons are
disabled, and each Show cue supplies their colors directly.

The renderer does not automatically copy matrix colors onto the rails. Their
choreography changes with the story:

| Story moment | Top and right rail behavior |
| --- | --- |
| Most acts | The top rail is an eight-act progress line: earlier acts remain dim and the current act is bright. The right rail reverses that line to frame the matrix. |
| The Search | A bright top light marks the current matrix column while a bright right light marks its row. Together they follow the moving search point. |
| The Storm | The rails become a red border around the broken-heart scene. |
| The Call | Identity colors arrive one by one. The top rail fills forward and the right rail fills in reverse as the community gathers. |
| Together and Finale | The rails carry the full identity spectrum, then rotate in opposite directions around the constellation. |
| Final spark | Both rails return to darkness so the single cyan light can close the story. |

The right rail therefore **does mirror the top rail in reverse during some
chapter frames**, but it is not a general color-mirroring effect. In other
scenes the rails mark coordinates, frame an emotion, count arrivals, or extend
motion beyond the matrix.

The Launchpad Pro Mk1 also has left and bottom controls. Those additional
positions are outside the common 80-light reference surface, remain reserved,
and are not used by the Show.

## Cinematic Color

Each authored light carries both an exact RGB value and a semantic palette
fallback. The supported Launchpad Pro Mk1 uses its direct RGB SysEx mode, with
independent red, green, and blue values from `0` to `63`. This gives the story
cool moonlight, warm tungsten, deep storm tones, graded hearts, and more than
80 distinct constellation colors instead of limiting it to operational state
colors.

Profiles without direct RGB render the same geometry through the fallback
palette. This is a show capability, not a Visual Protocol change; normal agent
states continue using their small, stable semantic vocabulary. See Novation's
[Launchpad Pro Programmer's Reference Guide](https://fael-downloads-prod.focusrite.com/customer/test/s3fs-public/downloads/Launchpad%20Pro%20Programmers%20Reference%20Guide%201.01.pdf)
for the Mk1 RGB command.

## Synchronized Score

`--audio` adds an original 16-bar stereo score synthesized by Pad-Lattice
itself. A solitary piano note discovers a six-note **spark motif** in B-flat
natural minor: `B-flat - F - D-flat - A-flat - C - B-flat`. Slow, wide string
voicings sustain the `B-flat minor - D-flat/A-flat - G-flat - Fsus`
progression for four or eight beats at a time, apart from the compact cadence
into Act III. Filtered stereo echoes answer at the `3+2+3` accent points; a
shallow modulated delay widens the ambience without doubling the dry melody.
Every piano event feeds this space. Through the middle acts, harmony changes
only once every eight beats so visual transitions unfold inside a continuous
musical field rather than receiving a new chord each time.

Cyan states the motif from the left and magenta answers from the right. The
storm reduces it to two E-flat-minor fragments; four spatial replies imply the
larger visual community. The complete motif returns at the `PL` finale,
supported by the sustained string progression, spacious piano, and a final low
cello B-flat. As the final mark resolves, an original vintage computer voice
says **"PAD LATTICE"**. The score briefly ducks beneath it for intelligibility.

The voice is synthesized directly from voiced formants, stop bursts, and
fricative noise. It uses no recorded speech, external text-to-speech service,
or Python audio dependency.

Every musical entrance is attached to a named story cue, so tempo changes
rescale the complete visual and musical timelines together.

The Python host renders the score through an available local player. The
browser uses a deterministic WAV compiled from that same score and bundled
with the application, avoiding a second TypeScript composition. Browser sound
is per-device, muted by default, and synchronized independently of the host
`--audio` flag. See [Audio Feedback](./audio-feedback.md) for supported host
players and the separate daemon earcon vocabulary.

## Compiled Once, Played Everywhere

![The visual story and score pass through the experience asset compiler to produce one performance manifest and audio set used by both Python MIDI and TypeScript browser runtimes](/img/experience-asset-compiler.svg)

Pad-Lattice calls this build boundary the **experience asset compiler**. The
visual story is authored expressively in Python alongside the original score,
voice, and earcons. A deterministic compiler then turns those sources into a
compact Performance Manifest and a WAV asset set.

The physical and virtual surfaces do not recreate the Show independently.
Both play those same versioned assets, with the same frames, colors, captions,
timing, and soundtrack. Runtime playback never imports or executes the
authoring functions. This keeps the creative source flexible while making the
result portable and reproducible.

[Performance Manifest Schema 1](https://mrueda.github.io/pad-lattice/schemas/performance-manifest-v1.json)
documents the generated contract. The interactive Demo intentionally follows
a second path: its stage graph is human-authored as
[Demo Manifest Schema 1](https://mrueda.github.io/pad-lattice/schemas/demo-manifest-v1.json),
then consumed by the same Python and TypeScript experience runtimes. See the
[Experience Asset Compiler](../technical-details/developer-guide.md#experience-asset-compiler)
section for the sources of truth and regeneration workflow.

## Visual Safety

The script sends only steady palette or RGB values. It does not use hardware
flash or pulse modes. Authored frames are held for at least 220 milliseconds,
and tests prevent majority-surface on/off transitions. MIDI output is cached,
so only lights whose values change are resent.

## Separate From The Visual Protocol

Visual Protocol 1 communicates operational agent meaning. A white question
mark, amber approval mark, or bright action must remain semantically reliable.
The show is an explicitly selected performance and therefore uses a separate
`ShowFrame` contract.

Each device profile maps an 8x8 canvas plus eight top and eight right showcase
lights. `ShowColor` pairs exact RGB with a semantic fallback, while the story
contains colors and geometry rather than MIDI note numbers. Another conforming
profile can therefore stage the same performance at its best available color
depth.
