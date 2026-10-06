# Client Generation Task

You are generating one client implementation for a specification-driven
messaging system.

## Primary Goal

Generate a complete, runnable client that conforms to the supplied
specifications.

The specification is authoritative.

Do not modify or reinterpret requirements simply because another
implementation would be easier.

---

## Generated Code Boundary

You may create and modify files ONLY inside:

```text
{{OUTPUT_DIRECTORY}}
```

Do not modify:

```text
spec/
server/
generator/
tests/
AGENTS.md
DESIGN.md
README.md
FUTURE.md
```

The output directory represents generated code and may be deleted before a
future regeneration.

---

## Platform

Generate the following platform:

```text
{{PLATFORM}}
```

The platform-specific specification is included below.

---

## Core Requirements

The generated client MUST implement:

1. Persistent user identity.
2. Text messaging between named users.
3. Client-generated message UUIDs.
4. Persistent local message storage.
5. Persistent offline outgoing queue.
6. Delivery states:
   - PENDING
   - SENDING
   - SENT
7. Retry using the original message ID.
8. Incoming message retrieval.
9. Duplicate prevention using `message_id`.
10. Explicit offline mode.
11. Queue flushing after reconnect.
12. Persistence across normal application restarts.
13. Communication with the local reference server.
14. Automated tests appropriate for the platform.

---

## Critical Offline Rule

The client MUST persist an outgoing message locally BEFORE successful network
delivery is assumed.

If the client is offline:

```text
create message
      |
      v
persist PENDING
      |
      v
display locally
```

When reconnecting:

```text
load PENDING
      |
      v
mark SENDING
      |
      v
send original message
      |
      +---- success ----> SENT
      |
      +---- failure ----> PENDING
```

Retries MUST reuse the original:

```text
message_id
sender
recipient
text
created_at
```

---

## Idempotency

Never generate a replacement `message_id` when retrying a stored message.

The reference server performs idempotency using `message_id`.

Generated clients must rely on that behavior to safely retry uncertain
deliveries.

---

## Implementation Quality

Prefer:

```text
simple
readable
idiomatic
testable
small
```

Avoid unnecessary production complexity.

Do not use turnkey messaging or chat SDKs.

General-purpose HTTP, JSON, persistence, UI, and testing libraries are
allowed.

---

## Validation

After generating the implementation:

1. Inspect the generated files.
2. Run the platform-appropriate tests.
3. Run the platform-appropriate build when available.
4. Repair errors caused by generated code.
5. Repeat validation until successful or until a genuine environment
   limitation prevents further validation.

Do NOT change the specification to make tests pass.

---

# COMMON PROTOCOL SPECIFICATION

{{PROTOCOL_SPEC}}

---

# COMMON CLIENT BEHAVIOR SPECIFICATION

{{BEHAVIOR_SPEC}}

---

# COMMON STORAGE SPECIFICATION

{{STORAGE_SPEC}}

---

# PLATFORM-SPECIFIC SPECIFICATION

{{PLATFORM_SPEC}}

---

# Final Instructions

Generate the complete client under:

```text
{{OUTPUT_DIRECTORY}}
```

Do not merely describe what should be generated.

Create the actual project files.

After generation, validate the implementation.

At completion, report:

```text
files created
tests executed
build commands executed
validation result
any environment limitations
```
