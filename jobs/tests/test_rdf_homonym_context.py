"""Observed Anduril collision across admission and page-backed mention matching."""
import copy
import json
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from classifier import find_evidence, load_match_terms, classify
from catalog_mentions import build_match_index, load_policy, catalog_mentions

@pytest.fixture(scope='module')
def matchers():
    fixture = json.loads((ROOT / 'tests/fixtures/catalog-mentions.json').read_text())
    index = build_match_index(fixture['ontologies'], fixture['software'], fixture['pageQids'],
                              load_policy(ROOT / 'catalog-mention-policy.json'))
    return load_match_terms(ROOT / 'vocabularies/kg-jobs.ttl'), index

@pytest.mark.parametrize('record', [
    {'title': 'Software Engineer, Robotics Data Foundation (Cloud)',
     'description': "...ABOUT THE TEAM The Robotics Data Foundation (RDF) team builds Anduril's vehicle telemetry backbone, from onboard systems to cloud."},
    {'description': 'The RDF (Robotics Data Foundation) team builds telemetry.'},
    {'description': 'The Robotics\nData  Foundation ( RDF ) team builds telemetry. The RDF team stores telemetry.'},
    {'title': 'Robotics Data Foundation engineer', 'description': 'Build the RDF telemetry platform.'},
    {'description': 'Join robotics data foundation (RDF).', 'qualifications': 'Experience on the RDF team.'},
])
def test_team_acronym_does_not_supply_kg_evidence(record, matchers):
    terms, index = matchers
    before = copy.deepcopy(record)
    evidence = find_evidence(record, terms)
    assert not any(e.concept_label == 'RDF' and e.strength == 'strong' for e in evidence)
    assert not any(m['qid'] == 'Q54872' for m in catalog_mentions(record, index))
    assert classify(evidence) == 'not_match'
    assert record == before

@pytest.mark.parametrize('description', [
    'Build RDF triples and query them with SPARQL.',
    'Use Resource Description Framework (RDF).',
    'Use RDF (Resource Description Framework).',
])
def test_explicit_semantic_rdf_survives_in_mixed_record(description, matchers):
    terms, index = matchers
    record = {'title': 'Robotics Data Foundation engineer', 'description': description}
    assert any(e.concept_label == 'RDF' for e in find_evidence(record, terms))
    assert any(m['qid'] == 'Q54872' for m in catalog_mentions(record, index))

@pytest.mark.parametrize('description', ['Experience with RDF.', 'RDF and SPARQL engineer.',
                                         'RDF Schema with RDFox.'])
def test_jobs_without_robotics_expansion_are_unchanged(description, matchers):
    terms, index = matchers
    record = {'description': description}
    assert any(e.concept_label == 'RDF' for e in find_evidence(record, terms))
    assert catalog_mentions(record, index)


def test_long_team_name_does_not_link_foundation_software(matchers):
    fixture = json.loads((ROOT / 'tests/fixtures/catalog-mentions.json').read_text())
    fixture['software']['items'].append({'title': 'Foundation',
        'wikidataId': 'https://www.wikidata.org/wiki/Q124653389', 'aliases': []})
    fixture['pageQids']['software']['Q124653389'] = 'foundation'
    index = build_match_index(fixture['ontologies'], fixture['software'], fixture['pageQids'],
                              load_policy(ROOT / 'catalog-mention-policy.json'))
    record = {'description': 'The Robotics Data Foundation team builds telemetry.'}
    assert not any(m['qid'] == 'Q124653389' for m in catalog_mentions(record, index))
    record['description'] += ' Experience using Foundation software.'
    assert any(m['qid'] == 'Q124653389' for m in catalog_mentions(record, index))


def test_qualification_preview_preserves_record_identity_and_source_fields(matchers):
    from live_records import classify_records
    record = {'id': 'anduril-example', 'active': True, 'title': 'Robotics Data Foundation',
              'description': 'The RDF team builds telemetry.', 'sourceUrl': 'https://example.org/job'}
    result = classify_records([record], matchers[0])
    assert len(result) == 1
    assert all(result[0][key] == value for key, value in record.items())
    assert result[0]['classification'] == 'not_match'

@pytest.mark.parametrize('record', [
    {'description': 'Robotics Data Foundation (RDF) team. Required skills: RDF and SPARQL.'},
    {'description': 'RDF (Robotics Data Foundation) team uses RDF with SPARQL.'},
    {'description': 'Use RDF with SPARQL. Join the Robotics Data Foundation (RDF) team.'},
    {'title': 'RDF and SPARQL engineer', 'description': 'Join Robotics Data Foundation (RDF).'},
    {'title': 'Robotics Data Foundation (RDF)', 'description': 'Experience with RDF and SPARQL.'},
    {'title': 'RDF Engineer', 'description': 'Robotics Data Foundation team builds SPARQL endpoints.'},
    {'title': 'Knowledge graph engineer', 'description': 'Robotics Data Foundation team.',
     'qualifications': 'Experience with RDF.'},
    {'title': 'Robotics Data Foundation', 'qualifications': 'RDF and SPARQL experience.'},
])
def test_both_senses_preserve_independently_supported_rdf(record, matchers):
    from rdf_context import analyze_rdf
    terms, index = matchers
    before = copy.deepcopy(record)
    decisions = analyze_rdf(record)
    assert any(d['sense'] == 'semantic' for d in decisions)
    assert any(e.concept_label == 'RDF' and e.strength == 'strong'
               for e in find_evidence(record, terms))
    # Catalog links use title/description only, even when qualifications support admission.
    if any(d['sense'] == 'semantic' and d['field'] in ('title', 'description') for d in decisions):
        assert any(m['qid'] == 'Q54872' for m in catalog_mentions(record, index))
    assert record == before


