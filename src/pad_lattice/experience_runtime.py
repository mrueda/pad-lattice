"""Nonblocking Demo and Show playback shared by daemon and standalone commands."""

from __future__ import annotations

import bisect
import sys
import time
from dataclasses import replace
from typing import TextIO

from pad_lattice.audio import (
    AudioFeedback,
    Earcon,
    Soundtrack,
    start_constellation_soundtrack,
)
from pad_lattice.devices.base import (
    ActionPressed,
    ControlSurface,
    ExperienceKind,
    ExperienceRequested,
    ExperienceStopRequested,
    ExperienceView,
    SessionSelected,
    SurfaceEvent,
)
from pad_lattice.experience_manifest import (
    DemoManifest,
    DemoStage,
    PerformanceManifest,
    load_builtin_demo,
    load_builtin_performance,
)
from pad_lattice.show import _story_timeline

DEFAULT_SHOW_LEAD_IN = 0.5
DEFAULT_DEMO_TERMINAL_HOLD = 2.0


class ExperienceController:
    """Advance one experience while preserving daemon responsiveness."""

    def __init__(
        self,
        surface: ControlSurface,
        *,
        audio_feedback: AudioFeedback | None = None,
        output: TextIO | None = None,
    ) -> None:
        self.surface = surface
        self.audio_feedback = audio_feedback
        self.output = output
        self.kind: ExperienceKind | None = None
        self._demo: DemoManifest | None = None
        self._demo_stage: DemoStage | None = None
        self._demo_terminal_at: float | None = None
        self._show: PerformanceManifest | None = None
        self._show_boundaries: tuple[float, ...] = ()
        self._show_start = 0.0
        self._show_cue_index = -1
        self._tempo = 1.0
        self._host_show_audio = False
        self._soundtrack: Soundtrack | None = None
        self._audio_sequence = 0
        self._frame = 0
        self.demo_actions: list[object] = []
        self.last_reason: str | None = None

    @property
    def active(self) -> bool:
        return self.kind is not None

    def start(
        self,
        kind: ExperienceKind,
        *,
        now: float,
        tempo: float = 1.0,
        host_show_audio: bool = False,
        lead_in: float = DEFAULT_SHOW_LEAD_IN,
    ) -> bool:
        if self.active:
            return False
        if tempo <= 0:
            raise ValueError("experience tempo must be positive")
        if kind == "demo":
            self._start_demo(now)
        else:
            self._start_show(
                now,
                tempo=tempo,
                host_show_audio=host_show_audio,
                lead_in=lead_in,
            )
        self.last_reason = None
        return True

    def block(self, kind: ExperienceKind, reason: str) -> None:
        self.surface.set_experience(
            ExperienceView(status="blocked", kind=kind, reason=reason)
        )

    def handle_event(self, event: SurfaceEvent, *, now: float) -> bool:
        if self.kind == "demo":
            return self._handle_demo_event(event, now=now)
        if self.kind == "show":
            return isinstance(event, (ActionPressed, SessionSelected))
        return False

    def tick(self, *, now: float) -> bool:
        """Advance playback and return true when an experience just ended."""

        if self.kind == "demo":
            if self._demo_terminal_at is not None and now >= self._demo_terminal_at:
                self.stop(reason="complete")
                return True
            return False
        if self.kind != "show" or self._show is None:
            return False
        if now < self._show_start:
            return False
        if self._host_show_audio and self._soundtrack is None:
            self._soundtrack = start_constellation_soundtrack(
                _story_timeline(self._show.cues, tempo=self._tempo)
            )
        elapsed = (now - self._show_start) * self._tempo
        if elapsed >= self._show.duration:
            self.stop(reason="complete")
            return True
        cue_index = bisect.bisect_right(self._show_boundaries, elapsed)
        if cue_index != self._show_cue_index:
            self._show_cue_index = cue_index
            cue = self._show.cues[cue_index]
            self.surface.render_show_frame(cue.frame)
            self.surface.set_experience(
                ExperienceView(
                    status="playing",
                    kind="show",
                    title=self._show.title,
                    cue_index=cue_index,
                    caption=cue.caption or cue.act,
                    elapsed_ms=round(elapsed * 1000),
                    duration_ms=round(self._show.duration * 1000),
                    tempo=self._tempo,
                    audio_asset=f"experiences/{self._show.audio_asset}",
                )
            )
            self._print_show_cue(cue.act, cue.caption)
        return False

    def stop(self, *, reason: str = "stopped") -> bool:
        if not self.active:
            return False
        if self._soundtrack is not None:
            self._soundtrack.close()
            self._soundtrack = None
        previous_kind = self.kind
        self.last_reason = reason
        self.kind = None
        self._demo = None
        self._demo_stage = None
        self._demo_terminal_at = None
        self._show = None
        self._show_boundaries = ()
        self._show_cue_index = -1
        self.surface.set_experience(
            ExperienceView(status="idle", kind=previous_kind, reason=reason)
        )
        return True

    def _start_demo(self, now: float) -> None:
        self.kind = "demo"
        self._demo = load_builtin_demo()
        self._demo_stage = self._demo.stage(self._demo.initial_stage)
        self._demo_terminal_at = None
        self.demo_actions.clear()
        self._publish_demo_stage(self._demo_stage, audio=self._demo_stage.enter_audio)

    def _start_show(
        self,
        now: float,
        *,
        tempo: float,
        host_show_audio: bool,
        lead_in: float,
    ) -> None:
        if lead_in < 0:
            raise ValueError("show lead-in must not be negative")
        self.kind = "show"
        self._show = load_builtin_performance()
        elapsed = 0.0
        boundaries: list[float] = []
        for cue in self._show.cues[:-1]:
            elapsed += cue.duration
            boundaries.append(elapsed)
        self._show_boundaries = tuple(boundaries)
        self._show_start = now + lead_in
        self._show_cue_index = -1
        self._tempo = tempo
        self._host_show_audio = host_show_audio
        self.surface.set_experience(
            ExperienceView(
                status="starting",
                kind="show",
                title=self._show.title,
                duration_ms=round(self._show.duration * 1000),
                tempo=tempo,
                audio_asset=f"experiences/{self._show.audio_asset}",
                start_delay_ms=round(lead_in * 1000),
            )
        )
        if self.output is not None:
            print(f"Pad-Lattice show: {self._show.title}", file=self.output, flush=True)

    def _handle_demo_event(self, event: SurfaceEvent, *, now: float) -> bool:
        stage = self._demo_stage
        demo = self._demo
        if stage is None or demo is None or stage.terminal:
            return isinstance(event, (ActionPressed, SessionSelected))
        for transition in stage.transitions:
            if transition.event_type == "select":
                if not isinstance(event, SessionSelected) or event.slot != transition.slot:
                    continue
                self.demo_actions.append(event)
                slot = event.slot
            else:
                if not isinstance(event, ActionPressed) or event.action != transition.action:
                    continue
                self.demo_actions.append(event.action)
                selected = next(
                    (session for session in stage.view.sessions if session.selected),
                    None,
                )
                slot = selected.slot if selected is not None else None
            next_stage = demo.stage(transition.next_stage)
            self._demo_stage = next_stage
            audio = transition.audio or next_stage.enter_audio
            self._publish_demo_stage(next_stage, audio=audio, slot=slot)
            if next_stage.terminal:
                self._demo_terminal_at = now + DEFAULT_DEMO_TERMINAL_HOLD
            return True
        return isinstance(event, (ActionPressed, SessionSelected))

    def _publish_demo_stage(
        self,
        stage: DemoStage,
        *,
        audio: str | None,
        slot: int | None = None,
    ) -> None:
        self.surface.render(replace(stage.view, frame=self._frame))
        self._frame += 1
        if audio is not None:
            self._audio_sequence += 1
            self._play_earcon(audio, slot=slot)
        self.surface.set_experience(
            ExperienceView(
                status="playing",
                kind="demo",
                title=self._demo.title if self._demo is not None else None,
                cue_index=(
                    self._demo.stages.index(stage) if self._demo is not None else None
                ),
                caption=stage.prompt.title,
                detail=stage.prompt.detail,
                audio_cue=audio,
                audio_slot=slot,
                audio_sequence=self._audio_sequence,
            )
        )
        if self.output is not None:
            print(stage.prompt.title, file=self.output, flush=True)
            print(f"  {stage.prompt.detail}", file=self.output, flush=True)

    def _play_earcon(self, name: str, *, slot: int | None) -> None:
        if self.audio_feedback is None:
            return
        try:
            cue = Earcon(name)
        except ValueError:
            return
        self.audio_feedback.play(cue, slot=slot)

    def _print_show_cue(self, act: str, caption: str | None) -> None:
        if self.output is None:
            return
        if caption is not None:
            print(f"{act}: {caption}", file=self.output, flush=True)


