# Client Behavior Specification

## 1. Purpose

This document defines the observable behavior that every generated messaging
client MUST implement.

The protocol format and HTTP endpoints are defined in `protocol.md`.

This document focuses on client behavior, including:

- first launch;
- user identification;
- sending messages;
- receiving messages;
- offline operation;
- queue flushing;
- reconnection;
- duplicate prevention;
- application restart behavior.

All generated clients MUST provide equivalent behavior even when their
platform-specific implementations differ.

---

## 2. First Launch

When the client starts and no local user identity exists, it MUST display a
login or identification interface.

The user MUST be able to enter a display name.

The Continue/Login action MUST NOT proceed when the name is empty after
trimming whitespace.

Example:

```text
Enter your name: Alice
```

When the user continues while online:

1. Trim leading and trailing whitespace from the name.
2. Send `POST /users/register`.
3. Wait for a successful server response.
4. Persist the user name locally.
5. Enter the messaging interface.
6. Request incoming messages.

When the application starts again, the stored identity MUST be reused.

The user MUST NOT be required to enter the name again after a normal
application restart.

---

## 3. Messaging Interface

After identification, the client MUST provide a messaging interface.

At minimum, the user MUST be able to:

- see their current identity;
- specify a recipient;
- enter message text;
- send a message;
- view sent messages;
- view received messages;
- determine whether an outgoing message is pending or sent;
- enable and disable the reproducible offline mode.

The visual design MAY differ between platforms.

The behavior MUST remain equivalent.

---

## 4. Creating an Outgoing Message

When the user selects Send, the client MUST validate:

```text
recipient != empty
message text != empty
```

Both values MUST be checked after trimming whitespace.

If validation fails, the client MUST NOT create or submit a message.

If validation succeeds, the client MUST:

1. Generate a UUID for `message_id`.
2. Set `sender` to the locally identified user.
3. Set `recipient` to the selected recipient.
4. Store the validated text.
5. Generate a UTC ISO-8601 `created_at` timestamp.
6. Persist the message locally.
7. Set its delivery state to `PENDING`.
8. Display the message immediately.

The message MUST be persisted before network delivery is considered complete.

---

## 5. Sending While Online

If the client is online after creating the message, it SHOULD immediately
attempt delivery.

Before making the request:

```text
PENDING -> SENDING
```

The client sends the message using:

```text
POST /messages
```

If the server returns a successful response for the same `message_id`:

```text
SENDING -> SENT
```

The client MUST persist the new state.

If the request fails because of a timeout, connection error, or server error:

```text
SENDING -> PENDING
```

The message MUST remain stored locally.

The client MUST NOT create a replacement message with a different
`message_id`.

---

## 6. Sending While Offline

When explicit offline mode is enabled, the client MUST NOT attempt server
requests.

The user MUST still be able to create messages.

A newly created message MUST:

1. Receive a `message_id`.
2. Be persisted locally.
3. Have delivery state `PENDING`.
4. Appear immediately in the conversation.

Example:

```text
Alice -> Bob: Are you there?
Status: PENDING
```

The message MUST remain available after navigating away from the conversation
or restarting the client.

---

## 7. Entering Offline Mode

The client MUST provide a reproducible way to enter offline mode.

When offline mode is enabled:

```text
network operations = disabled
```

The client MUST NOT:

- register users with the server;
- send queued messages;
- poll for incoming messages.

Local functionality MUST remain available.

The user MUST still be able to:

- view locally stored messages;
- compose messages;
- queue messages.

The UI SHOULD make the offline state visible.

Example:

```text
OFFLINE
```

---

## 8. Reconnecting

When offline mode is disabled, the client transitions back to online mode.

The client MUST then:

1. Resume server communication.
2. Flush pending outgoing messages.
3. Retrieve incoming messages.

The client SHOULD perform queue flushing before or together with incoming
message synchronization.

---

## 9. Queue Flushing

The client MUST query local storage for messages with:

```text
delivery_state = PENDING
```

Pending messages SHOULD be processed in their local creation order.

For each pending message:

```text
PENDING
   |
   v
SENDING
```

The client MUST submit the original stored message.

The following fields MUST NOT be regenerated during retry:

```text
message_id
sender
recipient
text
created_at
```

If the server acknowledges the message:

```text
SENDING -> SENT
```

If delivery fails:

```text
SENDING -> PENDING
```

No failed message may be silently deleted.

---

