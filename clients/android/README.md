# Generated Android client

Open this directory in Android Studio or use JDK 17+ and an Android SDK with platform 36 installed.
Set `ANDROID_HOME` or put `sdk.dir=/path/to/sdk` in `local.properties`.

```sh
./gradlew test
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The default server is `http://10.0.2.2:8000/`. Override at build time:
`./gradlew assembleDebug -PserverUrl=http://192.168.1.10:8000/`.
For a USB device, `adb reverse tcp:8000 tcp:8000` and build with
`-PserverUrl=http://localhost:8000/`.

Start the repository reference server separately. Register Alice on one device
and Bob on another client. Enter the other user's name in Recipient to view
that conversation. Send online, enable Offline mode on both clients, and send
again. Messages remain PENDING even across restart. Reconnect Alice, take Alice
offline again, reconnect Bob, then reconnect Alice. Both clients should have
their peer's messages exactly once and outgoing acknowledgements marked SENT.

The offline switch is persisted. Registration requires online mode. Mode changes
wait for the current synchronization (at most the bounded requests already in
progress); once OFFLINE appears, no network request starts. Online polling and
retry run every five seconds while the ViewModel lives. Sync / retry is also
available. No background service is needed for this demonstration.

Room persists identity, mode, messages and states. Startup recovers SENDING to
PENDING. Incoming records retain response order rather than sorting by clocks;
outgoing records precede received records in the conversation, each group in
its own creation/acceptance order. Repository tests use real Room databases and
fake HTTP APIs; HTTP tests use MockWebServer to verify wire serialization.
