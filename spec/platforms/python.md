# Python Client Platform Specification

## 1. Purpose

This document defines Python-specific implementation requirements for the
generated messaging client.

The common messaging behavior is defined by:

- `spec/protocol.md`
- `spec/behavior.md`
- `spec/storage.md`

Those specifications are authoritative.

This document defines HOW the common requirements should be implemented by the
Python client.

---

## 2. Technology Stack

The generated Python client MUST use:

```text
Language: Python 3
Interface: Command-line interface (CLI)
Networking: General-purpose HTTP library
Persistence: SQLite
Serialization: JSON
```

The implementation MUST NOT use a messaging or chat SDK.

The client MUST run locally without cloud services.

---

## 3. Generated Project Structure

The generated Python client SHOULD have a structure similar to:

```text
clients/python/
├── client.py
├── api.py
├── database.py
├── models.py
├── sync.py
├── requirements.txt
└── tests/
    ├── test_database.py
    └── test_sync.py
```

The exact structure MAY differ if responsibilities remain clearly separated.

---

## 4. Server Configuration

The Python client SHOULD connect to:

```text
http://localhost:8000
```

The server base URL SHOULD be configurable.

The client MUST use the endpoints defined in `spec/protocol.md`:

```text
POST /users/register
POST /messages
GET /messages/{username}
```

---

## 5. User Identity

On first launch, when no stored identity exists, the client MUST ask the user
for a name.

Example:

```text
Messaging Client

Enter your name: Alice
```

The client MUST reject a blank name.

When online, the client MUST register the name with the server.

After successful registration, the name MUST be persisted locally.

On future launches, the client MUST reuse the stored name.

---

## 6. SQLite Persistence

SQLite MUST be used for persistent message storage.

The client MUST persist:

```text
message_id
sender
recipient
text
created_at
delivery_state
```

`message_id` MUST be unique.

A conceptual table is:

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivery_state TEXT NOT NULL
);
```

The exact schema MAY differ if it preserves the same behavior.

User identity MUST also be stored persistently.

---

## 7. Delivery States

Outgoing messages MUST support:

```text
PENDING
SENDING
SENT
```

The state transitions MUST follow the common specification.

Successful delivery:

```text
PENDING
   |
   v
SENDING
   |
   v
SENT
```

Failed delivery:

```text
SENDING
   |
   v
PENDING
```

---

## 8. CLI Commands

The client SHOULD provide simple commands that allow the required scenario to
be reproduced.

At minimum, the interface MUST support behavior equivalent to:

```text
send <recipient> <message>
messages <user>
offline
online
sync
status
quit
```

Example:

```text
> send Bob Hi Bob
Message sent.
```

While offline:

```text
> send Bob This message is queued
Message queued locally.
```

The exact command syntax MAY differ if the required behavior remains easy to
demonstrate.

---

## 9. Sending Messages

When the user sends a valid message, the client MUST:

1. Generate a UUID.
2. Set the sender to the stored local user.
3. Set the recipient.
4. Set the message text.
5. Generate a UTC ISO-8601 timestamp.
6. Persist the message in SQLite as `PENDING`.
7. Attempt delivery if online.

The message MUST be persisted before successful network delivery is assumed.

---

## 10. Offline Mode

The CLI MUST provide an explicit offline mode.

Example:

```text
> offline

Offline mode enabled.
```

While offline:

- network requests MUST NOT be attempted;
- stored messages MUST remain accessible;
- new messages MUST be accepted;
- new outgoing messages MUST be stored as `PENDING`.

Example:

```text
> send Alice I am replying while offline

Message queued locally.
```

---

## 11. Returning Online

The CLI MUST allow offline mode to be disabled.

Example:

```text
> online

Online mode enabled.
Synchronizing...
```

When returning online, the client MUST:

1. Find pending outgoing messages.
2. Attempt to deliver them.
3. Update successfully acknowledged messages to `SENT`.
4. Preserve failed messages as `PENDING`.
5. Retrieve incoming messages.
6. Store newly received messages.

---

## 12. Queue Flushing

The synchronization component MUST query SQLite for retryable messages.

Conceptually:

```text
SELECT messages
WHERE delivery_state = PENDING
ORDER BY created_at
```

Each message MUST be retried using its existing:

```text
message_id
sender
recipient
text
created_at
```

Those values MUST NOT be regenerated.

---

## 13. Receiving Messages

The client MUST retrieve incoming messages using:

```text
GET /messages/{username}
```

Each received message MUST be stored in SQLite.

Before insertion, the client MUST check for an existing `message_id`.

Duplicate messages MUST NOT create duplicate database records.

---

## 14. Synchronization

The Python client SHOULD expose synchronization as a reusable component rather
than placing all synchronization logic directly inside the CLI loop.

Conceptually:

```text
CLI
 |
 v
Sync Service
 |        \
 v         v
SQLite    HTTP API
```

This separation makes the generated client easier to test.

---

## 15. Application Restart

The following MUST survive restarting the Python process:

```text
user identity
messages
message IDs
timestamps
delivery states
pending queue
```

If the process stops while a message is `SENDING`, that message MUST be
considered retryable on the next launch.

The original `message_id` MUST be reused.

---

## 16. Conversation Display

The CLI MUST provide a way to display messages exchanged with another user.

Example:

```text
> messages Bob

Conversation with Bob

Me: Hi Bob
    SENT

Bob: What is it?

Me: I will tell you later
    PENDING
```

Exact formatting is platform-specific.

---

## 17. Status

The CLI SHOULD provide a status command.

Example:

```text
> status

User: Alice
Network mode: OFFLINE
Pending messages: 1
```

This makes the offline/reconnection behavior easier to demonstrate and test.

---

## 18. Error Handling

Network failures MUST NOT terminate the application unexpectedly.

If the server is unavailable:

```text
Message queued - server unavailable.
```

The corresponding message MUST remain `PENDING`.

The user MUST NOT need to recreate the message.

---

## 19. Testing Requirements

The generated Python client SHOULD contain automated tests.

Tests SHOULD cover:

```text
message persistence
pending queue behavior
successful delivery
failed delivery
retry behavior
duplicate prevention
restart recovery
```

The generator validation process SHOULD run:

```text
python -m pytest
```

All generated tests MUST pass before generation is considered successful.

---

## 20. Interoperability

The Python client MUST communicate successfully with the generated Android
client through the same local server.

For example:

```text
Android Alice
      |
      v
Local Server
      |
      v
Python Bob
```

and:

```text
Python Alice
      |
      v
Local Server
      |
      v
Android Bob
```

Both combinations MUST follow the behavior defined by the common
specifications.

---

## 21. Generated Code Boundary

Everything under:

```text
clients/python/
```

is generated client code.

It MUST be safe to delete this directory.

Running the generator MUST recreate the Python client from the specifications.

The authoritative behavior MUST remain outside the generated directory under:

```text
spec/
```

---

## 22. Simplicity

The Python client exists primarily to demonstrate:

```text
cross-language generation
protocol interoperability
offline persistence
queue synchronization
specification consistency
```

It SHOULD remain intentionally small.

It does NOT require:

```text
graphical UI
cloud infrastructure
authentication
WebSockets
push notifications
external messaging services
```

The simplest implementation satisfying the specification SHOULD be preferred.
