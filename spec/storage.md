# Local Storage Specification

## 1. Purpose

This document defines the persistent local data requirements for generated
messaging clients.

The goal is to ensure that all generated clients provide equivalent offline,
retry, deduplication, and restart behavior regardless of the storage technology
used by a particular platform.

The exact database implementation is platform-specific.

---

## 2. Required Persistent Data

Every generated client MUST persist:

1. The local user's identity.
2. Sent messages.
3. Received messages.
4. Outgoing message delivery state.

This information MUST survive a normal application restart.

---

## 3. User Identity Storage

The client MUST persist the user's registered display name.

Conceptual model:

```text
UserIdentity
------------
name
```

Example:

```text
name = Alice
```

After the identity has been stored, subsequent launches MUST reuse it.

The implementation MAY use any appropriate platform-specific persistent
storage mechanism.

---

## 4. Message Storage

Every locally stored message MUST contain at least:

```text
message_id
sender
recipient
text
created_at
delivery_state
```

Conceptual model:

```text
Message
--------------------------
message_id       string
sender           string
recipient        string
text             string
created_at       timestamp
delivery_state   state
```

`message_id` MUST uniquely identify a message in local storage.

The storage implementation MUST prevent multiple local records representing
the same `message_id`.

---

## 5. Delivery States

Outgoing messages MUST support these states:

```text
PENDING
SENDING
SENT
```

### PENDING

The message exists locally but has not been acknowledged by the server.

### SENDING

The client is currently attempting delivery.

### SENT

The server acknowledged the message.

Received messages do not require an outgoing delivery lifecycle.

A platform MAY represent received messages using a separate type or an
additional state as long as externally observable behavior remains equivalent.

---

## 6. Persist Before Sending

When a user creates a valid outgoing message, the client MUST persist it before
network delivery is considered complete.

Required order:

```text
User presses Send
        |
        v
Validate input
        |
        v
Generate message_id
        |
        v
Generate created_at
        |
        v
Persist message as PENDING
        |
        v
Display locally
        |
        v
Attempt network delivery
```

A client MUST NOT depend on successful network communication before storing the
message.

This rule ensures that a network failure cannot cause the newly created
message to disappear.

---

## 7. Pending Queue

The outgoing queue consists of locally stored outgoing messages whose
`delivery_state` is:

```text
PENDING
```

The queue MUST be derived from persistent local storage.

It MUST NOT exist only in application memory.

Therefore, pending messages MUST survive application restart.

Pending messages SHOULD be returned in creation order when the client prepares
to flush the queue.

---

## 8. Sending State

Before attempting a network request for a pending message, the client MAY
persist:

```text
delivery_state = SENDING
```

After successful server acknowledgement:

```text
delivery_state = SENT
```

After a failed delivery attempt:

```text
delivery_state = PENDING
```

The stored message contents MUST NOT change during these transitions.

In particular, the following values MUST remain unchanged:

```text
message_id
sender
recipient
text
created_at
```

---

## 9. Crash Recovery

A client may terminate while a message is in:

```text
SENDING
```

Because `SENDING` does not prove that the server accepted the message, clients
MUST treat persisted `SENDING` messages as retryable after application restart.

During startup, a generated client MUST either:

```text
SENDING -> PENDING
```

or include both `PENDING` and stale `SENDING` messages in its retry operation.

The original `message_id` MUST be reused.

Server idempotency makes this retry safe.

---

## 10. Received Message Storage

Messages retrieved from the server MUST be persisted locally.

Before inserting a received message, the client MUST check whether its
`message_id` already exists.

Conceptually:

```text
if message_id does not exist:
    insert message
else:
    ignore duplicate
```

Repeated server polling MUST NOT create duplicate local records.

---

## 11. Sent Message and Received Copy

A client MAY receive from the server a message that already exists locally.

For example, Alice may send a message and later retrieve server data that
contains the same `message_id`.

The client MUST recognize the existing message using `message_id`.

It MUST NOT insert a second copy.

---

## 12. Conversation Query

A conversation between the local user and another user consists of messages
where:

```text
(sender = local_user AND recipient = other_user)

OR

(sender = other_user AND recipient = local_user)
```

The client MUST be able to retrieve these messages from local storage for
display.

Conversation display MUST NOT depend on continuous server connectivity.

---

## 13. Local Ordering

Messages SHOULD be stored with enough information to provide deterministic
conversation ordering.

The protocol-defined `created_at` value MUST be persisted.

Implementations MAY also persist platform-specific metadata when required.

Platform-specific metadata MUST NOT change the protocol fields.

---

## 14. Offline Mode

When explicit offline mode is enabled:

```text
network communication = disabled
```

Local database operations MUST continue normally.

The user MUST still be able to:

```text
read stored messages
create messages
persist messages
query conversations
```

New outgoing messages MUST be stored as:

```text
PENDING
```

---

## 15. Reconnection

When the client returns online, it MUST query persistent storage for retryable
outgoing messages.

Conceptually:

```text
pendingMessages = storage.getPendingMessages()
```

For each pending message:

```text
attempt delivery
```

Successful delivery:

```text
PENDING -> SENDING -> SENT
```

Failed delivery:

```text
PENDING -> SENDING -> PENDING
```

No message may be deleted merely because delivery failed.

---

## 16. Application Restart

The following information MUST survive normal application restart:

```text
user identity
sent messages
received messages
pending messages
delivery states
message identifiers
timestamps
```

Example:

Alice is offline and creates:

```text
message_id = 123
sender = Alice
recipient = Bob
text = Hello Bob
delivery_state = PENDING
```

Alice closes the application.

After reopening it, the client MUST still contain:

```text
message_id = 123
sender = Alice
recipient = Bob
text = Hello Bob
delivery_state = PENDING
```

The client MUST NOT generate a replacement identifier.

---

## 17. Platform-Specific Storage

Different clients MAY use different persistence technologies.

### Android

The Android client SHOULD use:

```text
Room
```

Suggested conceptual components:

```text
MessageEntity
MessageDao
AppDatabase
UserPreferences
```

Room SHOULD enforce uniqueness for:

```text
message_id
```

### Python

The Python client SHOULD use:

```text
SQLite
```

or another local persistent database available without an external service.

The Python implementation MUST enforce the same uniqueness and persistence
semantics.

---

## 18. Storage Boundary

The specification defines WHAT must be persisted.

Platform implementations determine HOW it is persisted.

For example:

```text
Android
    Room database

Python
    SQLite database
```

Both implementations MUST still satisfy:

```text
same message identifiers
same message data
same delivery-state behavior
same retry behavior
same duplicate prevention
same restart behavior
```

---

## 19. Data Integrity Requirements

Generated clients MUST NOT:

- delete pending messages after a network failure;
- generate replacement IDs during retries;
- create duplicate records for the same `message_id`;
- keep the outgoing queue only in memory;
- lose the user's identity after normal restart;
- mark a message `SENT` without server acknowledgement.

Local persistence is part of the required messaging behavior and is not merely
an implementation optimization.
