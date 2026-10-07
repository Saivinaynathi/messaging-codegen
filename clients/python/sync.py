"""Reusable synchronization; explicit offline mode guards every network path."""
from api import APIError
from models import Message, nonblank


class SyncService:
    def __init__(self, database, api, offline=False):
        self.database = database
        self.api = api
        self.offline = offline
        self.received = []

    def identify(self, name):
        if self.offline:
            raise ValueError("First-time registration requires online mode")
        name = nonblank(name, "Name")
        self.api.register(name)
        self.database.set_user(name)
        return self.sync()

    def create(self, recipient, text):
        if not self.database.user:
            raise ValueError("Register before creating messages")
        message = Message.create(self.database.user, recipient, text)
        self.database.insert(message, "PENDING")
        return message

    def set_offline(self, offline):
        self.offline = offline
        return [] if offline else self.sync()

    def sync(self):
        errors = []
        self.received = []
        if self.offline or not self.database.user:
            return errors
        for message in self.database.pending():
            self.database.state(message.message_id, "SENDING")
            try:
                self.api.send(message)
            except APIError as error:
                self.database.state(message.message_id, "PENDING")
                errors.append(str(error))
            else:
                self.database.state(message.message_id, "SENT")
        try:
            for message in self.api.receive(self.database.user):
                if self.database.insert(message, "RECEIVED"):
                    self.received.append(message)
        except APIError as error:
            errors.append(str(error))
        return errors
