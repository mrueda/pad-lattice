import json
import os
from pathlib import Path
import stat
import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from pad_lattice.codex_discovery import _summaries, control_socket, discover_conversations


class Connection:
    def __init__(self, pages, threads):
        self.pages = iter(pages)
        self.threads = threads
        self.sent = []

    def send(self, raw):
        message = json.loads(raw)
        self.sent.append(message)
        method = message['method']
        if method == 'initialized':
            return
        if method == 'initialize':
            result = {}
        elif method == 'thread/loaded/list':
            result = next(self.pages)
        elif method == 'thread/read':
            result = {'thread': self.threads[message['params']['threadId']]}
        else:
            raise AssertionError(f'Unexpected mutating method: {method}')
        self.response = json.dumps({'id': message['id'], 'result': result})

    def recv(self, timeout):
        return self.response


def thread(name='Work', kind='active', flags=None, source='cli'):
    return {'name': name, 'cwd': '/projects/repo', 'source': source,
            'status': {'type': kind, 'activeFlags': flags or []},
            'preview': 'private prompt', 'turns': ['private history']}


class DiscoveryTest(TestCase):
    def test_discovery_reports_loaded_threads_without_claiming_terminal_presence(self):
        connection = Connection([{'data': ['live', 'closed']}],
                                {'live': thread('Live'), 'closed': thread('Montessori', kind='idle')})
        with patch('pad_lattice.codex_discovery.control_socket') as socket, \
                patch('pad_lattice.codex_discovery.unix_connect') as connect:
            socket.return_value.stat.return_value = SimpleNamespace(st_mode=stat.S_IFSOCK, st_uid=os.getuid())
            connect.return_value.__enter__.return_value = connection
            result = discover_conversations()
        self.assertTrue(result['available'])
        self.assertCountEqual([c['id'] for c in result['conversations']], ['live', 'closed'])
        self.assertNotIn('thread/resume', [m['method'] for m in connection.sent])

    def test_pagination_deduplication_filtering_and_metadata_only(self):
        connection = Connection([{'data': ['a', 'b'], 'nextCursor': 'more'},
                                 {'data': ['a', 'c', 'd']}],
                                {'a': thread('Review', flags=['waitingOnApproval']),
                                 'b': thread(source={'subAgent': {}}),
                                 'c': thread(kind='notLoaded'), 'd': thread('Build', kind='idle')})
        result = _summaries(connection, time.monotonic() + 1)
        self.assertEqual([c['id'] for c in result['conversations']], ['d', 'a'])
        self.assertEqual([c['state'] for c in result['conversations']], ['idle', 'approval'])
        self.assertNotIn('private', json.dumps(result))
        reads = [m for m in connection.sent if m['method'] == 'thread/read']
        self.assertEqual(len(reads), 4)
        self.assertTrue(all(m['params']['includeTurns'] is False for m in reads))
        self.assertEqual(connection.sent[5]['params']['cursor'], 'more')

    def test_state_mapping(self):
        threads = {'a': thread(flags=['waitingOnUserInput']), 'b': thread(kind='systemError'),
                   'c': thread(), 'd': thread(kind='futureValue')}
        result = _summaries(Connection([{'data': list(threads)}], threads), time.monotonic() + 1)
        self.assertEqual([c['state'] for c in result['conversations']], ['waiting', 'error', 'running', 'unknown'])

    def test_bounded_discovery(self):
        threads = {str(i): thread() for i in range(65)}
        result = _summaries(Connection([{'data': list(threads)}], threads), time.monotonic() + 1)
        self.assertEqual(len(result['conversations']), 64)
        self.assertTrue(result['truncated'])

    def test_timeout_and_rpc_error(self):
        with self.assertRaises(TimeoutError):
            _summaries(Connection([], {}), time.monotonic() - 1)
        connection = Mock()
        connection.recv.return_value = json.dumps({'id': 1, 'error': {'message': 'not supported'}})
        with self.assertRaises(RuntimeError):
            _summaries(connection, time.monotonic() + 1)

    def test_repeated_cursor_rejected(self):
        connection = Connection([{'data': [], 'nextCursor': 'x'}, {'data': [], 'nextCursor': 'x'}], {})
        with self.assertRaisesRegex(ValueError, 'cursor'):
            _summaries(connection, time.monotonic() + 1)

    def test_missing_socket_does_not_start_codex(self):
        with patch('pad_lattice.codex_discovery.Path.stat', side_effect=FileNotFoundError), \
                patch('pad_lattice.codex_discovery.unix_connect') as connect:
            self.assertFalse(discover_conversations()['available'])
            connect.assert_not_called()

    def test_reject_wrong_owner_or_non_socket(self):
        for mode, uid in [(stat.S_IFREG, os.getuid()), (stat.S_IFSOCK, os.getuid() + 1)]:
            with patch('pad_lattice.codex_discovery.Path.stat', return_value=SimpleNamespace(st_mode=mode, st_uid=uid)), \
                    patch('pad_lattice.codex_discovery.unix_connect') as connect:
                self.assertFalse(discover_conversations()['available'])
                connect.assert_not_called()

    def test_custom_codex_home(self):
        with patch.dict(os.environ, {'CODEX_HOME': '/tmp/custom-codex'}):
            self.assertEqual(control_socket(), Path('/tmp/custom-codex/app-server-control/app-server-control.sock'))

    def test_transport_failure_clears_conversations(self):
        with patch('pad_lattice.codex_discovery.Path.stat', return_value=SimpleNamespace(st_mode=stat.S_IFSOCK, st_uid=os.getuid())), \
                patch('pad_lattice.codex_discovery.unix_connect', side_effect=TimeoutError('timeout')):
            result = discover_conversations()
            self.assertFalse(result['available'])
            self.assertEqual(result['conversations'], [])
