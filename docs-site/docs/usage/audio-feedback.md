# Audio Feedback

import EarconSamples from '@site/src/components/EarconSamples';

**Earcons are short sounds for requests, actions, and results.** They complement
the lights during normal agent use, not just Demo and Show.
Working and typing stay silent.

## Enable Sound

In Desktop, turn on **Settings > Sound > Enable sound**, or use the speaker
button at the top. This setting covers live sessions, Demo, and Show.
Desktop remembers your choice. Each browser has its own sound toggle and
starts muted.

Sounds play through the computer, phone, or tablet, **not the Launchpad**.
A Launchpad sends MIDI messages; it has no speaker.

## Listen to the Sounds

These are the same files used by the app, played here in Session 1's pitch.
Other sessions use different pitches so you can distinguish them by ear.

<EarconSamples />

Action sounds follow the bridge's handling of the request, not just a click.
Turning sound off never changes agent behavior. Old sounds are not replayed
when you reconnect.

## CLI

Enable live feedback:

```bash
pad-lattice daemon --audio-feedback
```

Try the guided Demo or the separate creative Show with sound:

```bash
pad-lattice demo --audio
pad-lattice show --audio
```

CLI host audio is independent of Desktop and browser sound. Enable only one
output on the same computer to avoid hearing cues twice.

The host needs one of `pw-play`, `paplay`, `aplay`, `afplay`, or `ffplay`.
Desktop and browsers use bundled audio files instead.

With MIDI and host audio enabled, the Demo and daemon also speak the scrolling
greeting. Use `--no-greeting` to skip it.

For the shared audio sources and build process, see the
[experience asset compiler](../technical-details/developer-guide.md#experience-asset-compiler).
