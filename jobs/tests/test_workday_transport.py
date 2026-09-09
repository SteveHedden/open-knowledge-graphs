"""Exercise bounded Workday concurrency and timeout evidence without networking."""
import json
import multiprocessing
import threading
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest
import first_party_sources as fps
import source_progress
import task42_nightly


class Response:
    is_redirect = False
    is_permanent_redirect = False
    headers = {}
    status_code = 200

    def __init__(self, payload):
        self.body = json.dumps(payload).encode()
        self.closed = False

    def raise_for_status(self):
        if self.status_code != 200:
            raise fps.requests.HTTPError(response=self)

    def iter_content(self, size):
        yield self.body

    def close(self):
        self.closed = True


def transport(monkeypatch, *, fail=False):
    paths = [f"/job/test/Role_{index}" for index in range(9)]
    sessions, responses = [], []
    barrier = threading.Barrier(3, timeout=3)
    lock = threading.Lock()
    active = peak = 0

    class Session:
        def __init__(self):
            self.owner = threading.get_ident()
            self.calls = 0
            self.closed = False
            sessions.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def request(self, method, url, **kwargs):
            nonlocal active, peak
            assert threading.get_ident() == self.owner
            assert kwargs["allow_redirects"] is False
            self.calls += 1
            if method == "POST":
                response = Response({"total": len(paths), "jobPostings": [{"externalPath": path} for path in paths]})
            else:
                with lock:
                    active += 1
                    peak = max(peak, active)
                if self.calls == 1:
                    barrier.wait()
                time.sleep(0.005 if url.endswith("Role_0") else 0.02)
                response = Response({"jobPostingInfo": {"title": url}})
                if fail and url.endswith("Role_0"):
                    response.status_code = 429
                    response.headers = {"Retry-After": "60"}
                with lock:
                    active -= 1
            responses.append(response)
            return response

    monkeypatch.setattr(fps.requests, "Session", Session)
    return paths, sessions, responses, lambda: peak


def test_connections_reused_concurrency_bounded_and_output_sorted(monkeypatch):
    paths, sessions, responses, peak = transport(monkeypatch)
    source = fps.load_first_party_sources()["first-party-accenture"]
    payload = fps.fetch_source(source)
    assert [row["externalPath"] for row in payload["details"]] == sorted(paths)
    assert peak() == 3
    assert sorted(session.calls for session in sessions) == [1, 3, 3, 3]
    assert all(session.closed for session in sessions)
    assert all(response.closed for response in responses)


def test_rate_limit_stops_new_details_and_preserves_failure(monkeypatch, tmp_path):
    paths, sessions, responses, peak = transport(monkeypatch, fail=True)
    source_progress.configure(tmp_path / "progress.json")
    try:
        with pytest.raises(fps.FirstPartySourceError, match="HTTP 429"):
            fps.fetch_source(fps.load_first_party_sources()["first-party-accenture"])
        assert sum(session.calls for session in sessions) <= 4
        assert all(response.closed for response in responses)
        evidence = source_progress.read(tmp_path / "progress.json")
        assert evidence["failureHttpStatus"] == 429
        assert evidence["failureRetryAfter"] == "60"
        assert evidence["completedRequests"] == 3
        assert evidence["lastHttpStatus"] == 200
    finally:
        source_progress._path = None


def slow_worker(key, output):
    source_progress.configure(Path(output).with_suffix(".progress.json"))
    source_progress.report(phase="workday-details", completed=True, discoveredDetails=300)
    time.sleep(10)


def test_timeout_captures_progress_before_worker_cleanup(tmp_path):
    result = task42_nightly.execute_process_batch(
        ["slow-source"], tmp_path, source_timeout_seconds=0.2,
        context=multiprocessing.get_context("fork"), worker=slow_worker,
    )["slow-source"]
    assert result["status"] == "timed-out"
    assert result["rawPayload"] is None
    assert result["diagnostics"]["phase"] == "workday-details"
    assert result["diagnostics"]["completedRequests"] == 1
