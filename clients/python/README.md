# Generated Python messaging client

Requires Python 3.9+ on macOS/Linux. Runtime has no third-party dependencies.
Start the reference server separately, then launch two terminals:

```sh
python3 clients/python/client.py --db clients/python/alice.sqlite3
python3 clients/python/client.py --db clients/python/bob.sqlite3
```

Enter Alice and Bob respectively. Each database represents one identity.
`--server http://localhost:8000` configures transport; `--offline` starts an
already registered identity without network access. First registration requires
a successful server acknowledgement. Explicit mode is per process; use
`--offline` again to remain offline after restart.

Commands:

```text
send Bob Hi Bob, I have something important to tell you
messages Bob
offline
send Bob The important message was queued while I was offline.
status
online
sync
quit
```

Bob can reply with `send Alice What is it?`, enter `offline`, queue a reply,
and reconnect using `online`. Reconnect flushes the persistent queue and fetches
incoming messages. Online polling and retry run every five seconds, configurable
with `--poll-interval`. `messages "Mary Jane"` supports names containing spaces.
Messages display locally as PENDING before delivery is attempted. Failed sends
remain queued; matching server acknowledgements mark them SENT. Interrupted
SENDING messages recover as PENDING on restart. Incoming insertion order follows
server order rather than client timestamps. Use one running process per database.

Validation:

```sh
cd clients/python
python3 -m pip install -r requirements.txt
python3 -m pytest
python3 -m compileall -q client.py api.py database.py models.py sync.py tests
```

If pytest cannot be installed, the same tests can run without extra dependencies:
`python3 -m unittest discover -s tests -v`.

No separate build is required. Tests use temporary databases and include an
optional real reference-server HTTP scenario when FastAPI and uvicorn are installed.
Incoming messages are announced when polling discovers them and remain available
through `messages <user>` while offline. Malformed server data is reported as a
synchronization error rather than inserted into local storage.
