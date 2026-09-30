import importlib.util
from pathlib import Path
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_barrier', ROOT / '.github/workflows/scripts/wait_for_catalog_refreshes.py')
barrier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(barrier)


def run(ident, workflow='update-resource.yml', status='in_progress', branch='main'):
    return {'id': ident, 'path': '.github/workflows/' + workflow, 'status': status, 'head_branch': branch}


class Clock:
    value = 0
    def now(self): return self.value
    def sleep(self, duration): self.value += duration


@pytest.mark.parametrize('first', [1, 2])
def test_waits_for_both_completion_orders_and_quiet_period(first):
    clock = Clock()
    runs = [run(1), run(2, 'update-software.yml')]
    responses = iter([runs, [r for r in runs if r['id'] != first], [], [], []])
    fetch = Mock(side_effect=lambda: next(responses))
    barrier.wait_until_idle(fetch, clock=clock.now, sleep=clock.sleep, log=lambda _: None)
    assert clock.value == 60
    assert fetch.call_count == 5


def test_new_refresh_during_quiet_period_resets_wait():
    clock = Clock()
    responses = iter([[], [run(2, 'update-software.yml', 'queued')], [], [], []])
    barrier.wait_until_idle(lambda: next(responses), clock=clock.now, sleep=clock.sleep, log=lambda _: None)
    assert clock.value == 60


def test_active_selection_includes_parent_and_queued_runs_not_completed_or_unrelated():
    selected = barrier.active_runs([{'workflow_runs': [
        run(1, status='completed'), run(2, 'update-software.yml', 'queued'),
        run(3, 'refresh-catalog-data.yml'), run(4, branch='feature'),
        run(5, 'update-data.yml'), run(6, status='waiting')]}], 'main')
    assert [r['id'] for r in selected] == [2, 3, 6]


def test_api_error_and_timeout_never_authorize_publication():
    def fail(): raise RuntimeError('API unavailable')
    with pytest.raises(RuntimeError): barrier.wait_until_idle(fail)
    clock = Clock()
    with pytest.raises(TimeoutError):
        barrier.wait_until_idle(lambda: [run(1)], timeout=30, clock=clock.now,
                                sleep=clock.sleep, log=lambda _: None)


def test_combined_refresh_and_barrier_precede_publication():
    combined = (ROOT / '.github/workflows/refresh-catalog-data.yml').read_text()
    assert 'uses: ./.github/workflows/update-resource.yml' in combined
    assert 'uses: ./.github/workflows/update-software.yml' in combined
    assert 'schedule:' in combined
    for name in ['update-resource.yml', 'update-software.yml']:
        text = (ROOT / '.github/workflows' / name).read_text()
        assert 'workflow_call:' in text and 'workflow_dispatch:' in text
        assert 'schedule:' not in text
    publisher = (ROOT / '.github/workflows/update-data.yml').read_text()
    assert '"Refresh Resources and Software"' in publisher
    assert publisher.index('wait_for_catalog_refreshes.py') < publisher.index('Pin latest validated dataset snapshots')
    assert "needs: publication_gate" in publisher
    assert 'EMBEDDINGS_PAUSED: "true"' in publisher
