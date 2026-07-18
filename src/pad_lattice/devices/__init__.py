"""Hardware-independent control-surface interfaces and MIDI profiles."""

from pad_lattice.devices.base import (
    ActionPressed,
    ControlSurface,
    SessionIndicator,
    SessionSelected,
    SurfaceEvent,
    SurfaceView,
)
from pad_lattice.devices.composite import CompositeSurface
from pad_lattice.devices.profiles import (
    DeviceCandidate,
    DeviceProfile,
    ProfileCatalog,
    ProfileError,
)

__all__ = [
    "ActionPressed",
    "ControlSurface",
    "CompositeSurface",
    "DeviceCandidate",
    "DeviceProfile",
    "ProfileCatalog",
    "ProfileError",
    "SessionIndicator",
    "SessionSelected",
    "SurfaceEvent",
    "SurfaceView",
]
