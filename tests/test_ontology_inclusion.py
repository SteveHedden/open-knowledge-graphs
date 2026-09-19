"""OWL/OBO inclusion survives upstream reparenting to ontology document."""
import sys
import unittest
from pathlib import Path
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fetch_data
import semantic_config

WD = Namespace('http://www.wikidata.org/entity/')
WDT = Namespace('http://www.wikidata.org/prop/direct/')

class OntologyInclusionTests(unittest.TestCase):
    def test_reparented_classes_descendants_and_overlapping_results(self):
        mappings = semantic_config.load_source_mappings(ROOT / 'sources.ttl')
        graph = Graph()
        for parent in ('Q62210692', 'Q81314568'):
            graph.add((WD[parent], WDT.P279, WD.Q141436168))
        graph.add((WD.Q2288360, WDT.P31, WD.Q62210692))  # SKOS
        graph.add((WD.Q29377821, WDT.P31, WD.Q62210692))  # SHACL
        graph.add((WD.Q81661512, WDT.P31, WD.Q81314568))  # Human Disease
        graph.add((WD.Q999001, WDT.P279, WD.Q81314568))
        graph.add((WD.Q999002, WDT.P31, WD.Q999001))  # descendant
        graph.add((WD.Q999002, WDT.P31, WD.Q62210692))  # overlap
        graph.add((WD.Q999003, WDT.P31, WD.Q141436168))  # generic document
        rows = []
        for qid in mappings.class_ids_for(semantic_config.ONTOLOGIES_DATASET):
            for row in graph.query(fetch_data.build_type_base_query(qid, mappings)):
                rows.append({'item': {'type': 'uri', 'value': str(row.item)},
                             'matchedTypeQid': {'type': 'literal', 'value': qid}})
        records, _, _ = fetch_data.parse_ontology_rows(
            rows, {}, {}, {}, mappings.class_target_map(semantic_config.ONTOLOGIES_DATASET))
        self.assertEqual(set(records), {str(WD[q]) for q in
                         ('Q2288360', 'Q29377821', 'Q81661512', 'Q999002')})
        self.assertGreater(len(rows), len(records))
        for record in records.values():
            self.assertEqual(record.types, {fetch_data.OKG.Ontology})

if __name__ == '__main__':
    unittest.main()