def run_experience_loop(
    surface: ControlSurface,
    kind: ExperienceKind,
    *,
    tempo: float = 1.0,
    audio_feedback: AudioFeedback | None = None,
    host_show_audio: bool = False,
    wait_for_request: bool = False,
    poll_interval: float = 0.03,
    output: TextIO | None = None,
    clock=time.monotonic,
    sleep=time.sleep,
) -> ExperienceController:
    """Run one standalone experience and always close its resources."""

    stream = output or sys.stdout
    controller = ExperienceController(
        surface,
        audio_feedback=audio_feedback,
        output=stream,
    )
    try:
        surface.initialize()
        if not wait_for_request:
            controller.start(
                kind,
                now=clock(),
                tempo=tempo,
                host_show_audio=host_show_audio,
                lead_in=0.0,
            )
        while controller.active or wait_for_request:
            now = clock()
            for event in surface.poll_events():
                if isinstance(event, ExperienceRequested):
                    if event.kind != kind:
                        controller.block(event.kind, f"This command is prepared for {kind}.")
                        continue
                    if controller.start(
                        kind,
                        now=now,
                        tempo=tempo,
                        host_show_audio=host_show_audio,
                    ):
                        wait_for_request = False
                    continue
                if isinstance(event, ExperienceStopRequested):
                    controller.stop()
                    wait_for_request = False
                    continue
                controller.handle_event(event, now=now)
            if controller.tick(now=now):
                break
            sleep(poll_interval)
    except KeyboardInterrupt:
        controller.stop(reason="cancelled")
    finally:
        try:
            controller.stop(reason="closed")
        finally:
            try:
                if audio_feedback is not None:
                    audio_feedback.close()
            finally:
                surface.close()
    return controller
