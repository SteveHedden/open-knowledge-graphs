"""The standards expansion must not admit unreviewed descendants."""
import sys
from pathlib import Path
from rdflib import Graph, Namespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data
import semantic_config
import wikidata_classification_audit

STANDARDS = {'Q45941145', 'Q1924747', 'Q18616720', 'Q61782522', 'Q61782519',
             'Q9341450', 'Q1043076', 'Q116671597'}


def test_direct_members_only_and_existing_subclass_behavior_preserved():
    mappings = semantic_config.load_source_mappings()
    wd = Namespace('http://www.wikidata.org/entity/')
    wdt = Namespace('http://www.wikidata.org/prop/direct/')
    graph = Graph()
    for qid in STANDARDS | {'Q324254'}:
        graph.add((wd[qid + 'Direct'], wdt.P31, wd[qid]))
        graph.add((wd[qid + 'Child'], wdt.P279, wd[qid]))
        graph.add((wd[qid + 'Indirect'], wdt.P31, wd[qid + 'Child']))
        query = fetch_data.build_type_base_query(qid, mappings)
        audit_query = wikidata_classification_audit.build_audit_query(qid, mappings)
        assert {row.item for row in graph.query(query)} == {row.item for row in graph.query(audit_query)}
        rows = list(graph.query(query))
        found = {str(row.item) for row in rows}
        assert str(wd[qid + 'Direct']) in found
        assert (str(wd[qid + 'Indirect']) in found) == (qid == 'Q324254')


def test_standards_and_schemas_keep_distinct_types():
    mappings = semantic_config.load_source_mappings()
    selected = {m.source_class_id: m for m in mappings.class_mappings_for(semantic_config.ONTOLOGIES_DATASET) if m.source_class_id in STANDARDS}
    assert set(selected) == STANDARDS
    for qid, mapping in selected.items():
        assert not mapping.include_subclasses
        assert mapping.projection_value == ('Schema' if qid == 'Q1043076' else 'Standard')