## 10. Receiving Messages

While online, the client SHOULD periodically retrieve messages using:

```text
GET /messages/{username}
```

The client MUST also retrieve messages after reconnecting.

For every returned message, the client MUST check local storage using
`message_id`.

If the message does not exist locally:

```text
persist message
display message
```

If the message already exists:

```text
do not create another copy
```

This behavior MUST make repeated polling safe.

---

## 11. Duplicate Prevention

`message_id` is the canonical identifier for duplicate detection.

For example, if the server returns:

```text
message_id = abc-123
```

three times, local storage MUST still contain only one message with:

```text
message_id = abc-123
```

Duplicate prevention MUST work across application restarts because received
messages are stored persistently.

---

## 12. Application Restart

Local identity, messages, and outgoing delivery states MUST survive a normal
application restart.

For example, suppose Alice creates:

```text
Alice -> Bob: I will send this later.
```

while offline.

The message has:

```text
state = PENDING
```

Alice closes the application.

When Alice opens the application again, the client MUST still contain the
message with the same:

```text
message_id
sender
recipient
text
created_at
delivery state
```

If the client is online after restart, it SHOULD attempt to flush pending
messages.

---

## 13. Conversation Display

Messages MUST visually distinguish between messages sent by the local user and
messages received from another user.

For an outgoing message, the UI SHOULD expose its delivery state.

Example:

```text
Alice:
Hi Bob
SENT

Bob:
Hello Alice

Alice:
Can you see this?
PENDING
```

The exact visual design is platform-specific and is not part of the protocol.

---

## 14. Failure Behavior

Temporary network failures MUST NOT result in message loss.

For:

```text
connection refused
timeout
connection interrupted
HTTP 5xx
```

the outgoing message MUST remain available for retry.

The client MAY display an error.

Example:

```text
Message queued - server unavailable
```

The user MUST NOT be required to type the message again.

---

## 15. Required Alice/Bob Scenario

All generated clients MUST support this sequence.

### Initial state

```text
Alice = ONLINE
Bob   = ONLINE
```

Alice sends:

```text
Hi Bob, I have something important to tell you
```

Bob receives the message.

Bob sends:

```text
What is it?
```

Alice receives the message.

### Alice goes offline

```text
Alice = OFFLINE
Bob   = ONLINE
```

Alice sends:

```text
The important message was queued while I was offline.
```

Expected Alice state:

```text
message = PENDING
```

### Bob goes offline

```text
Alice = OFFLINE
Bob   = OFFLINE
```

Bob sends:

```text
I am replying while offline too.
```

Expected Bob state:

```text
message = PENDING
```

### Alice reconnects

```text
Alice = ONLINE
Bob   = OFFLINE
```

Alice MUST flush her pending message.

Expected:

```text
Alice queued message = SENT
```

The server now contains Alice's message for Bob.

### Alice goes offline again

```text
Alice = OFFLINE
Bob   = OFFLINE
```

### Bob reconnects

```text
Alice = OFFLINE
Bob   = ONLINE
```

Bob MUST:

1. Retrieve Alice's queued message.
2. Display Alice's message.
3. Flush his own queued message.

Expected:

```text
Alice message visible to Bob
Bob queued message = SENT
```

### Alice reconnects

```text
Alice = ONLINE
Bob   = ONLINE
```

Alice MUST retrieve Bob's queued message.

Final expected state:

```text
Alice has Bob's messages.
Bob has Alice's messages.

No duplicate messages exist.

No successfully queued messages were lost.

No pending message received a new message_id during retry.
```

---

## 16. Platform Independence

This specification describes behavior rather than implementation.

An Android client MAY implement these requirements using:

```text
Room
Coroutines
Flow
ViewModel
Retrofit
```

A Python client MAY use:

```text
SQLite
HTTP libraries
async or synchronous processing
```

Those implementation choices MUST NOT change externally observable messaging
behavior.

---

## 17. Prohibited Behavior

Generated clients MUST NOT:

- discard messages because the network is unavailable;
- generate a new `message_id` during retry;
- create duplicate received messages;
- require network connectivity to compose a message;
- treat a message as `SENT` before server acknowledgement;
- use a turnkey messaging/chat SDK;
- change protocol fields independently of `protocol.md`;
- silently invent protocol behavior that contradicts the specification.

When implementation details are not specified, the generated client SHOULD
choose the simplest implementation that preserves the required behavior.
