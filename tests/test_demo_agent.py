from __future__ import annotations

from unittest import TestCase

from pad_lattice.demo_agent import DemoAgent, run_demo_surface


class FailingSurface:
    profile_id = "test/grid/device"
    input_name = "input"
    output_name = "output"
    selector_capacity = 4

    def __init__(self) -> None:
        self.closed = False

    def initialize(self) -> None:
        raise OSError("initialization failed")

    def render(self, view) -> None:
        pass

    def poll_events(self):
        return []

    def close(self) -> None:
        self.closed = True


class DemoAgentTest(TestCase):
    def test_initialization_failure_still_closes_surface(self) -> None:
        surface = FailingSurface()

        with self.assertRaisesRegex(OSError, "initialization failed"):
            run_demo_surface(surface, DemoAgent())

        self.assertTrue(surface.closed)
