"""Fan one semantic view out to multiple synchronized surfaces."""

from __future__ import annotations

from collections.abc import Iterable

from pad_lattice.devices.base import (
    ControlSurface,
    ExperienceView,
    ShowFrame,
    SurfaceEvent,
    SurfaceView,
)


class CompositeSurface:
    """Treat compatible physical and virtual surfaces as one control surface."""

    surface_kind = "composite"

    def __init__(self, surfaces: Iterable[ControlSurface]) -> None:
        self.surfaces = tuple(surfaces)
        if not self.surfaces:
            raise ValueError("composite surface requires at least one surface")

        reference = self.surfaces[0]
        for surface in self.surfaces[1:]:
            if surface.selector_capacity != reference.selector_capacity:
                raise ValueError("composite surfaces must have equal selector capacity")
            if surface.accent_names != reference.accent_names:
                raise ValueError("composite surfaces must use the same accent order")
            if surface.visual_protocol != reference.visual_protocol:
                raise ValueError("composite surfaces must use one visual protocol")

        self.profile_id = "+".join(surface.profile_id for surface in self.surfaces)
        self.input_name = "; ".join(surface.input_name for surface in self.surfaces)
        self.output_name = "; ".join(surface.output_name for surface in self.surfaces)
        self.selector_capacity = reference.selector_capacity
        self.accent_names = reference.accent_names
        self.visual_protocol = reference.visual_protocol
        self._initialized: list[ControlSurface] = []
        self._closed = False

    @property
    def descriptors(self) -> tuple[dict[str, object], ...]:
        return tuple(_surface_descriptor(surface) for surface in self.surfaces)

    def initialize(self) -> None:
        try:
            for surface in self.surfaces:
                self._initialized.append(surface)
                surface.initialize()
        except BaseException:
            self.close()
            raise

    def render(self, view: SurfaceView) -> None:
        for surface in self.surfaces:
            surface.render(view)

    def render_show_frame(self, frame: ShowFrame) -> None:
        for surface in self.surfaces:
            surface.render_show_frame(frame)

    def set_experience(self, view: ExperienceView) -> None:
        for surface in self.surfaces:
            surface.set_experience(view)

    def poll_events(self) -> list[SurfaceEvent]:
        events: list[SurfaceEvent] = []
        for surface in self.surfaces:
            events.extend(surface.poll_events())
        return events

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        pending_error: BaseException | None = None
        initialized = self._initialized or list(self.surfaces)
        for surface in reversed(initialized):
            try:
                surface.close()
            except BaseException as exc:
                if pending_error is None:
                    pending_error = exc
        self._initialized.clear()
        if pending_error is not None:
            raise pending_error


def surface_descriptors(surface: ControlSurface) -> tuple[dict[str, object], ...]:
    descriptors = getattr(surface, "descriptors", None)
    if isinstance(descriptors, tuple):
        return descriptors
    return (_surface_descriptor(surface),)


def _surface_descriptor(surface: ControlSurface) -> dict[str, object]:
    if surface.surface_kind not in {"midi", "web"}:
        raise ValueError(f"unknown surface kind: {surface.surface_kind!r}")
    return {
        "kind": surface.surface_kind,
        "profile": surface.profile_id,
        "visual_protocol": surface.visual_protocol,
        "input": surface.input_name,
        "output": surface.output_name,
    }
