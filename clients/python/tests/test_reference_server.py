"""Real HTTP validation against the hand-written reference server, unchanged."""
import importlib.util
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import API, APIError
from database import Database
from sync import SyncService


class ReferenceServerTests(unittest.TestCase):
    def test_http_offline_reconnect_scenario(self):
        try:
            import uvicorn
            import fastapi
        except ImportError:
            self.skipTest('Reference server dependencies are not installed')
        try:
            listener = socket.socket()
            listener.bind(('127.0.0.1', 0))
            listener.listen()
        except OSError as error:
            listener.close()
            self.skipTest(f'Local listening sockets unavailable: {error}')
        self.addCleanup(listener.close)
        source = Path(__file__).resolve().parents[3] / 'server' / 'app.py'
        spec = importlib.util.spec_from_file_location('reference_server', source)
        module = importlib.util.module_from_spec(spec)
        # Loading existing infrastructure must not create files outside this client.
        old = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = old
        server = uvicorn.Server(uvicorn.Config(module.app, log_level='error'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        def stop():
            server.should_exit = True
            thread.join(timeout=5)
        self.addCleanup(stop)
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(server.started)
        api = API(f'http://127.0.0.1:{listener.getsockname()[1]}')
        with tempfile.TemporaryDirectory(dir=source.parents[1] / 'clients' / 'python') as directory:
            alice_db = Database(Path(directory) / 'alice.sqlite3')
            bob_db = Database(Path(directory) / 'bob.sqlite3')
            try:
                alice = SyncService(alice_db, api)
                bob = SyncService(bob_db, api)
                alice.identify('Alice')
                bob.identify('Bob')
                alice.create('Bob', 'Hi Bob, I have something important to tell you')
                self.assertEqual(alice.sync(), [])
                self.assertEqual(bob.sync(), [])
                bob.create('Alice', 'What is it?')
                self.assertEqual(bob.sync(), [])
                alice.sync()
                alice.set_offline(True)
                a = alice.create('Bob', 'The important message was queued while I was offline.')
                bob.set_offline(True)
                b = bob.create('Alice', 'I am replying while offline too.')
                self.assertEqual(len(module.messages_by_id), 2)
                self.assertEqual(alice.set_offline(False), [])
                alice.set_offline(True)
                self.assertEqual(bob.set_offline(False), [])
                self.assertEqual(alice.set_offline(False), [])
                # Retrying a previously accepted message remains idempotent.
                api.send(a)
                api.send(b)
                alice.sync()
                bob.sync()
                self.assertEqual(len(module.messages_by_id), 4)
                self.assertEqual(len(alice_db.conversation('Bob')), 4)
                self.assertEqual(len(bob_db.conversation('Alice')), 4)
                self.assertEqual(alice_db.get(a.message_id)['delivery_state'], 'SENT')
                self.assertEqual(bob_db.get(b.message_id)['delivery_state'], 'SENT')
            finally:
                alice_db.close()
                bob_db.close()

    def test_reference_handlers_through_transport(self):
        """Exercise JSON transport and actual server handlers without binding a port."""
        import io
        import json
        from urllib.parse import unquote
        from unittest.mock import patch
        try:
            import fastapi
        except ImportError:
            self.skipTest('Reference server dependencies are not installed')
        source = Path(__file__).resolve().parents[3] / 'server' / 'app.py'
        spec = importlib.util.spec_from_file_location('reference_handlers', source)
        module = importlib.util.module_from_spec(spec)
        old = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = old

        def transport(request, timeout):
            path = request.full_url.removeprefix('http://localhost:8000')
            if path == '/users/register':
                result = module.register_user(module.UserRegistration(**json.loads(request.data)))
            elif path == '/messages':
                result = module.send_message(module.Message(**json.loads(request.data)))
            else:
                result = module.get_messages(unquote(path.removeprefix('/messages/')))
            response = io.BytesIO(result.model_dump_json().encode('utf-8'))
            response.status = 200
            return response

        with tempfile.TemporaryDirectory(dir=source.parents[1] / 'clients' / 'python') as directory:
            db = Database(Path(directory) / 'alice.sqlite3')
            try:
                with patch('api.urlopen', side_effect=transport):
                    api = API()
                    service = SyncService(db, api)
                    service.identify('Alice')
                    message = service.create('Bob', 'Héllo 世界')
                    self.assertEqual(service.sync(), [])
                    api.send(message)
                    self.assertEqual(api.receive('Bob'), [message])
                    self.assertEqual(len(module.messages_by_id), 1)
                    self.assertEqual(db.get(message.message_id)['delivery_state'], 'SENT')
            finally:
                db.close()