def test_explicit_robotics_occurrence_is_not_reinterpreted_by_neighboring_sparql(matchers):
    from rdf_context import analyze_rdf
    record = {'description': 'Robotics Data Foundation (RDF) works with SPARQL.'}
    assert [d['sense'] for d in analyze_rdf(record)] == ['robotics']
    assert not any(e.concept_label == 'RDF' for e in find_evidence(record, matchers[0]))
    assert not any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))


def test_unresolved_occurrence_is_distinct_from_both_supported_senses(matchers):
    from rdf_context import analyze_rdf
    record = {'description': 'Robotics Data Foundation (RDF). RDF is mentioned. Use RDF with SPARQL.'}
    assert [d['sense'] for d in analyze_rdf(record)] == ['robotics', 'ambiguous', 'semantic']
    rdf_evidence = [e for e in find_evidence(record, matchers[0]) if e.concept_label == 'RDF']
    assert sorted(e.strength for e in rdf_evidence) == ['contextual', 'strong']
    assert any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))


def test_cross_field_semantic_context_does_not_reinterpret_team_reference(matchers):
    from rdf_context import analyze_rdf
    record = {'title': 'SPARQL engineer', 'description': 'Robotics Data Foundation (RDF). The RDF team builds telemetry.'}
    assert [d['sense'] for d in analyze_rdf(record)] == ['robotics', 'robotics']
    assert not any(e.concept_label == 'RDF' for e in find_evidence(record, matchers[0]))


def test_separate_bullet_does_not_resolve_an_ambiguous_occurrence(matchers):
    from rdf_context import analyze_rdf
    record = {'description': 'Robotics Data Foundation (RDF)\nRDF mentioned\nSPARQL skills'}
    assert [d['sense'] for d in analyze_rdf(record)] == ['robotics', 'ambiguous']
    rdf = [e for e in find_evidence(record, matchers[0]) if e.concept_label == 'RDF']
    assert len(rdf) == 1 and rdf[0].strength == 'contextual'
    assert not any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))


@pytest.mark.parametrize('semantic_text', [
    'Use RDF/XML and Turtle',
    'Publish semantic data using RDF.',
])
@pytest.mark.parametrize('layout', ['same-field', 'semantic-description', 'semantic-title'])
def test_reported_serialization_and_semantic_data_survive_mixed_meanings(
    semantic_text, layout, matchers
):
    from rdf_context import analyze_rdf
    robotics = 'Robotics Data Foundation (RDF) team.'
    if layout == 'same-field':
        record = {'description': robotics + ' ' + semantic_text}
    elif layout == 'semantic-description':
        record = {'title': robotics, 'description': semantic_text}
    else:
        record = {'title': semantic_text, 'description': robotics}
    before = copy.deepcopy(record)
    decisions = analyze_rdf(record)
    assert sorted(d['sense'] for d in decisions) == ['robotics', 'semantic']
    evidence = [e for e in find_evidence(record, matchers[0]) if e.concept_label == 'RDF']
    assert len(evidence) == 1 and evidence[0].strength == 'strong'
    assert classify(evidence) == 'qualified'
    assert any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))
    assert record == before


@pytest.mark.parametrize('semantic_text', [
    'Use RDF / XML and Turtle.',
    'Publish semantic\n data using RDF.',
])
def test_serialization_and_semantic_data_formatting_variants(semantic_text, matchers):
    record = {'title': 'Robotics Data Foundation (RDF)', 'description': semantic_text}
    assert any(e.concept_label == 'RDF' and e.strength == 'strong'
               for e in find_evidence(record, matchers[0]))
    assert any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))


@pytest.mark.parametrize('description', [
    'Robotics Data Foundation (RDF) team builds telemetry.',
    'Robotics Data Foundation (RDF). The RDF team publishes telemetry.',
    'RDF (Robotics Data Foundation) team uses XML for telemetry.',
])
def test_robotics_only_stays_excluded_after_semantic_marker_extension(description, matchers):
    record = {'description': description}
    evidence = find_evidence(record, matchers[0])
    assert not any(e.concept_label == 'RDF' for e in evidence)
    assert classify(evidence) == 'not_match'
    assert not any(m['qid'] == 'Q54872' for m in catalog_mentions(record, matchers[1]))
