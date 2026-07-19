from __future__ import annotations

from unittest import TestCase

from pad_lattice.devices.base import (
    ActionPressed,
    ExperienceView,
    SessionSelected,
    ShowColor,
    ShowFrame,
    SurfaceView,
)
from pad_lattice.devices.composite import CompositeSurface, surface_descriptors
from pad_lattice.events import AgentState, ControlAction


class FakeSurface:
    selector_capacity = 8
    accent_names = (
        "cyan", "magenta", "lime", "orange", "violet", "teal", "rose", "sky"
    )
    visual_protocol = 1

    def __init__(self, profile_id: str, *, fail_initialize: bool = False) -> None:
        self.profile_id = profile_id
        self.surface_kind = "web" if profile_id == "virtual/browser" else "midi"
        self.input_name = f"{profile_id} input"
        self.output_name = f"{profile_id} output"
        self.fail_initialize = fail_initialize
        self.initialized = False
        self.closed = False
        self.views = []
        self.show_frames = []
        self.experiences = []
        self.events = []

    def initialize(self) -> None:
        self.initialized = True
        if self.fail_initialize:
            raise OSError("initialization failed")

    def render(self, view) -> None:
        self.views.append(view)

    def render_show_frame(self, frame) -> None:
        self.show_frames.append(frame)

    def set_experience(self, view) -> None:
        self.experiences.append(view)

    def poll_events(self):
        events, self.events = self.events, []
        return events

    def close(self) -> None:
        self.closed = True


class CompositeSurfaceTest(TestCase):
    def test_broadcasts_views_and_merges_events(self) -> None:
        midi = FakeSurface("novation/launchpad/pro-mk1")
        web = FakeSurface("virtual/browser")
        composite = CompositeSurface((midi, web))
        midi.events.append(ActionPressed(ControlAction.STOP))
        web.events.append(SessionSelected(2))
        view = SurfaceView(AgentState.RUNNING)
        show_color = ShowColor("off", (0, 0, 0))
        show_frame = ShowFrame(
            grid=tuple(tuple(show_color for _ in range(8)) for _ in range(8)),
            top=tuple(show_color for _ in range(8)),
            right=tuple(show_color for _ in range(8)),
        )
        experience = ExperienceView(status="playing", kind="show")

        composite.initialize()
        composite.render(view)
        composite.render_show_frame(show_frame)
        composite.set_experience(experience)

        self.assertEqual(midi.views, [view])
        self.assertEqual(web.views, [view])
        self.assertEqual(midi.show_frames, [show_frame])
        self.assertEqual(web.show_frames, [show_frame])
        self.assertEqual(midi.experiences, [experience])
        self.assertEqual(web.experiences, [experience])
        self.assertEqual(
            composite.poll_events(),
            [ActionPressed(ControlAction.STOP), SessionSelected(2)],
        )
        composite.close()
        self.assertTrue(midi.closed)
        self.assertTrue(web.closed)

    def test_rolls_back_every_surface_after_partial_initialization(self) -> None:
        first = FakeSurface("virtual/browser")
        second = FakeSurface("novation/launchpad/pro-mk1", fail_initialize=True)
        composite = CompositeSurface((first, second))

        with self.assertRaises(OSError):
            composite.initialize()

        self.assertTrue(first.closed)
        self.assertTrue(second.closed)

    def test_rejects_incompatible_surfaces(self) -> None:
        first = FakeSurface("virtual/browser")
        second = FakeSurface("other")
        second.selector_capacity = 4
        with self.assertRaisesRegex(ValueError, "selector capacity"):
            CompositeSurface((first, second))

    def test_descriptors_preserve_each_surface(self) -> None:
        composite = CompositeSurface(
            (FakeSurface("virtual/browser"), FakeSurface("novation/launchpad/pro-mk1"))
        )
        descriptors = surface_descriptors(composite)
        self.assertEqual([item["kind"] for item in descriptors], ["web", "midi"])
