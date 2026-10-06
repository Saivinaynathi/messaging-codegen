from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="Local Messaging Server",
    description="Minimal in-memory server for the messaging code generator demo.",
    version="1.0.0",
)


class UserRegistration(BaseModel):
    name: str = Field(min_length=1)


class UserRegistrationResponse(BaseModel):
    name: str
    status: str


class Message(BaseModel):
    message_id: str
    sender: str
    recipient: str
    text: str
    created_at: str


class MessageAcceptedResponse(BaseModel):
    message_id: str
    status: str


class MessagesResponse(BaseModel):
    messages: List[Message]


# ---------------------------------------------------------------------------
# In-memory server state.
#
# Server persistence is intentionally out of scope. Restarting the server
# clears all registered users and messages.
# ---------------------------------------------------------------------------

users: set[str] = set()

# message_id -> Message
messages_by_id: Dict[str, Message] = {}

# Preserves first-acceptance order.
message_order: List[str] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/users/register", response_model=UserRegistrationResponse)
def register_user(request: UserRegistration) -> UserRegistrationResponse:
    name = request.name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="User name cannot be empty")

    # Registration is intentionally idempotent.
    users.add(name)

    return UserRegistrationResponse(
        name=name,
        status="registered",
    )


@app.post("/messages", response_model=MessageAcceptedResponse)
def send_message(message: Message) -> MessageAcceptedResponse:
    if not message.message_id.strip():
        raise HTTPException(status_code=400, detail="message_id cannot be empty")

    if not message.sender.strip():
        raise HTTPException(status_code=400, detail="sender cannot be empty")

    if not message.recipient.strip():
        raise HTTPException(status_code=400, detail="recipient cannot be empty")

    if not message.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    # Idempotency:
    # If this ID was already accepted, do not create another message.
    if message.message_id in messages_by_id:
        return MessageAcceptedResponse(
            message_id=message.message_id,
            status="accepted",
        )

    messages_by_id[message.message_id] = message
    message_order.append(message.message_id)

    return MessageAcceptedResponse(
        message_id=message.message_id,
        status="accepted",
    )


@app.get("/messages/{username}", response_model=MessagesResponse)
def get_messages(username: str) -> MessagesResponse:
    username = username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="username cannot be empty")

    result = [
        messages_by_id[message_id]
        for message_id in message_order
        if messages_by_id[message_id].recipient == username
    ]

    return MessagesResponse(messages=result)
