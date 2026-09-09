"""Small, atomic worker diagnostics; never store response bodies or credentials."""
import json
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
