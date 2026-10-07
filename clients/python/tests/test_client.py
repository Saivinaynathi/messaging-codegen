import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import API, APIError
from client import command, synchronize
from database import Database
from models import Message
from sync import SyncService


class FakeAPI:
    def __init__(self):
        self.messages = {}
        self.calls = []
        self.fail = False
        self.lose_ack = False
        self.database = None

    def register(self, name):
        self.calls.append(name)
        if self.fail:
            raise APIError("unavailable")

    def send(self, message):
        self.calls.append(message.payload())
        if self.database:
            assert self.database.get(message.message_id)['delivery_state'] == 'SENDING'
        if self.fail:
            raise APIError("unavailable")
        self.messages.setdefault(message.message_id, message)
        if self.lose_ack:
            raise APIError("acknowledgement lost")

    def receive(self, name):
        self.calls.append(name)
        if self.fail:
            raise APIError("unavailable")
        return [message for message in self.messages.values() if message.recipient == name]


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'alice.sqlite3'
        self.db = Database(self.path)
        self.addCleanup(lambda: self.db.close())
        self.api = FakeAPI()
        self.service = SyncService(self.db, self.api)
        self.service.identify(' Alice ')
        self.api.database = self.db

    def test_registration_only_persisted_on_acknowledgement(self):
        other = Database(Path(self.temp.name) / 'other.sqlite3')
        self.addCleanup(other.close)
        service = SyncService(other, self.api)
        self.api.fail = True
        with self.assertRaises(APIError):
            service.identify('Bob')
        self.assertIsNone(other.user)
        service.offline = True
        self.api.calls.clear()
        with self.assertRaises(ValueError):
            service.identify('Bob')
        self.assertEqual(self.api.calls, [])

    def test_blank_validation(self):
        for recipient, text in [(' ', 'text'), ('Bob', ' ' )]:
            with self.assertRaises(ValueError):
                self.service.create(recipient, text)
        self.assertEqual(self.db.pending(), [])

    def test_offline_restart_and_reconnect(self):
        self.service.set_offline(True)
        self.api.calls.clear()
        original = self.service.create(' Bob ', ' Héllo 世界 ')
        self.service.sync()
        self.assertEqual(self.api.calls, [])
        self.assertEqual(self.db.get(original.message_id)['delivery_state'], 'PENDING')
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(self.db.user, 'Alice')
        self.assertEqual(self.db.pending(), [original])
        self.api.database = self.db
        self.service = SyncService(self.db, self.api, offline=True)
        self.assertEqual(self.service.set_offline(False), [])
        self.assertEqual(self.db.get(original.message_id)['delivery_state'], 'SENT')
        self.assertEqual(self.api.messages[original.message_id], original)

    def test_failure_and_uncertain_delivery_reuse_payload(self):
        original = self.service.create('Bob', 'hello')
        self.api.fail = True
        self.assertTrue(self.service.sync())
        self.assertEqual(self.db.pending(), [original])
        self.api.fail = False
        self.api.lose_ack = True
        self.service.sync()
        self.assertEqual(self.db.pending(), [original])
        self.api.lose_ack = False
        self.service.sync()
        self.assertEqual(len(self.api.messages), 1)
        payloads = [call for call in self.api.calls if isinstance(call, dict)]
        self.assertEqual(payloads, [original.payload()] * 3)

    def test_crash_recovery(self):
        original = self.service.create('Bob', 'recover')
        self.db.state(original.message_id, 'SENDING')
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(self.db.pending(), [original])

    def test_incoming_order_deduplication_across_restart(self):
        first = Message('one', 'Bob', 'Alice', 'first', '2030-01-01T00:00:00Z')
        second = Message('two', 'Bob', 'Alice', 'second', '2020-01-01T00:00:00Z')
        self.api.messages = {'one': first, 'two': second}
        self.service.sync()
        self.service.sync()
        self.db.close()
        self.db = Database(self.path)
        self.service = SyncService(self.db, self.api)
        self.service.sync()
        self.assertEqual([r['message_id'] for r in self.db.conversation('Bob')], ['one', 'two'])

    def test_cli_displays_before_network_and_offline_commands(self):
        self.service.set_offline(True)
        self.api.calls.clear()
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            command('send Bob hello', self.service)
            command('messages Bob', self.service)
            command('sync', self.service)
            command('status', self.service)
            self.assertIn('PENDING', output.getvalue())
            self.assertIn('OFFLINE', output.getvalue())
        self.assertEqual(self.api.calls, [])

    def test_polling_displays_only_new_incoming_messages(self):
        message = Message.create('Bob', 'Alice', 'hello')
        self.api.messages[message.message_id] = message
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            synchronize(self.service)
            synchronize(self.service)
            self.assertEqual(output.getvalue().count('Bob -> Me: hello'), 1)

    def test_alice_bob_scenario(self):
        bob_db = Database(Path(self.temp.name) / 'bob.sqlite3')
        self.addCleanup(bob_db.close)
        bob = SyncService(bob_db, self.api)
        bob.identify('Bob')
        self.api.database = None
        a1 = self.service.create('Bob', 'Hi Bob, I have something important to tell you')
        self.service.sync()
        bob.sync()
        b1 = bob.create('Alice', 'What is it?')
        bob.sync()
        self.service.sync()
        self.service.set_offline(True)
        a2 = self.service.create('Bob', 'The important message was queued while I was offline.')
        bob.set_offline(True)
        b2 = bob.create('Alice', 'I am replying while offline too.')
        self.assertEqual(len(self.api.messages), 2)
        self.service.set_offline(False)
        self.service.set_offline(True)
        bob.set_offline(False)
        self.service.set_offline(False)
        bob.sync()
        for db, other in [(self.db, 'Bob'), (bob_db, 'Alice')]:
            self.assertEqual(len(db.conversation(other)), 4)
            self.assertEqual(db.pending(), [])
        for message in [a1, a2]:
            self.assertEqual(self.db.get(message.message_id)['delivery_state'], 'SENT')
        for message in [b1, b2]:
            self.assertEqual(bob_db.get(message.message_id)['delivery_state'], 'SENT')


