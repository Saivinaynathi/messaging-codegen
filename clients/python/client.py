"""Run with python3 client.py --db alice.sqlite3."""
import argparse
import select
import shlex
import sys
import time
from pathlib import Path

from api import API, APIError
from database import Database
from sync import SyncService

HELP = 'send <recipient> <message> | messages <user> | offline | online | sync | status | help | quit\nUse quotes around names containing spaces.'


def report(errors):
    for error in errors:
        print(f"Synchronization failed; unsent messages remain queued: {error}")


def synchronize(service):
    report(service.sync())
    show_received(service)


def show_received(service):
    for message in service.received:
        print(f"{message.sender} -> Me: {message.text}", flush=True)


def command(line, service):
    args = shlex.split(line)
    if not args:
        return True
    name, *values = args
    db = service.database
    if name == "quit" and not values:
        return False
    if name == "send" and len(values) >= 2:
        message = service.create(values[0], " ".join(values[1:]))
        print(f"Me -> {message.recipient}: {message.text}\n    PENDING", flush=True)
        synchronize(service)
        print(f"Delivery state: {db.get(message.message_id)['delivery_state']}")
    elif name == "messages" and len(values) == 1:
        print(f"Conversation with {values[0]}")
        for row in db.conversation(values[0]):
            outgoing = row['sender'] == db.user
            print(f"{'Me' if outgoing else row['sender']}: {row['text']}")
            if outgoing:
                print(f"    {row['delivery_state']}")
    elif name in ("offline", "online") and not values:
        report(service.set_offline(name == "offline"))
        if not service.offline:
            show_received(service)
        print(f"Network mode: {'OFFLINE' if service.offline else 'ONLINE'}")
    elif name == "sync" and not values:
        synchronize(service)
    elif name == "status" and not values:
        print(f"User: {db.user}\nNetwork mode: {'OFFLINE' if service.offline else 'ONLINE'}\nPending messages: {len(db.pending())}")
    else:
        print(HELP)
    return True


def main():
    parser = argparse.ArgumentParser(description="Persistent offline-capable messaging CLI")
    parser.add_argument("--db", default=str(Path(__file__).with_name("messages.sqlite3")))
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=5)
    options = parser.parse_args()
    if options.poll_interval <= 0:
        parser.error("--poll-interval must be positive")
    db = Database(options.db)
    service = SyncService(db, API(options.server), options.offline)
    print("Messaging Client")
    try:
        while not db.user:
            name = input("Enter your name (or quit): ")
            if name == "quit":
                return
            try:
                report(service.identify(name))
                show_received(service)
            except (ValueError, APIError) as error:
                print(error)
                if service.offline:
                    return
        synchronize(service)
        print(f"User: {db.user}\n{HELP}")
        next_poll = time.monotonic() + options.poll_interval
        while True:
            print("> ", end="", flush=True)
            # A single event loop keeps SQLite and mode changes serialized.
            while not select.select([sys.stdin], [], [], max(0, next_poll - time.monotonic()))[0]:
                synchronize(service)
                next_poll = time.monotonic() + options.poll_interval
            line = sys.stdin.readline()
            if not line:
                break
            try:
                if not command(line, service):
                    break
            except (ValueError, APIError) as error:
                print(error)
            if time.monotonic() >= next_poll:
                synchronize(service)
                next_poll = time.monotonic() + options.poll_interval
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
