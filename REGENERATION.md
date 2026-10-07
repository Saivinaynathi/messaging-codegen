# Regeneration Validation

## Purpose

This document records the results of regenerating messaging clients from the project specifications using the Codex-based generator.

## Python Client

- Generated in a separate Git worktree.
- Python source compilation succeeded.
- All 7 automated tests passed.
- The regenerated client successfully sent a message to the reference messaging server.
- The server confirmed receipt of the message.

**Result: PASS**

## Android Client

- Generated in a separate Git worktree.
- Generated project includes Jetpack Compose, Room, Retrofit/OkHttp, Hilt, and Gradle configuration.
- Initial unit tests failed because Java 26 was incompatible with the test tooling.
- Switched the Gradle runtime to JDK 17.
- `./gradlew clean testDebugUnitTest` completed successfully.
- `./gradlew assembleDebug` completed successfully.
- A debug APK was generated.

**Result: PASS for compilation, unit tests, and APK generation.**

The regenerated Android application has not yet been independently tested on an emulator against the reference server.

## Reproduction

Run from the repository root:

```bash
python3 generator/generate.py python
python3 generator/generate.py android
```

For Android validation, configure JDK 17:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
```

Then run from `clients/android`:

```bash
./gradlew clean testDebugUnitTest
./gradlew assembleDebug
```

## Conclusion

The generator has demonstrated that it can recreate both client implementations from the specification.

Python regeneration passed automated tests and server interoperability verification. Android regeneration passed automated unit tests and produced a debug APK.

The remaining verification is to launch the regenerated Android application and confirm runtime interoperability with the Python client.
