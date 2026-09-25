"""Reproduce the source contract changes observed on 2026-09-25."""
import json
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import first_party_sources as fps


def source(key):
    return fps.load_first_party_sources()[key]


def row(job_id):
    return {'response': {'id': str(job_id), 'urlTitle': 'Research Fellow'}}


def test_successfactors_fetches_all_pages_before_details_and_counts_every_request(monkeypatch):
    src = source('first-party-the-open-university')
    post = Mock(side_effect=[{'totalJobs': 3, 'jobSearchResult': [row(1), row(2)]},
                             {'totalJobs': 3, 'jobSearchResult': [row(3)]}])
    detail = Mock(return_value='<html>detail</html>')
    monkeypatch.setattr(fps, '_post_json', post)
    monkeypatch.setattr(fps, '_fetch_html', detail)
    payload = fps._fetch_successfactors(src)
    assert [call.args[2]['pageNumber'] for call in post.call_args_list] == [0, 1]
    assert all(call.args[2]['sortBy'] == 'date' for call in post.call_args_list)
    assert [d['id'] for d in payload['details']] == ['1', '2', '3']
    assert fps.request_count_from_payload(payload, src) == 5
    assert payload['listing']['totalJobs'] == len(payload['listing']['jobSearchResult']) == 3


@pytest.mark.parametrize('second', [
    {'totalJobs': 3, 'jobSearchResult': [row(1)]},
    {'totalJobs': 4, 'jobSearchResult': [row(3)]},
    {'totalJobs': 3, 'jobSearchResult': []},
    {'totalJobs': 3, 'jobSearchResult': [row(3), row(4)]},
])
def test_successfactors_rejects_repeated_changed_truncated_or_excess_pages(monkeypatch, second):
    src = source('first-party-the-open-university')
    monkeypatch.setattr(fps, '_post_json', Mock(side_effect=[
        {'totalJobs': 3, 'jobSearchResult': [row(1), row(2)]}, second]))
    detail = Mock()
    monkeypatch.setattr(fps, '_fetch_html', detail)
    with pytest.raises(fps.FirstPartySourceError):
        fps._fetch_successfactors(src)
    detail.assert_not_called()


def test_successfactors_preserves_request_budget_when_another_page_is_needed(monkeypatch):
    src = replace(source('first-party-the-open-university'), max_requests_per_run=4)
    post = Mock(return_value={'totalJobs': 3, 'jobSearchResult': [row(1), row(2)]})
    monkeypatch.setattr(fps, '_post_json', post)
    with pytest.raises(fps.FirstPartySourceError, match='request cap'):
        fps._fetch_successfactors(src)
    assert post.call_count == 1


def test_successfactors_replay_requires_matching_page_evidence():
    src = source('first-party-the-open-university')
    payload = json.loads((ROOT/'tests/fixtures/first-party-pilot'/f'{src.key}.json').read_text())
    payload['listingPages'] = [deepcopy(payload['listing'])]
    assert fps.records_from_payload(payload, src)
    payload['listingPages'][0]['jobSearchResult'] = []
    with pytest.raises(fps.FirstPartySourceError, match='page evidence'):
        fps.records_from_payload(payload, src)


def microsoft_payload(permalink):
    src = source('first-party-microsoft-research')
    payload = json.loads((ROOT/'tests/fixtures/first-party-pilot'/f'{src.key}.json').read_text())
    compact = payload['listingPages'][0]['posts'][0]
    raw = {'data': {'ID':compact['id'], 'post_name':compact['slug'],
        'post_content':compact['content'], 'post_status':compact['status'],
        'post_type':compact['type'], 'post_title':compact['title'],
        'post_date_gmt':compact['date'], 'permalink':permalink, 'meta':{}}}
    payload['listingPages'][0]['posts'] = [fps._microsoft_listing_item(raw)]
    return src, payload


def test_microsoft_application_permalink_without_duplicate_meta_is_supported():
    url='https://apply.careers.microsoft.com/careers/job/1970393556768654'
    src,payload=microsoft_payload(url)
    records=fps.records_from_payload(payload,src)
    assert records[0]['canonicalUrl']==url
    assert records[0]['requisitionId']=='1970393556768654'


@pytest.mark.parametrize('url', [
    'https://evil.example/careers/job/1970393556768654',
    'https://apply.careers.microsoft.com/other/1970393556768654',
    'https://apply.careers.microsoft.com/careers/job/1970393556768654?redirect=other',
])
def test_microsoft_does_not_promote_unreviewed_application_urls(url):
    src,payload=microsoft_payload(url)
    with pytest.raises(fps.FirstPartySourceError, match='permalink/content contract'):
        fps.records_from_payload(payload,src)
