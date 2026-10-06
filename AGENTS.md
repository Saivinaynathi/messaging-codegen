# AGENTS.md

## Project Purpose

This repository is a specification-driven code generation system.

The primary deliverable is NOT the example messaging application itself.

The primary deliverable is the generator workflow that uses an agentic coding
tool to transform platform-independent specifications into working client
implementations.

The messaging application is the reference workload used to demonstrate that
the generator can produce interoperable clients in different languages.

---

## Source of Truth

The authoritative requirements are located under:

```text
spec/
```

The specification is intentionally separated into:

```text
spec/protocol.md
spec/behavior.md
spec/storage.md
spec/platforms/android.md
spec/platforms/python.md
```

Generated implementations MUST conform to these files.

When generated code and the specification disagree, the specification wins.

Do not silently change the specification to make generated code easier to
implement.

---

## Repository Boundaries

The repository contains both hand-written and generated code.

### Hand-written

The following areas are maintained manually:

```text
README.md
DESIGN.md
FUTURE.md
AGENTS.md
spec/
generator/
server/
tests/
```

These files define the system, generator, validation, and reference server.

### Generated

The following directories contain generated client implementations:

```text
clients/android/
clients/python/
```

These directories MAY be deleted and recreated by the generator.

Do not place authoritative protocol requirements only inside generated code.

---

## Core Generation Requirement

The generator MUST be capable of recreating:

```text
clients/android/
clients/python/
```

from the specification.

A successful regeneration workflow should conceptually be:

```text
specification
     |
     v
generator harness
     |
     v
agentic coding tool
     |
     +------------------+
     |                  |
     v                  v
Android client      Python client
     |                  |
     +--------+---------+
              |
              v
       validation/tests
```

The generated clients MUST NOT share source code.

They communicate only through the protocol defined under `spec/`.

---

## Agent Responsibilities

When generating a client, the agent MUST:

1. Read the common specifications.
2. Read the requested platform specification.
3. Treat the specification as authoritative.
4. Generate code only within the requested generated client directory.
5. Implement local persistence.
6. Implement offline queueing.
7. Implement retry behavior.
8. Preserve `message_id` during retries.
9. Implement duplicate prevention.
10. Implement explicit offline mode.
11. Implement synchronization after reconnecting.
12. Add appropriate automated tests.
13. Build or test the generated implementation.
14. Repair generation errors when possible without changing the specification.

---

## Protocol Requirements

All generated clients MUST use the protocol defined by:

```text
spec/protocol.md
```

Important properties include:

```text
client-generated message UUID
idempotent message submission
persistent outgoing queue
PENDING -> SENDING -> SENT
failed SENDING -> PENDING
duplicate prevention using message_id
HTTP-based local server communication
```

Do not invent incompatible endpoints or JSON fields.

---

## Android Generation

When generating:

```text
clients/android/
```

read:

```text
spec/protocol.md
spec/behavior.md
spec/storage.md
spec/platforms/android.md
```

The implementation should follow the Android platform profile, including:

```text
Kotlin
Jetpack Compose
MVVM / Clean Architecture
Coroutines
Flow / StateFlow
Room
Retrofit
OkHttp
Hilt
Gradle
```

The Android client MUST remain independent from the Python client.

---

## Python Generation

When generating:

```text
clients/python/
```

read:

```text
spec/protocol.md
spec/behavior.md
spec/storage.md
spec/platforms/python.md
```

The implementation should follow the Python platform profile, including:

```text
Python 3
CLI
SQLite
HTTP
JSON
```

The Python client MUST remain independent from the Android client.

---

## Server

The local reference server is located under:

```text
server/
```

The server is hand-written infrastructure.

Do NOT rewrite the server merely to accommodate incorrect generated client
behavior.

Generated clients must conform to the server protocol because both are based on
the authoritative specification.

---

## Offline Behavior

Offline behavior is a required feature, not an optional enhancement.

A generated client MUST allow the user to create a message while offline.

The message MUST be persisted locally with:

```text
PENDING
```

When the client reconnects, it MUST retry the original message using the same:

```text
message_id
sender
recipient
text
created_at
```

Only server acknowledgement may transition the message to:

```text
SENT
```

---

## Idempotency

Retries MUST NOT generate new message identifiers.

If network delivery has an uncertain outcome, retry the same message with the
same `message_id`.

The server is responsible for treating repeated submissions of an already
accepted `message_id` as the same logical message.

---

## Generated Code Quality

Generated code should be:

```text
readable
small
testable
idiomatic for its platform
appropriately separated by responsibility
```

Avoid unnecessary abstractions.

Avoid production infrastructure that is unrelated to the take-home
requirements.

Prefer the simplest implementation that fully satisfies the specification.

---

## Validation

Generation is not complete merely because files were created.

The generated implementation MUST be validated.

### Python

Prefer running:

```text
python -m pytest
```

### Android

Prefer running:

```text
./gradlew test
./gradlew assembleDebug
```

If validation fails because of generated code, repair the generated
implementation.

Do not modify the specification simply to make failing generated code pass.

---

## Cross-Client Interoperability

The final generated clients MUST support communication such as:

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

Both clients MUST implement equivalent externally observable behavior.

---

## Required Demonstration Scenario

Generated clients MUST support the Alice/Bob scenario defined in:

```text
spec/protocol.md
spec/behavior.md
```

This includes:

```text
online messaging
Alice offline queue
Bob offline queue
Alice reconnect
Bob reconnect
queue flushing
message retrieval
duplicate prevention
```

---

## Modification Rules

When working as the generation agent:

DO:

```text
read the specification first
keep changes inside the requested generated directory
run relevant tests
repair generated implementation errors
keep implementations simple
```

DO NOT:

```text
change protocol requirements without explicit instruction
modify the hand-written server to hide client bugs
share implementation source between generated clients
use turnkey messaging SDKs
remove offline persistence
replace retries with new message IDs
mark messages SENT before acknowledgement
```

---

## Evolution

The architecture should make future specification changes possible.

Examples include:

```text
reactions
attachments
group conversations
message editing
read receipts
```

When the specification evolves, the preferred workflow is:

```text
change specification
        |
        v
regenerate clients
        |
        v
run validation
```

rather than manually implementing the feature independently in every client.

---

## Final Principle

The key property of this repository is:

> The specification describes the behavior, the generator interprets the
> specification, and generated clients implement that behavior.

Generated applications are evidence that the generation system works.

They are not the source of truth.
