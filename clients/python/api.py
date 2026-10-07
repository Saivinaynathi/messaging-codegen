"""Protocol HTTP transport using the Python standard library."""
import http.client
import json
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from models import Message


class APIError(Exception):
    pass


class API:
    def __init__(self, base_url="http://localhost:8000", timeout=5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(self.base_url + path, data=data,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise APIError(f"Unexpected HTTP status {response.status}")
                return json.load(response)
        except (URLError, OSError, http.client.HTTPException, ValueError) as error:
            raise APIError(str(error)) from error

    def register(self, name):
        response = self.request("/users/register", {"name": name})
        if not isinstance(response, dict) or response.get("name") != name or response.get("status") != "registered":
            raise APIError("Invalid registration acknowledgement")

    def send(self, message):
        response = self.request("/messages", message.payload())
        if not isinstance(response, dict) or response.get("message_id") != message.message_id or response.get("status") != "accepted":
            raise APIError("Invalid message acknowledgement")

    def receive(self, name):
        response = self.request("/messages/" + quote(name, safe=""))
        try:
            messages = response["messages"]
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            result = [Message.from_payload(row) for row in messages]
            if any(message.recipient != name for message in result):
                raise ValueError("Message addressed to another user")
            return result
        except (TypeError, KeyError, ValueError) as error:
            raise APIError(f"Invalid incoming response: {error}") from error
