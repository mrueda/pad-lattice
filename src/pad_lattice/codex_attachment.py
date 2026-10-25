"""Join existing local Codex conversations without owning their terminals."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
import json
import os
import stat
import threading
import time
from uuid import uuid4

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from pad_lattice import __version__
from pad_lattice.client import PadLatticeClient
from pad_lattice.codex_discovery import control_socket
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import open_message_connection, session_lease_message, state_message

APPROVAL_METHODS = {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}


@dataclass
class LiveConversation:
    """Only live routing data; never retain transcript or tool output."""

    thread_id: str
    state: AgentState = AgentState.WAITING_FOR_REPLY
    turn_id: str | None = None
    pending: dict = field(default_factory=dict)
    interrupted_turn: str | None = None

    def status(self, status):
        kind = status.get("type")
        if kind == "notLoaded":
            raise ConnectionError("Codex unloaded this conversation")
        if kind == "idle":
            self.turn_id = None
            self.pending.clear()
            if self.state not in {AgentState.SUCCESS, AgentState.CANCELLED, AgentState.ERROR}:
                self.state = AgentState.WAITING_FOR_REPLY
        elif kind == "active":
            flags = status.get("activeFlags", [])
            self.state = (AgentState.WAITING_FOR_APPROVAL if "waitingOnApproval" in flags else
                          AgentState.WAITING_FOR_REPLY if "waitingOnUserInput" in flags else AgentState.RUNNING)
        elif kind == "systemError":
            self.state = AgentState.ERROR
            self.turn_id = None
            self.pending.clear()
        else:
            raise ValueError("Unsupported Codex thread status")

    def event(self, message):
        method = message.get("method")
        params = message.get("params", {})
        if not isinstance(params, dict) or params.get("threadId") != self.thread_id:
            return
        if "id" in message:
            request_id = message["id"]
            if not isinstance(request_id, (str, int)) or isinstance(request_id, bool):
                raise ValueError("Invalid Codex request ID")
            if len(self.pending) >= 64 and request_id not in self.pending:
                raise ValueError("Too many pending Codex requests")
            turn_id = params.get("turnId")
            if isinstance(turn_id, str) and turn_id:
                if self.turn_id and turn_id != self.turn_id:
                    return
                self.turn_id = turn_id
            supported = method in APPROVAL_METHODS and bool(turn_id)
            if method == "item/commandExecution/requestApproval" and params.get("kind", "command") != "command":
                supported = False
            decisions = params.get("availableDecisions", ["accept", "decline"])
            actions = tuple(action for action, decision in ((ControlAction.APPROVE, "accept"), (ControlAction.REJECT, "decline"))
                            if supported and isinstance(decisions, list) and decision in decisions)
            self.pending[request_id] = (actions, params.get("itemId"))
            self.state = AgentState.WAITING_FOR_APPROVAL if method in APPROVAL_METHODS else AgentState.WAITING_FOR_REPLY
        elif method == "serverRequest/resolved":
            removed = self.pending.pop(params.get("requestId"), None)
            if removed is not None and not self.pending and self.turn_id:
                self.state = AgentState.RUNNING
        elif method == "thread/status/changed":
            self.status(params["status"])
        elif method == "thread/closed":
            raise ConnectionError("Codex closed this conversation")
        elif method == "turn/started":
            turn_id = params["turn"]["id"]
            if self.turn_id != turn_id:
                self.pending.clear()
            self.turn_id = turn_id
            self.state = AgentState.RUNNING
        elif method == "turn/completed":
            turn = params["turn"]
            if self.turn_id and turn["id"] != self.turn_id:
                return
            self.turn_id = None
            self.pending.clear()
            self.state = {"completed": AgentState.SUCCESS, "interrupted": AgentState.CANCELLED,
                          "failed": AgentState.ERROR}.get(turn["status"], AgentState.WAITING_FOR_REPLY)
        elif method == "item/completed":
            item_id = params.get("item", {}).get("id")
            if item_id:
                previous = len(self.pending)
                self.pending = {key: value for key, value in self.pending.items() if value[1] != item_id}
                if previous and not self.pending and self.turn_id:
                    self.state = AgentState.RUNNING

    def controls(self):
        actions = []
        request_id = None
        if len(self.pending) == 1:
            request_id, (choices, _) = next(iter(self.pending.items()))
            actions.extend(choices)
        if self.turn_id and self.turn_id != self.interrupted_turn:
            actions.append(ControlAction.STOP)
        return tuple(actions), request_id, self.turn_id


class CodexAttachment:
    def __init__(self, thread_id, socket_path):
        self.thread_id = thread_id
        self.client = PadLatticeClient(socket_path)
        self.agent = AgentIdentity("codex", thread_id)
        self.live = LiveConversation(thread_id)
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.connected = False
        self.slot = None
        self.worker = threading.Thread(target=self._run, name="codex-attachment", daemon=True)
        self.sequence = 0
        self.ws = None

    def close(self):
        self.stop.set()
        if self.ws is not None:
            self.ws.close()
        if self.worker.is_alive():
            self.worker.join(timeout=3)

    def _receive(self, timeout):
        message = json.loads(self.ws.recv(timeout=timeout))
        if not isinstance(message, dict):
            raise ValueError("Invalid Codex message")
        if "method" in message:
            self.live.event(message)
        return message

    def _request(self, method, params):
        self.sequence += 1
        request_id = f"pad-lattice-{self.sequence}"
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
        deadline = time.monotonic() + 6
        while not self.stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Codex did not answer {method}")
            message = self._receive(remaining)
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise RuntimeError(f"Codex rejected {method}")
                return message["result"]
        raise ConnectionError("Attachment stopped")

    def _run(self):
        subscription = None
        try:
            path = control_socket()
            info = path.stat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("Codex control socket must belong to the current user")
            with ExitStack() as stack:
                self.ws = stack.enter_context(unix_connect(str(path), uri="ws://localhost/", open_timeout=2,
                    close_timeout=0.2, max_size=4 * 1024 * 1024, compression=None))
                self._request("initialize", {"clientInfo": {"name": "pad_lattice", "version": __version__}})
                self.ws.send(json.dumps({"method": "initialized"}))
                summary = self._request("thread/read", {"threadId": self.thread_id, "includeTurns": False})["thread"]
                if summary.get("source") != "cli" or summary.get("status", {}).get("type") == "notLoaded":
                    raise ValueError("Only loaded Codex CLI conversations can be attached")
                self.live.status(summary["status"])
                # No policy/model/config overrides and no turn/start: join the live thread.
                resumed = self._request("thread/resume", {"threadId": self.thread_id, "excludeTurns": True})
                self.live.status(resumed["thread"]["status"])
                if self.live.state == AgentState.RUNNING and not self.live.turn_id:
                    turns = self._request("thread/turns/list", {"threadId": self.thread_id, "limit": 1,
                        "sortDirection": "desc", "itemsView": "notLoaded"}).get("data", [])
                    if (self.live.state == AgentState.RUNNING and not self.live.turn_id
                            and turns and turns[0].get("status") == "inProgress"):
                        self.live.turn_id = turns[0]["id"]
                lease = stack.enter_context(open_message_connection(self.client.socket_path))
                metadata = {"label": (summary.get("name") or "Codex")[:64], "source": "app-server"}
                if summary.get("cwd"):
                    metadata["cwd"] = summary["cwd"]
                ack = lease.request(session_lease_message(uuid4().hex, agent=self.agent, metadata=metadata))
                if ack.get("type") != "session_lease_ack":
                    raise RuntimeError("Pad-Lattice could not register this conversation")
                self.slot = ack.get("session", {}).get("slot")
                if self.slot is None:
                    raise RuntimeError("All eight pad slots are occupied")
                signature = None
                published = None
                token = None
                self.connected = True
                self.ready.set()
                while not self.stop.is_set():
                    # Drain server events before accepting a physical/browser action.
                    for _ in range(64):
                        try:
                            self._receive(0.001)
                        except TimeoutError:
                            break
                    controls = self.live.controls()
                    if self.live.state != published:
                        reply = lease.request(state_message(self.live.state, agent=self.agent, reply=True))
                        if reply.get("type") != "state_ack":
                            raise RuntimeError("Pad-Lattice rejected a state update")
                        published = self.live.state
                    if controls != signature:
                        if subscription:
                            subscription.close()
                        subscription = None
                        signature = controls
                        actions, _, _ = controls
                        if actions:
                            token = uuid4().hex
                            subscription = self.client.subscribe_actions(self.agent, actions, request_id=token,
                                                                         one_shot=True, timeout=0.02)
                            subscription.__enter__()
                    if subscription:
                        try:
                            event = subscription.receive()
                        except TimeoutError:
                            continue
                        # A resolved request or completed turn invalidates its exact capability.
                        for _ in range(64):
                            try:
                                self._receive(0.001)
                            except TimeoutError:
                                break
                        if (event.agent == self.agent and event.request_id == token
                                and self.live.controls() == signature and event.action in signature[0]):
                            _, request_id, turn_id = signature
                            if event.action == ControlAction.STOP:
                                self.live.interrupted_turn = turn_id
                                self._request("turn/interrupt", {"threadId": self.thread_id, "turnId": turn_id})
                            elif request_id is not None:
                                decision = "accept" if event.action == ControlAction.APPROVE else "decline"
                                self.ws.send(json.dumps({"id": request_id, "result": {"decision": decision}}))
                        subscription.close()
                        subscription = None
                    else:
                        self.stop.wait(0.03)
        except (OSError, ValueError, RuntimeError, WebSocketException, KeyError, TypeError, AttributeError) as exc:
            if not self.stop.is_set():
                self.error = str(exc)
        finally:
            if subscription:
                subscription.close()
            self.connected = False
            self.ready.set()


class AttachmentManager:
    """Desktop operations are serialized by its worker; snapshots use a lock."""

    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.attachments = {}
        self.lock = threading.Lock()
        self.closed = False

    def snapshot(self):
        with self.lock:
            return {key: {"connected": value.connected, "error": value.error}
                    for key, value in self.attachments.items()}

    def discard_disconnected(self):
        with self.lock:
            expired = [key for key, value in self.attachments.items()
                       if not value.worker.is_alive()]
            for key in expired:
                del self.attachments[key]

    def attach(self, thread_id):
        if not isinstance(thread_id, str) or not thread_id or len(thread_id) > 128:
            raise ValueError("Invalid conversation ID")
        with self.lock:
            if self.closed:
                raise RuntimeError("Desktop is closing")
            previous = self.attachments.get(thread_id)
            if previous and previous.connected:
                return {"slot": previous.slot}
            if sum(item.connected for item in self.attachments.values()) >= 8:
                raise ValueError("Eight conversations are already attached")
        status = PadLatticeClient(self.socket_path).status()
        if any(item["backend"] == "codex" and item["session_id"] == thread_id for item in status["sessions"]):
            raise ValueError("This conversation is already connected through the scoped launcher")
        if len(status["sessions"]) >= 8:
            raise ValueError("All eight pad slots are occupied")
        if previous:
            previous.close()
        attachment = CodexAttachment(thread_id, self.socket_path)
        with self.lock:
            if self.closed:
                raise RuntimeError("Desktop is closing")
            self.attachments[thread_id] = attachment
            attachment.worker.start()
        if not attachment.ready.wait(12):
            attachment.close()
            raise TimeoutError("Codex did not attach in time")
        if attachment.error:
            raise RuntimeError(attachment.error)
        return {"slot": attachment.slot}

    def detach(self, thread_id):
        if not isinstance(thread_id, str):
            raise ValueError("Invalid conversation ID")
        with self.lock:
            attachment = self.attachments.pop(thread_id, None)
        if attachment:
            attachment.close()
        return {}

    def close(self):
        with self.lock:
            self.closed = True
            attachments = list(self.attachments.values())
            self.attachments.clear()
        for attachment in attachments:
            attachment.close()
