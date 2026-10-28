"""Minimal agent adapter. No Codex, model API, or shell commands are invoked."""

from __future__ import annotations

import argparse
from contextlib import suppress
import sys
import time
from typing import Callable, TextIO
from uuid import uuid4

from pad_lattice.client import PadLatticeClient
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import ProtocolError, open_message_connection, session_lease_message


def run_adapter(
    client: PadLatticeClient,
    agent: AgentIdentity,
    work: Callable[[], None],
    *,
    label: str = "Example adapter",
    timeout: float = 60,
    outcome_hold: float = 2,
    output: TextIO | None = None,
) -> int:
    if timeout <= 0 or outcome_hold < 0:
        raise ValueError("timeout must be positive and outcome_hold must not be negative")
    stream = output or sys.stdout
    request_id = uuid4().hex
    decisions = (ControlAction.APPROVE, ControlAction.REJECT)

    # The lease removes the session and its controls even if this process exits.
    with open_message_connection(client.socket_path, timeout=client.timeout) as lease:
        ack = lease.request(session_lease_message(uuid4().hex, agent=agent, metadata={"label": label}))
        if ack.get("type") != "session_lease_ack":
            raise ProtocolError("daemon did not acknowledge the session lease")
        try:
            client.report_state(AgentState.RUNNING, agent=agent, reply=True)
            with client.subscribe_actions(
                agent, decisions, request_id=request_id, one_shot=True, timeout=timeout,
            ) as pending:
                client.report_state(AgentState.WAITING_FOR_APPROVAL, agent=agent, reply=True)
                print(f"{label}: approve or reject the sample calculation on the pad.", file=stream, flush=True)
                try:
                    decision = pending.receive()
                except TimeoutError:
                    decision = None
                if decision is not None and (decision.agent != agent or decision.request_id != request_id
                        or decision.action not in decisions):
                    raise ProtocolError("decision does not match this approval request")

            # Close the subscription before leaving the approval state.
            if decision is None:
                client.report_state(AgentState.CANCELLED, agent=agent, reply=True)
                print("Approval timed out. No work was performed.", file=stream, flush=True)
                return 2
            if decision.action is ControlAction.APPROVE:
                client.report_state(AgentState.RUNNING, agent=agent, reply=True)
                work()
                client.report_state(AgentState.SUCCESS, agent=agent, reply=True)
                print("Sample work completed.", file=stream, flush=True)
                result = 0
            else:
                client.report_state(AgentState.CANCELLED, agent=agent, reply=True)
                print("Rejected. No work was performed.", file=stream, flush=True)
                result = 2
            if outcome_hold:
                time.sleep(outcome_hold)
            return result
        except KeyboardInterrupt:
            with suppress(OSError, ProtocolError):
                client.report_state(AgentState.CANCELLED, agent=agent, reply=True)
            print("Adapter interrupted.", file=stream, flush=True)
            return 130
        except Exception:
            with suppress(OSError, ProtocolError):
                client.report_state(AgentState.ERROR, agent=agent, reply=True)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", help="Unix socket of an already running Pad-Lattice daemon")
    parser.add_argument("--label", default="Example adapter")
    parser.add_argument("--timeout", type=float, default=60, help="Seconds to wait for a decision (default: 60)")
    args = parser.parse_args()

    def sample_work() -> None:
        print(f"Sum of squares, 1 to 100: {sum(number ** 2 for number in range(1, 101))}", flush=True)

    try:
        return run_adapter(
            PadLatticeClient(args.socket), AgentIdentity("example", uuid4().hex), sample_work,
            label=args.label, timeout=args.timeout,
        )
    except (OSError, ValueError) as error:
        print(f"Adapter stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
