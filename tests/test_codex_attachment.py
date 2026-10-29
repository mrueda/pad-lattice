import json
import os
from pathlib import Path
import queue
import sys
from tempfile import TemporaryDirectory
import threading
import time
from unittest import TestCase
from unittest.mock import Mock, patch

from websockets.sync.server import unix_serve
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

from pad_lattice.client import PadLatticeClient
from pad_lattice.codex_attachment import AttachmentManager, CodexAttachment
from pad_lattice.codex_state import ConversationFamily, LiveConversation
from pad_lattice.events import AgentState, ControlAction
from test_desktop import EngineHarness


def approval(thread='a', request=20, method='item/commandExecution/requestApproval'):
    return {'id': request, 'method': method, 'params': {'threadId': thread, 'turnId': f'turn-{thread}', 'itemId': 'item'}}


def question(thread='a', request=30):
    return {'id': request, 'method': 'item/tool/requestUserInput', 'params': {
        'threadId': thread, 'turnId': f'turn-{thread}', 'itemId': 'question-item',
        'questions': [{'id': 'choice', 'header': 'Tests', 'question': 'Which tests?',
                       'isOther': True, 'isSecret': False, 'options': [
                           {'label': 'Unit', 'description': 'Fast tests'},
                           {'label': 'All', 'description': 'Full suite'}]}]}}


