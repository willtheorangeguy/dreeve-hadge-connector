import argparse
import logging
import os
import signal
import sqlite3
import threading
from dataclasses import asdict

from .config import Config
from .github import GitHub, RemoteError
from .sync import run_sync

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Deliver Hadge workout summaries to Dreeve")
    parser.add_argument("command", choices=["check", "preview", "sync", "watch"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # fit-tool may install a WARNING-level root handler while importing its profile.
    # basicConfig then does nothing; explicitly enable the watcher's progress messages.
    logging.getLogger().setLevel(logging.INFO)
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        config = Config.from_env()
        if args.command == "check":
            with_client = GitHub(config)
            try:
                snapshot = with_client.snapshot()
                if not config.watch_dir.is_dir() or not os.access(config.watch_dir, os.W_OK):
                    raise ValueError("WATCH_DIR must be an existing writable directory")
                if config.watch_dir.resolve() == config.state_dir.resolve():
                    raise ValueError("STATE_DIR must be separate from WATCH_DIR")
                log.info("GitHub access OK; %d yearly workout files; watch folder accessible",
                         len(snapshot.files))
                log.info("check does not write files; sync verifies actual delivery permissions")
                return 0
            finally:
                with_client.close()
        while not stopped.is_set():
            delay = config.interval
            client = None
            try:
                # Re-read the secret each cycle to support token rotation.
                client = GitHub(config)
                result = run_sync(config, client, preview=args.command == "preview")
                log.info("%s: %s", "Preview" if args.command == "preview" else "Watch delivery",
                         ", ".join(f"{key}={value}" for key, value in asdict(result).items()))
                if args.command != "watch":
                    return 1 if result.rejected else 0
            except (ValueError, OSError, RuntimeError, sqlite3.DatabaseError) as exc:
                # Filesystem errors can contain paths, but never dump HTTP bodies or credentials.
                log.error("%s", exc)
                if args.command != "watch":
                    return 1
                if isinstance(exc, RemoteError):
                    delay = max(delay, exc.retry_after)
            finally:
                if client:
                    client.close()
            stopped.wait(delay)
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.DatabaseError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
