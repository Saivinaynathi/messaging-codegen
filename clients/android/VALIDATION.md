# Validation result

Generated files are restricted to `clients/android`.

Commands attempted:

```sh
./gradlew --gradle-user-home .gradle-user-home test --no-daemon
./gradlew --gradle-user-home .gradle-user-home assembleDebug --no-daemon
```

Both commands failed during Gradle startup, before project configuration,
compilation, or execution of any tests:

```text
Could not create service of type FileLockContentionHandler
java.net.SocketException: Operation not permitted
```

The execution sandbox prevents Gradle's local socket use. Approval escalation
is unavailable. Tests and APK compilation are therefore unverified, not passed.
Full output is in `test-validation.log` and `build-validation.log`.

Static inspection checked manifest XML parsing, the Gradle wrapper archive,
Kotlin brace balance, test file presence, and the generated directory boundary.
Source review checked persistent Room uniqueness, unchanged retry payloads,
matching acknowledgements, SENDING recovery, offline request gating, and
response-order metadata.

Six automated tests are provided in `RepositoryTest.kt` and `ProtocolTest.kt`.
Run the README commands in an environment allowing Gradle sockets and dependency
downloads, with Android SDK platform 36 installed. This machine only has platform
36.1; the required platform 36 and uncached dependencies may need downloading
once Gradle startup is permitted. Device interoperability has not been exercised.