class LiveConversationTest(TestCase):
    def test_close_rejects_queued_and_new_answers_without_sending(self):
        attachment = CodexAttachment('a', '/tmp/unused-pad-lattice-test.sock')
        attachment.connected = True
        attachment.ws = Mock()
        results = [queue.Queue(maxsize=1) for _ in range(3)]
        for result in results:
            attachment.question_answers.put(('token', {}, lambda: True, time.monotonic() + 2, result))
        attachment.close()
        self.assertFalse(attachment.connected)
        self.assertTrue(attachment.question_answers.empty())
        for result in results:
            self.assertEqual(result.get_nowait(), 'Conversation is no longer connected')
        with self.assertRaisesRegex(ValueError, 'no longer connected'):
            attachment.answer_question('token', {}, lambda: True)
        attachment.ws.send.assert_not_called()

    def test_answer_connection_failure_reaches_caller_without_timeout(self):
        attachment = CodexAttachment('a', '/tmp/unused-pad-lattice-test.sock')
        attachment.ws = Mock()
        attachment.live.event(question())
        pending = attachment.live.questions[30]
        result = queue.Queue(maxsize=1)
        attachment.question_answers.put((pending['token'], {'choice': 0}, lambda: True,
                                         time.monotonic() + 2, result))
        attachment.ws.send.side_effect = ConnectionError('Connection closed')
        with self.assertRaises(ConnectionError):
            attachment._answer_pending()
        self.assertEqual(result.get_nowait(), 'Connection closed')
        attachment.ws.send.assert_called_once()
        self.assertIn(30, attachment.live.questions)

    def test_idle_is_ready_and_clears_requests_without_claiming_disconnection(self):
        live = LiveConversation('a')
        self.assertEqual(live.state, AgentState.IDLE)
        live.event(question())
        live.status({'type': 'idle'})
        self.assertEqual(live.state, AgentState.IDLE)
        self.assertFalse(live.pending)
        self.assertFalse(live.questions)
        self.assertEqual(live.controls(), ((), None, None))
        family = ConversationFamily(live)
        self.assertEqual(family.attention(), {'pending_count': 0, 'child_attention_count': 0})
        live.status({'type': 'active', 'activeFlags': ['waitingOnUserInput']})
        self.assertEqual(family.state, AgentState.WAITING_FOR_REPLY)
        self.assertEqual(family.attention()['pending_count'], 1)

    def test_closed_archived_and_deleted_events_end_the_attachment(self):
        for method in ('thread/closed', 'thread/archived', 'thread/deleted'):
            with self.subTest(method=method), self.assertRaises(ConnectionError):
                LiveConversation('a').event({'method': method, 'params': {'threadId': 'a'}})

    def test_authoritative_status_clears_missed_request_resolution(self):
        for message in (approval(), question()):
            live = LiveConversation('a')
            live.event(message)
            live.status({'type': 'active', 'activeFlags': []}, reconcile=True)
            self.assertEqual(live.state, AgentState.RUNNING)
            self.assertFalse(live.pending)
            self.assertFalse(live.pending_states)
            self.assertFalse(live.approvals)
            self.assertFalse(live.questions)
            self.assertEqual(live.controls()[0], (ControlAction.STOP,))

    def test_reconciliation_retains_only_the_kind_still_waiting(self):
        live = LiveConversation('a')
        live.event(approval())
        live.event(question())
        live.status({'type': 'active', 'activeFlags': ['waitingOnUserInput']}, reconcile=True)
        self.assertEqual(live.state, AgentState.WAITING_FOR_REPLY)
        self.assertEqual(list(live.pending), [30])
        self.assertFalse(live.approvals)

    def test_active_status_does_not_hide_a_pending_request(self):
        for message, state in [(approval(), AgentState.WAITING_FOR_APPROVAL),
                               (question(), AgentState.WAITING_FOR_REPLY)]:
            live = LiveConversation('a')
            live.event(message)
            live.status({'type': 'active', 'activeFlags': []})
            self.assertEqual(live.state, state)

    def test_approval_context_is_bounded_and_removed_on_resolution(self):
        live = LiveConversation('a')
        message = approval()
        message['params'].update(command='x' * 5000, reason='Run tests', cwd='/work', additionalPermissions={'network': {}})
        live.event(message)
        self.assertEqual(len(live.approvals[20]['command']), 4096)
        self.assertTrue(live.approvals[20]['truncated'])
        self.assertTrue(live.approvals[20]['additional_permissions'])
        live.event({'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.assertFalse(live.approvals)

    def test_question_requires_safe_bounded_choices_and_clears_on_resolution(self):
        live = LiveConversation('a')
        message = question()
        live.event(message)
        self.assertEqual(live.questions[30]['questions'][0]['options'][1]['label'], 'All')
        live.event({'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 30}})
        self.assertFalse(live.questions)
        message['params']['questions'][0]['isSecret'] = True
        live.event(message)
        self.assertFalse(live.questions)
        message['params']['questions'][0]['isSecret'] = False
        message['params']['questions'][0]['options'] = None
        live.event(message)
        self.assertFalse(live.questions)

    def test_only_matching_thread_and_single_pending_request_can_be_approved(self):
        live = LiveConversation('a')
        live.event(approval('b'))
        self.assertEqual(live.controls()[0], ())
        live.event(approval())
        self.assertIn(ControlAction.APPROVE, live.controls()[0])
        live.event(approval(request=21))
        self.assertNotIn(ControlAction.APPROVE, live.controls()[0])
        live.event({'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.assertEqual(live.controls()[1], 21)

    def test_special_requests_never_get_yes_no_controls(self):
        for method in ['item/tool/requestUserInput', 'item/permissions/requestApproval', 'attestation/generate',
                       'mcpServer/elicitation/request', 'future/requestApproval']:
            live = LiveConversation('a')
            live.event(approval(method=method))
            self.assertNotIn(ControlAction.APPROVE, live.controls()[0])
            self.assertNotIn(ControlAction.REJECT, live.controls()[0])

    def test_available_decisions_and_stdin_are_respected(self):
        live = LiveConversation('a')
        message = approval()
        message['params']['availableDecisions'] = ['decline', 'acceptForSession']
        live.event(message)
        self.assertNotIn(ControlAction.APPROVE, live.controls()[0])
        self.assertIn(ControlAction.REJECT, live.controls()[0])
        message['params']['kind'] = 'stdin'
        live.event(message)
        self.assertEqual(live.controls()[0], (ControlAction.STOP,))

    def test_completed_turn_clears_controls_and_ignores_old_turn(self):
        live = LiveConversation('a')
        live.event(approval())
        live.event({'method': 'turn/completed', 'params': {'threadId': 'a', 'turn': {'id': 'old', 'status': 'completed'}}})
        self.assertIn(ControlAction.APPROVE, live.controls()[0])
        live.event({'method': 'turn/completed', 'params': {'threadId': 'a', 'turn': {'id': 'turn-a', 'status': 'completed'}}})
        self.assertEqual(live.controls()[0], ())
        self.assertEqual(live.state, AgentState.SUCCESS)
        live.status({'type': 'idle'})
        self.assertEqual(live.state, AgentState.SUCCESS)


class ConversationFamilyTest(TestCase):
    def test_child_attention_is_aggregated_and_multiple_requests_have_no_approval(self):
        root = LiveConversation('a')
        root.event({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': 'turn-a'}}})
        family = ConversationFamily(root)
        for ident in ('one', 'two', 'three'):
            child = LiveConversation(ident)
            child.status({'type': 'active', 'activeFlags': ['waitingOnApproval']})
            family.children[ident] = child
        self.assertEqual(root.state, AgentState.RUNNING)
        self.assertEqual(family.state, AgentState.WAITING_FOR_APPROVAL)
        self.assertEqual(family.attention(), {'pending_count': 3, 'child_attention_count': 3})
        family.event(approval('one'))
        self.assertEqual(family.controls(), ((ControlAction.STOP,), None, 'turn-a'))
        # Pending requests without a replay are still blockers, not silently ignored.
        family.children['two'].status({'type': 'idle'})
        family.children['three'].status({'type': 'idle'})
        self.assertEqual(family.controls()[1], ('one', 20))
        self.assertIn(ControlAction.APPROVE, family.controls()[0])
        family.event({'method': 'thread/closed', 'params': {'threadId': 'one'}})
        self.assertEqual(family.state, AgentState.RUNNING)
        self.assertNotIn(ControlAction.APPROVE, family.controls()[0])

    def test_unrelated_events_do_not_become_requests_or_change_state(self):
        root = LiveConversation('a')
        root.status({'type': 'active', 'activeFlags': []})
        family = ConversationFamily(root)
        family.event(approval('other-root'))
        family.event(question('unknown-child'))
        self.assertIsNone(family.request_target())
        self.assertEqual(family.state, AgentState.RUNNING)


class AttachmentIntegrationTest(TestCase):
    def setUp(self):
        # macOS TMPDIR is too long for this nested Unix socket address.
        self.temp = TemporaryDirectory(prefix='pl-attach-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        codex_home = root / 'codex-home'
        control_dir = codex_home / 'app-server-control'
        control_dir.mkdir(parents=True)
        control_path = control_dir / 'app-server-control.sock'
        self.assertLess(len(os.fsencode(control_path)), 104)
        environment = patch.dict(os.environ, {'CODEX_HOME': str(codex_home)})
        environment.start()
        self.addCleanup(environment.stop)
        self.engine = EngineHarness([sys.executable, '-m', 'pad_lattice.desktop_entry'], root)
        self.addCleanup(self.engine.close)
        self.manager = AttachmentManager(self.engine.socket)
        self.client = PadLatticeClient(self.engine.socket)
        self.connections = {}
        self.messages = queue.Queue()
        self.loaded = True
        self.child_threads = {}
        self.replayed_requests = {}
        self.thread_statuses = {}
        self.fake_pending = {}
        self.server = unix_serve(self.handle, str(control_path))
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.addCleanup(self.close_server)
        self.addCleanup(self.manager.close)

    def close_server(self):
        self.server.shutdown()
        self.server_thread.join(timeout=3)

    def handle(self, connection):
        try:
            self.serve(connection)
        except ConnectionClosed:
            pass

    def serve(self, connection):
        for raw in connection:
            message = json.loads(raw)
            method = message.get('method')
            if method not in {'thread/loaded/list', 'thread/read'}:
                self.messages.put(message)
            if method is None or method == 'initialized':
                continue
            params = message.get('params', {})
            thread_id = params.get('threadId', 'a')
            if method == 'initialize':
                result = {}
            elif method == 'thread/loaded/list':
                result = {'data': ['a', *self.child_threads] if self.loaded else [], 'nextCursor': None}
            elif method in {'thread/read', 'thread/resume'}:
                result = {'thread': {'id': thread_id, 'source': 'cli', 'name': f'Conversation {thread_id}',
                                    'cwd': '/projects/test', 'status': {'type': 'active' if self.loaded else 'notLoaded', 'activeFlags': []}}}
                if thread_id in self.child_threads:
                    result['thread'].update(self.child_threads[thread_id])
                if thread_id in self.thread_statuses:
                    result['thread']['status'] = self.thread_statuses[thread_id]
            elif method == 'thread/turns/list':
                result = {'data': [{'id': f'turn-{thread_id}', 'status': 'inProgress', 'items': []}]}
            elif method == 'turn/interrupt':
                result = {}
            else:
                raise AssertionError(method)
            connection.send(json.dumps({'id': message['id'], 'result': result}))
            if method == 'thread/resume':
                self.connections[thread_id] = connection
                for request in self.replayed_requests.get(thread_id, []):
                    self.record_status(request)
                    connection.send(json.dumps(request))

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.02)
        self.fail('Timed out waiting for bridge state')

    def controls(self):
        messages = self.engine.request('snapshot')['messages']
        return next(m for m in messages if m['type'] == 'surface')['view']['available_actions']

    def record_status(self, message):
        params = message.get('params', {})
        ident = params.get('threadId')
        pending = self.fake_pending.setdefault(ident, {})
        method = message.get('method')
        if 'id' in message:
            pending[message['id']] = 'waitingOnApproval' if 'Approval' in method else 'waitingOnUserInput'
        elif method == 'serverRequest/resolved':
            pending.pop(params.get('requestId'), None)
        else:
            return
        self.thread_statuses[ident] = {'type': 'active', 'activeFlags': sorted(set(pending.values()))}

    def send(self, thread_id, message):
        self.record_status(message)
        self.connections[thread_id].send(json.dumps(message))

    def drain(self):
        result = []
        while not self.messages.empty():
            result.append(self.messages.get_nowait())
        return result

    def action(self, action):
        self.engine.request('surface', {'protocol': 1, 'type': 'action', 'action': action})

    def child(self, ident, parent='a', waiting=True):
        self.child_threads[ident] = {
            'source': {'subAgent': {'thread_spawn': {'parent_thread_id': parent, 'agent_nickname': ident}}},
            'status': {'type': 'active', 'activeFlags': ['waitingOnApproval'] if waiting else []}}

    def test_idle_chats_do_not_need_attention_but_real_questions_do(self):
        self.thread_statuses['a'] = {'type': 'idle'}
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'idle')
        self.assertEqual(self.engine.request('attention')['sessions'], [])
        self.assertEqual(self.controls(), [])
        self.send('a', question())
        self.wait_for(lambda: len(self.engine.request('attention')['sessions']) == 1)
        self.thread_statuses['a'] = {'type': 'idle'}
        self.send('a', {'method': 'thread/status/changed', 'params': {'threadId': 'a', 'status': {'type': 'idle'}}})
        self.wait_for(lambda: not self.engine.request('attention')['sessions'])
        self.assertEqual(self.client.status()['sessions'][0]['state'], 'idle')
        self.assertEqual(self.controls(), [])
        self.assertIsNone(self.engine.request('question_status')['question'])

    def test_retained_thread_can_be_manually_disconnected_without_history_changes(self):
        self.thread_statuses['a'] = {'type': 'idle'}
        self.manager.attach('a')
        self.assertEqual(len(self.client.status()['sessions']), 1)
        self.manager.detach('a')
        self.wait_for(lambda: not self.client.status()['sessions'])
        self.assertTrue(self.loaded)
        self.assertNotIn('a', self.manager.snapshot())
        self.assertEqual(self.manager.attach('a')['slot'], 0)
        self.assertFalse(any(message.get('method') in {'thread/delete', 'thread/archive'} for message in self.drain()))

    def test_completed_turn_settles_to_ready_without_false_attention(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.thread_statuses['a'] = {'type': 'idle'}
        self.send('a', {'method': 'turn/completed', 'params': {'threadId': 'a',
                   'turn': {'id': 'turn-a', 'status': 'completed'}}})
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'success')
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'idle')
        self.assertEqual(self.engine.request('attention')['sessions'], [])

    def test_closed_middle_chat_releases_only_its_scene(self):
        for ident in ('a', 'b', 'c'):
            self.manager.attach(ident)
        before = {s['session_id']: (s['slot'], s['accent']) for s in self.client.status()['sessions']}
        self.send('b', approval('b'))
        self.engine.request('surface', {'protocol': 1, 'type': 'select_session', 'slot': 1})
        self.wait_for(lambda: 'approve' in self.controls())
        self.send('b', {'method': 'thread/closed', 'params': {'threadId': 'b'}})
        self.wait_for(lambda: len(self.client.status()['sessions']) == 2)
        after = self.client.status()
        self.assertEqual({s['session_id']: (s['slot'], s['accent']) for s in after['sessions']},
                         {ident: before[ident] for ident in ('a', 'c')})
        self.assertIsNone(after['selected'])
        self.assertEqual(self.controls(), [])

    def test_poll_clears_stale_parent_approval_when_resolved_event_is_missing(self):
        self.manager.attach('a')
        self.send('a', approval())
        self.wait_for(lambda: 'approve' in self.controls())
        self.thread_statuses['a'] = {'type': 'active', 'activeFlags': []}
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'running')
        self.assertNotIn('approve', self.controls())
        self.assertIsNone(self.manager.approval(0))

    def test_existing_children_flag_parent_without_occupying_scenes(self):
        for ident in ('one', 'two', 'three'):
            self.child(ident)
        self.child('unrelated', parent='another-root')
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        attention = self.wait_for(lambda: (value if (value := self.engine.request('attention'))['sessions'] else None))
        self.assertEqual(len(attention['sessions']), 1)
        self.assertEqual(attention['sessions'][0]['state'], 'waiting_for_approval')
        self.assertEqual(attention['sessions'][0]['child_attention_count'], 3)
        status = self.engine.request('approval_status')
        self.assertEqual(status['pending_count'], 3)
        self.assertIsNone(status['approval'])
        self.assertNotIn('approve', self.controls())
        sessions = self.client.status()['sessions']
        self.assertEqual([(s['session_id'], s['slot']) for s in sessions], [('a', 0)])
        resumed = [m['params']['threadId'] for m in self.drain() if m.get('method') == 'thread/resume']
        self.assertCountEqual(resumed, ['a', 'one', 'two', 'three'])

    def test_single_child_approval_is_request_scoped_and_identified_locally(self):
        self.child('worker')
        message = approval('worker', request=51)
        message['params'].update(command='npm test', cwd='/child/work')
        self.replayed_requests['worker'] = [message]
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.wait_for(lambda: 'approve' in self.controls())
        details = self.engine.request('approval_status')['approval']
        self.assertEqual(details['agent_label'], 'worker')
        self.assertEqual(details['command'], 'npm test')
        self.assertNotIn('/child/work', json.dumps(self.engine.request('snapshot')))
        self.drain()
        self.action('approve')
        self.assertEqual(self.messages.get(timeout=3), {'id': 51, 'result': {'decision': 'accept'}})
        self.child_threads['worker']['status'] = {'type': 'active', 'activeFlags': []}
        self.send('worker', {'method': 'serverRequest/resolved', 'params': {'threadId': 'worker', 'requestId': 51}})
        self.wait_for(lambda: not self.engine.request('attention')['sessions'])
        self.assertFalse(any(m.get('method') in {'turn/start', 'thread/start'} for m in self.drain()))

    def test_new_nested_child_is_discovered_and_removed_without_detaching_parent(self):
        self.child('worker', waiting=False)
        self.manager.attach('a')
        self.child('nested', parent='worker')
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'waiting_for_approval')
        self.assertIn('nested', self.connections)
        del self.child_threads['nested']
        self.send('nested', {'method': 'thread/closed', 'params': {'threadId': 'nested'}})
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'running')
        self.assertTrue(self.manager.snapshot()['a']['connected'])

    def test_child_question_is_scoped_and_second_waiter_disables_answer(self):
        self.child('worker', waiting=False)
        self.replayed_requests['worker'] = [question('worker', request=61)]
        self.manager.attach('a')
        pending = self.wait_for(lambda: self.manager.question(0))
        self.send('a', approval())
        self.wait_for(lambda: self.manager.question(0) is None)
        with self.assertRaisesRegex(ValueError, 'no longer available'):
            self.manager.answer_question(0, pending['token'], {'choice': 0}, lambda: True)
        self.send('a', {'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.wait_for(lambda: self.manager.question(0))
        self.drain()
        self.manager.answer_question(0, pending['token'], {'choice': 0}, lambda: True)
        self.assertEqual(self.messages.get(timeout=3), {'id': 61, 'result': {'answers': {'choice': {'answers': ['Unit']}}}})

    def test_live_attachment_state_targeted_approval_stop_and_detach(self):
        self.assertEqual(self.manager.attach('a')['slot'], 0)
        self.assertEqual(self.manager.attach('b')['slot'], 1)
        self.wait_for(lambda: len(self.client.status()['sessions']) == 2)
        self.assertEqual({s['session_id']: s['slot'] for s in self.client.status()['sessions']}, {'a': 0, 'b': 1})
        initial = self.drain()
        initializations = [m for m in initial if m.get('method') == 'initialize']
        self.assertTrue(all(m['params']['capabilities']['experimentalApi'] for m in initializations))
        resumes = [m for m in initial if m.get('method') == 'thread/resume']
        self.assertEqual(len(resumes), 2)
        self.assertTrue(all(set(m['params']) == {'threadId', 'excludeTurns'} for m in resumes))
        self.send('a', approval('a'))
        self.send('b', approval('b', request=21))
        sessions = self.client.status()['sessions']
        slot = next(item['slot'] for item in sessions if item['session_id'] == 'b')
        self.engine.request('surface', {'protocol': 1, 'type': 'select_session', 'slot': slot})
        self.wait_for(lambda: 'approve' in self.controls())
        self.action('approve')
        response = self.messages.get(timeout=3)
        self.assertEqual(response, {'id': 21, 'result': {'decision': 'accept'}})
        self.assertTrue(self.messages.empty())
        self.send('b', {'method': 'serverRequest/resolved', 'params': {'threadId': 'b', 'requestId': 21}})
        self.wait_for(lambda: 'stop' in self.controls())
        self.action('stop')
        response = self.messages.get(timeout=3)
        self.assertEqual(response['method'], 'turn/interrupt')
        self.assertEqual(response['params'], {'threadId': 'b', 'turnId': 'turn-b'})
        self.manager.detach('b')
        self.wait_for(lambda: len(self.client.status()['sessions']) == 1)
        self.assertFalse(any(m.get('method') in {'turn/start', 'thread/start'} for m in self.drain()))

    def test_question_answer_is_scoped_and_stale_answers_are_rejected(self):
        self.manager.attach('a')
        self.manager.attach('b')
        self.drain()
        self.send('a', question('a', 30))
        self.send('b', question('b', 31))
        first = self.wait_for(lambda: self.manager.question(0))
        second = self.wait_for(lambda: self.manager.question(1))
        with self.assertRaisesRegex(ValueError, 'Invalid or outdated'):
            self.manager.answer_question(1, first['token'], {'choice': 0}, lambda: True)
        with self.assertRaisesRegex(ValueError, 'no longer available'):
            self.manager.answer_question(1, second['token'], {'choice': 0}, lambda: False)
        self.manager.answer_question(1, second['token'], {'choice': 1}, lambda: True)
        self.assertEqual(self.messages.get(timeout=3), {'id': 31, 'result': {'answers': {'choice': {'answers': ['All']}}}})
        self.assertIsNone(self.manager.question(1))
        self.assertIsNotNone(self.manager.question(0))
        self.send('a', {'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 30}})
        self.wait_for(lambda: self.manager.question(0) is None)
        with self.assertRaises(ValueError):
            self.manager.answer_question(0, first['token'], {'choice': 0}, lambda: True)

    def test_multiple_questions_require_all_valid_choices(self):
        self.manager.attach('a')
        self.drain()
        message = question()
        message['params']['questions'].append({'id': 'format', 'header': 'Output', 'question': 'Format?',
            'isOther': False, 'isSecret': False, 'options': [{'label': 'Text', 'description': ''}]})
        self.send('a', message)
        pending = self.wait_for(lambda: self.manager.question(0))
        with self.assertRaisesRegex(ValueError, 'Invalid or outdated'):
            self.manager.answer_question(0, pending['token'], {'choice': 0}, lambda: True)
        with self.assertRaisesRegex(ValueError, 'Invalid or outdated'):
            self.manager.answer_question(0, pending['token'], {'choice': True, 'format': 0}, lambda: True)
        self.manager.answer_question(0, pending['token'], {'choice': 0, 'format': 0}, lambda: True)
        self.assertEqual(self.messages.get(timeout=3), {'id': 30, 'result': {'answers': {
            'choice': {'answers': ['Unit']}, 'format': {'answers': ['Text']}}}})

    def test_desktop_question_request_requires_current_selection(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.drain()
        self.send('a', question())
        self.wait_for(lambda: next(m for m in self.engine.request('snapshot')['messages']
                                   if m['type'] == 'surface')['view']['selected_state'] == 'waiting_for_reply')
        time.sleep(0.2)
        status = self.wait_for(lambda: (value if (value := self.engine.request('question_status'))['question']
                                       and type(value['revision']) is int else None))
        with self.assertRaises(Exception):
            self.engine.request('answer_question', {'slot': status['slot'], 'revision': -1,
                                                     'token': status['question']['token'], 'answers': {'choice': 0}})
        self.engine.request('answer_question', {'slot': status['slot'], 'revision': status['revision'],
                                                'token': status['question']['token'], 'answers': {'choice': 0}})
        self.assertEqual(self.messages.get(timeout=3), {'id': 30, 'result': {'answers': {'choice': {'answers': ['Unit']}}}})

    def test_approval_context_is_local_and_follows_the_selected_request(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.drain()
        message = approval()
        message['params'].update(command='npm test', reason='Run tests', cwd='/private/project')
        self.send('a', message)
        status = self.wait_for(lambda: (value if (value := self.engine.request('approval_status'))['approval'] else None))
        self.assertEqual(status['approval']['command'], 'npm test')
        self.assertEqual(status['approval']['cwd'], '/private/project')
        self.assertNotIn('npm test', json.dumps(self.engine.request('snapshot')))
        self.send('a', {'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.wait_for(lambda: self.engine.request('approval_status')['approval'] is None)

    def test_paired_browser_questions_are_opt_in_and_request_scoped(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.drain()
        self.send('a', question())
        self.wait_for(lambda: self.engine.request('question_status')['question'])
        time.sleep(0.2)
        self.engine.events.clear()
        self.engine.request('surface', {'protocol': 1, 'type': 'create_pairing'})
        pairing = next(event['payload'] for event in self.engine.events
                       if event.get('event') == 'surface' and event.get('payload', {}).get('type') == 'pairing')
        port = self.engine.request('status')['port']
        origin = f'http://127.0.0.1:{port}'
        with connect(f'ws://127.0.0.1:{port}/ws', origin=origin, proxy=None, close_timeout=1) as browser:
            browser.send(json.dumps({'protocol': 1, 'type': 'authenticate', 'credential': pairing['pin']}))
            self.assertEqual(json.loads(browser.recv(timeout=2))['type'], 'authenticated')
            def request(message):
                browser.send(json.dumps({'protocol': 1, 'type': 'question_request', **message}))
                while True:
                    received = json.loads(browser.recv(timeout=3))
                    if received['type'] == 'question_response' and received['request_id'] == message['request_id']:
                        return received
                    self.assertNotIn('Which tests?', json.dumps(received))
            denied = request({'request_id': '1', 'operation': 'status'})
            self.assertIn('sharing is off', denied['error'])
            self.engine.request('settings', {'share_browser_questions': True})
            status = request({'request_id': '2', 'operation': 'status'})['result']
            self.assertEqual(status['question']['questions'][0]['question'], 'Which tests?')
            answer = {'operation': 'answer', 'slot': status['slot'], 'revision': status['revision'],
                      'token': status['question']['token'], 'answers': {'choice': 1}}
            self.engine.request('settings', {'share_browser_questions': False})
            self.assertIn('sharing is off', request({'request_id': '3', **answer})['error'])
            self.engine.request('settings', {'share_browser_questions': True})
            bad = dict(answer, revision=status['revision'] + 100)
            self.assertIn('selected conversation', request({'request_id': '4', **bad})['error'])
            self.assertEqual(request({'request_id': '5', **answer})['result'], {})
            self.assertEqual(self.messages.get(timeout=3), {'id': 30, 'result': {'answers': {'choice': {'answers': ['All']}}}})
            self.assertTrue(request({'request_id': '6', **answer})['error'])
            self.assertTrue(self.messages.empty())

    def test_question_content_is_not_broadcast_to_other_paired_devices(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.send('a', question())
        self.wait_for(lambda: self.engine.request('question_status')['question'])
        self.engine.request('settings', {'share_browser_questions': True})
        port = self.engine.request('status')['port']
        origin = f'http://127.0.0.1:{port}'
        def pair():
            self.engine.events.clear()
            self.engine.request('surface', {'protocol': 1, 'type': 'create_pairing'})
            pin = next(e['payload']['pin'] for e in self.engine.events if e.get('payload', {}).get('type') == 'pairing')
            browser = connect(f'ws://127.0.0.1:{port}/ws', origin=origin, proxy=None, close_timeout=1)
            self.addCleanup(browser.close)
            browser.send(json.dumps({'protocol': 1, 'type': 'authenticate', 'credential': pin}))
            self.assertEqual(json.loads(browser.recv(timeout=2))['type'], 'authenticated')
            return browser
        first, second = pair(), pair()
        first.send(json.dumps({'protocol': 1, 'type': 'question_request', 'request_id': 'private', 'operation': 'status'}))
        while True:
            message = json.loads(first.recv(timeout=3))
            if message.get('request_id') == 'private':
                self.assertEqual(message['result']['question']['questions'][0]['question'], 'Which tests?')
                break
        while True:
            try:
                message = json.loads(second.recv(timeout=0.2))
            except TimeoutError:
                break
            self.assertNotEqual(message.get('type'), 'question_response')
            self.assertNotIn('Which tests?', json.dumps(message))

    def test_resolved_approval_disappears_and_reject_is_single_request_only(self):
        self.manager.attach('a')
        self.drain()
        self.send('a', approval())
        self.wait_for(lambda: 'approve' in self.controls())
        self.send('a', {'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.wait_for(lambda: 'approve' not in self.controls())
        self.wait_for(lambda: self.client.status()['sessions'][0]['state'] == 'running')
        self.action('approve')
        self.assertTrue(self.messages.empty())
        self.send('a', approval(request=22, method='item/fileChange/requestApproval'))
        self.wait_for(lambda: 'reject' in self.controls())
        self.action('reject')
        self.assertEqual(self.messages.get(timeout=3), {'id': 22, 'result': {'decision': 'decline'}})

    def test_socket_loss_removes_controls_and_session(self):
        self.manager.attach('a')
        self.wait_for(lambda: len(self.client.status()['sessions']) == 1)
        self.connections['a'].close()
        self.wait_for(lambda: not self.client.status()['sessions'])
        self.wait_for(lambda: not self.manager.snapshot()['a']['connected'])

    def test_desktop_reports_unexpected_attachment_loss_without_restarting_codex(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.wait_for(lambda: len(self.client.status()['sessions']) == 1)
        self.engine.events.clear()
        self.connections['a'].close()
        self.wait_for(lambda: not self.client.status()['sessions'])
        self.wait_for(lambda: (self.engine.request('snapshot') is not None and any(
            event.get('event') == 'attachment_disconnected' and event.get('thread_id') == 'a'
            for event in self.engine.events)))
        self.assertFalse(any(m.get('method') in {'turn/start', 'thread/start'} for m in self.drain()))

    def test_saved_conversation_is_not_resumed(self):
        self.loaded = False
        with self.assertRaisesRegex(RuntimeError, 'loaded'):
            self.manager.attach('a')
        self.assertNotIn('thread/resume', [m.get('method') for m in self.drain()])
        self.assertFalse(self.client.status()['sessions'])

    def test_desktop_operations_expose_connection_and_slot(self):
        result = self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.assertEqual(result['slot'], 0)
        self.wait_for(lambda: len(self.client.status()['sessions']) == 1)
        self.assertEqual(self.client.status()['sessions'][0]['metadata']['source'], 'app-server')
        self.engine.request('detach_conversation', {'thread_id': 'a'})
        self.wait_for(lambda: not self.client.status()['sessions'])

    def test_refresh_removes_closed_conversations_and_failed_attachments(self):
        self.engine.request('attach_conversation', {'thread_id': 'a'})
        self.assertTrue(self.engine.request('list_conversations')['conversations'][0]['connected'])
        self.loaded = False
        self.connections['a'].close()
        self.wait_for(lambda: not self.client.status()['sessions'])
        self.wait_for(lambda: not self.engine.request('list_conversations')['conversations'])
        self.assertEqual(self.engine.request('list_conversations')['conversations'], [])
