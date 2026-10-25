import json
import os
from pathlib import Path
import queue
import sys
from tempfile import TemporaryDirectory
import threading
import time
from unittest import TestCase
from unittest.mock import patch

from websockets.sync.server import unix_serve
from websockets.exceptions import ConnectionClosed

from pad_lattice.client import PadLatticeClient
from pad_lattice.codex_attachment import AttachmentManager, LiveConversation
from pad_lattice.events import AgentState, ControlAction
from test_desktop import EngineHarness


def approval(thread='a', request=20, method='item/commandExecution/requestApproval'):
    return {'id': request, 'method': method, 'params': {'threadId': thread, 'turnId': f'turn-{thread}', 'itemId': 'item'}}


class LiveConversationTest(TestCase):
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
            self.messages.put(message)
            method = message.get('method')
            if method is None or method == 'initialized':
                continue
            params = message.get('params', {})
            thread_id = params.get('threadId', 'a')
            if method == 'initialize':
                result = {}
            elif method == 'thread/loaded/list':
                result = {'data': ['a'] if self.loaded else [], 'nextCursor': None}
            elif method in {'thread/read', 'thread/resume'}:
                result = {'thread': {'id': thread_id, 'source': 'cli', 'name': f'Conversation {thread_id}',
                                    'cwd': '/projects/test', 'status': {'type': 'active' if self.loaded else 'notLoaded', 'activeFlags': []}}}
            elif method == 'thread/turns/list':
                result = {'data': [{'id': f'turn-{thread_id}', 'status': 'inProgress', 'items': []}]}
            elif method == 'turn/interrupt':
                result = {}
            else:
                raise AssertionError(method)
            connection.send(json.dumps({'id': message['id'], 'result': result}))
            if method == 'thread/resume':
                self.connections[thread_id] = connection

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

    def send(self, thread_id, message):
        self.connections[thread_id].send(json.dumps(message))

    def drain(self):
        result = []
        while not self.messages.empty():
            result.append(self.messages.get_nowait())
        return result

    def action(self, action):
        self.engine.request('surface', {'protocol': 1, 'type': 'action', 'action': action})

    def test_live_attachment_state_targeted_approval_stop_and_detach(self):
        self.assertEqual(self.manager.attach('a')['slot'], 0)
        self.assertEqual(self.manager.attach('b')['slot'], 1)
        self.wait_for(lambda: len(self.client.status()['sessions']) == 2)
        self.assertEqual({s['session_id']: s['slot'] for s in self.client.status()['sessions']}, {'a': 0, 'b': 1})
        initial = self.drain()
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

    def test_resolved_approval_disappears_and_reject_is_single_request_only(self):
        self.manager.attach('a')
        self.drain()
        self.send('a', approval())
        self.wait_for(lambda: 'approve' in self.controls())
        self.send('a', {'method': 'serverRequest/resolved', 'params': {'threadId': 'a', 'requestId': 20}})
        self.wait_for(lambda: 'approve' not in self.controls())
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
