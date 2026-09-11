"""Emply listings contain JSON inside a JavaScript string literal."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import first_party_sources as fps


@pytest.fixture(scope='module')
def source():
    return fps.load_first_party_sources()['first-party-danish-bibliographic-centre']


def listing(rows, count=None):
    # Encode JSON as a JS string, as Emply's JSON.parse('...') embedding does.
    encoded = json.dumps(json.dumps(rows, ensure_ascii=False), ensure_ascii=False)[1:-1]
    encoded = encoded.replace("'", r"\'")
    return "proceedBatch({ vacancies : JSON.parse('" + encoded + "'), count : " + str(len(rows) if count is None else count) + "});"


def test_nested_html_quotes_unicode_backslashes_and_apostrophes(source):
    rows = [{'shortId': 'example', 'title': 'Bibliotekar – København 📚',
             'description': '<a href="https://example.org/">Danish library</a>\nReader\'s path C:\\new\\texts; literal \\u0026'}]
    assert fps._emply_listing(listing(rows), source) == rows


def test_realistic_emply_html_unicode_escaping(source):
    embedded = r'''[{\"shortId\":\"example\",\"description\":\"\\u003ca href=\\\"https://example.org/\\\"\\u003eLæs mere\\u003c/a\\u003e\"}]'''
    payload = "proceedBatch({ vacancies : JSON.parse('" + embedded + "'), count : 1});"
    assert fps._emply_listing(payload, source)[0]['description'] == '<a href="https://example.org/">Læs mere</a>'


@pytest.mark.parametrize('raw', [r'[{\"title\":\"bad\q\"}]', r'[{\"title\":\"bad\xZZ\"}]', r'[{invalid}]'])
def test_malformed_embedded_json_is_rejected(source, raw):
    with pytest.raises(fps.FirstPartySourceError, match='malformed'):
        fps._emply_listing("proceedBatch({ vacancies : JSON.parse('" + raw + "'), count : 1});", source)


def test_empty_talent_pool_and_partial_batch_rules(source):
    assert fps._emply_listing(listing([]), source) == []
    assert fps._emply_listing(listing([{'talentPool': True}]), source) == []
    with pytest.raises(fps.FirstPartySourceError, match='partial'):
        fps._emply_listing(listing([{'shortId': 'example'}], count=2), source)
    with pytest.raises(fps.FirstPartySourceError, match='one embedded'):
        fps._emply_listing(listing([]) + listing([]), source)
