"""Small, atomic worker diagnostics; never store response bodies or credentials."""
import json
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import threading
import time
from pathlib import Path

_lock = threading.Lock()
_path = None
_state = {}
_started = 0.0


def configure(path):
    global _path, _state, _started
    _path = Path(path)
    _state = {}
    _started = time.monotonic()
    report(phase="pipeline")


def report(*, completed=False, **fields):
    if _path is None:
        return
    with _lock:
        _state.update(fields)
        if completed:
            _state["completedRequests"] = _state.get("completedRequests", 0) + 1
        _state["elapsedSeconds"] = round(time.monotonic() - _started, 3)
        _path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _path.with_suffix(".tmp")
        temporary.write_text(json.dumps(_state), encoding="utf-8")
        os.replace(temporary, _path)


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

# Public progress lines contain counters and phase names, never job text, URLs,
# request headers or credentials. Flush immediately for GitHub's live log viewer.
def emit(event, **fields):
    print(json.dumps({"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}, sort_keys=True), flush=True)


def safe_snapshot(state):
    allowed = ("phase", "completedRequests", "completedDetails", "discoveredDetails", "listingPages", "lastHttpStatus", "lastRequestSeconds")
    return {key: state[key] for key in allowed if key in (state or {})}


@contextmanager
def phase(name, *, interval_seconds=30, **identity):
    """Report start, wall time while blocked, and success/failure of a phase."""
    started = time.monotonic()
    stop = threading.Event()
    report(phase=name)
    emit("phase-start", phase=name, **identity)
    def heartbeat():
        while not stop.wait(interval_seconds):
            emit("phase-progress", phase=name, elapsedSeconds=round(time.monotonic()-started, 3), **identity)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    status = "completed"
    try:
        yield
    except BaseException:
        status = "failed"
        raise
    finally:
        stop.set()
        thread.join()
        emit("phase-end", phase=name, status=status, elapsedSeconds=round(time.monotonic()-started, 3), **identity)
