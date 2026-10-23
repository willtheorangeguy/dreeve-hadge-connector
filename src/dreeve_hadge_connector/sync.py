import hashlib
import logging
from contextlib import contextmanager
from dataclasses import dataclass

from filelock import FileLock, Timeout

from .fit import build_fit
from .state import State
from .workout import parse_csv

log = logging.getLogger(__name__)


@dataclass
class Result:
    delivered: int = 0
    planned: int = 0
    skipped: int = 0
    filtered: int = 0
    changed: int = 0
    rejected: int = 0
    cached_files: int = 0


@contextmanager
def open_state(config, preview):
    if preview:
        state = State(config.state_dir, readonly=True)
        try:
            yield state
        finally:
            state.close()
        return
    config.state_dir.mkdir(parents=True, exist_ok=True)
    lock = FileLock(config.state_dir / "sync.lock", timeout=0)
    try:
        with lock:
            state = State(config.state_dir)
            try:
                yield state
            finally:
                state.close()
    except Timeout:
        raise RuntimeError("Another sync process is using this state directory") from None


def run_sync(config, github, *, preview=False):
    if config.watch_dir.resolve() == config.state_dir.resolve():
        raise ValueError("STATE_DIR must be separate from WATCH_DIR")
    result = Result()
    with open_state(config, preview) as state:
        if not preview:
            if not config.watch_dir.is_dir():
                raise ValueError("WATCH_DIR must be an existing directory mounted from Dreeve")
            for row in state.pending():
                state.deliver(row, config.watch_dir)
                result.delivered += 1
        snapshot = github.snapshot()
        repo = snapshot.repository_id
        # Re-reading is required when EXPORT_SINCE moves backwards. Include it in the cache scope.
        scope = repo + ":" + (config.since.isoformat() if config.since else "all")
        seen = {}
        for source in snapshot.files:
            if state.cached(scope, source.path, source.sha):
                result.cached_files += 1
                continue
            try:
                workouts, rejected = parse_csv(github.read(source, snapshot.commit))
            except ValueError as exc:
                log.error("%s: %s", source.path, exc)
                result.rejected += 1
                continue
            for rejection in rejected:
                log.error("%s row %d: %s", source.path, rejection.row, rejection.reason)
            result.rejected += len(rejected)
            complete = not rejected
            for number, workout in workouts:
                if config.since and workout.start < config.since:
                    result.filtered += 1
                    continue
                fingerprint = workout.fingerprint()
                existing = state.get(repo, workout.uuid)
                previous = existing["fingerprint"] if existing else seen.get(workout.uuid)
                if previous:
                    if previous != fingerprint:
                        result.changed += 1
                        log.warning("%s row %d: previously seen UUID changed; manual review required",
                                    source.path, number)
                    else:
                        result.skipped += 1
                    continue
                try:
                    payload = build_fit(workout, config.repository)
                except (ValueError, OverflowError):
                    log.error("%s row %d: values could not be encoded as FIT", source.path, number)
                    result.rejected += 1
                    complete = False
                    continue
                seen[workout.uuid] = fingerprint
                if preview:
                    result.planned += 1
                    log.info("%s row %d: would deliver workout %s", source.path, number, workout.uuid)
                    continue
                namespace = hashlib.sha256(repo.encode()).hexdigest()[:16]
                filename = f"hadge-{namespace}-{workout.uuid}.fit"
                state.prepare(repo, workout, filename, payload)
                state.deliver(state.get(repo, workout.uuid), config.watch_dir)
                result.delivered += 1
            if complete and not preview:
                state.checkpoint(scope, source.path, source.sha)
    return result
