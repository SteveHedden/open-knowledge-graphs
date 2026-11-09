"""Reviewed historical pages survive publication without promoting dead URLs."""
import asyncio
import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_pages as pages
from historical_resources import POLICY, historical_record
import test_page_membership as membership_tests


def records():
    return [dict(wikidataId=f'https://www.wikidata.org/wiki/{qid}',
                 canonicalUrl=f'https://openknowledgegraphs.com/resource/historical-{qid.lower()}/',
                 title=f'Historical resource {qid}', description=entry['notice'],
                 homepage=entry['homepage'] or None, types=['ControlledVocabulary'])
            for qid, entry in POLICY.items()]


def test_review_is_bound_to_identity_and_exact_homepage():
    for record in records():
        assert pages.passes_content_filter(record)
        assert not historical_record({**record, 'wikidataId': 'https://www.wikidata.org/wiki/Q123'})
        assert not historical_record({**record, 'homepage': 'https://new.example.org/'})
        assert not pages.passes_content_filter({**record, 'description': ''})
    assert not pages.passes_content_filter(dict(title='Unknown', description='A historical resource without review.'))


def test_notices_and_json_ld_do_not_promote_dead_homepages():
    for record in records():
        rendered = pages.make_page(record, 'resource', 'historical')
        assert 'Historical resource</h2>' in rendered
        assert 'Homepage &nearr;' not in rendered
        if record['homepage']:
            assert f'href="{pages.esc(record["homepage"])}"' not in rendered
        for link in historical_record(record)['links']:
            assert f'href="{pages.esc(link["url"])}"' in rendered
            assert pages.esc(link['label']) in rendered
        assert json.loads(pages.make_json_ld(record, 'resource'))['url'] == record['canonicalUrl']


def test_historical_urls_do_not_trigger_requests():
    with mock.patch.object(pages.aiohttp.ClientSession, 'get', side_effect=AssertionError('unexpected network')):
        assert asyncio.run(pages.check_links(records())) == set()


def test_generation_and_next_night_baseline_keep_all_five():
    fixture = membership_tests.PageMembershipBaselineTests()
    fixture.setUp()
    try:
        items = records()
        fixture.write_candidate(items)
        fixture.run_generator(good_urls=[])
        registry = fixture.page_registry()
        assert set(registry['resource']) == set(POLICY)
        assert set(registry['historicalResources']) == set(POLICY)
        fixture.write_baseline(items, registry['resource'])
        baseline = pages.load_verified_page_membership(fixture.baseline)
        assert len(baseline) == 5
        checker = fixture.run_generator('--membership-baseline', str(fixture.baseline))
        checker.assert_not_called()
        assert fixture.page_registry()['resource'] == registry['resource']
        assert pages.cached_homepages_fresh(fixture.candidate, {})
    finally:
        fixture.tearDown()


def test_actual_catalog_records_preserve_evidence_without_linking_dead_websites():
    root = Path(__file__).resolve().parents[1]
    items = json.loads((root / 'data/ontologies.json').read_text())['items']
    reviewed = [item for item in items if historical_record(item)]
    assert len(reviewed) == 5
    for item in reviewed:
        rendered = pages.make_page(item, 'resource', 'historical')
        if item.get('homepage'):
            assert f'href="{pages.esc(item["homepage"])}"' not in rendered
            ld = json.loads(pages.make_json_ld(item, 'resource'))
            assert not any(entry.get('url') == item['homepage'] for entry in ld.get('subjectOf', []))
            for entry in item.get('detailStatements', []):
                if entry['property'].endswith('/P856'):
                    assert entry['statement'] in rendered
