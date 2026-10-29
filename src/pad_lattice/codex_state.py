"""Interpret Codex events without sockets, workers, or desktop dependencies."""

from dataclasses import dataclass, field
from uuid import uuid4

from pad_lattice.events import AgentState, ControlAction

APPROVAL_METHODS = {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}
ATTENTION_STATES = {AgentState.WAITING_FOR_APPROVAL, AgentState.WAITING_FOR_REPLY, AgentState.ERROR}


def selectable_questions(params):
    """Accept only bounded, non-secret multiple-choice requests."""
    questions = params.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 3:
        return None
    result = []
    ids = set()
    for question in questions:
        if not isinstance(question, dict) or question.get("isSecret") is not False:
            return None
        ident, title, prompt, options = (question.get("id"), question.get("header"),
                                         question.get("question"), question.get("options"))
        if (not isinstance(ident, str) or not 0 < len(ident) <= 128 or ident in ids
                or not isinstance(title, str) or len(title) > 256
                or not isinstance(prompt, str) or not 0 < len(prompt) <= 4096
                or not isinstance(options, list) or not 1 <= len(options) <= 9):
            return None
        choices = []
        for option in options:
            if not isinstance(option, dict):
                return None
            label, description = option.get("label"), option.get("description")
            if (not isinstance(label, str) or not 0 < len(label) <= 512
                    or not isinstance(description, str) or len(description) > 2048):
                return None
            choices.append({"label": label, "description": description})
        if len({choice["label"] for choice in choices}) != len(choices):
            return None
        ids.add(ident)
        result.append({"id": ident, "header": title, "question": prompt, "options": choices})
    return result


@dataclass
class LiveConversation:
    """Only live routing data; never retain transcript or tool output."""

    thread_id: str
    state: AgentState = AgentState.IDLE
    turn_id: str | None = None
    pending: dict = field(default_factory=dict)
    pending_states: dict = field(default_factory=dict)
    questions: dict = field(default_factory=dict)
    approvals: dict = field(default_factory=dict)
    interrupted_turn: str | None = None
    active: bool = False
    event_revision: int = 0

    def _clear_requests(self):
        self.pending.clear()
        self.pending_states.clear()
        self.questions.clear()
        self.approvals.clear()

    def _pending_state(self):
        return (AgentState.WAITING_FOR_APPROVAL if AgentState.WAITING_FOR_APPROVAL in self.pending_states.values()
                else AgentState.WAITING_FOR_REPLY)

    def status(self, status, *, reconcile=False):
        kind = status.get("type")
        if kind == "notLoaded":
            raise ConnectionError("Codex unloaded this conversation")
        if kind == "idle":
            self.active = False
            self.turn_id = None
            self._clear_requests()
            if self.state not in {AgentState.SUCCESS, AgentState.CANCELLED, AgentState.ERROR}:
                self.state = AgentState.IDLE
        elif kind == "active":
            self.active = True
            flags = status.get("activeFlags", [])
            if reconcile:
                waiting = set()
                if "waitingOnApproval" in flags:
                    waiting.add(AgentState.WAITING_FOR_APPROVAL)
                if "waitingOnUserInput" in flags:
                    waiting.add(AgentState.WAITING_FOR_REPLY)
                self.pending = {key: value for key, value in self.pending.items()
                                if self.pending_states.get(key) in waiting}
                self.pending_states = {key: value for key, value in self.pending_states.items() if key in self.pending}
                self.questions = {key: value for key, value in self.questions.items() if key in self.pending}
                self.approvals = {key: value for key, value in self.approvals.items() if key in self.pending}
            self.state = (self._pending_state() if self.pending else
                          AgentState.WAITING_FOR_APPROVAL if "waitingOnApproval" in flags else
                          AgentState.WAITING_FOR_REPLY if "waitingOnUserInput" in flags else AgentState.RUNNING)
        elif kind == "systemError":
            self.active = False
            self.state = AgentState.ERROR
            self.turn_id = None
            self._clear_requests()
        else:
            raise ValueError("Unsupported Codex thread status")

    def event(self, message):
        method = message.get("method")
        params = message.get("params", {})
        if not isinstance(params, dict) or params.get("threadId") != self.thread_id:
            return
        if "id" in message or method in {"serverRequest/resolved", "thread/status/changed", "thread/closed",
                                        "thread/archived", "thread/deleted",
                                        "turn/started", "turn/completed", "item/completed"}:
            self.event_revision += 1
        if "id" in message:
            self.active = True
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
            self.pending_states[request_id] = (AgentState.WAITING_FOR_APPROVAL if method in APPROVAL_METHODS
                                              or method == "item/permissions/requestApproval" else AgentState.WAITING_FOR_REPLY)
            self.questions.pop(request_id, None)
            self.approvals.pop(request_id, None)
            if supported and actions:
                details = {"kind": "command" if method == "item/commandExecution/requestApproval" else "file_change",
                           "truncated": False, "additional_permissions": any(params.get(field) for field in
                               ("additionalPermissions", "networkApprovalContext", "proposedNetworkPolicyAmendments"))}
                for name in ("command", "reason", "cwd", "grantRoot"):
                    value = params.get(name)
                    if isinstance(value, str) and value:
                        details[name] = value[:4096]
                        details["truncated"] |= len(value) > 4096
                self.approvals[request_id] = details
            if method == "item/tool/requestUserInput" and turn_id:
                questions = selectable_questions(params)
                if questions:
                    self.questions[request_id] = {"token": uuid4().hex, "questions": questions}
            self.state = self._pending_state()
        elif method == "serverRequest/resolved":
            removed = self.pending.pop(params.get("requestId"), None)
            self.pending_states.pop(params.get("requestId"), None)
            self.questions.pop(params.get("requestId"), None)
            self.approvals.pop(params.get("requestId"), None)
            if removed is not None and not self.pending and self.turn_id:
                self.state = AgentState.RUNNING
            elif removed is not None and self.pending:
                self.state = self._pending_state()
        elif method == "thread/status/changed":
            self.status(params["status"])
        elif method in {"thread/closed", "thread/archived", "thread/deleted"}:
            raise ConnectionError("Codex closed this conversation")
        elif method == "turn/started":
            self.active = True
            turn_id = params["turn"]["id"]
            if self.turn_id != turn_id:
                self._clear_requests()
            self.turn_id = turn_id
            self.state = AgentState.RUNNING
        elif method == "turn/completed":
            turn = params["turn"]
            if self.turn_id and turn["id"] != self.turn_id:
                return
            self.active = False
            self.turn_id = None
            self._clear_requests()
            self.state = {"completed": AgentState.SUCCESS, "interrupted": AgentState.CANCELLED,
                          "failed": AgentState.ERROR}.get(turn["status"], AgentState.IDLE)
        elif method == "item/completed":
            item_id = params.get("item", {}).get("id")
            if item_id:
                previous = len(self.pending)
                self.pending = {key: value for key, value in self.pending.items() if value[1] != item_id}
                self.pending_states = {key: value for key, value in self.pending_states.items() if key in self.pending}
                self.questions = {key: value for key, value in self.questions.items() if key in self.pending}
                self.approvals = {key: value for key, value in self.approvals.items() if key in self.pending}
                if previous and not self.pending and self.turn_id:
                    self.state = AgentState.RUNNING
                elif self.pending:
                    self.state = self._pending_state()

    def controls(self):
        actions = []
        request_id = None
        if len(self.pending) == 1:
            request_id, (choices, _) = next(iter(self.pending.items()))
            actions.extend(choices)
        if self.turn_id and self.turn_id != self.interrupted_turn:
            actions.append(ControlAction.STOP)
        return tuple(actions), request_id, self.turn_id


