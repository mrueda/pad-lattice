"""Join existing local Codex conversations without owning their terminals."""

from __future__ import annotations

from contextlib import ExitStack
import json
import os
import queue
import stat
import threading
import time
from uuid import uuid4

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from pad_lattice import __version__
from pad_lattice.client import PadLatticeClient
from pad_lattice.codex_discovery import control_socket
from pad_lattice.codex_state import ConversationFamily, LiveConversation
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import open_message_connection, session_lease_message, state_message

CHILD_REFRESH_SECONDS = 2.0
MAX_FAMILY_THREADS = 256




class CodexAttachment:
    def __init__(self, thread_id, socket_path, on_disconnect=None):
        self.thread_id = thread_id
        self.client = PadLatticeClient(socket_path)
        self.agent = AgentIdentity("codex", thread_id)
        self.live = LiveConversation(thread_id)
        self.family = ConversationFamily(self.live)
        self.thread_sources = {}
        self.next_child_refresh = 0.0
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.connected = False
        self.slot = None
        self.worker = threading.Thread(target=self._run, name="codex-attachment", daemon=True)
        self.sequence = 0
        self.ws = None
        self.on_disconnect = on_disconnect
        self.live_lock = threading.Lock()
        self.question_answers = queue.Queue(maxsize=4)

    def question(self):
        with self.live_lock:
            target = self.family.request_target()
            if not self.connected or not target or len(target.questions) != 1:
                return None
            return next(iter(target.questions.values()))

    def approval(self):
        with self.live_lock:
            target = self.family.request_target()
            if not self.connected or not target or len(target.approvals) != 1:
                return None
            result = dict(next(iter(target.approvals.values())))
            if target is not self.live:
                result["agent_label"] = self.family.labels.get(target.thread_id, "Child agent")
            return result

    def attention(self):
        with self.live_lock:
            return self.family.attention()

    def answer_question(self, token, answers, still_selected):
        result = queue.Queue(maxsize=1)
        try:
            with self.live_lock:
                if not self.connected or self.stop.is_set():
                    raise ValueError("Conversation is no longer connected")
                self.question_answers.put_nowait((token, answers, still_selected, time.monotonic() + 2, result))
            error = result.get(timeout=2)
        except queue.Full:
            raise ValueError("Another answer is being submitted") from None
        except queue.Empty:
            raise TimeoutError("Codex did not accept the answer in time") from None
        if error:
            raise ValueError(error)
        return {}

    def _answer_pending(self):
        try:
            token, answers, still_selected, deadline, result = self.question_answers.get_nowait()
        except queue.Empty:
            return
        error = None
        with self.live_lock:
            target = self.family.request_target()
            pending = target.questions if target else {}
            if (time.monotonic() >= deadline or not still_selected() or len(pending) != 1):
                error = "This question is no longer available"
            else:
                request_id, question = next(iter(pending.items()))
                questions = question["questions"]
                if (token != question["token"] or not isinstance(answers, dict)
                        or set(answers) != {q["id"] for q in questions}
                        or any(type(answers[q["id"]]) is not int or not 0 <= answers[q["id"]] < len(q["options"])
                               for q in questions)):
                    error = "Invalid or outdated answer"
                else:
                    payload = {q["id"]: {"answers": [q["options"][answers[q["id"]]]["label"]]} for q in questions}
                    try:
                        self.ws.send(json.dumps({"id": request_id, "result": {"answers": payload}}))
                    except (OSError, WebSocketException) as exc:
                        result.put_nowait(str(exc))
                        raise
                    target.pending.pop(request_id, None)
                    target.pending_states.pop(request_id, None)
                    pending.pop(request_id, None)
                    target.state = AgentState.RUNNING
        result.put_nowait(error)

    def _disconnect_answers(self):
        with self.live_lock:
            self.connected = False
            while True:
                try:
                    *_, result = self.question_answers.get_nowait()
                except queue.Empty:
                    break
                result.put_nowait("Conversation is no longer connected")

    def close(self):
        self.stop.set()
        self._disconnect_answers()
        if self.ws is not None:
            self.ws.close()
        if self.worker.is_alive():
            self.worker.join(timeout=3)

    def _receive(self, timeout):
        message = json.loads(self.ws.recv(timeout=timeout))
        if not isinstance(message, dict):
            raise ValueError("Invalid Codex message")
        if "method" in message:
            with self.live_lock:
                self.family.event(message)
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

    def _refresh_children(self):
        """Discover ancestry from Codex metadata, then join only loaded descendants."""
        revision = self.live.event_revision
        root = self._request("thread/read", {"threadId": self.thread_id, "includeTurns": False})["thread"]
        with self.live_lock:
            # A newer event wins over a status snapshot captured before that event.
            if self.live.event_revision == revision:
                self.live.status(root["status"], reconcile=True)
        loaded = set()
        cursor = None
        cursors = set()
        while True:
            params = {"limit": 64}
            if cursor:
                params["cursor"] = cursor
            page = self._request("thread/loaded/list", params)
            ids = page.get("data")
            if not isinstance(ids, list) or any(not isinstance(ident, str) for ident in ids):
                raise ValueError("Invalid loaded Codex threads")
            loaded.update(ids)
            if len(loaded) > MAX_FAMILY_THREADS:
                raise ValueError("Too many loaded Codex threads to track safely")
            cursor = page.get("nextCursor")
            if not cursor:
                break
            if not isinstance(cursor, str) or cursor in cursors:
                raise ValueError("Invalid loaded Codex thread cursor")
            cursors.add(cursor)

        summaries = {}
        for ident in sorted(loaded - self.thread_sources.keys() - {self.thread_id}):
            thread = self._request("thread/read", {"threadId": ident, "includeTurns": False})["thread"]
            source = thread.get("source")
            subagent = source.get("subAgent") if isinstance(source, dict) else None
            spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
            self.thread_sources[ident] = spawn if isinstance(spawn, dict) else {}
            summaries[ident] = thread

        def descendant(ident):
            seen = set()
            while ident not in seen:
                seen.add(ident)
                parent = self.thread_sources.get(ident, {}).get("parent_thread_id")
                if parent == self.thread_id:
                    return True
                if not isinstance(parent, str):
                    break
                ident = parent
            return False

        descendants = {ident for ident in loaded if descendant(ident)}
        with self.live_lock:
            for ident in self.family.children.keys() - descendants:
                del self.family.children[ident]
                self.family.labels.pop(ident, None)
        for ident in sorted(descendants):
            previous = self.family.children.get(ident)
            revision = previous.event_revision if previous else None
            thread = summaries.get(ident)
            if thread is None:
                thread = self._request("thread/read", {"threadId": ident, "includeTurns": False})["thread"]
            if thread.get("status", {}).get("type") == "notLoaded":
                with self.live_lock:
                    self.family.children.pop(ident, None)
                    self.family.labels.pop(ident, None)
                continue
            with self.live_lock:
                joining = ident not in self.family.children
                child = self.family.children.setdefault(ident, LiveConversation(ident))
                name = self.thread_sources[ident].get("agent_nickname")
                self.family.labels[ident] = name[:80] if isinstance(name, str) and name else "Child agent"
                if joining or child.event_revision == revision:
                    child.status(thread["status"], reconcile=True)
            if joining:
                # Joining a loaded child subscribes to its exact requests; it starts no turn.
                resumed = self._request("thread/resume", {"threadId": ident, "excludeTurns": True})
                with self.live_lock:
                    child.status(resumed["thread"]["status"])

        # Keep unloaded ancestors only while a loaded descendant still references them.
        keep = set(loaded)
        for ident in descendants:
            while ident in self.thread_sources:
                parent = self.thread_sources[ident].get("parent_thread_id")
                if not isinstance(parent, str) or parent in keep:
                    break
                keep.add(parent)
                ident = parent
        self.thread_sources = {ident: source for ident, source in self.thread_sources.items() if ident in keep}
        self.next_child_refresh = time.monotonic() + CHILD_REFRESH_SECONDS

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
                self._request("initialize", {"clientInfo": {"name": "pad_lattice", "version": __version__},
                    "capabilities": {"experimentalApi": True, "requestAttestation": False}})
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
                self._refresh_children()
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
                    if time.monotonic() >= self.next_child_refresh:
                        self._refresh_children()
                    # Drain server events before accepting a physical/browser action.
                    for _ in range(64):
                        try:
                            self._receive(0.001)
                        except TimeoutError:
                            break
                    self._answer_pending()
                    controls = self.family.controls()
                    state = self.family.state
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
                    if state != published:
                        reply = lease.request(state_message(state, agent=self.agent, reply=True))
                        if reply.get("type") != "state_ack":
                            raise RuntimeError("Pad-Lattice rejected a state update")
                        # Closing a capability uses another socket. The daemon may still
                        # see it for this update, so retain the acknowledged state and retry.
                        published = AgentState(reply["state"])
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
                                and self.family.controls() == signature and event.action in signature[0]):
                            _, request, turn_id = signature
                            if event.action == ControlAction.STOP:
                                self.live.interrupted_turn = turn_id
                                self._request("turn/interrupt", {"threadId": self.thread_id, "turnId": turn_id})
                            elif request is not None:
                                decision = "accept" if event.action == ControlAction.APPROVE else "decline"
                                self.ws.send(json.dumps({"id": request[1], "result": {"decision": decision}}))
                        subscription.close()
                        subscription = None
                    else:
                        self.stop.wait(0.03)
        except (OSError, ValueError, RuntimeError, WebSocketException, KeyError, TypeError, AttributeError) as exc:
            if not self.stop.is_set():
                self.error = str(exc)
                if self.connected and self.on_disconnect:
                    self.on_disconnect(self.thread_id)
        finally:
            try:
                if subscription:
                    subscription.close()
            finally:
                self._disconnect_answers()
                self.ready.set()


