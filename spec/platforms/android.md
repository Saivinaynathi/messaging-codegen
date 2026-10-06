# Android Platform Specification

## 1. Purpose

This document defines Android-specific implementation requirements for the
generated messaging client.

The common messaging behavior is defined by:

- `spec/protocol.md`
- `spec/behavior.md`
- `spec/storage.md`

Those files are authoritative for messaging behavior.

This document defines HOW those requirements should be implemented on Android.

Android-specific implementation choices MUST NOT change the common protocol
semantics.

---

## 2. Technology Stack

The generated Android client MUST use:

```text
Language: Kotlin
UI: Jetpack Compose
Architecture: MVVM with Clean Architecture separation
Concurrency: Kotlin Coroutines
Reactive state: Flow / StateFlow
Local database: Room
Networking: Retrofit + OkHttp
Dependency Injection: Hilt
Build system: Gradle
```

The generated client MUST be a native Android application.

Turnkey messaging or chat SDKs MUST NOT be used.

---

## 3. Minimum Application Structure

The generated project SHOULD organize code into responsibilities similar to:

```text
app/
└── src/main/java/<package>/
    ├── data/
    │   ├── local/
    │   │   ├── AppDatabase.kt
    │   │   ├── MessageDao.kt
    │   │   └── MessageEntity.kt
    │   │
    │   ├── remote/
    │   │   ├── MessagingApi.kt
    │   │   └── MessageDto.kt
    │   │
    │   └── repository/
    │       └── MessageRepositoryImpl.kt
    │
    ├── domain/
    │   ├── model/
    │   │   └── Message.kt
    │   │
    │   └── repository/
    │       └── MessageRepository.kt
    │
    ├── presentation/
    │   ├── login/
    │   │   ├── LoginScreen.kt
    │   │   └── LoginViewModel.kt
    │   │
    │   └── chat/
    │       ├── ChatScreen.kt
    │       └── ChatViewModel.kt
    │
    ├── sync/
    │   └── MessageSyncManager.kt
    │
    ├── di/
    │   └── AppModule.kt
    │
    └── MainActivity.kt
```

The exact file structure MAY vary if the generated implementation provides the
same architectural separation.

---

## 4. Domain Message Model

The Android client MUST represent the protocol message fields:

```text
message_id
sender
recipient
text
created_at
```

The client MUST also maintain the local delivery state:

```text
PENDING
SENDING
SENT
```

A conceptual Kotlin model is:

```kotlin
data class Message(
    val messageId: String,
    val sender: String,
    val recipient: String,
    val text: String,
    val createdAt: String,
    val deliveryState: DeliveryState
)
```

The exact implementation MAY differ.

The JSON representation sent to the server MUST use the field names defined in
`protocol.md`.

---

## 5. Room Persistence

Room MUST be used for persistent message storage.

The message table MUST contain enough information to persist:

```text
message_id
sender
recipient
text
created_at
delivery_state
```

`message_id` MUST be unique.

Room MUST prevent duplicate message records for the same `message_id`.

The DAO MUST support operations equivalent to:

```text
insert message
find message by message_id
observe conversation
get pending messages
update delivery state
```

Pending messages MUST survive application restart.

---

## 6. User Identity Persistence

The user's display name MUST survive application restart.

The Android implementation MAY use:

```text
DataStore
```

or another appropriate Android persistent key-value mechanism.

The stored user identity MUST follow the behavior defined in
`spec/behavior.md`.

---

## 7. Networking

Retrofit MUST be used to implement the HTTP API.

OkHttp MUST be used as the underlying HTTP client.

The API interface MUST support the protocol endpoints:

```text
POST /users/register
POST /messages
GET /messages/{username}
```

The Android emulator server address SHOULD default to:

```text
http://10.0.2.2:8000
```

The base URL SHOULD be configurable rather than duplicated throughout the
application.

---

## 8. Coroutines and Flow

Network and database operations MUST NOT block the Android main thread.

Kotlin Coroutines MUST be used for asynchronous operations.

Flow or StateFlow SHOULD be used for observable application state.

The UI SHOULD react to changes in Room and ViewModel state rather than manually
refreshing the entire screen.

---

## 9. Repository

A repository layer SHOULD coordinate:

```text
Room
Retrofit
offline queue
message synchronization
```

The presentation layer SHOULD NOT communicate directly with Retrofit or Room.

Conceptually:

```text
Compose UI
    |
    v
ViewModel
    |
    v
Repository
   / \
  v   v
Room Retrofit
```

The repository MUST preserve the behavior defined by the common
specifications.

---

## 10. Login Screen