class ConversationFamily:
    """One surface slot for a CLI conversation and its verified child threads."""

    def __init__(self, root):
        self.root = root
        self.children = {}
        self.labels = {}

    def members(self):
        return (self.root, *self.children.values())

    def waiting(self):
        return [live for live in self.members() if live.pending or
                live.active and live.state in ATTENTION_STATES]

    @property
    def state(self):
        states = {live.state for live in self.children.values() if live.active or live.state == AgentState.ERROR}
        states.add(self.root.state)
        for state in (AgentState.WAITING_FOR_APPROVAL, AgentState.ERROR, AgentState.WAITING_FOR_REPLY):
            if state in states:
                return state
        if AgentState.RUNNING in states:
            return AgentState.RUNNING
        return self.root.state

    def request_target(self):
        waiting = self.waiting()
        if len(waiting) == 1 and len(waiting[0].pending) == 1:
            return waiting[0]
        return None

    def controls(self):
        target = self.request_target()
        actions = []
        request = None
        if target:
            request_id, (choices, _) = next(iter(target.pending.items()))
            actions.extend(choices)
            request = (target.thread_id, request_id)
        # Stop belongs to the selected parent turn, never an arbitrary child.
        if self.root.turn_id and self.root.turn_id != self.root.interrupted_turn:
            actions.append(ControlAction.STOP)
        return tuple(actions), request, self.root.turn_id

    def attention(self):
        waiting = self.waiting()
        return {"pending_count": sum(max(1, len(live.pending)) for live in waiting),
                "child_attention_count": sum(live is not self.root for live in waiting)}

    def event(self, message):
        params = message.get("params", {})
        if not isinstance(params, dict):
            return
        ident = params.get("threadId")
        live = self.root if ident == self.root.thread_id else self.children.get(ident)
        if live is None:
            return
        try:
            live.event(message)
        except ConnectionError:
            if live is self.root:
                raise
            self.children.pop(ident, None)
            self.labels.pop(ident, None)
