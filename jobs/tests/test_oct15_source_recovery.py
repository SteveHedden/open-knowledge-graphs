from dataclasses import replace
from unittest.mock import Mock
import pytest
import requests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import first_party_sources as fps

@pytest.mark.parametrize('html,zero', [
 ('<h2 id="search-results">View Results <span>(0\n)</span><a><img></a></h2>', True),
 ('<h2 id="search-results">View Results <span>(1)</span></h2>', False),
 ('<script>View Results (0)</script>', False),
 ('<h2>View Results (0)</h2>', False),
])
def test_peopleadmin_explicit_result_count(html, zero):
    parser = fps._PeopleAdminListingParser(fps.load_first_party_sources()['first-party-renaissance-computing-institute'])
    parser.feed(html)
    assert parser.explicit_zero is zero


def test_workday_retries_transport_failure_and_counts_attempts(monkeypatch):
    source = fps.load_first_party_sources()['first-party-accenture']
    budget = fps._WorkdayRequestBudget(source)
    response = Mock(is_redirect=False, is_permanent_redirect=False, headers={}, status_code=200)
    response.iter_content.return_value = [b'{}']
    session = Mock()
    session.request.side_effect = [requests.ConnectionError('connection interrupted'), response]
    monkeypatch.setattr(fps.time, 'sleep', lambda _: None)
    assert fps._workday_request(source, session, 'GET', source.endpoint, budget=budget) == b'{}'
    assert budget.counts['detailRequests'] == 2
    assert response.close.called


def test_workday_retry_cannot_exceed_budget(monkeypatch):
    source = replace(fps.load_first_party_sources()['first-party-accenture'], max_requests_per_run=2)
    session = Mock()
    session.request.side_effect = requests.ConnectionError('interrupted')
    monkeypatch.setattr(fps.time, 'sleep', lambda _: None)
    with pytest.raises(fps.FirstPartySourceError, match='request cap'):
        fps._workday_request(source, session, 'GET', source.endpoint, budget=fps._WorkdayRequestBudget(source))
    assert session.request.call_count == 2


def test_workday_does_not_retry_http_error(monkeypatch):
    source = fps.load_first_party_sources()['first-party-accenture']
    response = Mock(is_redirect=False, is_permanent_redirect=False, status_code=429, headers={})
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    session = Mock(); session.request.return_value = response
    with pytest.raises(fps.FirstPartySourceError):
        fps._workday_request(source, session, 'GET', source.endpoint)
    assert session.request.call_count == 1


def test_pinpoint_requires_department_identity():
    source = fps.load_first_party_sources()['first-party-metaphacts']
    assert fps.records_from_payload({'data': []}, source) == []
    assert fps.records_from_payload({'data': [{'job': {'structure_custom_group_one': {'id': '7343', 'name': 'Sales'}}}]}, source) == []
    for payload in [{}, {'data': [{'job': {}}]}, {'data': [], 'next': '/page/2'}]:
        with pytest.raises(fps.FirstPartySourceError):
            fps.records_from_payload(payload, source)


def test_unavailable_workday_rows_are_accounted_for_not_silently_dropped():
    import json
    from copy import deepcopy
    source = fps.load_first_party_sources()['first-party-accenture']
    path = Path(__file__).parent / 'fixtures/first-party-pilot/first-party-accenture.json'
    payload = json.loads(path.read_text())
    count = payload['listingPages'][0]['total']
    payload['listingPages'][0]['total'] += 1
    payload['listingPages'][0]['jobPostings'].append({'bulletFields': ['R12345678', 'Location Negotiable']})
    payload['unavailableRequisitions'] = ['R12345678']
    assert len(fps.records_from_payload(payload, source)) == count
    bad = deepcopy(payload); bad['unavailableRequisitions'] = []
    with pytest.raises(fps.FirstPartySourceError, match='evidence'):
        fps.records_from_payload(bad, source)
    bad = deepcopy(payload); bad['listingPages'][0]['jobPostings'][-1]['title'] = 'Broken actual job'
    with pytest.raises(fps.FirstPartySourceError, match='path'):
        fps.records_from_payload(bad, source)


def test_pipeline_retains_unavailable_job_without_refreshing_its_date(tmp_path):
    import json
    import live_pipeline
    fixture = Path(__file__).parent / 'fixtures/first-party-pilot/first-party-accenture.json'
    payload = json.loads(fixture.read_text())
    old_time = '2026-10-13T12:00:00Z'
    new_time = '2026-10-15T12:00:00Z'
    live_pipeline.run_pipeline(source_key='first-party-accenture', runtime_dir=tmp_path,
        retrieved_at=old_time, first_party_fetcher=lambda _: payload, defer_materialization=True)
    snapshot = tmp_path / 'sources/first-party-accenture.json'
    old_records = json.loads(snapshot.read_text())
    old_id = old_records[0]['sourceRecordId']
    # Fixture uses R001; the source placeholder shape permits that requisition ID.
    payload['listingPages'][0]['jobPostings'] = [{'bulletFields': [old_id, 'Location Negotiable']}]
    payload['details'] = []
    payload['unavailableRequisitions'] = [old_id]
    payload['requestBatches'] = [{'batch': 1, 'listingRequests': 1, 'detailRequests': 0}]
    result = live_pipeline.run_pipeline(source_key='first-party-accenture', runtime_dir=tmp_path,
        retrieved_at=new_time, first_party_fetcher=lambda _: payload, defer_materialization=True)
    assert json.loads(snapshot.read_text()) == old_records
    assert result['completeSourceSnapshot'] is False
    assert result['unavailableRequisitions'] == [old_id]
    assert result['retainedUnavailableCount'] == 1
