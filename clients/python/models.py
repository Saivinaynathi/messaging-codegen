"""Immutable protocol messages; delivery state belongs to local storage."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


def nonblank(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} must not be blank")
    return value


@dataclass(frozen=True)
class Message:
    message_id: str
    sender: str
    recipient: str
    text: str
    created_at: str

    @classmethod
    def create(cls, sender, recipient, text):
        recipient = nonblank(recipient, "Recipient")
        text = nonblank(text, "Message text")
        return cls(str(uuid4()), sender, recipient, text,
                   datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def payload(self):
        return asdict(self)

    @classmethod
    def from_payload(cls, row):
        """Validate wire data without changing the original protocol fields."""
        message = cls(**{key: row[key] for key in cls.__dataclass_fields__})
        for key, value in message.payload().items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid {key}")
        UUID(message.message_id)
        timestamp = datetime.fromisoformat(message.created_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("created_at must be UTC")
        return message
