"""Progress must remain visible during slow work without exposing payloads."""
import json
import sys
import time
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import source_progress as progress


def test_phase_heartbeat_and_failure_are_flushed(capsys):
    with pytest.raises(ValueError):
        with progress.phase('catalog-matching', sourceKey='fixture', interval_seconds=0.01):
            time.sleep(0.04)
            raise ValueError('private response body')
    output = capsys.readouterr().out
    rows = [json.loads(line) for line in output.splitlines()]
    assert rows[0]['event'] == 'phase-start'
    assert any(row['event'] == 'phase-progress' for row in rows)
    assert rows[-1]['event'] == 'phase-end'
    assert rows[-1]['status'] == 'failed'
    assert rows[-1]['elapsedSeconds'] > 0
    assert 'private response body' not in output
    assert all(row['sourceKey'] == 'fixture' for row in rows)


def test_request_progress_logs_only_allowed_counters():
    result = progress.safe_snapshot({'phase': 'detail', 'completedRequests': 3,
        'lastHttpStatus': 200, 'lastStartedPath': '/secret?token=private',
        'description': 'private job text', 'headers': {'Authorization': 'secret'}})
    assert result == {'phase': 'detail', 'completedRequests': 3, 'lastHttpStatus': 200}
    assert progress.safe_snapshot(None) == {}


def _progress_test_worker(key, output):
    if key == 'slow':
        time.sleep(1)
    Path(output).write_text(json.dumps({'error': None, 'run': {}, 'rawPayload': {}}))


def test_fast_source_finishes_before_slow_source_timeout(tmp_path, capsys):
    import multiprocessing
    import task42_nightly as nightly
    result = nightly.execute_process_batch(['slow', 'fast'], tmp_path,
        source_timeout_seconds=0.15, context=multiprocessing.get_context('fork'),
        worker=_progress_test_worker)
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    finished = [row for row in rows if row['event'] == 'source-end']
    assert [row['sourceKey'] for row in finished] == ['fast', 'slow']
    assert result['slow']['status'] == 'timed-out'
    assert result['fast']['status'] == 'fetched'
    assert all('workerElapsedSeconds' in value for value in result.values())