class AttachmentManager:
    """Desktop operations are serialized by its worker; snapshots use a lock."""

    def __init__(self, socket_path, on_disconnect=None):
        self.socket_path = socket_path
        self.attachments = {}
        self.lock = threading.Lock()
        self.closed = False
        self.on_disconnect = on_disconnect

    def snapshot(self):
        with self.lock:
            return {key: {"connected": value.connected, "error": value.error}
                    for key, value in self.attachments.items()}

    def _connected_at(self, slot):
        with self.lock:
            return next((item for item in self.attachments.values() if item.connected and item.slot == slot), None)

    def question(self, slot):
        attachment = self._connected_at(slot)
        return attachment.question() if attachment else None

    def approval(self, slot):
        attachment = self._connected_at(slot)
        return attachment.approval() if attachment else None

    def attention(self, slot):
        attachment = self._connected_at(slot)
        return attachment.attention() if attachment else {"pending_count": 0, "child_attention_count": 0}

    def answer_question(self, slot, token, answers, still_selected):
        attachment = self._connected_at(slot)
        if attachment is None:
            raise ValueError("Conversation is no longer connected")
        return attachment.answer_question(token, answers, still_selected)

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
        attachment = CodexAttachment(thread_id, self.socket_path, self.on_disconnect)
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
        if not attachment.connected or attachment.stop.is_set():
            raise ConnectionError("Conversation disconnected during attachment")
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