On first launch, the application MUST display a login screen when no stored
identity exists.

The screen MUST contain at minimum:

```text
Messaging Demo

Your name:
[                 ]

[ Continue ]
```

The Continue action MUST reject a blank name.

After successful registration, the user identity MUST be persisted and the
application MUST navigate to the messaging interface.

---

## 11. Chat Screen

The messaging interface MUST allow the user to:

```text
view their current username
enter/select a recipient
view messages
enter message text
send a message
see outgoing delivery state
enable/disable offline mode
```

A simple interface is sufficient.

Visual complexity is NOT a goal of this project.

The generated client SHOULD prioritize understandable behavior over elaborate
UI design.

---

## 12. Sending a Message

When the user presses Send, the ViewModel/repository flow MUST follow the
common specification.

Conceptually:

```text
Compose
   |
   | Send
   v
ViewModel
   |
   v
Repository
   |
   +----> Create UUID
   |
   +----> Store PENDING in Room
   |
   +----> Attempt Retrofit request if online
```

The message MUST be stored in Room before successful network delivery is
assumed.

---

## 13. Offline Mode

The Android application MUST provide an explicit offline-mode control for
demonstration and testing.

A simple Compose switch or button is sufficient.

Example:

```text
Offline Mode: [ ON ]
```

When offline mode is ON:

```text
Retrofit network operations MUST NOT be attempted.
```

Room operations MUST continue normally.

Messages created while offline MUST be stored as:

```text
PENDING
```

When offline mode changes from ON to OFF, the client MUST initiate
synchronization.

---

## 14. Queue Synchronization

A synchronization component MUST be responsible for retrying pending messages.

The implementation MAY use a component such as:

```text
MessageSyncManager
```

For this local demonstration, WorkManager is NOT required.

The synchronization process MUST:

1. Read pending messages from Room.
2. Attempt delivery using Retrofit.
3. Mark successful messages as `SENT`.
4. Return failed messages to `PENDING`.
5. Retrieve incoming messages.
6. Deduplicate received messages by `message_id`.

Coroutines SHOULD be used for synchronization.

---

## 15. Incoming Messages

Incoming messages MUST be retrieved using the endpoint defined in
`protocol.md`.

Retrieved messages MUST be stored in Room.

Before insertion, the application MUST ensure that a message with the same
`message_id` does not already exist.

Room uniqueness constraints SHOULD provide an additional safeguard against
duplicates.

The Compose UI SHOULD observe local Room data.

Therefore, newly synchronized messages SHOULD automatically become visible
when local storage changes.

---

## 16. Application Restart

After application restart:

1. Restore the stored user identity.
2. Restore messages from Room.
3. Recover retryable `SENDING` messages.
4. Retry pending messages if online.
5. Retrieve incoming messages if online.

A pending message MUST retain its original:

```text
message_id
sender
recipient
text
created_at
```

---

## 17. UI State

ViewModels SHOULD expose immutable UI state using StateFlow.

Example conceptual state:

```kotlin
data class ChatUiState(
    val currentUser: String,
    val recipient: String,
    val messages: List<Message>,
    val messageText: String,
    val offline: Boolean,
    val error: String? = null
)
```

This example is illustrative rather than mandatory.

Generated code MAY use a different representation if the behavior remains
equivalent.

---

## 18. Error Handling

Network errors MUST NOT crash the application.

Failures MUST preserve pending messages.

The UI MAY display simple status information such as:

```text
Offline
```

or:

```text
Message queued - server unavailable
```

Detailed production error handling is outside the scope of this exercise.

---

## 19. Testing Requirements

The generated Android client SHOULD contain unit tests for important behavior.

Tests SHOULD cover at least:

```text
message creation
pending message persistence
successful state transition to SENT
failed delivery returning to PENDING
duplicate message handling
queue flushing
```

The generated project MUST compile successfully.

The generator validation process SHOULD run:

```text
./gradlew test
./gradlew assembleDebug
```

---

## 20. Generated Code Boundary

The Android project under:

```text
clients/android/
```

is generated code.

It MUST be safe to delete this directory and regenerate it using the project's
agentic generator.

Hand-written protocol behavior MUST NOT be hidden inside this directory.

The authoritative requirements remain under:

```text
spec/
```

---

## 21. Simplicity

This project evaluates protocol design and code generation.

The Android implementation SHOULD therefore avoid unnecessary complexity.

The generated application does NOT require:

```text
Firebase
cloud services
authentication SDKs
push notifications
WebSockets
complex navigation
animations
production analytics
```

The simplest implementation satisfying the common specifications SHOULD be
preferred.