class TransportTests(unittest.TestCase):
    def test_incoming_validation_and_original_payload(self):
        api = API()
        message = Message.create('Bob', 'Alice', 'Héllo 世界')
        with patch.object(api, 'request', return_value={'messages': [message.payload()]}):
            self.assertEqual(api.receive('Alice'), [message])
        for field, value in [('message_id', 'invalid'), ('text', None),
                             ('created_at', '2026-01-01T00:00:00'),
                             ('created_at', '2026-01-01T00:00:00+02:00'),
                             ('recipient', 'Someone else')]:
            payload = dict(message.payload(), **{field: value})
            with patch.object(api, 'request', return_value={'messages': [payload]}):
                with self.assertRaises(APIError):
                    api.receive('Alice')

    def test_acknowledgement_validation(self):
        api = API()
        message = Message.create('Alice', 'Bob', 'hello')
        for response in [{}, {'message_id': 'wrong', 'status': 'accepted'},
                         {'message_id': message.message_id, 'status': 'failed'}, []]:
            with patch.object(api, 'request', return_value=response):
                with self.assertRaises(APIError):
                    api.send(message)

    def test_username_encoding(self):
        api = API()
        with patch.object(api, 'request', return_value={'messages': []}) as request:
            api.receive('Mary Jane & Bob')
            request.assert_called_once_with('/messages/Mary%20Jane%20%26%20Bob')


if __name__ == '__main__':
    unittest.main()

class NetworkFailureTests(unittest.TestCase):
    def test_http_errors_timeouts_and_malformed_ack_remain_pending(self):
        from urllib.error import HTTPError, URLError
        from uuid import UUID
        failures = [HTTPError('http://localhost/messages', 400, 'bad request', {}, None),
                    HTTPError('http://localhost/messages', 503, 'unavailable', {}, None),
                    URLError('connection refused'), TimeoutError('timeout')]
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as directory:
            db = Database(Path(directory) / 'test.sqlite3')
            try:
                db.set_user('Alice')
                service = SyncService(db, API())
                message = service.create('Bob', 'hello')
                UUID(message.message_id)
                self.assertTrue(message.created_at.endswith('Z'))
                for error in failures:
                    with patch('api.urlopen', side_effect=error):
                        self.assertTrue(service.sync())
                    self.assertEqual(db.pending(), [message])
                # A mismatched ID must not promote a stored message to SENT.
                with patch.object(service.api, 'request', return_value={
                    'message_id': 'different-id', 'status': 'accepted'}):
                    self.assertTrue(service.sync())
                self.assertEqual(db.pending(), [message])
            finally:
                db.close()
