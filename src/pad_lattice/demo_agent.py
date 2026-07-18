"""Standalone guided conversation for demonstrating the control surface."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TextIO

from pad_lattice.audio import AudioFeedback, Earcon
from pad_lattice.devices.base import ActionPressed, ControlSurface, SurfaceView
from pad_lattice.events import AgentState, ControlAction


@dataclass(frozen=True)
class DemoQuestion:
    """One yes/no prompt and the visual state that gives it context."""

    prompt: str
    state: AgentState


DEMO_QUESTIONS = (
    DemoQuestion(
        "Can you see the white question mark on the controller?",
        AgentState.WAITING_FOR_REPLY,
    ),
    DemoQuestion(
        "The demo agent requests permission to run a simulated task. Approve it?",
        AgentState.WAITING_FOR_APPROVAL,
    ),
    DemoQuestion(
        "Was the difference between reply (?) and approval (!) clear?",
        AgentState.WAITING_FOR_REPLY,
    ),
)

ANSWER_ACTIONS = frozenset({ControlAction.APPROVE, ControlAction.REJECT})


def run_demo_surface(
    surface: ControlSurface,
    *,
    questions: Sequence[DemoQuestion] = DEMO_QUESTIONS,
    poll_interval: float = 0.03,
    feedback_seconds: float = 0.8,
    success_seconds: float = 2.0,
    output: TextIO | None = None,
    audio_feedback: AudioFeedback | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[ControlAction, ...]:
    """Ask a short conversation through any configured control surface."""

    stream = output or sys.stdout
    answers: list[ControlAction] = []
    try:
        surface.initialize()
        print("Pad-Lattice guided demo", file=stream)
        print("Green Approve = yes; red Reject = no. Press Ctrl-C to exit.", file=stream)

        for index, question in enumerate(questions, start=1):
            surface.render(
                SurfaceView(
                    selected_state=question.state,
                    available_actions=ANSWER_ACTIONS,
                )
            )
            if audio_feedback is not None:
                cue = (
                    Earcon.APPROVAL
                    if question.state is AgentState.WAITING_FOR_APPROVAL
                    else Earcon.QUESTION
                )
                audio_feedback.play(cue)
            print(f"[{index}/{len(questions)}] {question.prompt}", file=stream, flush=True)

            action = _wait_for_answer(surface, poll_interval=poll_interval, sleep=sleep)
            answers.append(action)
            if audio_feedback is not None:
                audio_feedback.play(
                    Earcon.APPROVE
                    if action is ControlAction.APPROVE
                    else Earcon.REJECT
                )
            answer = "yes" if action is ControlAction.APPROVE else "no"
            print(f"Answer: {answer}", file=stream, flush=True)

            feedback_state = AgentState.RUNNING
            if (
                question.state is AgentState.WAITING_FOR_APPROVAL
                and action is ControlAction.REJECT
            ):
                feedback_state = AgentState.CANCELLED
            surface.render(SurfaceView(selected_state=feedback_state))
            sleep(feedback_seconds)

        surface.render(SurfaceView(selected_state=AgentState.SUCCESS))
        if audio_feedback is not None:
            audio_feedback.play(Earcon.SUCCESS)
        print("Demo complete.", file=stream, flush=True)
        sleep(success_seconds)
    except KeyboardInterrupt:
        print("Demo cancelled.", file=stream, flush=True)
    finally:
        try:
            surface.close()
        finally:
            if audio_feedback is not None:
                audio_feedback.close()

    return tuple(answers)


def _wait_for_answer(
    surface: ControlSurface,
    *,
    poll_interval: float,
    sleep: Callable[[float], None],
) -> ControlAction:
    while True:
        for event in surface.poll_events():
            if isinstance(event, ActionPressed) and event.action in ANSWER_ACTIONS:
                return event.action
        sleep(poll_interval)
