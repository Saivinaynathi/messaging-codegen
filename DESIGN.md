# Design

## 1. Goal

This project demonstrates a specification-driven code generator that uses an
agentic coding tool to generate interoperable messaging clients in different
programming languages.

The messaging application is intentionally small. The primary deliverable is
the reusable generation harness and the specification that drives it.

The core guarantee is:

> If the generated client code is deleted, the generator can recreate working
> clients whose behavior conforms to the specification.

## 2. Design Principles

### Specification Is the Source of Truth

Messaging behavior is defined in the files under `spec/`.

Generated clients must implement the specification rather than inventing
platform-specific protocol behavior.

Questions about message delivery, offline behavior, retries, identifiers, or
synchronization should be answerable from the specification without reading
the generated client source code.

### Separate Protocol From Platform

The common specification defines behavior shared by every client, including:

- user identity
- message format
- sending and receiving
- offline queueing
- reconnection
- retries
- duplicate prevention

Platform profiles define implementation-specific choices without changing
protocol semantics.

For example:

- Android: Kotlin, Jetpack Compose, Room, Retrofit, Coroutines/Flow
- Python: Python standard/general-purpose HTTP and local storage libraries

Both clients must exhibit the same externally observable behavior.

### Offline First

Sending a message does not depend on immediate network availability.

A client creates a stable message identifier and stores the outgoing message
locally before attempting network delivery.

If delivery fails or the client is offline, the message remains pending and
is retried after connectivity returns.

### Idempotent Delivery

Every message has a client-generated unique `message_id`.

Retries reuse the same identifier.

The server treats repeated submissions of the same `message_id` as the same
message. This prevents duplicate delivery when a client cannot determine
whether a previous network request succeeded.

### Generated Code Has an Explicit Boundary

The following directories are generated:

- `clients/android/`
- `clients/python/`

The specification, generator, server, tests, and project documentation are
maintained outside that generation boundary.

Generated client directories should be safe to delete and recreate.

## 3. Architecture

The system is divided into five layers:

    Specification
         |
         v
    Agentic Generator
         |
         v
    Platform Profiles
         |
         v
    Generated Clients
         |
         v
    Conformance Validation

The generated Android and Python clients communicate with the same local
messaging server.

    Android Client ----\
                        \
                         >---- Local Messaging Server
                        /
    Python Client -----/

The server is intentionally simple because server architecture is not the
focus of this exercise.

## 4. Generator Design

The generator combines:

1. Common protocol specification
2. Behavioral requirements
3. Storage/offline requirements
4. Platform-specific profile
5. Agent instructions

These inputs are provided to the selected agentic coding tool.

Generation is followed by platform validation such as compilation and tests.

The intended workflow is:

    Spec
      |
      v
    Generate
      |
      v
    Build
      |
      v
    Test
      |
      +---- failure ---> repair/retry
      |
      v
    Valid Client

## 5. Messaging Model

A message contains at minimum:

- `message_id`
- `sender`
- `recipient`
- `text`
- `created_at`

The identifier is created by the sending client before the message is placed
in the local outgoing queue.

A simplified outgoing lifecycle is:

    PENDING
       |
       v
    SENDING
       |
       v
    SENT

If transmission fails:

    SENDING -> PENDING

The detailed semantics are defined by the specification rather than this
design document.

## 6. Technology Choices

### Android Client

The Android implementation uses:

- Kotlin
- Jetpack Compose
- MVVM / Clean Architecture
- Coroutines and Flow
- Room
- Retrofit / OkHttp
- Hilt

These technologies provide explicit networking, persistence, and state
management without relying on a messaging SDK.

### Second Client

The second client is implemented in Python.

Using Python provides a clearly independent implementation that cannot share
application source code with the Kotlin Android client.

### Server

The server is a small local Python HTTP service with in-memory state.

It intentionally avoids production concerns such as authentication,
persistent databases, cloud infrastructure, and distributed scaling.

## 7. Testing Strategy

Quality is evaluated at multiple levels:

- protocol/model tests
- offline queue tests
- retry/idempotency tests
- platform build/tests
- cross-client scenario testing
- full regeneration testing

The final regeneration test deletes generated client code, runs the generator,
builds the clients again, and executes the validation workflow.

## 8. Evolution

The harness is designed around specifications rather than this particular
messaging feature set.

Future specifications could introduce features such as:

- delivery/read receipts
- reactions
- attachments
- group conversations
- message editing
- alternative transports

These features should be introduced by extending the specification and
platform requirements rather than rewriting the generator around a single
hard-coded messaging application.
