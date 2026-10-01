"""Qualifiers remain attached to the correct statement through RDF and HTML."""
import sys
from pathlib import Path
from copy import deepcopy
from rdflib import Graph, URIRef
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import detail_metadata as details
import generate_pages as pages
import fetch_data as fetch


def binding(value, kind='uri'):
    return {'type': kind, 'value': value}


def rows():
    base = {'item': binding('http://www.wikidata.org/entity/Q123'),
            'statement': binding('http://www.wikidata.org/entity/statement/Q123-license'),
            'property': binding('http://www.wikidata.org/entity/P275'),
            'propertyLabel': binding('copyright license', 'literal'),
            'value': binding('http://www.wikidata.org/entity/Q334661'),
            'valueLabel': binding('Apache License 2.0', 'literal'),
            'rank': binding(details.WB + 'NormalRank'),
            'qualifier': binding('http://www.wikidata.org/entity/P548'),
            'qualifierLabel': binding('version type', 'literal'),
            'qualifierValue': binding('6.0', 'literal')}
    other = deepcopy(base)
    other['statement'] = binding('http://www.wikidata.org/entity/statement/Q123-other')
    other['valueLabel'] = binding('CC BY 4.0', 'literal')
    other['value'] = binding('http://www.wikidata.org/entity/Q20007257')
    for key in ['qualifier', 'qualifierLabel', 'qualifierValue']:
        del other[key]
    return [base, other, base]


def test_round_trip_scopes_multiple_licenses_and_deduplicates():
    entries = details.parse(rows())['http://www.wikidata.org/entity/Q123']
    assert len(entries) == 2
    graph = Graph(); subject = URIRef('https://openknowledgegraphs.com/resource/example/')
    details.add_to_graph(graph, subject, entries)
    restored = Graph().parse(data=graph.serialize(format='turtle'), format='turtle')
    assert details.projection(restored, subject) == entries
    html = details.render(entries)
    assert 'Apache License 2.0' in html and 'CC BY 4.0' in html
    assert html.count('version type: 6.0') == 1
    assert entries[1]['qualifiers'] == []
    assert details.parse(list(reversed(rows()))) == details.parse(rows())


def test_deprecated_excluded_preferred_does_not_erase_scoped_normal_statement():
    data = rows(); deprecated = deepcopy(data[0]); deprecated['rank'] = binding(details.WB + 'DeprecatedRank')
    deprecated['statement'] = binding('http://www.wikidata.org/entity/statement/Q123-old')
    data[1]['rank'] = binding(details.WB + 'PreferredRank')
    entries = details.parse(data + [deprecated])['http://www.wikidata.org/entity/Q123']
    assert len(entries) == 2
    assert 'Preferred statement' in details.render(entries)


def test_page_fallback_and_scoped_json_ld():
    item = {'title': 'Example', 'description': 'A reusable ontology.', 'licenses': ['Apache 2.0', 'CC BY 4.0'],
            'canonicalUrl': 'https://openknowledgegraphs.com/resource/example/',
            'homepage': 'https://example.org', 'wikidataId': 'https://www.wikidata.org/wiki/Q123'}
    html = pages.make_page(item, 'resource', 'example')
    assert 'Apache 2.0, CC BY 4.0' in html
    item['detailStatements'] = details.parse(rows())['http://www.wikidata.org/entity/Q123']
    assert 'license' not in pages.make_json_ld(item, 'resource')
    html = pages.make_page(item, 'resource', 'example')
    assert html.count('<h2>Licenses</h2>') == 1
    assert 'version type: 6.0' in html


def test_identifier_relationship_and_html_safety():
    data = rows()[:1]
    data[0].update(property=binding('http://www.wikidata.org/entity/P8605'),
                   propertyLabel=binding('Catalog <ID>', 'literal'), value=binding('<bad>', 'literal'))
    entries = details.parse(data)['http://www.wikidata.org/entity/Q123']
    entries[0]['label'] = '<script>alert(1)</script>'
    html = details.render(entries)
    assert '<script>' not in html and 'Catalog &lt;ID&gt;' in html
    entries[0]['property'] = 'http://www.wikidata.org/entity/P155'
    assert '<h2>Predecessors</h2>' in details.render(entries)
    entries[0]['value'] = binding('javascript:alert(1)')
    assert 'href="javascript:' not in details.render(entries)


def test_query_is_bounded_and_requests_scope_and_identifier_types():
    query = details.query(['Q123', 'Q456'])
    assert 'VALUES ?item { wd:Q123 wd:Q456 }' in query
    for token in ['wikibase:ExternalId', 'wd:P155', 'wd:P156', 'wd:P6216', 'wikibase:timePrecision', 'DeprecatedRank']:
        assert token in query


def test_both_imports_round_trip_without_changing_flat_table_fields():
    import semantic_config
    import validate_catalog
    mappings = semantic_config.load_source_mappings()
    qid = 'http://www.wikidata.org/entity/Q123'
    for software in (False, True):
        record = fetch.ResourceRecord(qid, 'Example', description='A reusable ontology.',
                                      types={fetch.OKG.Software if software else fetch.OKG.Ontology},
                                      licenses={'http://www.wikidata.org/entity/Q334661'},
                                      detail_statements=details.parse(rows())[qid])
        graph = fetch.build_graph({qid: record}, {'http://www.wikidata.org/entity/Q334661': 'Apache 2.0'},
                                  {}, set(), {}, software, dataset_path='software' if software else 'resource',
                                  slug_registry={'Q123': 'example'})
        item = fetch.extract_items_from_graph(graph, record.types, software, mappings.projection_type_labels)[0]
        assert item['licenses'] == ['Apache 2.0']
        assert len(item['detailStatements']) == 2
        report = validate_catalog.ValidationReport()
        validate_catalog.validate_public_iris([graph], {'catalog': {'items': [item]}}, report)
        assert not report.errors


def test_date_precision_and_calendar_are_not_discarded():
    data = rows()[:1]
    data[0].update(qualifierValue=binding('2020-01-01T00:00:00Z', 'literal'),
                   precision=binding('9', 'literal'), calendar=binding('http://www.wikidata.org/entity/Q1985727'))
    entry = details.parse(data)['http://www.wikidata.org/entity/Q123'][0]
    assert details.display_value(entry['qualifiers'][0]) == '2020'
    entry['qualifiers'][0]['calendar'] = 'http://www.wikidata.org/entity/Q1985786'
    assert 'calendar or precision not supported' in details.display_value(entry['qualifiers'][0])
