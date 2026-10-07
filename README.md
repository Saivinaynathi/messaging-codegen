# Specification-Driven Messaging Code Generator

A specification-first code generation project that uses an agentic coding tool (Codex) to generate interoperable messaging clients in two different programming languages.

The primary deliverable is the **code generator**, not the messaging application itself. The messaging application demonstrates that the generator can produce clients that follow the same protocol and behavioral requirements.

## 1. Project Overview

The system includes:

- **Android client:** Kotlin, Jetpack Compose, Room, Retrofit, Coroutines, and Hilt.
- **Python client:** Command-line application using HTTP and SQLite.
- **Local server:** Python-based messaging server.
- **Generator:** Python orchestration script that assembles specifications and invokes Codex.
- **Specifications:** Platform-independent protocol, behavior, and storage requirements, plus platform-specific implementation profiles.

The Android and Python clients are independently generated. They do not share implementation source code.

## 2. Repository Structure

```text
messaging-codegen/
├── AGENTS.md
├── DESIGN.md
├── FUTURE.md
├── README.md
├── REGENERATION.md
├── spec/
│   ├── protocol.md
│   ├── behavior.md
│   ├── storage.md
│   └── platforms/
├── generator/
│   ├── generate.py
│   └── prompts/
├── server/
│   ├── app.py
│   └── requirements.txt
├── clients/
│   ├── android/
│   └── python/
└── tests/
```

## 3. Generated vs. Handwritten Code

**Handwritten / maintained infrastructure:**

- `spec/` — authoritative requirements
- `generator/` — generation orchestration and prompt templates
- `server/` — local reference messaging server
- `tests/` — shared validation infrastructure
- `AGENTS.md`, `DESIGN.md`, `README.md`, `REGENERATION.md`, `FUTURE.md` — project documentation

**Generated client implementations:**

- `clients/android/` — Android messaging application
- `clients/python/` — Python messaging application

The generator produces client implementations from the specifications. Client-specific implementation details may differ, but externally observable messaging behavior must remain consistent.

## 4. Messaging Protocol

The server exposes three main endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/users/register` | Register a user |
| POST | `/messages` | Send a message |
| GET | `/messages/{username}` | Retrieve messages |

Each message contains:

- `message_id`
- `sender`
- `recipient`
- `text`
- `created_at`

Messages use stable client-generated identifiers to support idempotent retries.

See `spec/protocol.md` for the authoritative protocol.

## 5. Run the Server

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r server/requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

The server runs at:

```text
http://localhost:8000
```

Leave the server terminal running while testing clients.

## 6. Run the Python Client

Open a second terminal and navigate to the repository root.

Install dependencies:

```bash
source .venv/bin/activate
python -m pip install -r clients/python/requirements.txt
```

Start the client:

```bash
python3 clients/python/client.py --db clients/python/alice.sqlite3
```

Enter a user name when prompted.

The client supports messaging commands, explicit offline/online mode, synchronization, and local message storage.

For client-specific commands, see `clients/python/README.md`.

## 7. Run the Android Client

Open the Android project:

```text
clients/android/
```

Use Android Studio with an Android emulator.

The Android emulator can access the host machine's local server using:

```text
http://10.0.2.2:8000
```

To build from the terminal:

```bash
cd clients/android
./gradlew assembleDebug
```

To install on a running emulator:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The Android application supports user identification, messaging, local persistence, and offline synchronization.

## 8. Generate Clients Using Codex

The generator is implemented in:

```text
generator/generate.py
```

The agent instructions are defined in:

```text
AGENTS.md
```

The generation prompt template is located in:

```text
generator/prompts/generate_client.md
```

The generator reads the authoritative specifications and the selected platform profile, assembles the generation prompt, and invokes Codex to create or regenerate a client.

From the repository root:

**Preview Python generation:**

```bash
python3 generator/generate.py python --dry-run
```

**Preview Android generation:**

```bash
python3 generator/generate.py android --dry-run
```

**Generate Python:**

```bash
python3 generator/generate.py python
```

**Generate Android:**

```bash
python3 generator/generate.py android
```

Codex must be installed and configured for actual generation.

Generation should be performed in a clean Git worktree so that output changes can be inspected before being accepted.

## 9. Offline Messaging

Both clients implement the same offline-first requirements:

1. Create a message with a stable unique identifier.
2. Save the message locally before network delivery.
3. Keep the message in `PENDING` state while offline.
4. Attempt delivery after reconnecting.
5. Change its state to `SENT` after successful server acknowledgement.
6. Retrieve incoming messages and deduplicate them by `message_id`.

The server uses message identifiers to prevent duplicate acceptance when a client retries a request.

## 10. Interoperability Scenario

The required scenario uses Alice and Bob:

1. Alice and Bob register with the server.
2. Alice sends Bob a message.
3. Bob replies to Alice.
4. Alice goes offline and queues another message.
5. Bob goes offline and queues another message.
6. Alice reconnects and sends her pending message.
7. Alice disconnects again.
8. Bob reconnects, receives Alice's message, and sends his pending message.
9. Alice reconnects and receives Bob's message.

The expected result is that both users receive their messages without duplicates or lost pending messages.

See `spec/behavior.md` for detailed requirements.

## 11. Testing

**Python tests:**

```bash
python -m pytest clients/python/tests -v
```

**Android tests:**

```bash
cd clients/android
./gradlew testDebugUnitTest
```

**Android debug build:**

```bash
./gradlew assembleDebug
```

Testing should cover offline queues, retries, message identifiers, duplicate handling, persistence, and interoperability.

## 12. Regeneration Validation

Client regeneration was tested in isolated Git worktrees.

The Python client was regenerated and its automated tests passed.

The Android client was regenerated, its unit tests passed, and a debug APK was built after selecting a compatible Java version.

See `REGENERATION.md` for validation details.

## 13. Design and Future Extensions

- `DESIGN.md` — system architecture and design decisions
- `AGENTS.md` — agentic coding instructions
- `REGENERATION.md` — regeneration testing and evidence
- `FUTURE.md` — possible extensions and improvements

Future client functionality should originate from specification changes rather than independent manual changes to generated implementations.
