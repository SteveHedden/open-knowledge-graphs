"""Supplementary Wikidata links survive import and appear only on detail pages."""
import sys
from pathlib import Path

from rdflib import URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data as fetch
import generate_pages as pages
import semantic_config
import validate_catalog


def test_both_catalogs_preserve_multiple_links_through_rdf_json_and_html():
    mappings = semantic_config.load_source_mappings()
    qid = 'http://www.wikidata.org/entity/Q123'
    docs = ['https://example.org/docs', 'https://example.org/paper?a=1&b=2']
    downloads = ['https://example.org/ontology.ttl', 'https://example.org/archive.zip']
    binding = lambda value: {'type': 'uri', 'value': value}
    rows = [dict(item=binding(qid), matchedTypeQid=binding('Q324254'),
                 officialWebsite=binding('https://example.org'),
                 sourceCodeRepo=binding('https://github.com/example/resource'),
                 documentation=binding(doc), downloads=binding(download))
            for doc in docs for download in downloads]
    for software in (False, True):
        args = (rows + rows[:1], {qid: 'Example'}, {qid: 'A reusable ontology for testing links.'}, {})
        records = (fetch.parse_software_rows(*args) if software else
                   fetch.parse_ontology_rows(*args, {'Q324254': fetch.OKG.Ontology}))[0]
        dataset = 'software' if software else 'resource'
        graph = fetch.build_graph(records, {}, {}, set(), {}, software,
                                  dataset_path=dataset, slug_registry={'Q123': 'example'})
        types = {fetch.OKG.Software} if software else {fetch.OKG.Ontology}
        item = fetch.extract_items_from_graph(graph, types, software, mappings.projection_type_labels)[0]
        assert item['documentation'] == sorted(docs)
        assert item['downloads'] == sorted(downloads)
        assert item['homepage'] == 'https://example.org'
        assert item['sourceRepo'] == 'https://github.com/example/resource'
        html = pages.make_page(item, dataset, 'example')
        for link in docs + downloads:
            assert 'href="' + pages.esc(link) + '"' in html
        assert html.count('>Documentation</h2>') == 1
        assert html.count('>Downloads / full text</h2>') == 1
        report = validate_catalog.ValidationReport()
        validate_catalog.validate_public_iris([graph], {'catalog': {'items': [item]}}, report)
        assert not report.errors


def test_queries_request_declared_link_properties():
    mappings = semantic_config.load_source_mappings()
    for query in [fetch.build_type_base_query('Q324254', mappings),
                  fetch.build_inclusion_base_query(('Q123',), mappings),
                  fetch.build_software_base_query(('Q123',), mappings)]:
        assert 'wdt:P973 ?documentation' in query
        assert 'wdt:P953 ?downloads' in query


def test_optional_sections_are_safe_and_do_not_change_page_eligibility():
    assert pages.render_resource_links({}) == ''
    item = {'title': 'Example', 'description': 'A sufficiently descriptive ontology.',
            'documentation': ['javascript:alert(1)', 'https://[bad', 'https://example.org/?a="quoted"&b=2'],
            'downloads': ['data:text/html,unsafe', 'https://example.org/data.zip']}
    html = pages.render_resource_links(item)
    assert 'javascript:' not in html and 'data:text/html' not in html and 'https://[bad' not in html
    assert '&quot;quoted&quot;&amp;b=2' in html
    assert not pages.passes_content_filter(item)  # Links do not substitute for a homepage.


def test_catalog_validation_rejects_non_array_or_relative_link_values():
    for value in ('https://example.org/docs', ['relative/path'], [None]):
        report = validate_catalog.ValidationReport()
        validate_catalog.validate_public_iris([], {'catalog': {'documentation': value}}, report)
        assert report.has_error('json-contract')
