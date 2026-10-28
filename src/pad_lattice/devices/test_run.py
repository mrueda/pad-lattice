"""Nonblocking hardware checks shared by the terminal and Desktop."""

from __future__ import annotations

from dataclasses import dataclass
import time

from pad_lattice.devices.base import ActionPressed, SessionSelected, SessionIndicator, SurfaceView
from pad_lattice.events import AgentState, ControlAction

VISUAL_STATES = (
    (AgentState.RUNNING, "steady blue ellipsis"),
    (AgentState.WAITING_FOR_REPLY, "white question mark"),
    (AgentState.USER_TYPING, "cyan chevron"),
    (AgentState.WAITING_FOR_APPROVAL, "restrained amber exclamation mark"),
    (AgentState.SUCCESS, "green happy face"),
    (AgentState.ERROR, "red X"),
    (AgentState.CANCELLED, "gray hollow square"),
)


@dataclass(frozen=True)
class TestStep:
    group: str
    key: str
    prompt: str
    view: SurfaceView
    expected: ActionPressed | SessionSelected | None = None

    @property
    def id(self):
        return f"{self.group}:{self.key}"


class ProfileTestRun:
    """Own one surface exclusively; never forward test inputs to an agent."""

    def __init__(self, surface, profile, *, event_timeout=15.0, clock=time.monotonic):
        self.surface, self.profile = surface, profile
        self.clock, self.event_timeout = clock, event_timeout
        self.steps = [TestStep("visual", "idle", "Dim three-pad idle dash", SurfaceView(None))]
        self.steps.extend(TestStep("visual", state.value, description, SurfaceView(state))
                          for state, description in VISUAL_STATES)
        self.steps.append(TestStep("visual", "overflow", "One steady amber overflow indicator",
                                  SurfaceView(AgentState.WAITING_FOR_REPLY, overflow_count=1)))
        self.steps.extend(TestStep("actions", action.value, f"Press {action.value.upper()}",
                                   SurfaceView(AgentState.WAITING_FOR_REPLY,
                                               available_actions=frozenset({action})), ActionPressed(action))
                          for action in ControlAction)
        self.steps.extend(TestStep("selectors", str(slot + 1), f"Press agent selector {slot + 1}",
                                   SurfaceView(AgentState.WAITING_FOR_REPLY, sessions=tuple(
                                       SessionIndicator(index, VISUAL_STATES[index % len(VISUAL_STATES)][0],
                                                        index == slot, surface.accent_names[index])
                                       for index in range(surface.selector_capacity))), SessionSelected(slot))
                          for slot in range(surface.selector_capacity))
        self.checks = {group: {step.key: False for step in self.steps if step.group == group}
                       for group in ("visual", "actions", "selectors")}
        self.index = 0
        self.status = "ready"
        self.failure_stage = None
        self.deadline = 0.0
        self.last_result = None
        self.closed = False

    @property
    def active(self):
        return self.status == "running"

    @property
    def step(self):
        return self.steps[self.index] if self.active else None

    def start(self):
        if self.status != "ready":
            raise ValueError("This test has already started.")
        try:
            self.surface.initialize()
        except BaseException:
            self.cancel("initialize")
            raise
        self.status = "running"
        self._render()

    def _render(self):
        try:
            self.surface.render(self.step.view)
            self.deadline = self.clock() + self.event_timeout
        except BaseException:
            self.cancel("output")
            raise

    def answer(self, step_id, passed):
        if self.step is None or step_id != self.step.id:
            raise ValueError("The test has moved to another step. Refresh and try again.")
        if type(passed) is not bool or (self.step.expected is not None and passed):
            raise ValueError("Input checks must be confirmed by the controller.")
        self._advance(passed)

    def _advance(self, passed):
        step = self.step
        self.checks[step.group][step.key] = passed
        self.last_result = {"prompt": step.prompt, "passed": passed}
        self.index += 1
        if self.index == len(self.steps):
            self.status = "completed"
            self._close()
        else:
            self._render()

    def tick(self):
        if not self.active:
            return
        try:
            events = self.surface.poll_events()
        except (OSError, RuntimeError):
            self.cancel("input")
            return
        # Consume each batch once; repeated or unrelated presses cannot skip steps.
        if self.step.expected is not None:
            if self.step.expected in events:
                self._advance(True)
            elif self.clock() >= self.deadline:
                self._advance(False)

    def cancel(self, reason="cancelled"):
        if self.status in {"completed", "cancelled"}:
            return
        self.failure_stage = reason
        self.status = "cancelled"
        self._close()

    def _close(self):
        if not self.closed:
            self.closed = True
            try:
                self.surface.close()
            except (OSError, RuntimeError):
                self.failure_stage = self.failure_stage or "close"

    def snapshot(self):
        step = self.step
        return {"status": self.status, "index": min(self.index + 1, len(self.steps)),
                "total": len(self.steps), "failure_stage": self.failure_stage,
                "last_result": self.last_result,
                "step": None if step is None else {
                    "id": step.id, "group": step.group, "key": step.key, "prompt": step.prompt,
                    "seconds_left": max(0, round(self.deadline - self.clock())) if step.expected else None,
                }, "results": self.checks}
